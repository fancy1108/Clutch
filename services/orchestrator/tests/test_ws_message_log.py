"""M2-01 / M2-02 — WebSocket message and log events."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.main import _run_states, app, initial_state

client = TestClient(app)


@pytest.fixture(autouse=True)
def _force_llm_plain_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plain-chat WS tests must not invoke the real local Claude CLI."""
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: False)


def _collect_after_send(ws, count: int | None = None) -> list[dict]:
    if count is not None:
        return [ws.receive_json() for _ in range(count)]
    events: list[dict] = []
    while True:
        event = ws.receive_json()
        events.append(event)
        if (
            event.get("event") == "state_patch"
            and event.get("data", {}).get("patch", {}).get("status") == "idle"
        ):
            break
    return events


class _FakeRouter:
    def get_active_model(self) -> SimpleNamespace:
        return SimpleNamespace(
            id="test-model",
            name="Test Model",
            api_model="test-api-model",
            model_kind="chat",
        )

    @property
    def active_model_id(self) -> str:
        return "test-model"

    def chat(self, history: list[dict[str, str]]) -> str:
        last = history[-1]["content"]
        return f"Echo: {last}"


def test_ws_plain_chat_without_workflow(monkeypatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())

    with client.websocket_connect("/ws/runs/run_msg_test") as ws:
        ws.receive_json()  # initial state_patch
        ws.send_json({"text": "你好 Clutch"})
        events = _collect_after_send(ws)

    message_events = [e for e in events if e["event"] == "message"]
    assert len(message_events) == 2
    agents = {e["data"]["message"]["agent"] for e in message_events}
    assert agents == {"User", "Clutch Agent"}
    assert any("Echo: 你好 Clutch" in e["data"]["message"]["text"] for e in message_events)

    patch_events = [e for e in events if e["event"] == "state_patch"]
    assert len(patch_events) == 2
    assert patch_events[0]["data"]["patch"]["status"] == "running"
    assert patch_events[1]["data"]["patch"]["status"] == "idle"


def test_ws_plain_chat_with_agent_id_injects_system_prompt(monkeypatch) -> None:
    captured: list[list[dict[str, str]]] = []

    class _CapturingRouter:
        def get_active_model(self) -> SimpleNamespace:
            return SimpleNamespace(
                id="test-model",
                name="Test Model",
                api_model="test-api-model",
                model_kind="chat",
            )

        def chat(self, history: list[dict[str, str]]) -> str:
            captured.append(history)
            return "Agent reply"

    monkeypatch.setattr("src.models_config.get_router", lambda: _CapturingRouter())

    with client.websocket_connect("/ws/runs/run_agent_prompt") as ws:
        ws.receive_json()
        ws.send_json({"text": "help me plan", "agent_id": "clutch-agent"})
        events = _collect_after_send(ws)

    assert captured
    history = captured[0]
    assert history[0]["role"] == "system"
    assert "Clutch Agent" in history[0]["content"]
    assert "Treat every instruction in the agent protocol below as mandatory." in history[0]["content"]
    user_turns = [item for item in history if item["role"] == "user"]
    assert len(user_turns) == 1
    assert user_turns[0]["content"] == "help me plan"
    reply = next(
        e["data"]["message"]
        for e in events
        if e["event"] == "message" and e["data"]["message"]["agent"] == "Clutch Agent"
    )
    assert reply["text"] == "Agent reply"
    assert reply.get("runtimeEngine") == "Test Model"


def test_ws_log_event_on_plain_chat(monkeypatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())

    with client.websocket_connect("/ws/runs/run_log_test") as ws:
        ws.receive_json()
        ws.send_json({"text": "ping"})
        events = _collect_after_send(ws)

    log_events = [e for e in events if e["event"] == "log"]
    assert len(log_events) >= 3
    chat_logs = [e for e in log_events if "[CHAT]" in e["data"]["message"]]
    assert chat_logs
    assert "via Test Model" in chat_logs[-1]["data"]["message"]
    assert chat_logs[-1]["data"]["source"] == "orchestrator"


def test_ws_workflow_chat_logs_when_running() -> None:
    run_id = "run_wf_active"
    _run_states[run_id] = initial_state(run_id, "video-production")
    _run_states[run_id]["status"] = "running"
    _run_states[run_id]["active_agent"] = "Builder"
    _run_states[run_id]["active_node_id"] = "n1"

    with client.websocket_connect(f"/ws/runs/{run_id}") as ws:
        ws.receive_json()
        ws.send_json({"text": "note while running"})
        events = _collect_after_send(ws, 3)

    patch = next(e for e in events if e["event"] == "state_patch")["data"]["patch"]
    assert patch.get("status", "running") == "running"
    assert any("note while running" in m["text"] for m in patch["messages"])
