"""Tests for shell_session manager."""

from __future__ import annotations

import time

import pytest

from src.shell_session import (
    SessionState,
    ShellSession,
    ShellSessionBusyError,
    ShellSessionManager,
    strip_ansi,
)


def test_strip_ansi_removes_escape_codes() -> None:
    assert "OK" in strip_ansi("\x1b[31mOK\x1b[0m")


def test_manager_busy_rejects_second_acquire(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = ShellSessionManager()
    session = ShellSession(
        run_id="run-a",
        workspace_path="/tmp",
        state=SessionState.BUSY,
        master_fd=1,
        pid=99999,
    )
    manager._sessions["run-a"] = session
    monkeypatch.setattr(ShellSession, "alive", lambda self: True)
    with pytest.raises(ShellSessionBusyError):
        manager.get_or_create("run-a", workspace_path="/tmp")


def test_mark_idle_from_busy() -> None:
    manager = ShellSessionManager()
    session = ShellSession(run_id="run-b", workspace_path="/tmp", state=SessionState.BUSY)
    manager._sessions["run-b"] = session
    manager.mark_idle("run-b")
    assert session.state == SessionState.IDLE


def test_sweep_idle_terminates_past_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_SHELL_IDLE_SEC", "1")
    manager = ShellSessionManager()
    session = ShellSession(
        run_id="run-idle",
        workspace_path="/tmp",
        state=SessionState.IDLE,
        master_fd=-1,
        pid=-1,
    )
    session.last_activity_at = 0.0
    manager._sessions["run-idle"] = session
    closed: list[bool] = []

    def fake_close(self: ShellSession, *, write_snapshot: bool = True) -> None:
        closed.append(write_snapshot)
        self.state = SessionState.TERMINATED

    monkeypatch.setattr(ShellSession, "close", fake_close)
    terminated = manager.sweep_idle()
    assert terminated == ["run-idle"]
    assert closed == [True]


def test_sweep_idle_skips_busy_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_SHELL_IDLE_SEC", "0")
    manager = ShellSessionManager()
    session = ShellSession(
        run_id="run-busy",
        workspace_path="/tmp",
        state=SessionState.BUSY,
        master_fd=1,
        pid=1,
    )
    session.last_activity_at = 0.0
    manager._sessions["run-busy"] = session
    assert manager.sweep_idle() == []
    assert session.state == SessionState.BUSY


def test_sweep_max_lifetime_terminates_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_SHELL_MAX_SEC", "1")
    monkeypatch.setenv("CLUTCH_SHELL_IDLE_SEC", "99999")
    manager = ShellSessionManager()
    session = ShellSession(
        run_id="run-max",
        workspace_path="/tmp",
        state=SessionState.IDLE,
        master_fd=-1,
        pid=-1,
    )
    session.created_at = 0.0
    session.last_activity_at = time.monotonic()
    manager._sessions["run-max"] = session

    def fake_close(self: ShellSession, *, write_snapshot: bool = True) -> None:
        self.state = SessionState.TERMINATED

    monkeypatch.setattr(ShellSession, "close", fake_close)
    assert manager.sweep_idle() == ["run-max"]


def test_manager_repeated_idle_cycles(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate 100+ busy/idle cycles without leaking sessions (acceptance #9 lite)."""
    manager = ShellSessionManager()
    for i in range(120):
        run_id = f"run-cycle-{i % 3}"
        session = ShellSession(
            run_id=run_id,
            workspace_path="/tmp",
            state=SessionState.BUSY,
            master_fd=i + 10,
            pid=i + 100,
        )
        manager._sessions[run_id] = session
        manager.mark_idle(run_id)
        assert manager._sessions[run_id].state == SessionState.IDLE
    assert len(manager._sessions) == 3


def test_pool_evicts_oldest_idle_when_at_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_SHELL_MAX_SESSIONS", "2")
    manager = ShellSessionManager()
    old = ShellSession(
        run_id="run-old",
        workspace_path="/tmp",
        state=SessionState.IDLE,
        master_fd=1,
        pid=1,
    )
    old.last_activity_at = 1.0
    busy = ShellSession(
        run_id="run-busy",
        workspace_path="/tmp",
        state=SessionState.BUSY,
        master_fd=2,
        pid=2,
    )
    manager._sessions["run-old"] = old
    manager._sessions["run-busy"] = busy

    closed: list[str] = []

    def fake_close(self: ShellSession, *, write_snapshot: bool = True) -> None:
        closed.append(self.run_id)
        self.state = SessionState.TERMINATED

    monkeypatch.setattr(ShellSession, "close", fake_close)
    monkeypatch.setattr(ShellSession, "_spawn", lambda self: None)

    session = manager.get_or_create("run-new", workspace_path="/tmp")
    assert session.run_id == "run-new"
    assert "run-old" in closed
    assert "run-busy" in manager._sessions
    assert manager._sessions["run-new"].state == SessionState.BUSY


def test_pool_full_when_all_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.shell_session import ShellSessionPoolFullError

    monkeypatch.setenv("CLUTCH_SHELL_MAX_SESSIONS", "1")
    manager = ShellSessionManager()
    manager._sessions["run-busy"] = ShellSession(
        run_id="run-busy",
        workspace_path="/tmp",
        state=SessionState.BUSY,
        master_fd=1,
        pid=1,
    )
    monkeypatch.setattr(ShellSession, "_spawn", lambda self: None)
    with pytest.raises(ShellSessionPoolFullError):
        manager.get_or_create("run-new", workspace_path="/tmp")
