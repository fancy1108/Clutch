"""M2-01 / M2-02 — WebSocket message and log events."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.main import _run_states, app, initial_state

client = TestClient(app)


def _collect_after_send(ws, count: int) -> list[dict]:
    return [ws.receive_json() for _ in range(count)]


class _FakeRouter:
    def get_active_model(self) -> SimpleNamespace:
        return SimpleNamespace(name="Test Model")

    def chat(self, history: list[dict[str, str]]) -> str:
        last = history[-1]["content"]
        return f"Echo: {last}"


def test_ws_plain_chat_without_workflow(monkeypatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())

    with client.websocket_connect("/ws/runs/run_msg_test") as ws:
        ws.receive_json()  # initial state_patch
        ws.send_json({"text": "你好 Clutch"})
        events = _collect_after_send(ws, 4)

    message_events = [e for e in events if e["event"] == "message"]
    assert len(message_events) == 2
    agents = {e["data"]["message"]["agent"] for e in message_events}
    assert agents == {"User", "Test Model"}
    assert any("Echo: 你好 Clutch" in e["data"]["message"]["text"] for e in message_events)

    patch_events = [e for e in events if e["event"] == "state_patch"]
    assert len(patch_events) == 1
    patch = patch_events[0]["data"]["patch"]
    assert patch["status"] == "idle"
    assert patch.get("active_node_id", "") == ""


def test_ws_log_event_on_plain_chat(monkeypatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())

    with client.websocket_connect("/ws/runs/run_log_test") as ws:
        ws.receive_json()
        ws.send_json({"text": "ping"})
        events = _collect_after_send(ws, 4)

    log_events = [e for e in events if e["event"] == "log"]
    assert len(log_events) == 1
    assert "[CHAT]" in log_events[0]["data"]["message"]
    assert log_events[0]["data"]["source"] == "orchestrator"


def test_ws_workflow_chat_stub_when_workflow_selected() -> None:
    run_id = "run_wf_stub"
    _run_states[run_id] = initial_state(run_id, "video-production")
    _run_states[run_id]["active_agent"] = "Builder"

    with client.websocket_connect(f"/ws/runs/{run_id}") as ws:
        ws.receive_json()
        ws.send_json({"text": "run checks"})
        events = _collect_after_send(ws, 4)

    message_events = [e for e in events if e["event"] == "message"]
    agents = {e["data"]["message"]["agent"] for e in message_events}
    assert agents == {"User", "Orchestrator"}

    patch = next(e for e in events if e["event"] == "state_patch")["data"]["patch"]
    assert patch["active_node_id"] == "n1"
    assert patch["status"] == "running"
