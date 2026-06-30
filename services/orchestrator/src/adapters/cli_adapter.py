"""CLI subprocess adapter (M3-01)."""

from __future__ import annotations

import os
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from src.claude_hybrid_output_parser import extract_cli_issue_message, extract_codex_assistant_output, extract_tty_cli_output
from src.preferences_storage import tr

if os.name != "nt":
    import pty
    import select


@dataclass(frozen=True)
class CliResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class CliAdapterError(RuntimeError):
    pass


def _timeout_error(command: list[str], timeout: float) -> CliAdapterError:
    binary = command[0] if command else "cli"
    return CliAdapterError(
        tr(
            f"`{binary}` timed out after {timeout:g}s. "
            "Try a simpler prompt, or set CLUTCH_CLAUDE_CLI_TIMEOUT (seconds).",
            f"`{binary}` 在 {timeout:g} 秒后超时。"
            "可尝试更简短的指令，或设置环境变量 CLUTCH_CLAUDE_CLI_TIMEOUT（秒）。",
        )
    )


def _drain_stream(
    pipe,
    chunks: list[str],
    stream: str,
    on_line: Callable[[str, str], None] | None,
) -> None:
    try:
        for line in iter(pipe.readline, ""):
            chunks.append(line)
            if on_line and line:
                on_line(stream, line.rstrip("\n\r"))
    finally:
        pipe.close()


