"""Spawn / kill shell commands as a process group (D11 / D34)."""

from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path


def command_key(command: str) -> str:
    return " ".join((command or "").split())


def popen_shell(command: str, cwd: str) -> subprocess.Popen[str]:
    shell = os.environ.get("SHELL") or ("cmd.exe" if os.name == "nt" else "/bin/bash")
    kwargs: dict[str, object] = {
        "args": command,
        "shell": True,
        "cwd": cwd,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
        "env": {**os.environ, "PWD": cwd},
        "executable": shell if os.name != "nt" and Path(shell).is_file() else None,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(**kwargs)  # type: ignore[arg-type]


def kill_tree(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
        )
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.terminate()
        except Exception:
            pass
    try:
        proc.wait(timeout=2)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except Exception:
            pass
    try:
        proc.wait(timeout=1)
    except Exception:
        pass
