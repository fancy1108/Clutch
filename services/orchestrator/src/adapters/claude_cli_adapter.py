"""Claude CLI adapter for subprocess execution (M3-01)."""

from __future__ import annotations

import os

from src.adapters.cli_adapter import run_cli

_DEFAULT_CHAT_TIMEOUT_SEC = float(os.environ.get("CLUTCH_CLAUDE_CLI_TIMEOUT", "600"))


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

    result = run_cli(cmd, cwd=cwd, timeout=timeout if timeout is not None else _DEFAULT_CHAT_TIMEOUT_SEC)
    return result.stdout
