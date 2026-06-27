"""Cooperative cancellation for in-flight workflow runs."""

from __future__ import annotations

import threading

_lock = threading.Lock()
_cancelled: set[str] = set()


class WorkflowCancelled(Exception):
    """Raised when a supervisor stops a workflow run."""


def request_workflow_cancel(run_id: str) -> None:
    with _lock:
        _cancelled.add(run_id)


def clear_workflow_cancel(run_id: str) -> None:
    with _lock:
        _cancelled.discard(run_id)


def is_workflow_cancelled(run_id: str) -> bool:
    with _lock:
        return run_id in _cancelled
