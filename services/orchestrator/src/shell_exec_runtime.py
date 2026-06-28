"""SHELL_EXEC: run claude -p inside a long-lived ShellSession bash PTY."""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from src.claude_hybrid_output_parser import ClaudeHybridOutputParser, marker_completed_in_output, parse_hybrid_claude_output
from src.hybrid_audit_log import (
    HybridTurnResult,
    append_hybrid_turn_audit,
    build_turn_audit_line,
    summarize_shell_command,
)
from src.shell_session import (
    ShellSession,
    ShellSessionError,
    read_until_marker,
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


def _build_agy_shell_cmd(
    *,
    agy_binary: str,
    prompt: str,
    marker: str,
    conversation_id: str | None,
    system_prompt: str | None = None,
) -> str:
    effective = prompt
    if system_prompt:
        effective = f"{system_prompt}\n\nUser Request:\n{prompt}"
    agy_args: list[str] = [f"{agy_binary} -p \"$CLUTCH_P\""]
    if conversation_id:
        agy_args.append(f"--conversation {conversation_id}")
    agy_args.append("--dangerously-skip-permissions")
    agy_line = " ".join(agy_args)
    return (
        f"CLUTCH_P={_shell_quote(effective)}; "
        f"{agy_line}; "
        f"echo {marker}"
    )


def _record_hybrid_turn_audit(
    session: ShellSession,
    *,
    agent: str,
    turn_id: str,
    marker: str,
    cmd: str,
    duration_ms: int,
    result: HybridTurnResult,
    cli_session_id: str | None,
    message: str,
) -> None:
    append_hybrid_turn_audit(
        build_turn_audit_line(
            run_id=session.run_id,
            turn_id=turn_id,
            marker=marker,
            duration_ms=duration_ms,
            result=result,
            cli_session_id=cli_session_id,
            agent=agent,
            command_summary=summarize_shell_command(cmd) if cmd else "",
            node_id=session.owner_node_id,
            message=message,
        )
    )


def _execute_hybrid_turn(
    session: ShellSession,
    *,
    agent: Literal["claude", "agy"],
    cmd: str,
    marker: str,
    turn_id: str,
    timeout_s: float,
    system_prompt: str | None,
    cli_session_id: str | None,
    on_lock_wait: Callable[[], None] | None = None,
) -> ShellExecResult:
    import os

    def _run_turn() -> ShellExecResult:
        run_id = session.run_id
        start = time.monotonic()
        result: HybridTurnResult = "error"
        message = ""

        try:
            write_line(session.master_fd, cmd)
            raw = read_until_marker(session.master_fd, marker, max_wait_s=timeout_s)
            if not marker_completed_in_output(raw, marker):
                result = "timeout"
                message = f"hybrid {agent} turn timed out waiting for marker {marker}"
                raise ShellSessionError(message)
            parsed = ClaudeHybridOutputParser().parse_structured(
                raw,
                marker=marker,
                shell_command=cmd,
                system_prompt=system_prompt,
            )
            if not parsed.assistant:
                result = "empty"
                message = f"hybrid {agent} turn produced empty stdout"
                raise ShellSessionError(message)
            result = "ok"
            message = f"hybrid {agent} turn ok marker={marker}"
            return ShellExecResult(
                stdout=parsed.assistant,
                logs=[f"[HYBRID] {agent} exec in shell session {run_id}"],
                cli_session_id=cli_session_id,
                raw_output=parsed.raw,
                output_events=parsed.output_event_dicts(),
            )
        except ShellSessionError as exc:
            if result == "error":
                lowered = str(exc).lower()
                if "timed out" in lowered:
                    result = "timeout"
                elif "empty stdout" in lowered:
                    result = "empty"
            message = str(exc)
            raise
        except Exception as exc:
            message = str(exc)
            raise
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            _record_hybrid_turn_audit(
                session,
                agent=agent,
                turn_id=turn_id,
                marker=marker,
                cmd=cmd,
                duration_ms=duration_ms,
                result=result,
                cli_session_id=cli_session_id,
                message=message or f"hybrid {agent} turn {result}",
            )

    if os.environ.get("CLUTCH_E2E_FAKE_HYBRID") == "1":
        return _run_turn()

    from src.workspace_cli_lock import workspace_cli_turn

    with workspace_cli_turn(
        session.workspace_path,
        timeout_s=timeout_s,
        on_waiting=on_lock_wait,
    ):
        return _run_turn()


def run_agy_turn(
    session: ShellSession,
    *,
    prompt: str,
    agy_binary: str,
    timeout_s: float,
    cli_session_id: str | None = None,
    resume_session_id: str | None = None,
    new_session_id: str | None = None,
    context_prefix: str | None = None,
    system_prompt: str | None = None,
    on_lock_wait: Callable[[], None] | None = None,
) -> ShellExecResult:
    turn_id = uuid.uuid4().hex[:8]
    try:
        assert_no_interactive_command(prompt)
    except InteractiveCommandBlocked as exc:
        _record_hybrid_turn_audit(
            session,
            agent="agy",
            turn_id=turn_id,
            marker="",
            cmd="",
            duration_ms=0,
            result="blocked",
            cli_session_id=resume_session_id or cli_session_id,
            message=str(exc),
        )
        raise

    effective_prompt = prompt
    if context_prefix:
        effective_prompt = f"{context_prefix.strip()}\n\n{prompt}"

    session.ensure_workspace_cwd()
    marker = f"__CLUTCH_DONE_{turn_id}__"
    conv_id = new_session_id or resume_session_id or cli_session_id
    cmd = _build_agy_shell_cmd(
        agy_binary=agy_binary,
        prompt=effective_prompt,
        marker=marker,
        conversation_id=conv_id,
        system_prompt=system_prompt if not conv_id else None,
    )
    turn = _execute_hybrid_turn(
        session,
        agent="agy",
        cmd=cmd,
        marker=marker,
        turn_id=turn_id,
        timeout_s=timeout_s,
        system_prompt=system_prompt,
        cli_session_id=conv_id,
        on_lock_wait=on_lock_wait,
    )
    return ShellExecResult(
        stdout=turn.stdout,
        logs=turn.logs,
        cli_session_id=conv_id,
        raw_output=turn.raw_output,
        output_events=turn.output_events,
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
    on_lock_wait: Callable[[], None] | None = None,
) -> ShellExecResult:
    import os

    effective_prompt = prompt
    if context_prefix:
        effective_prompt = f"{context_prefix.strip()}\n\n{prompt}"

    if os.environ.get("CLUTCH_E2E_FAKE_HYBRID") == "1":
        delay = float(os.environ.get("CLUTCH_E2E_FAKE_HYBRID_DELAY", "0.15"))
        if delay > 0:
            time.sleep(delay)
        sid = new_session_id or resume_session_id or cli_session_id or uuid.uuid4().hex
        reply = f"E2E hybrid ({session.run_id}): {effective_prompt.strip()[:120]}"
        return ShellExecResult(
            stdout=reply,
            logs=[f"[HYBRID] e2e-fake claude turn in shell session {session.run_id}"],
            cli_session_id=sid,
            raw_output=f"CLUTCH_P={_shell_quote(effective_prompt[:40])}; claude -p (e2e-fake)",
            output_events=[
                {"type": "shell_echo", "visible": False, "content": "claude -p (e2e-fake)"},
                {"type": "assistant", "visible": True, "content": reply},
            ],
        )

    turn_id = uuid.uuid4().hex[:8]
    try:
        assert_no_interactive_command(prompt)
    except InteractiveCommandBlocked as exc:
        _record_hybrid_turn_audit(
            session,
            agent="claude",
            turn_id=turn_id,
            marker="",
            cmd="",
            duration_ms=0,
            result="blocked",
            cli_session_id=resume_session_id or cli_session_id or new_session_id,
            message=str(exc),
        )
        raise

    session.ensure_workspace_cwd()
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
    out_session = bootstrap_id or sid or cli_session_id
    turn = _execute_hybrid_turn(
        session,
        agent="claude",
        cmd=cmd,
        marker=marker,
        turn_id=turn_id,
        timeout_s=timeout_s,
        system_prompt=system_prompt,
        cli_session_id=out_session,
        on_lock_wait=on_lock_wait,
    )
    return ShellExecResult(
        stdout=turn.stdout,
        logs=turn.logs,
        cli_session_id=out_session,
        raw_output=turn.raw_output,
        output_events=turn.output_events,
    )
