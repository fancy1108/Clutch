from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ws_state_patch_on_connect() -> None:
    with client.websocket_connect("/ws/runs/run_m0_test") as ws:
        envelope = ws.receive_json()
        assert envelope["event"] == "state_patch"
        assert envelope["data"]["run_id"] == "run_m0_test"
        patch = envelope["data"]["patch"]
        assert patch["status"] == "running"
        assert patch["active_node_id"] == "start"
        assert len(patch["terminal_logs"]) >= 1


def test_ws_state_patch_on_message() -> None:
    with client.websocket_connect("/ws/runs/run_m0_ping") as ws:
        ws.receive_json()  # initial state_patch
        ws.send_json({"text": "Hello sidecar!"})
        events = [ws.receive_json() for _ in range(4)]
        patch_events = [e for e in events if e["event"] == "state_patch"]
        assert len(patch_events) == 1
        patch = patch_events[0]["data"]["patch"]
        assert patch["active_node_id"] == "n1"
        assert any("Hello sidecar!" in line for line in patch["terminal_logs"])
