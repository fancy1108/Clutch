"""Tests for GET /api/runs/{run_id}/debug (HRT-06)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from src.hybrid_audit_log import append_hybrid_turn_audit, build_turn_audit_line, get_hybrid_audit_dir
from src.main import _run_states, app
from src.run_state_store import save_run_state
from src.shell_session import SessionState, ShellSession, get_shell_session_manager
from src.state import initial_state

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_run_cache() -> None:
    _run_states.clear()
    yield
    _run_states.clear()


def test_get_run_debug_returns_status_logs_and_audit(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    run_id = "run_debug_api"
    state = initial_state(run_id)
    state["status"] = "idle"
    state["terminal_logs"] = [f"[CHAT] line {idx}" for idx in range(12)]
    save_run_state(state)

    audit_path = get_hybrid_audit_dir() / "2026-06-27.jsonl"
    append_hybrid_turn_audit(
        build_turn_audit_line(
            run_id=run_id,
            turn_id="turn1",
            marker="__CLUTCH_DONE_turn1__",
            duration_ms=900,
            result="ok",
            cli_session_id="sess-1",
            agent="claude",
            command_summary="claude -p [redacted]",
            node_id="plain_chat",
            message="hybrid claude turn ok",
            timestamp=datetime(2026, 6, 27, 12, 0, tzinfo=UTC),
        ),
        path=audit_path,
    )
    append_hybrid_turn_audit(
        build_turn_audit_line(
            run_id="run_other",
            turn_id="turn2",
            marker="__CLUTCH_DONE_turn2__",
            duration_ms=100,
            result="timeout",
            cli_session_id=None,
            agent="claude",
            command_summary="claude -p [redacted]",
            node_id="plain_chat",
            message="timeout",
            timestamp=datetime(2026, 6, 27, 12, 1, tzinfo=UTC),
        ),
        path=audit_path,
    )

    response = client.get(f"/api/runs/{run_id}/debug?logs_limit=3&audit_limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["status"] == "idle"
    assert body["terminal_logs_total"] == 12
    assert body["terminal_logs"] == ["[CHAT] line 9", "[CHAT] line 10", "[CHAT] line 11"]
    assert len(body["hybrid_audit"]) == 1
    assert body["hybrid_audit"][0]["run_id"] == run_id
    assert body["hybrid_audit"][0]["result"] == "ok"
    assert body["shell_session"] is None


def test_get_run_debug_includes_shell_session_when_active(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    run_id = "run_debug_shell"
    save_run_state(initial_state(run_id))

    manager = get_shell_session_manager()
    session = ShellSession(
        run_id=run_id,
        workspace_path="/tmp/clutch-debug",
        owner_node_id="plain_chat",
        state=SessionState.IDLE,
        master_fd=-1,
        pid=-1,
    )
    with manager._lock:
        manager._sessions[run_id] = session

    response = client.get(f"/api/runs/{run_id}/debug")
    assert response.status_code == 200
    shell = response.json()["shell_session"]
    assert shell is not None
    assert shell["state"] == "idle"
    assert shell["workspace_path"] == "/tmp/clutch-debug"
    assert shell["owner_node_id"] == "plain_chat"
    assert shell["alive"] is False

    manager.release(run_id)


def test_get_run_debug_clamps_limits(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    run_id = "run_debug_clamp"
    state = initial_state(run_id)
    state["terminal_logs"] = [f"log-{idx}" for idx in range(150)]
    save_run_state(state)

    response = client.get(f"/api/runs/{run_id}/debug?logs_limit=999")
    assert response.status_code == 200
    body = response.json()
    assert len(body["terminal_logs"]) == 100
