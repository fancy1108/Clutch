"""Claude CLI adapter for subprocess execution (M3-01)."""

from __future__ import annotations

import os
from collections.abc import Callable

from src.adapters.cli_adapter import run_cli

_DEFAULT_CHAT_TIMEOUT_SEC = float(os.environ.get("CLUTCH_CLAUDE_CLI_TIMEOUT", "600"))


def _stream_cli_line(on_log: Callable[[str], None], stream: str, line: str) -> None:
    if not line:
        return
    prefix = "[CLAUDE CLI]" if stream == "stdout" else "[CLAUDE CLI stderr]"
    on_log(f"{prefix} {line}")


def chat_claude_cli(
    prompt: str,
    *,
    cwd: str | None = None,
    system_prompt: str | None = None,
    session_id: str | None = None,
    resume_session_id: str | None = None,
    dangerously_skip_permissions: bool = True,
    allowed_tools: list[str] | None = None,
    timeout: float | None = None,
    binary: str | None = None,
    on_log: Callable[[str], None] | None = None,
) -> str:
    """Call local `claude` CLI in print mode, return response text."""
    if session_id and resume_session_id:
        raise ValueError("session_id and resume_session_id are mutually exclusive")
    cmd = [binary or "claude", "-p", prompt]
    if resume_session_id:
        cmd += ["--resume", resume_session_id]
    elif session_id:
        cmd += ["--session-id", session_id]
    if system_prompt:
        cmd += ["--append-system-prompt", system_prompt]
    if dangerously_skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    if allowed_tools:
        cmd += ["--allowed-tools", ",".join(allowed_tools)]

    effective_timeout = timeout if timeout is not None else _DEFAULT_CHAT_TIMEOUT_SEC
    on_line = None
    if on_log is not None:
        on_log(f"[CLAUDE CLI] Executing `{cmd[0]}` (timeout {effective_timeout:g}s)")
        on_line = lambda stream, line: _stream_cli_line(on_log, stream, line)

    result = run_cli(cmd, cwd=cwd, timeout=effective_timeout, on_line=on_line)
    if on_log is not None:
        on_log(f"[CLAUDE CLI] Exit code {result.exit_code}")
    return result.stdout
