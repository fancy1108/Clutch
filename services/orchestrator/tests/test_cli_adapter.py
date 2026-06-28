"""CLI adapter tests — M3-01."""

from __future__ import annotations

import pytest

from src.adapters.cli_adapter import (
    CliAdapterError,
    chat_generic_cli,
    compose_cli_argv,
    format_cli_issue_for_user,
    run_cli,
    run_cli_pty,
)


def test_run_cli_success() -> None:
    result = run_cli(["python3", "-c", "print('hello')"])
    assert result.ok
    assert "hello" in result.stdout


def test_run_cli_nonzero_exit_fails() -> None:
    with pytest.raises(CliAdapterError, match="退出码"):
        run_cli(["python3", "-c", "import sys; sys.exit(2)"])


def test_run_cli_streams_stdout_lines() -> None:
    streamed: list[tuple[str, str]] = []

    result = run_cli(
        ["python3", "-c", "import time; print('line-one'); time.sleep(0.05); print('line-two')"],
        on_line=lambda stream, line: streamed.append((stream, line)),
    )

    assert result.ok
    assert "line-one" in result.stdout
    assert "line-two" in result.stdout
    assert ("stdout", "line-one") in streamed
    assert ("stdout", "line-two") in streamed


def test_run_cli_pty_captures_output() -> None:
    try:
        result = run_cli_pty(["python3", "-c", "print('pty-hello')"])
    except OSError as exc:
        pytest.skip(f"PTY unavailable in this environment: {exc}")
    assert result.ok
    assert "pty-hello" in result.stdout


def test_chat_generic_cli_uses_pty_for_agy(monkeypatch) -> None:
    called = {}

    def fake_run_cli_pty(cmd, **kwargs):
        called["cmd"] = cmd
        from src.adapters.cli_adapter import CliResult

        return CliResult(command=cmd, exit_code=0, stdout="agy says hi", stderr="")

    monkeypatch.setattr("src.adapters.cli_adapter.run_cli_pty", fake_run_cli_pty)

    out = chat_generic_cli(
        "hello",
        binary="agy",
        extra_args=["--dangerously-skip-permissions"],
        conversation_mode="none",
        supports_append_system_prompt=False,
    )
    assert out == "agy says hi"
    assert called["cmd"] == ["agy", "--dangerously-skip-permissions", "-p", "hello"]


def test_compose_cli_argv_codex_uses_exec_positional_prompt() -> None:
    cmd = compose_cli_argv(
        binary="codex",
        effective_prompt="hello",
        prompt_flag="",
        conversation_mode="history_only",
        extra_args=[
            "exec",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            "--json",
        ],
        prepend_system_prompt=False,
        supports_append_system_prompt=False,
    )
    assert cmd == [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--json",
        "hello",
    ]
    assert "-p" not in cmd
    assert "--append-system-prompt" not in cmd
    assert "--conversation" not in cmd


def test_format_cli_issue_for_user_quota() -> None:
    msg = "Individual quota reached. Resets in 2h."
    out = format_cli_issue_for_user(msg)
    assert "quota limit reached" in out.lower() or "配额已用尽" in out
    assert "Individual quota reached" in out


def test_chat_generic_cli_surfaces_quota_from_pty() -> None:
    from src.adapters.cli_adapter import CliResult

    def fake_run_cli_pty(cmd, **kwargs):
        return CliResult(
            command=cmd,
            exit_code=0,
            stdout=format_cli_issue_for_user(
                "Individual quota reached. Please upgrade your subscription. Resets in 2h."
            ),
            stderr="",
        )

    out = chat_generic_cli(
        "hello",
        binary="agy",
        extra_args=["--dangerously-skip-permissions"],
        conversation_mode="none",
        supports_append_system_prompt=False,
        run_cli_fn=fake_run_cli_pty,
    )
    assert "quota limit reached" in out.lower() or "配额已用尽" in out
