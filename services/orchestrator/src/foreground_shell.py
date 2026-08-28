"""D34 — track foreground shell commands and transfer to bg_jobs."""

from __future__ import annotations

import contextvars
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any

from src.shell_proc import command_key, kill_tree, popen_shell

ForegroundNotifier = Callable[[str, dict[str, Any] | None], None]

_fg_context: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "foreground_shell_context", default=None
)
_active: dict[str, "_ForegroundCmd"] = {}
_lock = threading.Lock()
_notifiers: dict[str, ForegroundNotifier] = {}


def bind_foreground_context(ctx: dict[str, Any]) -> contextvars.Token[dict[str, Any] | None]:
    return _fg_context.set(ctx)


def release_foreground_context(token: contextvars.Token[dict[str, Any] | None]) -> None:
    _fg_context.reset(token)


def get_foreground_context() -> dict[str, Any] | None:
    return _fg_context.get()


def register_foreground_notifier(run_id: str, notifier: ForegroundNotifier) -> None:
    _notifiers[run_id] = notifier


def unregister_foreground_notifier(run_id: str) -> None:
    _notifiers.pop(run_id, None)


class _ForegroundCmd:
    def __init__(self, run_id: str, command: str, cwd: str, proc: subprocess.Popen[str]) -> None:
        self.run_id = run_id
        self.command = command
        self.cwd = cwd
        self.proc = proc
        self.transferred = False
        self._buffer: list[str] = []
        self._reader_done = threading.Event()
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()

    def _read_stdout(self) -> None:
        try:
            if self.proc.stdout is not None:
                for line in self.proc.stdout:
                    if self.transferred:
                        break
                    self._buffer.append(line)
        finally:
            self._reader_done.set()

    def output_so_far(self) -> str:
        return "".join(self._buffer)

    def title_snippet(self) -> str:
        cmd = self.command.strip()
        return cmd[:60] + ("…" if len(cmd) > 60 else "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "title": self.title_snippet(),
            "cwd": self.cwd,
        }


def _notify(run_id: str, payload: dict[str, Any] | None) -> None:
    notifier = _notifiers.get(run_id)
    if notifier:
        notifier(run_id, payload)


def _try_idle_hybrid_shell(run_id: str) -> bool:
    """True when hybrid shell session exists and is idle (preferred bg launcher)."""
    try:
        from src.shell_session import get_shell_session_manager, SessionState

        manager = get_shell_session_manager()
        with manager._lock:
            session = manager._sessions.get(run_id)
            if session is None or session.state == SessionState.TERMINATED:
                return False
            return session.state in (SessionState.IDLE, SessionState.READY) and session.alive()
    except Exception:
        return False


def occupying_foreground(run_id: str) -> str | None:
    with _lock:
        cmd = _active.get(run_id)
        if cmd is None or cmd.transferred or cmd.proc.poll() is not None:
            return None
        return cmd.command


def running_commands(run_id: str) -> list[str]:
    cmds: list[str] = []
    fg = occupying_foreground(run_id)
    if fg:
        cmds.append(fg)
    from src.bg_jobs import list_jobs

    for job in list_jobs(run_id):
        if job.get("status") == "running":
            raw = str(job.get("command") or "").strip()
            if raw:
                cmds.append(raw)
    return cmds


def already_running_command(run_id: str, command: str) -> str | None:
    key = command_key(command)
    if not key:
        return None
    for other in running_commands(run_id):
        if command_key(other) == key:
            return other
    return None


def start_foreground(run_id: str, command: str, cwd: str) -> _ForegroundCmd:
    trimmed = command.strip()
    with _lock:
        existing = _active.get(run_id)
        if existing and not existing.transferred and existing.proc.poll() is None:
            raise RuntimeError(
                f"Foreground command already running: {existing.command[:80]}"
            )
    proc = popen_shell(trimmed, cwd)
    cmd = _ForegroundCmd(run_id, trimmed, cwd, proc)
    with _lock:
        existing = _active.get(run_id)
        if existing and not existing.transferred and existing.proc.poll() is None:
            kill_tree(proc)
            raise RuntimeError(
                f"Foreground command already running: {existing.command[:80]}"
            )
        _active[run_id] = cmd
    _notify(run_id, cmd.to_dict())
    return cmd


def get_foreground(run_id: str) -> dict[str, Any] | None:
    with _lock:
        cmd = _active.get(run_id)
    return cmd.to_dict() if cmd else None


def clear_foreground(run_id: str) -> None:
    with _lock:
        _active.pop(run_id, None)
    _notify(run_id, None)


def wait_foreground(
    run_id: str,
    *,
    timeout_sec: float,
    poll_interval: float = 0.15,
) -> tuple[str, bool, int | None]:
    """Wait for foreground proc; return (output, transferred, exit_code)."""
    with _lock:
        cmd = _active.get(run_id)
    if cmd is None:
        return "", False, None

    deadline = time.monotonic() + max(1.0, timeout_sec)
    exit_code: int | None = None
    while time.monotonic() < deadline:
        if cmd.transferred:
            return cmd.output_so_far(), True, None
        if cmd.proc.poll() is not None:
            exit_code = cmd.proc.returncode
            cmd._reader_done.wait(timeout=2.0)
            break
        time.sleep(poll_interval)

    if not cmd.transferred and cmd.proc.poll() is None:
        job = transfer_to_background(run_id)
        if job is not None:
            return cmd.output_so_far(), True, None
        kill_tree(cmd.proc)
        exit_code = cmd.proc.poll() if cmd.proc.poll() is not None else -1

    output = cmd.output_so_far()
    transferred = cmd.transferred
    with _lock:
        if _active.get(run_id) is cmd:
            _active.pop(run_id, None)
    if not transferred:
        _notify(run_id, None)
    return output, transferred, exit_code


def transfer_to_background(run_id: str) -> dict[str, Any] | None:
    with _lock:
        cmd = _active.get(run_id)
        if cmd is None or cmd.transferred:
            return None
        cmd.transferred = True
        proc = cmd.proc
        command = cmd.command
        cwd = cmd.cwd
        output = cmd.output_so_far()
        _active.pop(run_id, None)

    from src.bg_jobs import adopt_process, start_job

    if proc.poll() is None:
        job = adopt_process(run_id, command, cwd, proc, output)
    else:
        # Process already finished — still register terminal state in bg list.
        job = start_job(run_id, command, cwd)
    _notify(run_id, None)
    return job

