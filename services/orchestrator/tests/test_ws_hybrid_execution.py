"""WebSocket hybrid execution details on plain chat replies."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.engine_router import EngineResult
from src.main import app

client = TestClient(app)


def _collect_after_send(ws) -> list[dict]:
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


@pytest.fixture
def hybrid_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    agent_record = {
        "id": "agent-claude-test",
        "name": "Claude test Session",
        "agentType": "claude-cli",
        "aiEngine": "Claude Code (Local CLI)",
        "markdownDoc": "## Protocol\n- Task validation",
    }
    monkeypatch.setattr(
        "src.engine_router.list_agents",
        lambda: [agent_record],
    )
    monkeypatch.setattr("src.agent_storage.get_agent_by_id", lambda _agent_id: agent_record)
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    workspace = {
        "id": "ws_hybrid_test",
        "name": "penpot",
        "workspace_path": "/tmp/clutch-hybrid-ws",
    }
    monkeypatch.setattr("src.workspace.get_workspace", lambda: workspace)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: workspace)
    monkeypatch.setattr("src.run_state_store.save_run_state", lambda _state: None)

    def fake_hybrid(**_kwargs: object) -> EngineResult:
        return EngineResult(
            engine="Claude CLI (Hybrid)",
            output="ENTJ 很果断。",
            logs=["[HYBRID] ok"],
            cli_session_id="sess-ws-1",
            raw_output="CLUTCH_P='hi'; claude -p ...",
            output_events=[
                {"type": "shell_echo", "visible": False, "content": "claude -p \"$CLUTCH_P\""},
                {"type": "system_prompt", "visible": False, "content": "You are Claude test Session"},
                {"type": "boundary_marker", "visible": False, "content": "__CLUTCH_DONE_x__"},
                {"type": "assistant", "visible": True, "content": "ENTJ 很果断。"},
            ],
        )

    monkeypatch.setattr("src.engine_router._route_claude_hybrid", fake_hybrid)
    monkeypatch.setattr("src.engine_router.route_engine", fake_hybrid)


def test_ws_hybrid_reply_includes_execution_details(hybrid_agent: None) -> None:
    with client.websocket_connect("/ws/runs/run_hybrid_exec") as ws:
        ws.receive_json()
        ws.send_json({"text": "你觉得 entj 怎么样", "agent_id": "agent-claude-test"})
        events = _collect_after_send(ws)

    hybrid_events = [event for event in events if event.get("event") == "hybrid_execution"]
    assert len(hybrid_events) == 1
    payload = hybrid_events[0]["data"]
    assert payload["rawOutput"] == "CLUTCH_P='hi'; claude -p ..."
    assert len(payload["outputEvents"]) == 4

    reply = next(
        event["data"]["message"]
        for event in events
        if event.get("event") == "message"
        and event["data"]["message"]["agent"] == "Claude test Session"
    )
    assert reply.get("outputEvents")
    assert reply.get("rawOutput")

    idle_patch = next(
        event["data"]["patch"]
        for event in events
        if event.get("event") == "state_patch"
        and event.get("data", {}).get("patch", {}).get("status") == "idle"
    )
    agent_messages = [
        message
        for message in idle_patch["messages"]
        if message.get("agent") == "Claude test Session"
    ]
    assert agent_messages[-1].get("outputEvents")
    assert agent_messages[-1].get("rawOutput")
    assert idle_patch.get("hybrid_executions")
    message_id = str(agent_messages[-1]["id"])
    assert idle_patch["hybrid_executions"][message_id].get("outputEvents")
