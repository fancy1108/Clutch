"""Automated POC acceptance #6 and #10 (HRT-10).

Maps to docs/research/pty-session.md §四:
- #6  concurrent input while BUSY → reject, no stdout mix
- #10 two run_id ShellSessions → isolated workspace / PTY
"""

from __future__ import annotations

import pytest

from src.engine_router import EngineResult, _route_claude_hybrid
from src.hybrid_concurrency import HybridPlainChatRejected
from src.runtime_registry import try_shell_exec_hybrid
from src.shell_session import (
    SessionState,
    ShellSession,
    ShellSessionBusyError,
    ShellSessionManager,
    ShellSessionPoolFullError,
    get_shell_session_manager,
)


def test_poc_06_busy_run_rejects_second_acquire(monkeypatch: pytest.MonkeyPatch) -> None:
    """POC #6: same run_id BUSY → second acquire raises before any new stdin write."""
    manager = ShellSessionManager()
    session = ShellSession(
        run_id="run-poc6",
        workspace_path="/tmp/poc6",
        state=SessionState.BUSY,
        master_fd=11,
        pid=1001,
    )
    manager._sessions["run-poc6"] = session
    monkeypatch.setattr(ShellSession, "alive", lambda self: True)

    with pytest.raises(ShellSessionBusyError, match="busy"):
        manager.get_or_create("run-poc6", workspace_path="/tmp/poc6")


def test_poc_06_pool_full_rejects_when_all_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    """POC #6 extension: pool saturated → new run rejected (strategy C)."""
    monkeypatch.setenv("CLUTCH_SHELL_MAX_SESSIONS", "1")
    manager = ShellSessionManager()
    manager._sessions["run-busy"] = ShellSession(
        run_id="run-busy",
        workspace_path="/tmp/busy",
        state=SessionState.BUSY,
        master_fd=1,
        pid=1,
    )
    monkeypatch.setattr(ShellSession, "_spawn", lambda self: None)

    with pytest.raises(ShellSessionPoolFullError):
        manager.get_or_create("run-new", workspace_path="/tmp/new")


def test_poc_06_hybrid_router_does_not_run_turn_when_busy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POC #6: hybrid path rejects at get_or_create; run_claude_turn never invoked."""
    manager = ShellSessionManager()
    manager._sessions["run-poc6-hybrid"] = ShellSession(
        run_id="run-poc6-hybrid",
        workspace_path="/tmp/ws",
        state=SessionState.BUSY,
        master_fd=12,
        pid=1002,
    )
    monkeypatch.setattr(ShellSession, "alive", lambda self: True)
    monkeypatch.setattr("src.shell_session.get_shell_session_manager", lambda: manager)
    monkeypatch.setattr("src.session_snapshot.load_snapshot", lambda _run_id: None)

    turn_called = {"ok": False}

    def fail_turn(*_args, **_kwargs):
        turn_called["ok"] = True
        raise AssertionError("run_claude_turn must not run when session is BUSY")

    monkeypatch.setattr("src.shell_exec_runtime.run_claude_turn", fail_turn)

    with pytest.raises(ShellSessionBusyError):
        _route_claude_hybrid(
            run_id="run-poc6-hybrid",
            workspace_path="/tmp/ws",
            prompt="second while busy",
            system_prompt=None,
            history=None,
            cli_session_id=None,
            cli_binary="claude",
            logs=[],
            on_log=None,
        )

    assert turn_called["ok"] is False


def test_poc_06_hybrid_registry_surfaces_busy_without_legacy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POC #6 + #15 boundary: BUSY is not legacy-fallback eligible."""
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")

    def busy_hybrid() -> EngineResult:
        raise ShellSessionBusyError("ShellSession run-x is busy")

    legacy_ran = {"ok": False}

    def legacy() -> EngineResult:
        legacy_ran["ok"] = True
        return EngineResult(engine="Legacy", output="fallback", logs=[])

    with pytest.raises(HybridPlainChatRejected) as exc_info:
        try_shell_exec_hybrid(
            agent_type="claude-cli",
            source="plain_chat",
            run_id="run-x",
            workspace_path="/tmp/ws",
            provider_spec=None,
            hybrid_route=busy_hybrid,
            legacy_route=legacy,
            logs=[],
            on_log=None,
            emit_log=lambda *_args: None,
        )

    assert exc_info.value.code == "session_busy"
    assert legacy_ran["ok"] is False


