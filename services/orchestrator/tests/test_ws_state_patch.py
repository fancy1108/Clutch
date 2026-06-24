from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["api_version"] == "2"


def test_ws_state_patch_on_connect() -> None:
    with client.websocket_connect("/ws/runs/run_m0_test") as ws:
        envelope = ws.receive_json()
        assert envelope["event"] == "state_patch"
        assert envelope["data"]["run_id"] == "run_m0_test"
        patch = envelope["data"]["patch"]
        assert patch["status"] == "idle"
        assert patch["active_node_id"] == ""
        assert patch["terminal_logs"] == []


def test_ws_state_patch_on_message(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.models_config.get_router",
        lambda: type(
            "_R",
            (),
            {
                "get_active_model": lambda self: type("M", (), {"name": "Test Model"})(),
                "chat": lambda self, history: "pong",
            },
        )(),
    )

    with client.websocket_connect("/ws/runs/run_m0_ping") as ws:
        ws.receive_json()  # initial state_patch
        ws.send_json({"text": "Hello sidecar!"})
        events = [ws.receive_json() for _ in range(5)]
        patch_events = [e for e in events if e["event"] == "state_patch"]
        assert len(patch_events) == 2
        
        patch1 = patch_events[0]["data"]["patch"]
        assert patch1["status"] == "running"
        assert any("Hello sidecar!" in m["text"] for m in patch1["messages"])
        
        patch2 = patch_events[1]["data"]["patch"]
        assert patch2["status"] == "idle"
        assert patch2.get("active_node_id", "") == ""
