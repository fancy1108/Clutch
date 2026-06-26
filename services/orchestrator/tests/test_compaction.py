"""Tests for context message compaction and archiving."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.state import ClutchState, initial_state
from src.compaction import should_compact, compact_run_messages, _estimate_tokens


@pytest.fixture(autouse=True)
def _force_llm_plain_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plain-chat WS tests must not invoke the real local Claude CLI."""
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: False)


def test_estimate_tokens() -> None:
    assert _estimate_tokens("hello world") == 2
    assert _estimate_tokens("") == 1
    assert _estimate_tokens("   ") == 1
    assert _estimate_tokens("one two three four") == 4


def test_should_compact() -> None:
    state = initial_state("run_test")
    # <= 5 messages, should always return False
    state["messages"] = [{"agent": "User", "text": "hello"}] * 5
    state["session_tokens"] = 20000
    assert not should_compact(state)

    # > 5 messages, session_tokens <= threshold (default 15000)
    state["messages"] = [{"agent": "User", "text": "hello"}] * 6
    state["session_tokens"] = 14999
    assert not should_compact(state)

    # > 5 messages, session_tokens > threshold
    state["session_tokens"] = 15001
    assert should_compact(state)


def test_should_compact_with_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    state = initial_state("run_test")
    state["messages"] = [{"agent": "User", "text": "hello"}] * 6
    state["session_tokens"] = 5000

    # default is 15000, so 5000 shouldn't compact
    assert not should_compact(state)

    # Override threshold to 4000
    monkeypatch.setenv("CLUTCH_COMPACT_THRESHOLD", "4000")
    assert should_compact(state)

    # Override threshold to invalid value, should fallback to default 15000
    monkeypatch.setenv("CLUTCH_COMPACT_THRESHOLD", "invalid")
    assert not should_compact(state)


@pytest.mark.asyncio
async def test_compact_run_messages_too_short() -> None:
    state = initial_state("run_test")
    state["messages"] = [{"agent": "User", "text": "hello"}] * 5
    state["session_tokens"] = 20000

    new_state = await compact_run_messages("run_test", state)
    # returned unchanged
    assert len(new_state["messages"]) == 5
    assert new_state["session_tokens"] == 20000


@pytest.mark.asyncio
async def test_compact_run_messages_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Set up active workspace mock so that get_archive_dir uses workspace path
    workspace_dir = tmp_path / "my_project"
    workspace_dir.mkdir()
    
    def mock_get_workspace():
        return {
            "id": "ws_123",
            "workspace_path": str(workspace_dir),
            "name": "my_project"
        }
    
    monkeypatch.setattr("src.workspace.get_workspace", mock_get_workspace)

    # Set up initial state with 8 messages
    state = initial_state("run_test")
    state["messages"] = [
        {"id": "msg_0", "agent": "System", "text": "Initial task instructions"},
        {"id": "msg_1", "agent": "User", "text": "Message 1"},
        {"id": "msg_2", "agent": "The Artist", "text": "Message 2"},
        {"id": "msg_3", "agent": "User", "text": "Message 3"},
        {"id": "msg_4", "agent": "User", "text": "Message 4"},
        {"id": "msg_5", "agent": "The Artist", "text": "Message 5"},
        {"id": "msg_6", "agent": "User", "text": "Message 6"},
        {"id": "msg_7", "agent": "The Artist", "text": "Message 7"},
    ]
    state["session_tokens"] = 20000

    # Mock router.chat to return a specific digest
    class FakeRouter:
        def chat(self, messages: list[dict[str, str]], model_id: str | None = None) -> dict[str, str]:
            # Verify the structure passed to LLM
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert "Summarize the following AI agent conversation" in messages[0]["content"]
            assert "User: Message 1" in messages[1]["content"]
            assert "The Artist: Message 2" in messages[1]["content"]
            assert "User: Message 3" in messages[1]["content"]
            # messages[-4:] are NOT summarized: User 4, Artist 5, User 6, Artist 7
            assert "Message 4" not in messages[1]["content"]
            return {"content": "LLM digest summary text here"}

    monkeypatch.setattr("src.models_config.get_router", lambda: FakeRouter())

    # Perform compaction
    new_state = await compact_run_messages("run_test", state)

    # Verify state updates
    # new message count: first_message (1) + digest_msg (1) + last_messages (4) = 6 messages
    assert len(new_state["messages"]) == 6
    assert new_state["messages"][0]["id"] == "msg_0"
    
    digest_msg = new_state["messages"][1]
    assert digest_msg["agent"] == "System"
    assert "LLM digest summary text here" in digest_msg["text"]
    assert "runs/archive/run_test.jsonl" in digest_msg["text"]
    assert "上下文已压缩" in digest_msg["text"]
    assert digest_msg["badge_text"] == "上下文压缩摘要"
    assert digest_msg["badgeText"] == "上下文压缩摘要"


    # Last 4 messages preserved: msg_4, msg_5, msg_6, msg_7
    assert new_state["messages"][2]["id"] == "msg_4"
    assert new_state["messages"][3]["id"] == "msg_5"
    assert new_state["messages"][4]["id"] == "msg_6"
    assert new_state["messages"][5]["id"] == "msg_7"

    # Verify token recount logic
    assert new_state["token_input"] == 4
    assert new_state["session_tokens"] == new_state["token_input"] + new_state["token_output"]
    assert new_state["session_cost_usd"] == round(new_state["session_tokens"] * 0.00000015, 6)

    # Verify archive file contents
    archive_file = workspace_dir / "runs" / "archive" / "run_test.jsonl"
    assert archive_file.is_file()
    lines = archive_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 8
    first_archived = json.loads(lines[0])
    assert first_archived["id"] == "msg_0"
    last_archived = json.loads(lines[-1])
    assert last_archived["id"] == "msg_7"


