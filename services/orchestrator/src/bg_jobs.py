"""D11 — background shell jobs per Chat run_id."""

from __future__ import annotations

import contextvars
import threading
import uuid
from collections import deque
from collections.abc import Callable
from subprocess import Popen
from typing import Any, Literal

from src.shell_proc import kill_tree, popen_shell

BgJobStatus = Literal["running", "done", "failed", "killed"]
BgJobsNotifier = Callable[[str, list[dict[str, Any]], dict[str, Any] | None], None]

_MAX_OUTPUT_CHARS = 80_000
_RING_LINES = 500

_bg_context: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "bg_job_context", default=None
)
_jobs_by_run: dict[str, dict[str, "BgJob"]] = {}
_jobs_lock = threading.Lock()
_notifiers: dict[str, BgJobsNotifier] = {}


def bind_bg_job_context(ctx: dict[str, Any]) -> contextvars.Token[dict[str, Any] | None]:
    return _bg_context.set(ctx)


def release_bg_job_context(token: contextvars.Token[dict[str, Any] | None]) -> None:
    _bg_context.reset(token)


def get_bg_job_context() -> dict[str, Any] | None:
    return _bg_context.get()


def register_bg_jobs_notifier(run_id: str, notifier: BgJobsNotifier) -> None:
    _notifiers[run_id] = notifier


def unregister_bg_jobs_notifier(run_id: str) -> None:
    _notifiers.pop(run_id, None)


class BgJob:
    def __init__(self, run_id: str, job_id: str, command: str, cwd: str) -> None:
        self.run_id = run_id
        self.job_id = job_id
        self.command = command
        self.cwd = cwd
        self.status: BgJobStatus = "running"
        self._buffer: deque[str] = deque(maxlen=_RING_LINES)
        self._total_chars = 0
        self.exit_code: int | None = None
        self._proc: Popen[str] | None = None
        self._thread: threading.Thread | None = None

    def append_output(self, text: str) -> None:
        if not text:
            return
        remaining = _MAX_OUTPUT_CHARS - self._total_chars
        if remaining <= 0:
            return
        chunk = text[:remaining]
        self._buffer.append(chunk)
        self._total_chars += len(chunk)

    def get_output(self) -> str:
        return "".join(self._buffer)

    def title_snippet(self) -> str:
        cmd = self.command.strip()
        return cmd[:60] + ("…" if len(cmd) > 60 else "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.job_id,
            "command": self.command,
            "title": self.title_snippet(),
            "status": self.status,
            "output": self.get_output(),
            "exit_code": self.exit_code,
        }


def _notify_run(run_id: str, *, finished: dict[str, Any] | None = None) -> None:
    jobs = list_jobs(run_id)
    notifier = _notifiers.get(run_id)
    if notifier:
        notifier(run_id, jobs, finished)


def _reader_thread(job: BgJob) -> None:
    proc = job._proc
    if proc is None or proc.stdout is None:
        return
    try:
        for line in proc.stdout:
            if job.status == "killed":
                break
            job.append_output(line)
            _notify_run(job.run_id)
    finally:
        if job.status == "killed":
            # kill_job already pushed the finished monitor patch — avoid a duplicate.
            return
        try:
            job.exit_code = proc.wait()
        except Exception:
            job.exit_code = -1
        job.status = "done" if job.exit_code == 0 else "failed"
        finished = job.to_dict()
        _notify_run(job.run_id, finished=finished)


def adopt_process(
    run_id: str,
    command: str,
    cwd: str,
    proc: Popen[str],
    initial_output: str = "",
) -> dict[str, Any]:
    """D34 — move a running foreground subprocess into the bg_jobs registry."""
    trimmed = command.strip()
    job_id = f"bg_{uuid.uuid4().hex[:8]}"
    job = BgJob(run_id, job_id, trimmed, cwd)
    job._proc = proc
    if initial_output:
        job.append_output(initial_output)
    with _jobs_lock:
        _jobs_by_run.setdefault(run_id, {})[job_id] = job
    job._thread = threading.Thread(target=_reader_thread, args=(job,), daemon=True)
    job._thread.start()
    payload = job.to_dict()
    _notify_run(run_id)
    return payload


def start_job(run_id: str, command: str, cwd: str) -> dict[str, Any]:
    trimmed = command.strip()
    if not trimmed:
        raise ValueError("command is required")
    job_id = f"bg_{uuid.uuid4().hex[:8]}"
    job = BgJob(run_id, job_id, trimmed, cwd)
    try:
        proc = popen_shell(trimmed, cwd)
    except Exception as exc:
        job.status = "failed"
        job.append_output(f"[job error] {exc}\n")
        with _jobs_lock:
            _jobs_by_run.setdefault(run_id, {})[job_id] = job
        finished = job.to_dict()
        _notify_run(run_id, finished=finished)
        return finished

    job._proc = proc
    with _jobs_lock:
        _jobs_by_run.setdefault(run_id, {})[job_id] = job
    job._thread = threading.Thread(target=_reader_thread, args=(job,), daemon=True)
    job._thread.start()
    payload = job.to_dict()
    _notify_run(run_id)
    return payload


def get_output(run_id: str, job_id: str) -> str | None:
    with _jobs_lock:
        job = _jobs_by_run.get(run_id, {}).get(job_id)
    if job is None:
        return None
    return job.get_output()


def kill_job(run_id: str, job_id: str) -> dict[str, Any] | None:
    with _jobs_lock:
        job = _jobs_by_run.get(run_id, {}).get(job_id)
    if job is None or job.status != "running":
        return job.to_dict() if job else None
    # Mark + notify first so Chat UI flips immediately; reap the process off-thread
    # so terminate/wait does not stall the WebSocket loop (felt like Kill "stuck").
    job.status = "killed"
    finished = job.to_dict()
    _notify_run(run_id, finished=finished)
    proc = job._proc

    def _reap() -> None:
        if proc is None or proc.poll() is not None:
            return
        kill_tree(proc)

    threading.Thread(target=_reap, daemon=True).start()
    return finished


def list_jobs(run_id: str) -> list[dict[str, Any]]:
    with _jobs_lock:
        jobs = list(_jobs_by_run.get(run_id, {}).values())
    return [job.to_dict() for job in jobs]


def get_job(run_id: str, job_id: str) -> dict[str, Any] | None:
    with _jobs_lock:
        job = _jobs_by_run.get(run_id, {}).get(job_id)
    return job.to_dict() if job else None
