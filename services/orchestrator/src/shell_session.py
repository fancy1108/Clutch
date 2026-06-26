"""Long-lived bash PTY ShellSession per run_id (SHELL_EXEC layer)."""

from __future__ import annotations

import os
import pty
import select
import shutil
import signal
import threading
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    CREATING = "creating"
    READY = "ready"
    BUSY = "busy"
    IDLE = "idle"
    DISCONNECTED = "disconnected"
    RECOVERING = "recovering"
    TERMINATED = "terminated"


class ShellSessionBusyError(RuntimeError):
    pass


class ShellSessionError(RuntimeError):
    pass


class ShellSessionPoolFullError(ShellSessionError):
    pass


from src.claude_hybrid_output_parser import marker_completed_in_output, strip_ansi


def _read_available(master_fd: int, *, wait_s: float) -> str:
    chunks: list[str] = []
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        r, _, _ = select.select([master_fd], [], [], min(0.2, remaining))
        if not r:
            continue
        try:
            data = os.read(master_fd, 65536)
        except OSError:
            break
        if not data:
            break
        chunks.append(data.decode(errors="replace"))
    return "".join(chunks)


def read_until_marker(master_fd: int, marker: str, *, max_wait_s: float) -> str:
    chunks: list[str] = []
    deadline = time.monotonic() + max_wait_s
    while time.monotonic() < deadline:
        chunk = _read_available(master_fd, wait_s=min(2.0, deadline - time.monotonic()))
        if chunk:
            chunks.append(chunk)
            if marker_completed_in_output("".join(chunks), marker):
                break
        elif chunks:
            time.sleep(0.1)
        else:
            time.sleep(0.05)
    return "".join(chunks)


def write_line(master_fd: int, line: str) -> None:
    os.write(master_fd, (line if line.endswith("\n") else line + "\n").encode())


def write_minimal_snapshot(*, run_id: str, cwd: str, workspace_path: str | None = None) -> Path:
    from src.session_snapshot import SessionSnapshot, save_snapshot

    snap = SessionSnapshot(
        run_id=run_id,
        workspace_path=workspace_path or cwd,
        cwd=cwd,
    )
    return save_snapshot(snap)


@dataclass
class ShellSession:
    run_id: str
    workspace_path: str
    owner_node_id: str = "plain_chat"
    state: SessionState = SessionState.CREATING
    master_fd: int = -1
    pid: int = -1
    created_at: float = field(default_factory=time.monotonic)
    last_activity_at: float = field(default_factory=time.monotonic)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def touch(self) -> None:
        self.last_activity_at = time.monotonic()

    def _spawn(self) -> None:
        shell = shutil.which("bash") or "/bin/bash"
        workspace = Path(self.workspace_path)
        workspace.mkdir(parents=True, exist_ok=True)
        pid, master_fd = pty.fork()
        if pid == 0:
            os.chdir(workspace)
            os.execvp(shell, [shell, "--norc", "--noprofile", "-i"])
            raise SystemExit(1)
        self.pid = pid
        self.master_fd = master_fd
        read_until_marker(master_fd, "$", max_wait_s=8.0)
        write_line(master_fd, "export COLUMNS=200 PS1='clutch$ '")
        read_until_marker(master_fd, "clutch$", max_wait_s=3.0)
        self.ensure_workspace_cwd()
        self.state = SessionState.READY
        self.touch()

    def ensure_workspace_cwd(self) -> None:
        if self.master_fd < 0:
            raise ShellSessionError("session not started")
        write_line(self.master_fd, f"cd {self.workspace_path}")
        read_until_marker(self.master_fd, "clutch$", max_wait_s=5.0)

    def alive(self) -> bool:
        if self.pid <= 0:
            return False
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False

    def close(self, *, write_snapshot: bool = True) -> None:
        cwd = self.workspace_path
        if write_snapshot and self.run_id:
            try:
                write_minimal_snapshot(
                    run_id=self.run_id,
                    cwd=cwd,
                    workspace_path=self.workspace_path,
                )
            except OSError:
                pass
        if self.master_fd >= 0:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = -1
        if self.pid > 0:
            try:
                os.kill(self.pid, signal.SIGTERM)
                os.waitpid(self.pid, 0)
            except (ChildProcessError, ProcessLookupError, OSError):
                pass
            self.pid = -1
        self.state = SessionState.TERMINATED


