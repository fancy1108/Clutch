"""Run state persistence tests — session conversation resume."""

from __future__ import annotations

import pytest

from src.run_state_store import load_run_state, save_run_state
from src.state import initial_state


@pytest.fixture(autouse=True)
def isolated_history_dir(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path))


def test_save_and_load_run_state_roundtrip() -> None:
    state = initial_state("run_persist01")
    state["messages"] = [
        {
            "id": "user_1",
            "agent": "User",
            "avatar": "",
            "time": "12:00",
            "text": "你好",
        },
        {
            "id": "reply_1",
            "agent": "Claude Sonnet",
            "avatar": "",
            "time": "12:01",
            "text": "你好！有什么可以帮你？",
        },
    ]
    state["terminal_logs"] = ["[CHAT] Claude Sonnet: 12 chars"]

    save_run_state(state)
    loaded = load_run_state("run_persist01")

    assert loaded is not None
    assert len(loaded["messages"]) == 2
    assert loaded["messages"][0]["text"] == "你好"
    assert loaded["terminal_logs"] == ["[CHAT] Claude Sonnet: 12 chars"]


def test_get_or_create_run_loads_persisted_state() -> None:
    from src.main import _get_or_create_run, _run_states

    state = initial_state("run_resume_api")
    state["messages"] = [{"id": "m1", "agent": "User", "avatar": "", "time": "09:00", "text": "history"}]
    save_run_state(state)
    _run_states.clear()

    loaded = _get_or_create_run("run_resume_api")
    assert len(loaded["messages"]) == 1
    assert loaded["messages"][0]["text"] == "history"


def test_get_run_state_http_returns_persisted_messages(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from src.main import _run_states, app

    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path))
    _run_states.clear()

    state = initial_state("run_http_state")
    state["messages"] = [{"id": "m1", "agent": "User", "avatar": "", "time": "10:00", "text": "saved"}]
    save_run_state(state)

    response = TestClient(app).get("/api/runs/run_http_state/state")
    assert response.status_code == 200
    body = response.json()
    assert body["state"]["messages"][0]["text"] == "saved"


def test_plain_chat_persists_messages(monkeypatch) -> None:
    from types import SimpleNamespace

    from fastapi.testclient import TestClient

    from src.main import _run_states, app

    class _FakeRouter:
        def get_active_model(self) -> SimpleNamespace:
            return SimpleNamespace(id="test-model", name="Test Model", model_kind="chat")

        def chat(self, history: list[dict[str, str]]) -> str:
            return f"Echo: {history[-1]['content']}"

    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())
    _run_states.clear()

    with TestClient(app).websocket_connect("/ws/runs/run_plain_persist") as ws:
        ws.receive_json()
        ws.send_json({"text": "你好"})
        for _ in range(4):
            ws.receive_json()

    reloaded = load_run_state("run_plain_persist")
    assert reloaded is not None
    assert any(message.get("text") == "你好" for message in reloaded["messages"])
    assert any("Echo: 你好" in str(message.get("text")) for message in reloaded["messages"])
