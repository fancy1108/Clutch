"""Tests for shell_session manager."""

from __future__ import annotations

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