_IDLE_SEC = float(os.environ.get("CLUTCH_SHELL_IDLE_SEC", "1800"))
_MAX_SEC = float(os.environ.get("CLUTCH_SHELL_MAX_SEC", "21600"))


def _idle_threshold_sec() -> float:
    return float(os.environ.get("CLUTCH_SHELL_IDLE_SEC", str(_IDLE_SEC)))


def _max_lifetime_sec() -> float:
    return float(os.environ.get("CLUTCH_SHELL_MAX_SEC", str(_MAX_SEC)))


def _max_sessions() -> int:
    """0 = unlimited; default 8 concurrent bash PTYs per Sidecar."""
    raw = os.environ.get("CLUTCH_SHELL_MAX_SESSIONS", "8").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 8


class ShellSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, ShellSession] = {}
        self._recovery_notices: set[str] = set()
        self._lock = threading.Lock()

    def _active_session_count(self) -> int:
        return sum(
            1
            for session in self._sessions.values()
            if session.state != SessionState.TERMINATED
        )

    def _evict_oldest_idle_unlocked(self) -> str | None:
        candidates = [
            (run_id, session)
            for run_id, session in self._sessions.items()
            if session.state in (SessionState.IDLE, SessionState.READY)
        ]
        if not candidates:
            return None
        run_id, session = min(candidates, key=lambda item: item[1].last_activity_at)
        self._sessions.pop(run_id, None)
        session.close()
        logger.info(
            "shell_session pool evicted idle run_id=%s active=%s limit=%s",
            run_id,
            self._active_session_count(),
            _max_sessions(),
        )
        return run_id

    def consume_shell_recovery(self, run_id: str) -> bool:
        with self._lock:
            if run_id in self._recovery_notices:
                self._recovery_notices.discard(run_id)
                return True
            return False

    def get_or_create(self, run_id: str, *, workspace_path: str, owner_node_id: str = "plain_chat") -> ShellSession:
        with self._lock:
            disconnected = False
            session = self._sessions.get(run_id)
            if session and session.state != SessionState.TERMINATED:
                if not session.alive():
                    disconnected = True
                    session.state = SessionState.DISCONNECTED
                    session.close(write_snapshot=True)
                    self._sessions.pop(run_id, None)
                    logger.warning(
                        "shell_session disconnected run_id=%s source=shell_session",
                        run_id,
                    )
                else:
                    if session.state in (SessionState.BUSY,):
                        raise ShellSessionBusyError(f"ShellSession {run_id} is busy")
                    session.state = SessionState.BUSY
                    session.touch()
                    return session
            limit = _max_sessions()
            if limit > 0 and self._active_session_count() >= limit:
                evicted = self._evict_oldest_idle_unlocked()
                if evicted is None:
                    raise ShellSessionPoolFullError(
                        f"ShellSession pool full ({limit}); all sessions busy"
                    )
            session = ShellSession(
                run_id=run_id,
                workspace_path=workspace_path,
                owner_node_id=owner_node_id,
                state=SessionState.RECOVERING,
            )
            session._spawn()
            self._sessions[run_id] = session
            session.state = SessionState.BUSY
            if disconnected:
                self._recovery_notices.add(run_id)
            return session

    def mark_idle(self, run_id: str) -> None:
        with self._lock:
            session = self._sessions.get(run_id)
            if session and session.state == SessionState.BUSY:
                session.state = SessionState.IDLE
                session.touch()

    def release(self, run_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(run_id, None)
        if session:
            session.close()

    def sweep_idle(self) -> list[str]:
        """Terminate sessions past idle or max lifetime (only when IDLE)."""
        now = time.monotonic()
        terminated: list[str] = []
        with self._lock:
            items = list(self._sessions.items())
        for run_id, session in items:
            if session.state not in (SessionState.IDLE, SessionState.READY):
                if now - session.created_at >= _max_lifetime_sec() and session.state == SessionState.BUSY:
                    continue
                continue
            idle_for = now - session.last_activity_at
            age = now - session.created_at
            if idle_for >= _idle_threshold_sec() or age >= _max_lifetime_sec():
                self.release(run_id)
                terminated.append(run_id)
        return terminated


_manager: ShellSessionManager | None = None


def get_shell_session_manager() -> ShellSessionManager:
    global _manager
    if _manager is None:
        _manager = ShellSessionManager()
    return _manager
