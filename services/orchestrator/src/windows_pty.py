"""ConPTY wrapper used by Windows CLI and Hybrid shell execution."""

import os
import subprocess
import time
from collections.abc import Callable


class WindowsPty:
    def __init__(self, command: list[str], *, cwd: str | None = None) -> None:
        from winpty import PTY

        if not command:
            raise ValueError("PTY command cannot be empty")
        self._pty = PTY(200, 30)
        cmdline = subprocess.list2cmdline(command[1:])
        self._pty.spawn(command[0], cmdline, cwd, None)

    @property
    def pid(self) -> int:
        return int(self._pty.pid)

    def isalive(self) -> bool:
        return bool(self._pty.isalive())

    def read(self, *, wait_s: float = 0.0) -> str:
        deadline = time.monotonic() + wait_s
        while True:
            chunk = str(self._pty.read(False) or "")
            if chunk or time.monotonic() >= deadline:
                return chunk
            time.sleep(min(0.02, max(0.0, deadline - time.monotonic())))

    def write(self, text: str) -> None:
        self._pty.write(text)

    def exit_code(self) -> int:
        return int(self._pty.get_exitstatus() or 0)

    def close(self, *, force: bool = False) -> None:
        if self.isalive():
            if not force:
                self.write("exit\r\n")
                time.sleep(0.1)
            if self.isalive():
                subprocess.run(
                    ["taskkill", "/PID", str(self.pid), "/T", "/F"],
                    capture_output=True,
                    check=False,
                )
        self._pty.cancel_io()


def run_windows_pty(
    command: list[str],
    *,
    cwd: str | None,
    timeout: float,
    on_output: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    proc = WindowsPty(command, cwd=cwd)
    chunks: list[str] = []
    deadline = time.monotonic() + timeout
    try:
        while proc.isalive():
            if time.monotonic() >= deadline:
                proc.close(force=True)
                raise subprocess.TimeoutExpired(command, timeout)
            chunk = proc.read(wait_s=0.05)
            if chunk:
                chunks.append(chunk)
                if on_output:
                    on_output(chunk)
        for _ in range(20):
            chunk = proc.read()
            if not chunk:
                break
            chunks.append(chunk)
        return proc.exit_code(), "".join(chunks)
    finally:
        proc.close(force=True)
