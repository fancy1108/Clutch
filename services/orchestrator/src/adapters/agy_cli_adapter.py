"""Antigravity CLI adapter for subprocess execution (M3-01)."""

from __future__ import annotations

import os
from collections.abc import Callable

from src.adapters.cli_adapter import run_cli

_DEFAULT_CHAT_TIMEOUT_SEC = float(os.environ.get("CLUTCH_AGY_CLI_TIMEOUT", "600"))


def _stream_cli_line(on_log: Callable[[str], None], stream: str, line: str) -> None:
    if not line:
        return
    prefix = "[ANTIGRAVITY CLI]" if stream == "stdout" else "[ANTIGRAVITY CLI stderr]"
    # Also filter logs streaming if needed, but stdout filtering is key.
    # We will log the raw lines, but filter the returned stdout for user view.
    on_log(f"{prefix} {line}")


def chat_agy_cli(
    prompt: str,
    *,
    cwd: str | None = None,
    system_prompt: str | None = None,
    session_id: str | None = None,
    resume_session_id: str | None = None,
    dangerously_skip_permissions: bool = True,
    timeout: float | None = None,
    binary: str | None = None,
    on_log: Callable[[str], None] | None = None,
) -> str:
    """Call local `agy` CLI in print mode, return response text."""
    if session_id and resume_session_id:
        raise ValueError("session_id and resume_session_id are mutually exclusive")
    
    # Prepend system prompt to user prompt if system prompt is present
    effective_prompt = prompt
    if system_prompt:
        effective_prompt = f"{system_prompt}\n\nUser Request:\n{prompt}"

    cmd = [binary or "agy", "-p", effective_prompt]
    if resume_session_id:
        cmd += ["--conversation", resume_session_id]
    elif session_id:
        # Note: agy uses --conversation for resuming, and generates conversation ID automatically.
        # Currently we don't have a direct flag to force a new custom conversation ID on launch, 
        # but we can pass it if supported or rely on agy resuming.
        pass
        
    if dangerously_skip_permissions:
        cmd.append("--dangerously-skip-permissions")

    effective_timeout = timeout if timeout is not None else _DEFAULT_CHAT_TIMEOUT_SEC
    on_line = None
    if on_log is not None:
        on_log(f"[ANTIGRAVITY CLI] Executing `{cmd[0]}` (timeout {effective_timeout:g}s)")
        on_line = lambda stream, line: _stream_cli_line(on_log, stream, line)

    result = run_cli(cmd, cwd=cwd, timeout=effective_timeout, on_line=on_line)
    if on_log is not None:
        on_log(f"[ANTIGRAVITY CLI] Exit code {result.exit_code}")
    return result.stdout
