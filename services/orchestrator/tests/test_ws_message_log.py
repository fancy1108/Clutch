"""M2-01 / M2-02 — WebSocket message and log events."""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def _collect_after_send(ws, count: int) -> list[dict]:
    return [ws.receive_json() for _ in range(count)]


def test_ws_message_events_on_chat_text() -> None:
    with client.websocket_connect("/ws/runs/run_msg_test") as ws:
        ws.receive_json()  # initial state_patch
        ws.send_json({"text": "你好 Clutch"})
        events = _collect_after_send(ws, 4)

    message_events = [e for e in events if e["event"] == "message"]
    assert len(message_events) == 2
    agents = {e["data"]["message"]["agent"] for e in message_events}
    assert agents == {"User", "Orchestrator"}
    assert any("你好 Clutch" in e["data"]["message"]["text"] for e in message_events)

    patch_events = [e for e in events if e["event"] == "state_patch"]
    assert len(patch_events) == 1
    assert patch_events[0]["data"]["patch"]["active_node_id"] == "n1"


def test_ws_log_event_on_chat_text() -> None:
    with client.websocket_connect("/ws/runs/run_log_test") as ws:
        ws.receive_json()
        ws.send_json({"text": "ping"})
        events = _collect_after_send(ws, 4)

    log_events = [e for e in events if e["event"] == "log"]
    assert len(log_events) == 1
    assert "Received: ping" in log_events[0]["data"]["message"]
    assert log_events[0]["data"]["source"] == "orchestrator"