def test_poc_10_two_run_ids_get_isolated_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    """POC #10: claude run + agy run → distinct ShellSession entries."""
    manager = ShellSessionManager()
    next_fd = {"value": 100}

    def fake_spawn(self: ShellSession) -> None:
        next_fd["value"] += 1
        self.master_fd = next_fd["value"]
        self.pid = next_fd["value"] + 1000
        self.state = SessionState.READY

    monkeypatch.setattr(ShellSession, "_spawn", fake_spawn)
    monkeypatch.setattr(
        "src.shell_session.read_until_contains",
        lambda *_args, **_kwargs: "clutch$ ",
    )
    monkeypatch.setattr("src.shell_session.write_line", lambda *_args, **_kwargs: None)

    claude = manager.get_or_create("run-claude", workspace_path="/tmp/clutch-claude")
    manager.mark_idle("run-claude")
    agy = manager.get_or_create("run-agy", workspace_path="/tmp/clutch-agy")

    assert claude.run_id == "run-claude"
    assert agy.run_id == "run-agy"
    assert claude.workspace_path == "/tmp/clutch-claude"
    assert agy.workspace_path == "/tmp/clutch-agy"
    assert claude.master_fd != agy.master_fd
    assert claude.pid != agy.pid
    assert set(manager._sessions.keys()) == {"run-claude", "run-agy"}


def test_poc_10_workspace_cwd_is_per_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """POC #10: each run_id cd's into its own workspace_path (no cross-run cwd)."""
    manager = ShellSessionManager()
    written: dict[int, list[str]] = {}

    def fake_spawn(self: ShellSession) -> None:
        self.master_fd = abs(hash(self.run_id)) % 10_000 + 100
        self.pid = self.master_fd + 5000
        self.state = SessionState.READY

    def record_write(fd: int, line: str) -> None:
        written.setdefault(fd, []).append(line)

    monkeypatch.setattr(ShellSession, "_spawn", fake_spawn)
    monkeypatch.setattr(
        "src.shell_session.read_until_contains",
        lambda *_args, **_kwargs: "clutch$ ",
    )
    monkeypatch.setattr("src.shell_session.write_line", record_write)

    session_a = manager.get_or_create("run-a", workspace_path="/projects/alpha")
    manager.mark_idle("run-a")
    session_b = manager.get_or_create("run-b", workspace_path="/projects/beta")
    manager.mark_idle("run-b")

    session_a.ensure_workspace_cwd()
    session_b.ensure_workspace_cwd()

    lines_a = written[session_a.master_fd]
    lines_b = written[session_b.master_fd]
    assert any(line.startswith("cd ") and "/projects/alpha" in line for line in lines_a)
    assert any(line.startswith("cd ") and "/projects/beta" in line for line in lines_b)
    assert not any("/projects/beta" in line for line in lines_a)
    assert not any("/projects/alpha" in line for line in lines_b)


def test_poc_10_debug_snapshot_per_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """POC #10: debug API can distinguish concurrent runs."""
    manager = ShellSessionManager()
    manager._sessions["run-claude"] = ShellSession(
        run_id="run-claude",
        workspace_path="/tmp/claude-ws",
        state=SessionState.IDLE,
        master_fd=21,
        pid=2001,
    )
    manager._sessions["run-agy"] = ShellSession(
        run_id="run-agy",
        workspace_path="/tmp/agy-ws",
        state=SessionState.BUSY,
        master_fd=22,
        pid=2002,
    )
    monkeypatch.setattr(ShellSession, "alive", lambda self: True)

    snap_claude = manager.debug_snapshot("run-claude")
    snap_agy = manager.debug_snapshot("run-agy")

    assert snap_claude is not None
    assert snap_agy is not None
    assert snap_claude["workspace_path"] == "/tmp/claude-ws"
    assert snap_agy["workspace_path"] == "/tmp/agy-ws"
    assert snap_claude["state"] == "idle"
    assert snap_agy["state"] == "busy"


def test_poc_10_global_manager_singleton_per_process() -> None:
    """POC #10: one manager indexes all run_id → session mappings."""
    a = get_shell_session_manager()
    b = get_shell_session_manager()
    assert a is b