def _run_cli_streaming(
    command: list[str],
    *,
    cwd: str | None,
    timeout: float,
    on_line: Callable[[str, str], None],
) -> CliResult:
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=_cli_subprocess_env(command),
    )
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    threads = [
        threading.Thread(
            target=_drain_stream,
            args=(proc.stdout, stdout_chunks, "stdout", on_line),
            daemon=True,
        ),
        threading.Thread(
            target=_drain_stream,
            args=(proc.stderr, stderr_chunks, "stderr", on_line),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()
    try:
        exit_code = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.wait()
        for thread in threads:
            thread.join()
        raise _timeout_error(command, timeout) from exc
    for thread in threads:
        thread.join()
    return CliResult(
        command=command,
        exit_code=exit_code,
        stdout="".join(stdout_chunks),
        stderr="".join(stderr_chunks),
    )


def _is_agy_binary(binary: str) -> bool:
    return binary.rsplit("/", 1)[-1] == "agy"


def _is_codex_binary(binary: str) -> bool:
    return binary.rsplit("/", 1)[-1] == "codex"


_RIVET_BINARY_NAMES: frozenset[str] = frozenset({"rivet", "t9"})


def is_rivet_binary(binary: str) -> bool:
    """True for Tianshu / Rivet CLI binaries (rivet, legacy t9)."""
    return binary.rsplit("/", 1)[-1] in _RIVET_BINARY_NAMES


def _cli_subprocess_env(command: list[str]) -> dict[str, str] | None:
    """Headless Rivet requires RIVET_FORCE_RECOVERY_CLI when Clutch spawns subprocesses."""
    if not command or not is_rivet_binary(command[0]):
        return None
    env = os.environ.copy()
    env["RIVET_FORCE_RECOVERY_CLI"] = "1"
    return env


def format_cli_issue_for_user(message: str, agent_type: str | None = None) -> str:
    """Turn agy quota/auth lines into a clear chat-visible message."""
    _ = agent_type
    lowered = message.lower()
    if "quota" in lowered or "rate limit" in lowered:
        return tr(
            f"Antigravity CLI quota limit reached. {message}",
            f"Antigravity CLI 配额已用尽。{message}",
        )
    if "authentication" in lowered:
        return tr(
            f"Antigravity CLI is not signed in. Run `agy` in a terminal to authenticate. ({message})",
            f"Antigravity CLI 未登录。请在终端运行 `agy` 完成登录。（{message}）",
        )
    return message


def _finalize_cli_content(content: str, *, raw: str = "") -> str:
    text = content.strip()
    if text:
        if extract_cli_issue_message(text):
            return format_cli_issue_for_user(text)
        return text
    issue = extract_cli_issue_message(raw) if raw else None
    if issue:
        return format_cli_issue_for_user(issue)
    return text


def run_cli_pty(
    command: list[str],
    *,
    cwd: str | None = None,
    timeout: float = 30.0,
    on_line: Callable[[str, str], None] | None = None,
) -> CliResult:
    """Run a CLI attached to a fresh PTY (required for `agy -p` headless capture)."""
    if not command:
        raise CliAdapterError(tr("CLI command cannot be empty", "CLI 命令不能为空"))

    if os.name == "nt":
        from src.windows_pty import run_windows_pty

        try:
            exit_code, raw = run_windows_pty(
                command,
                cwd=cwd,
                timeout=timeout,
                on_output=(lambda chunk: on_line("stdout", chunk)) if on_line else None,
            )
        except subprocess.TimeoutExpired as exc:
            raise _timeout_error(command, timeout) from exc
        stdout = _finalize_cli_content(extract_tty_cli_output(raw), raw=raw)
        result = CliResult(command=command, exit_code=exit_code, stdout=stdout, stderr=raw if not stdout else "")
        if not result.ok:
            raise CliAdapterError(f"CLI 退出码 {result.exit_code}: {stdout.strip() or raw.strip()}")
        return result

    master_fd, slave_fd = pty.openpty()
    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            env=_cli_subprocess_env(command),
        )
    except Exception:
        os.close(master_fd)
        os.close(slave_fd)
        raise
    os.close(slave_fd)

    raw_chunks: list[bytes] = []
    deadline = time.monotonic() + timeout
    try:
        while True:
            if proc.poll() is not None:
                while True:
                    ready, _, _ = select.select([master_fd], [], [], 0.05)
                    if not ready:
                        break
                    chunk = os.read(master_fd, 65536)
                    if not chunk:
                        break
                    raw_chunks.append(chunk)
                    if on_line:
                        on_line("stdout", chunk.decode("utf-8", errors="replace"))
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                proc.kill()
                proc.wait()
                raise _timeout_error(command, timeout)
            ready, _, _ = select.select([master_fd], [], [], min(remaining, 1.0))
            if ready:
                chunk = os.read(master_fd, 65536)
                if chunk:
                    raw_chunks.append(chunk)
                    if on_line:
                        on_line("stdout", chunk.decode("utf-8", errors="replace"))
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.wait()
        raise _timeout_error(command, timeout) from exc
    finally:
        os.close(master_fd)

    raw = b"".join(raw_chunks).decode("utf-8", errors="replace")
    stdout = _finalize_cli_content(extract_tty_cli_output(raw), raw=raw)
    exit_code = proc.returncode if proc.returncode is not None else 1
    result = CliResult(command=command, exit_code=exit_code, stdout=stdout, stderr=raw if not stdout else "")
    if not result.ok:
        detail = stdout.strip() or raw.strip()
        raise CliAdapterError(f"CLI 退出码 {result.exit_code}: {detail}")
    return result


def run_cli(
    command: list[str],
    *,
    cwd: str | None = None,
    timeout: float = 30.0,
    on_line: Callable[[str, str], None] | None = None,
) -> CliResult:
    if not command:
        raise CliAdapterError(tr("CLI command cannot be empty", "CLI 命令不能为空"))
    try:
        if on_line is not None:
            result = _run_cli_streaming(command, cwd=cwd, timeout=timeout, on_line=on_line)
        else:
            proc = subprocess.run(
                command,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                env=_cli_subprocess_env(command),
            )
            result = CliResult(
                command=command,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
    except subprocess.TimeoutExpired as exc:
        raise _timeout_error(command, timeout) from exc
    if not result.ok:
        raise CliAdapterError(
            f"CLI 退出码 {result.exit_code}: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result


def compose_cli_argv(
    *,
    binary: str,
    effective_prompt: str,
    prompt_flag: str = "-p",
    conversation_mode: str = "separate",
    session_id: str | None = None,
    resume_session_id: str | None = None,
    prepend_system_prompt: bool = False,
    system_prompt: str | None = None,
    supports_append_system_prompt: bool = True,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build argv for a non-interactive CLI turn (subcommand/flags before prompt)."""
    cmd: list[str] = [binary]
    if extra_args:
        cmd.extend(extra_args)

    if conversation_mode == "resume_or_new":
        if resume_session_id:
            cmd += ["--conversation", resume_session_id]
    elif conversation_mode == "separate":
        if resume_session_id:
            cmd += ["--resume", resume_session_id]
        elif session_id:
            cmd += ["--session-id", session_id]
    elif conversation_mode == "none":
        if resume_session_id:
            cmd += ["--conversation", resume_session_id]
    elif conversation_mode == "history_only":
        pass

    if prompt_flag:
        cmd += [prompt_flag, effective_prompt]
    else:
        cmd.append(effective_prompt)

    if not prepend_system_prompt and system_prompt and supports_append_system_prompt:
        cmd += ["--append-system-prompt", system_prompt]

    return cmd


def chat_generic_cli(
    prompt: str,
    *,
    binary: str,
    conversation_mode: str = "separate",
    extra_args: list[str] | None = None,
    prepend_system_prompt: bool = False,
    cwd: str | None = None,
    system_prompt: str | None = None,
    session_id: str | None = None,
    resume_session_id: str | None = None,
    timeout: float | None = None,
    on_log: Callable[[str], None] | None = None,
    log_prefix: str | None = None,
    run_cli_fn: Callable = run_cli,
    prompt_flag: str = "-p",
    supports_append_system_prompt: bool = True,
) -> str:
    """Call local CLI in print mode, return response text."""
    if session_id and resume_session_id:
        raise ValueError("session_id and resume_session_id are mutually exclusive")
    
    effective_prompt = prompt
    if system_prompt and (prepend_system_prompt or not supports_append_system_prompt):
        effective_prompt = f"{system_prompt}\n\nUser Request:\n{prompt}"

    cmd = compose_cli_argv(
        binary=binary,
        effective_prompt=effective_prompt,
        prompt_flag=prompt_flag,
        conversation_mode=conversation_mode,
        session_id=session_id,
        resume_session_id=resume_session_id,
        prepend_system_prompt=prepend_system_prompt,
        system_prompt=system_prompt,
        supports_append_system_prompt=supports_append_system_prompt,
        extra_args=extra_args,
    )

    effective_timeout = timeout if timeout is not None else 600.0
    
    prefix = log_prefix if log_prefix is not None else binary.split("/")[-1].split(".")[0].upper()
    on_line = None
    if on_log is not None:
        on_log(f"[{prefix} CLI] Executing `{cmd[0]}` (timeout {effective_timeout:g}s)")
        on_line = lambda stream, line: on_log(
            f"[{prefix} CLI] {line}" if stream == "stdout" else f"[{prefix} CLI stderr] {line}"
        )

    effective_run_cli = run_cli_fn
    if effective_run_cli is run_cli and _is_agy_binary(binary):
        effective_run_cli = run_cli_pty

    result = effective_run_cli(cmd, cwd=cwd, timeout=effective_timeout, on_line=on_line)
    if on_log is not None:
        on_log(f"[{prefix} CLI] Exit code {result.exit_code}")
    if _is_codex_binary(binary):
        stdout_text = extract_codex_assistant_output(result.stdout) or extract_tty_cli_output(result.stdout)
    else:
        stdout_text = result.stdout
    content = _finalize_cli_content(stdout_text, raw=result.stderr)
    if not content:
        stderr = result.stderr.strip()
        if stderr and not stderr.lower().startswith("warning:"):
            content = _finalize_cli_content(extract_cli_issue_message(stderr) or stderr, raw=stderr)
    return content


_CLI_BINARY_LABELS: dict[str, str] = {
    "claude-cli": "claude",
    "antigravity-cli": "agy",
    "agy-cli": "agy",
    "codex-cli": "codex",
    "aider-cli": "aider",
    "rivet-cli": "rivet",
}


def _cli_binary_label(agent_type: str | None) -> str:
    key = (agent_type or "").strip().lower()
    return _CLI_BINARY_LABELS.get(key, key.replace("-cli", "") or "cli")


def is_cli_auth_issue(text: str) -> bool:
    lowered = (text or "").lower()
    return any(
        token in lowered
        for token in (
            "authentication required",
            "please visit the url",
            "waiting for authentication",
            "sign in",
            "not signed in",
            "login required",
        )
    )


def is_formatted_login_retry_message(text: str) -> bool:
    lowered = (text or "").lower()
    return (
        "complete auth in terminal" in lowered
        or "请在终端" in (text or "")
        or "重新运行" in (text or "")
        or "重试" in (text or "")
    )


def format_cli_login_retry_message(
    agent_type: str,
    *,
    raw_message: str = "",
) -> str:
    binary = _cli_binary_label(agent_type)
    detail = ""
    raw = (raw_message or "").strip()
    if raw:
        if "世界观" in raw or len(raw) > 240 or "workflow" in raw.lower():
            from src.claude_hybrid_output_parser import extract_cli_issue_message

            issue = extract_cli_issue_message(raw) or ""
            if issue and len(issue) <= 240:
                detail = f" ({issue})"
        else:
            detail = f" ({raw})"
    return tr(
        f"CLI sign-in required for `{binary}`. Complete auth in Terminal, then retry this step.{detail}",
        f"`{binary}` 需要登录。请在终端完成认证后重新运行此步骤。{detail}",
    )


def format_cli_empty_output_message(agent_type: str | None) -> str:
    binary = _cli_binary_label(agent_type)
    return tr(
        f"`{binary}` CLI finished but returned no text.",
        f"`{binary}` CLI 已结束，但未返回文本。",
    )


def format_flow_cli_failure(display_name: str, agent_type: str | None, exc: BaseException) -> str:
    return tr(
        f"Could not run task with {display_name}. ({exc})",
        f"无法使用 {display_name} 执行任务。（{exc}）",
    )


def is_agent_task_failure(output: str) -> bool:
    text = (output or "").strip()
    if not text:
        return True
    lowered = text.lower()
    if is_formatted_login_retry_message(text):
        return True
    if "returned empty output" in lowered or "returned no text" in lowered or "未返回文本" in text:
        return True
    if format_cli_empty_output_message(None).split(".")[0].lower() in lowered:
        return True
    return False
