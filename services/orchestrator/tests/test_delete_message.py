"""WebSocket delete_message action."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import _apply_delete_message, _run_states, app, initial_state


client = TestClient(app)


def test_apply_delete_message_removes_message_and_hybrid_metadata() -> None:
    state = initial_state("run_delete_unit")
    state["messages"] = [
        {"id": "user_1", "agent": "User", "text": "hello", "avatar": "", "time": "12:00"},
        {"id": "agent_1", "agent": "Clutch", "text": "hi", "avatar": "", "time": "12:01"},
    ]
    state["hybrid_executions"] = {
        "agent_1": {"rawOutput": "stdout", "outputEvents": []},
    }

    updated, patch = _apply_delete_message(state, "agent_1")

    assert len(updated["messages"]) == 1
    assert updated["messages"][0]["id"] == "user_1"
    assert "agent_1" not in (updated.get("hybrid_executions") or {})
    assert patch["messages"] == updated["messages"]
    assert patch["hybrid_executions"] == {}


def test_delete_message_over_websocket() -> None:
    run_id = "run_delete_ws"
    state = initial_state(run_id)
    state["messages"] = [
        {"id": "user_1", "agent": "User", "text": "hello", "avatar": "", "time": "12:00"},
        {"id": "agent_1", "agent": "Clutch", "text": "hi", "avatar": "", "time": "12:01"},
    ]
    _run_states[run_id] = state

    with client.websocket_connect(f"/ws/runs/{run_id}") as ws:
        ws.receive_json()
        ws.send_json({"action": "delete_message", "message_id": "agent_1"})
        event = ws.receive_json()

    assert event["event"] == "state_patch"
    patch = event["data"]["patch"]
    assert len(patch["messages"]) == 1
    assert patch["messages"][0]["id"] == "user_1"
