"""Interactive PTY sessions for embedded CLI TUI (terminal workspace mode)."""

from __future__ import annotations

import asyncio
import codecs
import logging
import os
import shutil
import signal
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
    "antigravity-cli": "agy",
    "agy-cli": "agy",
    "agy": "agy",
    "codex-cli": "codex",
    "codex": "codex",
    "aider-cli": "aider",
    "aider": "aider",
    "rivet-cli": "rivet",
    "rivet": "rivet",
    "codebuddy-cli": "codebuddy",
    "codebuddy": "codebuddy",
    "cbc": "codebuddy",
    "ollama-cli": "ollama",
    "ollama": "ollama",
}


def _binary_for_agent_type(agent_type: str) -> str | None:
    from src.engine_router import CLI_ROUTING_CONFIGS

    key = agent_type.strip().lower()
    if not key or key == "clutch":
        return None
    cfg = CLI_ROUTING_CONFIGS.get(key)
    if isinstance(cfg, dict):
        binary = str(cfg.get("binary_name", "")).strip().lower()
        if binary:
            return binary
    mapped = CLI_BINARY_MAP.get(key)
    if mapped:
        return mapped.lower()
    if key.endswith("-cli"):
        return key[: -len("-cli")]
    return None


def configured_cli_binaries() -> set[str]:
    """Binary names for all configured / connected CLI agents (not Clutch built-in)."""
    binaries: set[str] = set()

    try:
        from src.agent_storage import list_agents
        from src.agent_type import agent_type_from_record

        for agent in list_agents():
            binary = _binary_for_agent_type(agent_type_from_record(agent))
            if binary:
                binaries.add(binary)
    except Exception:
        logger.debug("configured_cli_binaries: agent scan skipped", exc_info=True)

    try:
        from src.tools_status import load_connected_ids, resolve_agent_type_for_tool

        for tool_id in load_connected_ids():
            agent_type = resolve_agent_type_for_tool(tool_id)
            if not agent_type:
                continue
            binary = _binary_for_agent_type(agent_type)
            if binary:
                binaries.add(binary)
    except Exception:
        logger.debug("configured_cli_binaries: connected tools scan skipped", exc_info=True)

    if not binaries:
        binaries = {name.lower() for name in set(CLI_BINARY_MAP.values())}
    return binaries


def _command_matches_binary(command: str, binary: str) -> bool:
    tokens = command.strip().split()
    if not tokens:
        return False
    needle = binary.lower()
    for token in tokens:
        base = os.path.basename(token.lower())
        if base == needle or base == f"{needle}.exe":
            return True
    return False


def scan_system_cli_processes(binaries: set[str]) -> list[dict[str, str | int]]:
    if os.name == "nt" or not binaries:
        return []
    try:
        output = subprocess.check_output(
            ["ps", "-ax", "-o", "pid=,command="],
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return []

    results: list[dict[str, str | int]] = []
    seen: set[int] = set()
    own_pid = os.getpid()
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        if pid in seen or pid == own_pid:
            continue
        command = parts[1]
        lowered = command.lower()
        if lowered.startswith("grep ") or " grep " in lowered:
            continue
        for binary in binaries:
            if _command_matches_binary(command, binary):
                seen.add(pid)
                results.append({"pid": pid, "binary": binary, "command": command[:160]})
                break
    return results


class InteractivePtyStatus(str, Enum):
    BOOTING = "booting"
    READY = "ready"
    DETACHED = "detached"
    EXITED = "exited"
    BLOCKED = "blocked"


class InteractivePtyError(RuntimeError):
    pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _kill_pid(pid: int) -> None:
    if pid <= 0:
        return
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.05)
        if _pid_alive(pid):
            os.kill(pid, signal.SIGKILL)
    except OSError:
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
            return _pid_alive(self.pid)
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
        elif self.pid > 0:
            _kill_pid(self.pid)
        self.pid = -1
        self.status = InteractivePtyStatus.EXITED

    def write_input(self, data: str) -> None:
        with self._lock:
            if self.master_fd < 0:
                return
            payload = data.encode("utf-8", errors="replace")
            os.write(self.master_fd, payload)

    def resize(self, cols: int, rows: int) -> None:
        with self._lock:
            if self.master_fd < 0:
                return
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)


