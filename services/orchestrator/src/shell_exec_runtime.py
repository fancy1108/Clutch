"""SHELL_EXEC: run claude -p inside a long-lived ShellSession bash PTY."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from src.claude_hybrid_output_parser import ClaudeHybridOutputParser, parse_hybrid_claude_output
from src.shell_session import (
    ShellSession,
    ShellSessionError,
    read_until_marker,
    strip_ansi,
    write_line,
)

_INTERACTIVE_RE = re.compile(r"\b(vim|nano|less|more|top|htop|ssh)\b", re.I)


class InteractiveCommandBlocked(ShellSessionError):
    pass


@dataclass(frozen=True)
class ShellExecResult:
    stdout: str
    logs: list[str]
    cli_session_id: str | None
    raw_output: str | None = None
    output_events: list[dict[str, object]] | None = None


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def assert_no_interactive_command(text: str) -> None:
    if _INTERACTIVE_RE.search(text):
        raise InteractiveCommandBlocked("interactive shell command blocked in hybrid mode")


def extract_claude_output(plain: str, *, marker: str) -> str:
    return parse_hybrid_claude_output(plain, marker=marker)


def _build_claude_shell_cmd(
    *,
    claude_binary: str,
    prompt: str,
    marker: str,
    session_id: str | None,
    resume_session_id: str | None,
    system_prompt: str | None = None,
) -> str:
    claude_args: list[str] = [f"{claude_binary} -p \"$CLUTCH_P\""]
    if resume_session_id:
        claude_args.append(f"--resume {resume_session_id}")
    elif session_id:
        claude_args.append(f"--session-id {session_id}")
    if system_prompt:
        claude_args.append(f"--append-system-prompt {_shell_quote(system_prompt)}")
    claude_args.append("--dangerously-skip-permissions")
    claude_line = " ".join(claude_args)
    return (
        f"CLUTCH_P={_shell_quote(prompt)}; "
        f"{claude_line}; "
        f"echo {marker}"
    )


def run_claude_turn(
    session: ShellSession,
    *,
    prompt: str,
    claude_binary: str,
    timeout_s: float,
    cli_session_id: str | None = None,
    resume_session_id: str | None = None,
    new_session_id: str | None = None,
    context_prefix: str | None = None,
    system_prompt: str | None = None,
) -> ShellExecResult:
    assert_no_interactive_command(prompt)
    effective_prompt = prompt
    if context_prefix:
        effective_prompt = f"{context_prefix.strip()}\n\n{prompt}"

    session.ensure_workspace_cwd()
    turn_id = uuid.uuid4().hex[:8]
    marker = f"__CLUTCH_DONE_{turn_id}__"
    sid = resume_session_id or cli_session_id
    bootstrap_id = new_session_id
    cmd = _build_claude_shell_cmd(
        claude_binary=claude_binary,
        prompt=effective_prompt,
        marker=marker,
        session_id=bootstrap_id,
        resume_session_id=sid if not bootstrap_id else None,
        system_prompt=system_prompt if bootstrap_id else None,
    )
    logs = [f"[HYBRID] exec in shell session {session.run_id}"]
    write_line(session.master_fd, cmd)
    raw = read_until_marker(session.master_fd, marker, max_wait_s=timeout_s)
    plain = strip_ansi(raw)
    if marker not in plain:
        raise ShellSessionError(f"hybrid turn timed out waiting for marker {marker}")
    parsed = ClaudeHybridOutputParser().parse_structured(
        raw,
        marker=marker,
        shell_command=cmd,
        system_prompt=system_prompt,
    )
    if not parsed.assistant:
        raise ShellSessionError("hybrid turn produced empty stdout")
    out_session = bootstrap_id or sid or cli_session_id
    return ShellExecResult(
        stdout=parsed.assistant,
        logs=logs,
        cli_session_id=out_session,
        raw_output=parsed.raw,
        output_events=parsed.output_event_dicts(),
    )
