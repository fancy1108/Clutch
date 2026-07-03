"""Run state persistence tests — session conversation resume."""

from __future__ import annotations

import pytest

from src.run_state_store import (
    load_run_state,
    persisted_state_preferred,
    save_run_state,
    sync_run_state_from_disk,
)
from src.state import initial_state


@pytest.fixture(autouse=True)
def isolated_history_dir(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path))


def test_load_run_state_ignores_empty_or_corrupt_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path))
    from src.run_state_store import _states_dir

    states_dir = _states_dir()
    states_dir.mkdir(parents=True, exist_ok=True)
    (states_dir / "run_empty.json").write_text("", encoding="utf-8")
    (states_dir / "run_bad.json").write_text("{not-json", encoding="utf-8")

    assert load_run_state("run_empty") is None
    assert load_run_state("run_bad") is None


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


def test_save_and_load_terminal_orchestra_fields() -> None:
    state = initial_state("run_terminal_hist")
    state["dispatch_log"] = [
        {
            "id": "dispatch_1",
            "target": "OpenCode",
            "task": "Summarize project",
            "dispatch_mode": "switch",
        },
    ]
    state["pty_lanes"] = [
        {
            "lane_id": "lane_primary",
            "agent_type": "opencode-cli",
            "label": "OpenCode",
            "status": "completed",
            "focused": True,
            "collapsed": False,
            "run_id": "run_terminal_hist",
        },
    ]
    state["dispatch_edges"] = [{"from": "User", "to": "OpenCode"}]

    save_run_state(state)
    loaded = load_run_state("run_terminal_hist")

    assert loaded is not None
    assert len(loaded["dispatch_log"]) == 1
    assert loaded["dispatch_log"][0]["target"] == "OpenCode"
    assert len(loaded["pty_lanes"]) == 1
    assert loaded["pty_lanes"][0]["status"] == "completed"
    assert len(loaded["dispatch_edges"]) == 1


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


def test_get_run_state_http_returns_terminal_orchestra_fields(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fastapi.testclient import TestClient

    from src.main import _run_states, app

    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path))
    _run_states.clear()

    state = initial_state("run_http_terminal")
    state["dispatch_log"] = [{"id": "d1", "target": "OpenCode", "task": "Summarize"}]
    state["pty_lanes"] = []
    save_run_state(state)

    response = TestClient(app).get("/api/runs/run_http_terminal/state")
    assert response.status_code == 200
    body = response.json()
    assert len(body["state"]["dispatch_log"]) == 1
    assert body["state"]["dispatch_log"][0]["target"] == "OpenCode"


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


def test_persisted_state_preferred_when_disk_has_more_messages() -> None:
    memory = initial_state("run_hydrate")
    memory["status"] = "running"
    memory["messages"] = [
        {"id": "u1", "agent": "User", "avatar": "", "time": "12:00", "text": "hi"},
    ]
    persisted = initial_state("run_hydrate")
    persisted["status"] = "idle"
    persisted["messages"] = [
        {"id": "u1", "agent": "User", "avatar": "", "time": "12:00", "text": "hi"},
        {"id": "a1", "agent": "Claude", "avatar": "", "time": "12:01", "text": "hello back"},
    ]
    assert persisted_state_preferred(persisted, memory) is True


def test_sync_run_state_from_disk_upgrades_stale_memory() -> None:
    memory = initial_state("run_sync")
    memory["status"] = "running"
    memory["messages"] = [
        {"id": "u1", "agent": "User", "avatar": "", "time": "12:00", "text": "hi"},
    ]
    persisted = initial_state("run_sync")
    persisted["status"] = "idle"
    persisted["messages"] = memory["messages"] + [
        {"id": "a1", "agent": "Claude", "avatar": "", "time": "12:01", "text": "done"},
    ]
    save_run_state(persisted)

    synced = sync_run_state_from_disk("run_sync", memory)
    assert synced["status"] == "idle"
    assert len(synced["messages"]) == 2


def test_ws_connect_prefers_persisted_completed_turn() -> None:
    from fastapi.testclient import TestClient

    from src.main import _run_states, app

    _run_states.clear()
    stale = initial_state("run_ws_hydrate")
    stale["status"] = "running"
    stale["messages"] = [
        {"id": "u1", "agent": "User", "avatar": "", "time": "12:00", "text": "hi"},
    ]
    _run_states["run_ws_hydrate"] = stale

    fresh = initial_state("run_ws_hydrate")
    fresh["status"] = "idle"
    fresh["messages"] = stale["messages"] + [
        {"id": "a1", "agent": "Claude", "avatar": "", "time": "12:01", "text": "background reply"},
    ]
    save_run_state(fresh)

    with TestClient(app).websocket_connect("/ws/runs/run_ws_hydrate") as ws:
        envelope = ws.receive_json()

    assert envelope["event"] == "state_patch"
    patch = envelope["data"]["patch"]
    assert patch["status"] == "idle"
    assert any(message.get("text") == "background reply" for message in patch["messages"])