@pytest.mark.asyncio
async def test_compact_run_messages_fallback_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    # Set up initial state with 8 messages
    state = initial_state("run_test_fallback")
    state["messages"] = [
        {"id": "msg_0", "agent": "System", "text": "Initial task instructions"},
        {"id": "msg_1", "agent": "User", "text": "Message 1"},
        {"id": "msg_2", "agent": "The Artist", "text": "Message 2"},
        {"id": "msg_3", "agent": "User", "text": "Message 3"},
        {"id": "msg_4", "agent": "User", "text": "Message 4"},
        {"id": "msg_5", "agent": "The Artist", "text": "Message 5"},
        {"id": "msg_6", "agent": "User", "text": "Message 6"},
        {"id": "msg_7", "agent": "The Artist", "text": "Message 7"},
    ]
    state["session_tokens"] = 20000

    # Mock router.chat to raise Exception
    class BrokenRouter:
        def chat(self, messages, model_id=None):
            raise RuntimeError("API failure")

    monkeypatch.setattr("src.models_config.get_router", lambda: BrokenRouter())

    # Perform compaction
    new_state = await compact_run_messages("run_test_fallback", state)

    # Verify compaction still completes using fallback message
    assert len(new_state["messages"]) == 6
    digest_msg = new_state["messages"][1]
    assert digest_msg["agent"] == "System"
    assert "由于 Token 消耗达到阈值，历史对话已折叠" in digest_msg["text"]
    assert "User" in digest_msg["text"]
    assert "The Artist" in digest_msg["text"]


def test_ws_plain_chat_compaction_integration(monkeypatch) -> None:
    from src.main import _run_states, app

    # 1. Setup mock router that returns an echo response or summary
    class EchoRouter:
        def get_active_model(self):
            from types import SimpleNamespace
            return SimpleNamespace(
                id="test-model",
                name="Test Model",
                api_model="test-api-model",
                model_kind="chat",
            )

        @property
        def active_model_id(self) -> str:
            return "test-model"

        def chat(self, messages: list[dict[str, str]], model_id: str | None = None) -> str:
            # If system message is present, it's the compaction request!
            if messages[0]["role"] == "system" and "Summarize" in messages[0]["content"]:
                return "Mocked summary of conversation"
            # Otherwise it's regular chat
            return "Mocked reply"

    monkeypatch.setattr("src.models_config.get_router", lambda: EchoRouter())
    monkeypatch.setenv("CLUTCH_COMPACT_THRESHOLD", "10")  # threshold extremely low

    # 2. Setup state with 6 messages
    # This ensures len(messages) > 5 and token counts will trigger compaction
    run_id = "run_compaction_int_test"
    state = initial_state(run_id)
    state["messages"] = [
        {"id": "msg_0", "agent": "System", "text": "Start instruction"},
        {"id": "msg_1", "agent": "User", "text": "Message one"},
        {"id": "msg_2", "agent": "Clutch Agent", "text": "Message two"},
        {"id": "msg_3", "agent": "User", "text": "Message three"},
        {"id": "msg_4", "agent": "Clutch Agent", "text": "Message four"},
        {"id": "msg_5", "agent": "User", "text": "Message five"},
    ]
    state["token_input"] = 50
    state["token_output"] = 50
    state["session_tokens"] = 100
    _run_states[run_id] = state

    client = TestClient(app)
    with client.websocket_connect(f"/ws/runs/{run_id}") as ws:
        ws.receive_json()  # initial state_patch
        ws.send_json({"text": "User message triggering reply"})

        # Collect events until status is idle
        events = []
        while True:
            event = ws.receive_json()
            events.append(event)
            if (
                event.get("event") == "state_patch"
                and event.get("data", {}).get("patch", {}).get("status") == "idle"
            ):
                break

    # Find the state patch where compaction was applied
    compaction_patches = [
        e["data"]["patch"]
        for e in events
        if e["event"] == "state_patch" and "messages" in e["data"].get("patch", {})
    ]

    # The final state should have fewer messages, including a compaction digest.
    final_messages = compaction_patches[-1]["messages"]

    # We expect messages length to be 6 (messages[0], digest_msg, messages[-4:])
    assert len(final_messages) == 6
    assert final_messages[0]["text"] == "Start instruction"
    assert "Mocked summary of conversation" in final_messages[1]["text"]
    assert "上下文已压缩" in final_messages[1]["text"]


