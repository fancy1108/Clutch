"""validation_result WebSocket event tests — M2-14."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.main import _merge_patch, _run_states, _get_or_create_run, app

client = TestClient(app)


def test_validation_result_emitted_when_awaiting_human_on_connect() -> None:
    run_id = "run_validation_ws"
    state = _get_or_create_run(run_id)
    state = _merge_patch(
        state,
        {
            "status": "awaiting_human",
            "active_node_id": "n3",
            "active_agent": "Supervisor",
        },
    )
    _run_states[run_id] = state

    with client.websocket_connect(f"/ws/runs/{run_id}") as websocket:
        events: list[dict[str, object]] = []
        for _ in range(3):
            events.append(json.loads(websocket.receive_text()))

    event_names = [event["event"] for event in events]
    assert "validation_result" in event_names
    validation = next(event for event in events if event["event"] == "validation_result")
    data = validation["data"]
    assert data["passed"] is False
    assert "Evaluator" in str(data["message"])
