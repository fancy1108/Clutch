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
    from src.adapters.cli_adapter import chat_generic_cli
    
    extra_args = []
    if dangerously_skip_permissions:
        extra_args.append("--dangerously-skip-permissions")
    if allowed_tools:
        extra_args += ["--allowed-tools", ",".join(allowed_tools)]
        
    return chat_generic_cli(
        prompt,
        binary=binary or "claude",
        conversation_mode="separate",
        extra_args=extra_args,
        prepend_system_prompt=False,
        cwd=cwd,
        system_prompt=system_prompt,
        session_id=session_id,
        resume_session_id=resume_session_id,
        timeout=timeout,
        on_log=on_log,
        log_prefix="CLAUDE",
        run_cli_fn=run_cli,
    )
