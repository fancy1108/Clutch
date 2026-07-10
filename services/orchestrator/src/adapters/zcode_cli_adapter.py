"""ZCode CLI adapter (adds first-class support for Z.AI ZCode as a routable CLI engine).

ZCode is a headless-capable AI coding CLI shipped with the ZCode desktop app.
Its `zcode` binary lives at
`/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs` (a Node CJS script);
users typically expose it via a shim on their PATH.

Headless invocation shape mirrors Claude Code CLI:
    zcode -p "<prompt>" --mode yolo --json [--cwd <path>] [--resume <sess_...>]

Notes vs Codex CLI (a superficially similar engine):
- ZCode uses a print-flag (`-p`) rather than positional prompt; no `exec` subcommand.
- Permission mode is controlled by `--mode {plan,build,edit,yolo}`; `yolo`
  bypasses per-turn approvals and is the equivalent of
  `--dangerously-skip-permissions` on other CLIs.
- Session resumption uses `--resume <sessionId>` with `sess_...`-prefixed ids.
- `--json` emits a machine-readable envelope Clutch can parse.
"""

from __future__ import annotations

import os
from collections.abc import Callable

from src.adapters.cli_adapter import run_cli

_DEFAULT_CHAT_TIMEOUT_SEC = float(os.environ.get("CLUTCH_ZCODE_CLI_TIMEOUT", "600"))


def _stream_cli_line(on_log: Callable[[str], None], stream: str, line: str) -> None:
    if not line:
        return
    prefix = "[ZCODE CLI]" if stream == "stdout" else "[ZCODE CLI stderr]"
    on_log(f"{prefix} {line}")


def chat_zcode_cli(
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
    """Call local `zcode` CLI in headless print mode, return response text."""
    from src.adapters.cli_adapter import chat_generic_cli

    extra_args: list[str] = ["--json"]
    # `yolo` mode ≈ --dangerously-skip-permissions on other CLIs
    extra_args += ["--mode", "yolo" if dangerously_skip_permissions else "edit"]
    if disallowed_tools:
        extra_args += ["--disallowed-tools", ",".join(disallowed_tools)]

    return chat_generic_cli(
        prompt,
        binary=binary or "zcode",
        conversation_mode="separate",
        extra_args=extra_args,
        prepend_system_prompt=False,
        cwd=cwd,
        system_prompt=system_prompt,
        session_id=session_id,
        resume_session_id=resume_session_id,
        timeout=timeout or _DEFAULT_CHAT_TIMEOUT_SEC,
        on_log=on_log,
        log_prefix="ZCODE",
        run_cli_fn=run_cli,
    )
