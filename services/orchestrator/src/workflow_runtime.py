"""Per-run workflow step callbacks (incremental ClutchState during Flow)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

StepCallback = Callable[[dict[str, Any]], None]

_lock = threading.Lock()
_step_callbacks: dict[str, StepCallback] = {}


def register_workflow_step_callback(run_id: str, callback: StepCallback) -> None:
    with _lock:
        _step_callbacks[run_id] = callback


def clear_workflow_step_callback(run_id: str) -> None:
    with _lock:
        _step_callbacks.pop(run_id, None)


def emit_workflow_agent_step(run_id: str, patch: dict[str, Any]) -> None:
    if not run_id:
        return
    with _lock:
        callback = _step_callbacks.get(run_id)
    if callback is not None:
        callback(patch)
