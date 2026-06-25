"""Tests for the Claude CLI adapter."""

from __future__ import annotations

import pytest
from src.adapters.claude_cli_adapter import chat_claude_cli
from src.adapters.cli_adapter import CliResult


def test_chat_claude_cli_args(monkeypatch) -> None:
    called_cmd = None
    called_cwd = None
    called_timeout = None

    def fake_run_cli(cmd: list[str], *, cwd: str | None = None, timeout: float = 30.0) -> CliResult:
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
