"""Interactive PTY sessions for embedded CLI TUI (terminal workspace mode)."""

from __future__ import annotations

import asyncio
import codecs
import logging
import os
import shutil
import struct
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Awaitable, Callable

from src.shell_session import _read_available_bytes

if TYPE_CHECKING:
    pass

if os.name != "nt":
    import fcntl
    import pty
    import termios

logger = logging.getLogger(__name__)

PtyOutputHandler = Callable[[str, str], Awaitable[None]]

CLI_BINARY_MAP: dict[str, str] = {
    "claude-cli": "claude",
    "claude": "claude",
    "opencode-cli": "opencode",
    "opencode": "opencode",
}


class InteractivePtyStatus(str, Enum):
    BOOTING = "booting"
    READY = "ready"
    DETACHED = "detached"
    EXITED = "exited"
    BLOCKED = "blocked"


class InteractivePtyError(RuntimeError):
    pass


@dataclass
class InteractivePtySession:
    run_id: str
    workspace_path: str
    cli_tool: str
    binary: str
    master_fd: int = -1
    pid: int = -1
    _proc: subprocess.Popen[bytes] | None = field(default=None, repr=False)
    status: InteractivePtyStatus = InteractivePtyStatus.BOOTING
    attached: bool = False
    _pending_output: list[str] = field(default_factory=list, repr=False)
    _read_thread: threading.Thread | None = field(default=None, repr=False)
    _stop_read: threading.Event = field(default_factory=threading.Event, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def alive(self) -> bool:
        if self._proc is not None:
            return self._proc.poll() is None
        if self.pid > 0:
            try:
                os.kill(self.pid, 0)
                return True
            except OSError:
                return False
        return False

    def close(self) -> None:
        self._stop_read.set()
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=2)
        if self.master_fd >= 0:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = -1
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except (ProcessLookupError, subprocess.TimeoutExpired, OSError):
                try:
                    self._proc.kill()
                except OSError:
                    pass
            self._proc = None
        self.pid = -1
        self.status = InteractivePtyStatus.EXITED

    def write_input(self, data: str) -> None:
        with self._lock:
            if self.master_fd < 0:
                return
            payload = data.encode("utf-8", errors="replace")
            if isinstance(self.master_fd, int):
                os.write(self.master_fd, payload)
            else:
                self.master_fd.write(data)

    def resize(self, cols: int, rows: int) -> None:
        if self.master_fd < 0 or os.name == "nt":
            return
        winsize = struct.pack("HHHH", max(1, rows), max(1, cols), 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)


class InteractivePtyManager:
    def __init__(self) -> None:
        self._sessions: dict[str, InteractivePtySession] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._output_handler: PtyOutputHandler | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def set_output_handler(self, handler: PtyOutputHandler | None) -> None:
        self._output_handler = handler

    def resolve_binary(self, cli_tool: str) -> str:
        key = cli_tool.strip().lower()
        name = CLI_BINARY_MAP.get(key, key)
        path = shutil.which(name)
        if not path:
            raise InteractivePtyError(f"CLI binary not found: {name}")
        return path

    def attach(self, run_id: str, *, workspace_path: str, cli_tool: str) -> InteractivePtySession:
        with self._lock:
            session = self._sessions.get(run_id)
            if session and session.alive():
                session.attached = True
                if session.status in (InteractivePtyStatus.DETACHED, InteractivePtyStatus.BOOTING):
                    session.status = InteractivePtyStatus.READY
                self._flush_pending(session)
                return session
            if session:
                session.close()
            binary = self.resolve_binary(cli_tool)
            session = self._spawn(run_id, workspace_path, cli_tool, binary)
            self._sessions[run_id] = session
            return session

    def detach(self, run_id: str) -> None:
        with self._lock:
            session = self._sessions.get(run_id)
            if not session:
                return
            session.attached = False
            if session.alive():
                session.status = InteractivePtyStatus.DETACHED

    def write_input(self, run_id: str, data: str) -> None:
        session = self._sessions.get(run_id)
        if not session or not session.attached:
            raise InteractivePtyError(f"interactive PTY not attached for {run_id}")
        session.write_input(data)

    def resize(self, run_id: str, cols: int, rows: int) -> None:
        session = self._sessions.get(run_id)
        if session:
            session.resize(cols, rows)

    def get(self, run_id: str) -> InteractivePtySession | None:
        return self._sessions.get(run_id)

    def close(self, run_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(run_id, None)
            if session:
                session.close()

    def _spawn(
        self,
        run_id: str,
        workspace_path: str,
        cli_tool: str,
        binary: str,
    ) -> InteractivePtySession:
        if os.name == "nt":
            raise InteractivePtyError("Interactive PTY is not supported on Windows yet")
        session = InteractivePtySession(
            run_id=run_id,
            workspace_path=workspace_path,
            cli_tool=cli_tool,
            binary=binary,
            status=InteractivePtyStatus.BOOTING,
        )
        master_fd, slave_fd = pty.openpty()
        winsize = struct.pack("HHHH", 24, 80, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
        proc = subprocess.Popen(
            [binary],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=workspace_path,
            close_fds=True,
            start_new_session=True,
        )
        os.close(slave_fd)
        session.master_fd = master_fd
        session.pid = proc.pid
        session._proc = proc
        session.attached = True
        session.status = InteractivePtyStatus.READY
        session._read_thread = threading.Thread(
            target=self._read_loop,
            args=(session,),
            name=f"interactive-pty-{run_id}",
            daemon=True,
        )
        session._read_thread.start()
        logger.info(
            "interactive PTY spawned run_id=%s binary=%s workspace=%s",
            run_id,
            binary,
            workspace_path,
        )
        return session

    def _flush_pending(self, session: InteractivePtySession) -> None:
        pending = session._pending_output
        if not pending:
            return
        session._pending_output = []
        combined = "".join(pending)
        if combined:
            self._emit_output(session.run_id, combined)

    def _read_loop(self, session: InteractivePtySession) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        while not session._stop_read.is_set():
            if not session.alive():
                session.status = InteractivePtyStatus.EXITED
                break
            chunk_bytes = _read_available_bytes(session.master_fd, wait_s=0.15)
            if not chunk_bytes:
                continue
            chunk = decoder.decode(chunk_bytes)
            if not chunk:
                continue
            if session.attached:
                self._emit_output(session.run_id, chunk)
            else:
                session._pending_output.append(chunk)
                if sum(len(part) for part in session._pending_output) > 256_000:
                    session._pending_output = session._pending_output[-8:]
        decoder.decode(b"", final=True)

    def _emit_output(self, run_id: str, chunk: str) -> None:
        if not self._output_handler or not self._loop:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._output_handler(run_id, chunk),
                self._loop,
            )
        except RuntimeError:
            logger.debug("interactive PTY output dropped run_id=%s (no loop)", run_id)


interactive_pty_manager = InteractivePtyManager()
