"""Tests for the Claude CLI adapter."""

from __future__ import annotations

import pytest
from src.adapters.claude_cli_adapter import chat_claude_cli
from src.adapters.cli_adapter import CliResult


def test_chat_claude_cli_args(monkeypatch) -> None:
    called_cmd = None
    called_cwd = None
    called_timeout = None

    def fake_run_cli(
        cmd: list[str],
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
        on_line=None,
    ) -> CliResult:
        nonlocal called_cmd, called_cwd, called_timeout
        called_cmd = cmd
        called_cwd = cwd
        called_timeout = timeout
        return CliResult(command=cmd, exit_code=0, stdout="Mocked response", stderr="")

    monkeypatch.setattr("src.adapters.claude_cli_adapter.run_cli", fake_run_cli)

    res = chat_claude_cli(
        prompt="hello world",
        cwd="/tmp/fake",
        system_prompt="strict auditor",
        dangerously_skip_permissions=True,
        allowed_tools=["git *", "edit"],
        timeout=10.0,
    )

    assert res == "Mocked response"
    assert called_cmd == [
        "claude",
        "-p",
        "hello world",
        "--append-system-prompt",
        "strict auditor",
        "--dangerously-skip-permissions",
        "--allowed-tools",
        "git *,edit",
    ]
    assert called_cwd == "/tmp/fake"
    assert called_timeout == 10.0


def test_chat_claude_cli_session_id(monkeypatch) -> None:
    called_cmd = None

    def fake_run_cli(
        cmd: list[str],
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
        on_line=None,
    ) -> CliResult:
        nonlocal called_cmd
        called_cmd = cmd
        return CliResult(command=cmd, exit_code=0, stdout="session created", stderr="")

    monkeypatch.setattr("src.adapters.claude_cli_adapter.run_cli", fake_run_cli)

    res = chat_claude_cli(
        prompt="first turn",
        session_id="550e8400-e29b-41d4-a716-446655440000",
    )
    assert res == "session created"
    assert called_cmd == [
        "claude",
        "-p",
        "first turn",
        "--session-id",
        "550e8400-e29b-41d4-a716-446655440000",
        "--dangerously-skip-permissions",
    ]


def test_chat_claude_cli_resume(monkeypatch) -> None:
    called_cmd = None

    def fake_run_cli(
        cmd: list[str],
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
        on_line=None,
    ) -> CliResult:
        nonlocal called_cmd
        called_cmd = cmd
        return CliResult(command=cmd, exit_code=0, stdout="resumed", stderr="")

    monkeypatch.setattr("src.adapters.claude_cli_adapter.run_cli", fake_run_cli)

    res = chat_claude_cli(
        prompt="follow up",
        resume_session_id="550e8400-e29b-41d4-a716-446655440000",
    )
    assert res == "resumed"
    assert called_cmd == [
        "claude",
        "-p",
        "follow up",
        "--resume",
        "550e8400-e29b-41d4-a716-446655440000",
        "--dangerously-skip-permissions",
    ]


def test_chat_claude_cli_streams_via_on_log(monkeypatch) -> None:
    streamed: list[str] = []

    def fake_run_cli(
        cmd: list[str],
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
        on_line=None,
    ) -> CliResult:
        assert on_line is not None
        on_line("stdout", "chunk-a")
        on_line("stderr", "warn")
        return CliResult(command=cmd, exit_code=0, stdout="chunk-a", stderr="warn")

    monkeypatch.setattr("src.adapters.claude_cli_adapter.run_cli", fake_run_cli)

    res = chat_claude_cli(prompt="stream me", on_log=streamed.append)

    assert res == "chunk-a"
    assert any("[CLAUDE CLI] Executing" in line for line in streamed)
    assert "[CLAUDE CLI] chunk-a" in streamed
    assert "[CLAUDE CLI stderr] warn" in streamed
    assert any("Exit code 0" in line for line in streamed)
