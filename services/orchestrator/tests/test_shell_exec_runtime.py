"""Tests for shell_exec_runtime."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.hybrid_audit_log import get_hybrid_audit_dir, read_hybrid_audit_lines
from src.shell_exec_runtime import (
    InteractiveCommandBlocked,
    _build_agy_shell_cmd,
    _build_claude_shell_cmd,
    assert_no_interactive_command,
    extract_claude_output,
    run_claude_turn,
)
def test_interactive_command_blocked() -> None:
    with pytest.raises(InteractiveCommandBlocked):
        assert_no_interactive_command("please run vim on the file")


def test_extract_claude_output_strips_marker() -> None:
    raw = (
        "CLUTCH_P='x'; claude -p \"$CLUTCH_P\" --dangerously-skip-permissions; "
        "echo __CLUTCH_DONE_abc__\n"
        "noise\nOK\n"
        "__CLUTCH_DONE_abc__\n"
    )
    assert extract_claude_output(raw, marker="__CLUTCH_DONE_abc__") == "noise\nOK"


def test_build_claude_shell_cmd_keeps_flags_on_claude_invocation() -> None:
    cmd = _build_claude_shell_cmd(
        claude_binary="/usr/bin/claude",
        prompt="hello",
        marker="__CLUTCH_DONE_x__",
        session_id="sess-1",
        resume_session_id=None,
        system_prompt="You are helpful",
    )
    assert cmd.startswith("CLUTCH_P='hello'; /usr/bin/claude -p \"$CLUTCH_P\"")
    assert "--session-id sess-1" in cmd
    assert "--append-system-prompt 'You are helpful'" in cmd
    assert "--dangerously-skip-permissions" in cmd
    assert cmd.endswith("; echo __CLUTCH_DONE_x__")
    assert "; --append-system-prompt" not in cmd
    assert "; --dangerously-skip-permissions" not in cmd


def test_build_agy_shell_cmd_includes_conversation() -> None:
    cmd = _build_agy_shell_cmd(
        agy_binary="/opt/homebrew/bin/agy",
        prompt="hello",
        marker="__CLUTCH_DONE_x__",
        conversation_id="conv-1",
        system_prompt=None,
    )
    assert cmd.startswith("CLUTCH_P='hello'; /opt/homebrew/bin/agy -p \"$CLUTCH_P\"")
    assert "--conversation conv-1" in cmd
    assert "--dangerously-skip-permissions" in cmd
    assert cmd.endswith("; echo __CLUTCH_DONE_x__")


@dataclass
class _FakeSession:
    run_id: str = "run_hybrid_audit"
    owner_node_id: str = "plain_chat"
    master_fd: int = 99

    def ensure_workspace_cwd(self) -> None:
        return None


def test_run_claude_turn_writes_ok_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    session = _FakeSession()

    def fake_write_line(_fd: int, _line: str) -> None:
        return None

    def fake_read_until_marker(_fd: int, marker: str, *, max_wait_s: float) -> str:
        return (
            f"CLUTCH_P='hello'; claude -p \"$CLUTCH_P\" --dangerously-skip-permissions; "
            f"echo {marker}\nassistant reply\n{marker}\nclutch$ "
        )

    monkeypatch.setattr("src.shell_exec_runtime.write_line", fake_write_line)
    monkeypatch.setattr("src.shell_exec_runtime.read_until_marker", fake_read_until_marker)

    result = run_claude_turn(
        session,  # type: ignore[arg-type]
        prompt="hello",
        claude_binary="/usr/bin/claude",
        timeout_s=5.0,
        new_session_id="sess-new",
        system_prompt="You are helpful",
    )
    assert result.stdout == "assistant reply"

    lines = read_hybrid_audit_lines(run_id="run_hybrid_audit", audit_dir=get_hybrid_audit_dir())
    assert len(lines) == 1
    audit = lines[0]
    assert audit["result"] == "ok"
    assert audit["cli_session_id"] == "sess-new"
    assert audit["agent"] == "claude"
    assert audit["source"] == "shell_exec_runtime"
    assert "CLUTCH_P='[redacted]'" in str(audit["command_summary"])
    assert "You are helpful" not in str(audit["command_summary"])


def test_run_claude_turn_writes_timeout_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    session = _FakeSession()

    monkeypatch.setattr("src.shell_exec_runtime.write_line", lambda *_args: None)
    monkeypatch.setattr(
        "src.shell_exec_runtime.read_until_marker",
        lambda *_args, **_kwargs: "partial output without marker",
    )

    with pytest.raises(Exception, match="timed out"):
        run_claude_turn(
            session,  # type: ignore[arg-type]
            prompt="hello",
            claude_binary="/usr/bin/claude",
            timeout_s=1.0,
        )

    lines = read_hybrid_audit_lines(run_id="run_hybrid_audit", audit_dir=get_hybrid_audit_dir())
    assert len(lines) == 1
    assert lines[0]["result"] == "timeout"
    assert lines[0]["level"] == "error"


def test_run_claude_turn_writes_blocked_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    session = _FakeSession()

    with pytest.raises(InteractiveCommandBlocked):
        run_claude_turn(
            session,  # type: ignore[arg-type]
            prompt="open vim please",
            claude_binary="/usr/bin/claude",
            timeout_s=1.0,
        )

    lines = read_hybrid_audit_lines(run_id="run_hybrid_audit", audit_dir=get_hybrid_audit_dir())
    assert len(lines) == 1
    assert lines[0]["result"] == "blocked"
    assert lines[0]["duration_ms"] == 0
