"""Tests for shell_exec_runtime."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.hybrid_audit_log import get_hybrid_audit_dir, read_hybrid_audit_lines
from src.shell_exec_runtime import (
    InteractiveCommandBlocked,
    _build_agy_shell_cmd,
    _build_claude_shell_cmd,
    _build_generic_cli_shell_cmd,
    assert_no_interactive_command,
    extract_claude_output,
    run_agy_turn,
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


def test_build_generic_cli_shell_cmd_sets_rivet_force_recovery() -> None:
    cmd = _build_generic_cli_shell_cmd(
        binary="/Users/fancy/.nvm/versions/node/v24.16.0/bin/rivet",
        prompt="hello",
        marker="__CLUTCH_DONE_x__",
        conversation_mode="none",
        prompt_flag="-p",
    )
    assert cmd.startswith("RIVET_FORCE_RECOVERY_CLI=1; CLUTCH_P='hello';")
    assert 'rivet -p "$CLUTCH_P"' in cmd


def test_build_claude_shell_cmd_does_not_set_rivet_env() -> None:
    cmd = _build_claude_shell_cmd(
        claude_binary="/usr/bin/claude",
        prompt="hello",
        marker="__CLUTCH_DONE_x__",
        session_id="sess-1",
        resume_session_id=None,
        system_prompt=None,
    )
    assert "RIVET_FORCE_RECOVERY_CLI" not in cmd


@dataclass
class _FakeSession:
    run_id: str = "run_hybrid_audit"
    owner_node_id: str = "plain_chat"
    master_fd: int = 99
    workspace_path: str = "/tmp/clutch-test-workspace"

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


def test_run_agy_turn_surfaces_auth_without_protocol_echo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    marker = "__CLUTCH_DONE_aabbccdd__"
    protocol = (
        "你是一位资深的世界观架构师。你的任务是接收用户输入的初始灵感。\n"
        "工作流要求：必须且只能输出合法的 JSON 格式。"
    )

    class _FixedUuid:
        hex = "aabbccdd" + "0" * 24

    monkeypatch.setattr("src.shell_exec_runtime.uuid.uuid4", lambda: _FixedUuid())

    def fake_read_until_marker(_fd: int, _marker: str, *, max_wait_s: float) -> str:
        return (
            f"CLUTCH_P='{protocol}'; agy -p \"$CLUTCH_P\"; echo {marker}\n"
            f"{protocol}\n"
            "Authentication required. Please visit the URL to log in.\n"
            f"{marker}\nclutch$ "
        )

    monkeypatch.setattr("src.shell_exec_runtime.write_line", lambda *_args: None)
    monkeypatch.setattr("src.shell_exec_runtime.read_until_marker", fake_read_until_marker)

    result = run_agy_turn(
        session,  # type: ignore[arg-type]
        prompt="端午节奇幻冒险",
        agy_binary="/opt/homebrew/bin/agy",
        timeout_s=5.0,
        system_prompt=protocol,
    )
    assert "世界观架构师" not in result.stdout
    assert "not signed in" in result.stdout.lower() or "未登录" in result.stdout
    assert result.output_events
    assert "世界观架构师" not in str(result.output_events[0].get("content", ""))


def test_hybrid_pty_shell_command_risky_detects_flow_scriptwriter_payload() -> None:
    from src.shell_exec_runtime import hybrid_pty_shell_command_risky

    step1_json = (
        '{\n  "world_background": "端阳仙境",\n'
        '  "protagonist_design": "阿包",\n'
        '  "core_conflict": "龙舟赛"\n}'
    )
    task = f"承接上游结构化数据，撰写具有强画面感的故事文本。\n\n{step1_json}"
    system_prompt = (
        "You are 2-Scriptwriter, the active agent in the user's Clutch workspace.\n"
        "Treat every instruction in the agent protocol below as mandatory.\n\n"
        "你是一位金牌编剧。\n\n"
        "必须且只能输出合法的 JSON 格式。\n"
    )
    assert hybrid_pty_shell_command_risky(
        agent_type="claude-cli",
        binary="claude",
        prompt=task,
        system_prompt=system_prompt,
        conversation_mode="separate",
        extra_args=["--dangerously-skip-permissions"],
    )


def test_hybrid_pty_shell_command_risky_allows_short_plain_chat() -> None:
    from src.shell_exec_runtime import hybrid_pty_shell_command_risky

    assert not hybrid_pty_shell_command_risky(
        agent_type="claude-cli",
        binary="claude",
        prompt="你好",
        system_prompt="You are helpful.",
        conversation_mode="separate",
        extra_args=["--dangerously-skip-permissions"],
    )