class InteractivePtyManager:
    def __init__(self) -> None:
        self._sessions: dict[str, InteractivePtySession] = {}
        self._spawned_pids: dict[int, str] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._output_handler: PtyOutputHandler | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def set_output_handler(self, handler: PtyOutputHandler | None) -> None:
        self._output_handler = handler

    def resolve_binary(self, cli_tool: str) -> str:
        key = cli_tool.strip().lower()
        name = CLI_BINARY_MAP.get(key)
        if not name and key.endswith("-cli"):
            name = key[: -len("-cli")]
        if not name:
            name = key
        path = shutil.which(name)
        if not path:
            raise InteractivePtyError(f"CLI binary not found: {name}")
        return path

    def _session_belongs_to_run(self, session_key: str, run_id: str) -> bool:
        return session_key == run_id or session_key.startswith(f"{run_id}::")

    def _register_pid(self, pid: int, session_key: str) -> None:
        if pid > 0:
            self._spawned_pids[pid] = session_key

    def _unregister_pid(self, pid: int) -> None:
        if pid > 0:
            self._spawned_pids.pop(pid, None)

    def attach(
        self,
        session_key: str,
        *,
        workspace_path: str,
        cli_tool: str,
        cli_session_id: str | None = None,
    ) -> InteractivePtySession:
        with self._lock:
            session = self._sessions.get(session_key)
            if session and session.alive() and session.cli_tool == cli_tool:
                session.attached = True
                if session.status in (InteractivePtyStatus.DETACHED, InteractivePtyStatus.BOOTING):
                    session.status = InteractivePtyStatus.READY
                self._flush_pending(session)
                return session
            if session:
                self._unregister_pid(session.pid)
                session.close()
            binary = self.resolve_binary(cli_tool)
            session = self._spawn(
                session_key,
                workspace_path,
                cli_tool,
                binary,
                cli_session_id=cli_session_id,
            )
            self._sessions[session_key] = session
            return session

    def detach(self, session_key: str) -> None:
        with self._lock:
            session = self._sessions.get(session_key)
            if not session:
                return
            session.attached = False
            if session.alive():
                session.status = InteractivePtyStatus.DETACHED

    def write_input(self, session_key: str, data: str) -> None:
        session = self._sessions.get(session_key)
        if not session or not session.attached:
            raise InteractivePtyError(f"interactive PTY not attached for {session_key}")
        session.write_input(data)

    def resize(self, session_key: str, cols: int, rows: int) -> None:
        session = self._sessions.get(session_key)
        if session:
            session.resize(cols, rows)

    def get(self, session_key: str) -> InteractivePtySession | None:
        return self._sessions.get(session_key)

    def close(self, session_key: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_key, None)
            if session:
                self._unregister_pid(session.pid)
                session.close()

    def _pids_for_keep_lanes(self, run_id: str, keep_lane_ids: list[str] | None) -> set[int]:
        keep_keys = {f"{run_id}::{lane_id}" for lane_id in (keep_lane_ids or []) if lane_id}
        pids: set[int] = set()
        with self._lock:
            for key, session in self._sessions.items():
                if keep_keys and key not in keep_keys:
                    continue
                if session.alive() and session.pid > 0:
                    pids.add(session.pid)
            for pid, key in self._spawned_pids.items():
                if keep_keys and key not in keep_keys:
                    continue
                if _pid_alive(pid):
                    pids.add(pid)
        return pids

    def list_alive_for_run(self, run_id: str) -> list[dict[str, str]]:
        seen_pids: set[int] = set()
        alive: list[dict[str, str]] = []
        with self._lock:
            for key, session in self._sessions.items():
                if not self._session_belongs_to_run(key, run_id) or not session.alive():
                    continue
                if session.pid in seen_pids:
                    continue
                seen_pids.add(session.pid)
                _, lane_id = key.split("::", 1) if "::" in key else (run_id, "lane_primary")
                alive.append(
                    {
                        "session_key": key,
                        "lane_id": lane_id,
                        "cli_tool": session.cli_tool,
                        "pid": str(session.pid),
                        "source": "tracked",
                    }
                )

            for pid, key in list(self._spawned_pids.items()):
                if not self._session_belongs_to_run(key, run_id):
                    continue
                if pid in seen_pids:
                    continue
                if not _pid_alive(pid):
                    self._spawned_pids.pop(pid, None)
                    continue
                seen_pids.add(pid)
                _, lane_id = key.split("::", 1) if "::" in key else (run_id, "lane_primary")
                alive.append(
                    {
                        "session_key": key,
                        "lane_id": lane_id,
                        "cli_tool": "orphan",
                        "pid": str(pid),
                        "source": "orphan",
                    }
                )

        for proc in scan_system_cli_processes(configured_cli_binaries()):
            pid = int(proc["pid"])
            if pid in seen_pids:
                continue
            seen_pids.add(pid)
            alive.append(
                {
                    "session_key": f"system::{pid}",
                    "lane_id": "system",
                    "cli_tool": str(proc["binary"]),
                    "pid": str(pid),
                    "source": "system",
                }
            )
        return alive

    def close_for_run(self, run_id: str, *, keep_lane_ids: list[str] | None = None) -> list[str]:
        keep_keys = {f"{run_id}::{lane_id}" for lane_id in (keep_lane_ids or []) if lane_id}
        keep_pids = self._pids_for_keep_lanes(run_id, keep_lane_ids)
        closed: list[str] = []
        with self._lock:
            for key in list(self._sessions.keys()):
                if not self._session_belongs_to_run(key, run_id):
                    continue
                if keep_keys and key in keep_keys:
                    continue
                session = self._sessions.pop(key, None)
                if session:
                    self._unregister_pid(session.pid)
                    session.close()
                    closed.append(key)

            for pid, key in list(self._spawned_pids.items()):
                if not self._session_belongs_to_run(key, run_id):
                    continue
                if keep_keys and key in keep_keys:
                    continue
                _kill_pid(pid)
                self._spawned_pids.pop(pid, None)
                closed.append(f"pid:{pid}")

        for proc in scan_system_cli_processes(configured_cli_binaries()):
            pid = int(proc["pid"])
            if pid in keep_pids:
                continue
            _kill_pid(pid)
            closed.append(f"system:{pid}")
        return closed

    def _spawn(
        self,
        session_key: str,
        workspace_path: str,
        cli_tool: str,
        binary: str,
        cli_session_id: str | None = None,
    ) -> InteractivePtySession:
        if os.name == "nt":
            raise InteractivePtyError("Interactive PTY is not supported on Windows yet")
        session = InteractivePtySession(
            run_id=session_key,
            workspace_path=workspace_path,
            cli_tool=cli_tool,
            binary=binary,
            status=InteractivePtyStatus.BOOTING,
        )
        master_fd, slave_fd = pty.openpty()
        winsize = struct.pack("HHHH", 24, 80, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
        argv = [binary]
        tool_key = cli_tool.strip().lower()
        sid = str(cli_session_id or "").strip()
        if sid and tool_key in {"claude-cli", "claude", "codebuddy-cli", "codebuddy", "cbc"}:
            argv.extend(["--session-id", sid])
        proc = subprocess.Popen(
            argv,
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
            name=f"interactive-pty-{session_key}",
            daemon=True,
        )
        session._read_thread.start()
        self._register_pid(proc.pid, session_key)
        logger.info(
            "interactive PTY spawned session_key=%s binary=%s workspace=%s pid=%s",
            session_key,
            binary,
            workspace_path,
            proc.pid,
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

    def _emit_output(self, session_key: str, chunk: str) -> None:
        if not self._output_handler or not self._loop:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._output_handler(session_key, chunk),
                self._loop,
            )
        except RuntimeError:
            logger.debug("interactive PTY output dropped session_key=%s (no loop)", session_key)


interactive_pty_manager = InteractivePtyManager()
