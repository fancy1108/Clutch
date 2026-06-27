"""run_completed WebSocket event tests — M1-05."""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_run_completed_after_passed_run_on_ws_connect() -> None:
    start = client.post("/api/runs/start", json={"workflow_id": "video-production"})
    assert start.status_code == 200
    run_id = start.json()["run_id"]
    assert start.json()["status"] == "passed"

    with client.websocket_connect(f"/ws/runs/{run_id}") as ws:
        initial = ws.receive_json()
        assert initial["event"] == "state_patch"
        assert initial["data"]["patch"]["status"] == "passed"

        completed = ws.receive_json()
        assert completed["event"] == "run_completed"
        assert completed["data"]["run_id"] == run_id
        assert completed["data"]["status"] == "passed"
        assert completed["data"]["state"]["active_node_id"] == "end"
        assert completed["data"]["timestamp"]


def test_run_completed_after_http_stop_on_ws_connect() -> None:
    start = client.post("/api/runs/start", json={"workflow_id": "video-production"})
    run_id = start.json()["run_id"]
    client.post(f"/api/runs/{run_id}/stop")

    with client.websocket_connect(f"/ws/runs/{run_id}") as ws:
        ws.receive_json()
        completed = ws.receive_json()
        assert completed["event"] == "run_completed"
        assert completed["data"]["status"] == "failed"
        assert completed["data"]["state"]["status"] == "failed"


def test_plain_chat_stop_via_ws_action_sets_idle() -> None:
    with client.websocket_connect("/ws/runs/run_plain_chat_ws_stop") as ws:
        ws.receive_json()
        ws.send_json({"action": "stop_run"})
        saw_idle = False
        for _ in range(4):
            event = ws.receive_json()
            if event["event"] != "state_patch":
                continue
            status = event["data"].get("patch", {}).get("status")
            if status == "idle":
                saw_idle = True
                break
        assert saw_idle
