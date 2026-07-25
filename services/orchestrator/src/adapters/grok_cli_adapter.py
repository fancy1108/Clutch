"""D14 — external xAI Grok CLI adapter (`grok -p`, when on PATH)."""

from __future__ import annotations

from collections.abc import Callable

from src.adapters.cli_adapter import chat_generic_cli


def chat_grok_cli(
    prompt: str,
    *,
    cwd: str | None = None,
    system_prompt: str | None = None,
    session_id: str | None = None,
    resume_session_id: str | None = None,
    dangerously_skip_permissions: bool = True,
    allowed_tools: list[str] | None = None,
    disallowed_tools: list[str] | None = None,
    timeout: float | None = None,
    binary: str | None = None,
    on_log: Callable[[str], None] | None = None,
) -> str:
    extra_args: list[str] = []
    if dangerously_skip_permissions:
        extra_args.append("--dangerously-skip-permissions")
    return chat_generic_cli(
        prompt,
        binary=binary or "grok",
        conversation_mode="separate",
        extra_args=extra_args,
        prepend_system_prompt=False,
        cwd=cwd,
        system_prompt=system_prompt,
        session_id=session_id,
        resume_session_id=resume_session_id,
        on_log=on_log,
        prompt_flag="-p",
        supports_append_system_prompt=False,
        timeout=timeout,
    )
