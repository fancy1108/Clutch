"""Tests for shell_exec_runtime."""

from __future__ import annotations

import pytest

from src.shell_exec_runtime import (
    InteractiveCommandBlocked,
    _build_agy_shell_cmd,
    _build_claude_shell_cmd,
    assert_no_interactive_command,
    extract_claude_output,
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
