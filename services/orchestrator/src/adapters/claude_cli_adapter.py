"""Claude CLI adapter for subprocess execution (M3-01)."""

from __future__ import annotations

from src.adapters.cli_adapter import run_cli


def chat_claude_cli(
    prompt: str,
    *,
    cwd: str | None = None,
    system_prompt: str | None = None,
    dangerously_skip_permissions: bool = True,
    allowed_tools: list[str] | None = None,
    timeout: float = 120.0,
) -> str:
    """Call local `claude` CLI in print mode, return response text."""
    cmd = ["claude", "-p", prompt]
    if system_prompt:
        cmd += ["--append-system-prompt", system_prompt]
    if dangerously_skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    if allowed_tools:
        cmd += ["--allowed-tools", ",".join(allowed_tools)]

    result = run_cli(cmd, cwd=cwd, timeout=timeout)
    return result.stdout
