"""Cooperative cancellation for in-flight workflow runs."""

from __future__ import annotations

import threading

_lock = threading.Lock()
_cancelled: set[str] = set()


class WorkflowCancelled(Exception):
    """Raised when a supervisor stops a workflow run."""


class WorkflowStepFailed(Exception):
    """Raised when an agent_task node fails and downstream steps must not run."""

    def __init__(self, *, run_id: str, node_id: str, agent: str, message: str) -> None:
        self.run_id = run_id
        self.node_id = node_id
        self.agent = agent
        self.message = message
        super().__init__(message)


def request_workflow_cancel(run_id: str) -> None:
    with _lock:
        _cancelled.add(run_id)


def clear_workflow_cancel(run_id: str) -> None:
    with _lock:
        _cancelled.discard(run_id)


def is_workflow_cancelled(run_id: str) -> bool:
    with _lock:
        return run_id in _cancelled
