"""WebSocket dispatch_preview must not be routed as plain chat text."""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_ws_dispatch_preview_not_plain_chat() -> None:
    with client.websocket_connect("/ws/runs/run_d34_ws_route") as ws:
        ws.receive_json()
        ws.send_json({"action": "dispatch_preview", "text": "hello without agent"})
        resp = ws.receive_json()
    assert resp["event"] == "dispatch_preview"
    assert resp["data"]["ok"] is False
