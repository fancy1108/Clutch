"""SHELL_EXEC: run claude -p inside a long-lived ShellSession bash PTY."""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from src.adapters.cli_adapter import format_cli_issue_for_user, is_cli_auth_issue
from src.claude_hybrid_output_parser import (
    ClaudeHybridOutputParser,
    extract_cli_issue_message,
    extract_codex_assistant_output,
    marker_completed_in_output,
    parse_hybrid_claude_output,
    strip_ansi,
    _erase_backspaces,
    _extract_assistant_lines,
    _strip_shell_preamble,
)
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

_HYBRID_AGENT_TYPES: dict[str, str] = {
    "agy": "antigravity-cli",
    "antigravity": "antigravity-cli",
    "claude": "claude-cli",
    "codex": "codex-cli",
    "aider": "aider-cli",
}


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


def _is_codex_binary(binary: str) -> bool:
    return binary.rsplit("/", 1)[-1] == "codex"


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
    agent: str,
    cmd: str,
    marker: str,
    turn_id: str,
    timeout_s: float,
    system_prompt: str | None,
    user_prompt: str | None = None,
    cli_session_id: str | None,
    on_lock_wait: Callable[[], None] | None = None,
    use_codex_parser: bool = False,
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
            if use_codex_parser:
                assistant = extract_codex_assistant_output(raw, marker=marker)
                if assistant:
                    result = "ok"
                    message = f"hybrid {agent} turn ok marker={marker}"
                    return ShellExecResult(
                        stdout=assistant,
                        logs=[f"[HYBRID] {agent} exec in shell session {run_id}"],
                        cli_session_id=cli_session_id,
                        raw_output=raw,
                        output_events=[
                            {"type": "assistant", "visible": True, "content": assistant},
                        ],
                    )
            parsed = ClaudeHybridOutputParser().parse_structured(
                raw,
                marker=marker,
                shell_command=cmd,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            issue = extract_cli_issue_message(raw)
            if issue and is_cli_auth_issue(issue):
                formatted = format_cli_issue_for_user(
                    issue,
                    agent_type=_HYBRID_AGENT_TYPES.get(agent),
                )
                result = "ok"
                message = f"hybrid {agent} turn surfaced cli auth marker={marker}"
                return ShellExecResult(
                    stdout=formatted,
                    logs=[f"[HYBRID] {agent} exec in shell session {run_id}"],
                    cli_session_id=cli_session_id,
                    raw_output=raw,
                    output_events=[
                        {"type": "assistant", "visible": True, "content": formatted},
                    ],
                )
            if not parsed.assistant:
                if issue:
                    formatted = format_cli_issue_for_user(
                        issue,
                        agent_type=_HYBRID_AGENT_TYPES.get(agent),
                    )
                    result = "ok"
                    message = f"hybrid {agent} turn surfaced cli issue marker={marker}"
                    return ShellExecResult(
                        stdout=formatted,
                        logs=[f"[HYBRID] {agent} exec in shell session {run_id}"],
                        cli_session_id=cli_session_id,
                        raw_output=raw,
                        output_events=[
                            {"type": "assistant", "visible": True, "content": formatted},
                        ],
                    )
                fallback = _extract_assistant_lines(
                    _strip_shell_preamble(
                        _erase_backspaces(strip_ansi(raw)).replace("\r", ""),
                        marker=marker,
                    )
                )
                if fallback:
                    result = "ok"
                    message = f"hybrid {agent} turn ok (fallback parse) marker={marker}"
                    return ShellExecResult(
                        stdout=fallback,
                        logs=[f"[HYBRID] {agent} exec in shell session {run_id}"],
                        cli_session_id=cli_session_id,
                        raw_output=raw,
                        output_events=[
                            {"type": "assistant", "visible": True, "content": fallback},
                        ],
                    )
                result = "empty"
                message = f"hybrid {agent} turn produced empty stdout"
                from src.adapters.cli_adapter import format_cli_empty_output_message

                empty_msg = format_cli_empty_output_message(_HYBRID_AGENT_TYPES.get(agent))
                return ShellExecResult(
                    stdout=empty_msg,
                    logs=[f"[HYBRID] {agent} exec in shell session {run_id}", f"[HYBRID] {message}"],
                    cli_session_id=cli_session_id,
                    raw_output=raw,
                    output_events=[
                        {"type": "assistant", "visible": True, "content": empty_msg},
                    ],
                )
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


def _build_generic_cli_shell_cmd(
    *,
    binary: str,
    prompt: str,
    marker: str,
    new_session_id: str | None = None,
    resume_session_id: str | None = None,
    system_prompt: str | None = None,
    conversation_mode: str = "separate",
    extra_args: list[str] | None = None,
    prepend_system_prompt: bool = False,
    prompt_flag: str = "-p",
    supports_append_system_prompt: bool = True,
    close_stdin: bool = False,
) -> str:
    effective = prompt
    if system_prompt and prepend_system_prompt:
        effective = f"{system_prompt}\n\nUser Request:\n{prompt}"

    parts: list[str] = [binary]
    if extra_args:
        parts.extend(extra_args)

    if conversation_mode == "resume_or_new":
        if resume_session_id:
            parts.append(f"--conversation {resume_session_id}")
    elif conversation_mode == "separate":
        if new_session_id:
            parts.append(f"--session-id {new_session_id}")
        elif resume_session_id:
            parts.append(f"--resume {resume_session_id}")
    elif conversation_mode == "none":
        if resume_session_id:
            parts.append(f"--conversation {resume_session_id}")

    if prompt_flag:
        parts.append(f'{prompt_flag} "$CLUTCH_P"')
    else:
        parts.append('"$CLUTCH_P"')

    if not prepend_system_prompt and system_prompt and supports_append_system_prompt:
        parts.append(f"--append-system-prompt {_shell_quote(system_prompt)}")

    line = " ".join(parts)
    if close_stdin:
        line = f"{line} </dev/null"
    return (
        f"CLUTCH_P={_shell_quote(effective)}; "
        f"{line}; "
        f"echo {marker}"
    )


# Interactive bash PTY treats embedded newlines as multiple submissions; claude -p then
# never reaches the completion marker (see Flow step-2 Scriptwriter with upstream JSON).
HYBRID_PTY_MULTILINE_LINE_THRESHOLD = 10


def hybrid_pty_shell_command_risky(
    *,
    agent_type: str,
    binary: str,
    prompt: str,
    system_prompt: str | None = None,
    conversation_mode: str = "separate",
    extra_args: list[str] | None = None,
    prepend_system_prompt: bool = False,
    prompt_flag: str = "-p",
    supports_append_system_prompt: bool = True,
    close_stdin: bool = False,
) -> bool:
    """True when a hybrid shell line is too multiline for reliable PTY capture."""
    if agent_type.replace("-cli", "") != "claude":
        return False
    cmd = _build_generic_cli_shell_cmd(
        binary=binary,
        prompt=prompt,
        marker="__CLUTCH_PROBE__",
        new_session_id="probe",
        system_prompt=system_prompt,
        conversation_mode=conversation_mode,
        extra_args=extra_args,
        prepend_system_prompt=prepend_system_prompt,
        prompt_flag=prompt_flag,
        supports_append_system_prompt=supports_append_system_prompt,
        close_stdin=close_stdin,
    )
    return cmd.count("\n") > HYBRID_PTY_MULTILINE_LINE_THRESHOLD


def run_generic_cli_turn(
    session: ShellSession,
    *,
    agent_type: str,
    prompt: str,
    binary: str,
    timeout_s: float,
    conversation_mode: str,
    extra_args: list[str] | None = None,
    prepend_system_prompt: bool = False,
    cli_session_id: str | None = None,
    resume_session_id: str | None = None,
    new_session_id: str | None = None,
    context_prefix: str | None = None,
    system_prompt: str | None = None,
    on_lock_wait: Callable[[], None] | None = None,
    prompt_flag: str = "-p",
    supports_append_system_prompt: bool = True,
    close_stdin: bool = False,
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
            logs=[f"[HYBRID] e2e-fake {agent_type} turn in shell session {session.run_id}"],
            cli_session_id=sid,
            raw_output=f"CLUTCH_P={_shell_quote(effective_prompt[:40])}; {binary} {prompt_flag} (e2e-fake)",
            output_events=[
                {"type": "shell_echo", "visible": False, "content": f"{binary} {prompt_flag} (e2e-fake)"},
                {"type": "assistant", "visible": True, "content": reply},
            ],
        )

    turn_id = uuid.uuid4().hex[:8]
    try:
        assert_no_interactive_command(prompt)
    except InteractiveCommandBlocked as exc:
        _record_hybrid_turn_audit(
            session,
            agent=agent_type,
            turn_id=turn_id,
            marker="",
            cmd="",
            duration_ms=0,
            result="blocked",
            cli_session_id=new_session_id or resume_session_id or cli_session_id,
            message=str(exc),
        )
        raise

    session.ensure_workspace_cwd()
    marker = f"__CLUTCH_DONE_{turn_id}__"
    
    cmd = _build_generic_cli_shell_cmd(
        binary=binary,
        prompt=effective_prompt,
        marker=marker,
        new_session_id=new_session_id,
        resume_session_id=resume_session_id or cli_session_id,
        system_prompt=system_prompt,
        conversation_mode=conversation_mode,
        extra_args=extra_args,
        prepend_system_prompt=prepend_system_prompt,
        prompt_flag=prompt_flag,
        supports_append_system_prompt=supports_append_system_prompt,
        close_stdin=close_stdin,
    )
    conv_id = new_session_id or resume_session_id or cli_session_id
    
    turn = _execute_hybrid_turn(
        session,
        agent=agent_type,  # type: ignore
        cmd=cmd,
        marker=marker,
        turn_id=turn_id,
        timeout_s=timeout_s,
        system_prompt=system_prompt,
        user_prompt=effective_prompt,
        cli_session_id=conv_id,
        on_lock_wait=on_lock_wait,
        use_codex_parser=_is_codex_binary(binary),
    )
    return ShellExecResult(
        stdout=turn.stdout,
        logs=turn.logs,
        cli_session_id=conv_id,
        raw_output=turn.raw_output,
        output_events=turn.output_events,
    )


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
    return run_generic_cli_turn(
        session,
        agent_type="agy",
        prompt=prompt,
        binary=agy_binary,
        timeout_s=timeout_s,
        conversation_mode="none",
        extra_args=["--dangerously-skip-permissions"],
        prepend_system_prompt=False,
        cli_session_id=cli_session_id,
        resume_session_id=resume_session_id,
        new_session_id=new_session_id,
        context_prefix=context_prefix,
        system_prompt=system_prompt,
        on_lock_wait=on_lock_wait,
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
    return run_generic_cli_turn(
        session,
        agent_type="claude",
        prompt=prompt,
        binary=claude_binary,
        timeout_s=timeout_s,
        conversation_mode="separate",
        extra_args=["--dangerously-skip-permissions"],
        prepend_system_prompt=False,
        cli_session_id=cli_session_id,
        resume_session_id=resume_session_id,
        new_session_id=new_session_id,
        context_prefix=context_prefix,
        system_prompt=system_prompt,
        on_lock_wait=on_lock_wait,
    )
