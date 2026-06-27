"""Per-workspace CLI lock — serialize claude/agy turns in the same workspace."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from src.shell_session import ShellSessionError

_locks: dict[str, threading.Lock] = {}
_meta_lock = threading.Lock()


def _get_lock(workspace_path: str) -> threading.Lock:
    key = str(workspace_path)
    with _meta_lock:
        lock = _locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _locks[key] = lock
        return lock


@contextmanager
def workspace_cli_turn(
    workspace_path: str,
    *,
    timeout_s: float,
    on_waiting: Callable[[], None] | None = None,
) -> Iterator[None]:
    lock = _get_lock(workspace_path)
    if on_waiting is not None:
        on_waiting()
    acquired = lock.acquire(timeout=timeout_s)
    if not acquired:
        raise ShellSessionError(
            f"workspace CLI lock timeout after {timeout_s}s for {workspace_path}"
        )
    try:
        yield
    finally:
        lock.release()
