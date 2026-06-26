"""CLI subprocess adapter (M3-01)."""

from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass

from src.preferences_storage import tr


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
        bufsize=1,
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
                timeout=timeout,
                check=False,
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
