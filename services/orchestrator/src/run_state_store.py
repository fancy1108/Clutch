"""Persist full ClutchState per run_id for session resume (conversation history)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.run_history import sessions_data_dir
from src.state import ClutchState, initial_state

_SAFE_RUN_ID = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


def _states_dir() -> Path:
    return sessions_data_dir() / "states"


def _state_path(run_id: str) -> Path:
    if not _SAFE_RUN_ID.match(run_id):
        raise ValueError(f"Invalid run_id: {run_id!r}")
    return _states_dir() / f"{run_id}.json"


# Optional ClutchState fields written by orchestrator patches (terminal orchestra, hybrid, etc.)
_PERSISTED_OPTIONAL_KEYS = frozenset({
    "hybrid_executions",
    "shell_session_status",
    "shell_pool_blocker_run_ids",
    "shell_pool_blockers",
    "shell_pool_queue_position",
    "shell_pool_queue_depth",
    "refining_node_id",
    "refine_draft_output",
    "refine_agent_id",
    "pty_lanes",
    "dispatch_log",
    "dispatch_edges",
    "pending_handoff_drafts",
    "focused_lane_id",
    "pending_pty_inject",
})


def _coerce_state(data: dict[str, Any], run_id: str) -> ClutchState:
    workflow_id = str(data.get("workflow_id", ""))
    state = initial_state(run_id, workflow_id)
    for key in state:
        if key in data:
            state[key] = data[key]  # type: ignore[literal-required]
    for key in _PERSISTED_OPTIONAL_KEYS:
        if key in data:
            state[key] = data[key]  # type: ignore[literal-required]
    state["run_id"] = run_id
    return state


def load_run_state(run_id: str) -> ClutchState | None:
    path = _state_path(run_id)
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return _coerce_state(data, run_id)


def save_run_state(state: ClutchState) -> None:
    directory = _states_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = _state_path(state["run_id"])
    path.write_text(
        json.dumps(dict(state), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def delete_run_state(run_id: str) -> None:
    try:
        path = _state_path(run_id)
        if path.is_file():
            path.unlink()
    except ValueError:
        pass


def persisted_state_preferred(persisted: ClutchState, memory: ClutchState) -> bool:
    """True when disk has a newer completed turn than in-memory (HRT-09)."""
    p_msgs = len(persisted.get("messages") or [])
    m_msgs = len(memory.get("messages") or [])
    if p_msgs > m_msgs:
        return True
    return (
        p_msgs == m_msgs
        and persisted.get("status") == "idle"
        and memory.get("status") == "running"
    )


def sync_run_state_from_disk(run_id: str, memory: ClutchState) -> ClutchState:
    from src.hybrid_concurrency import clear_stale_shell_rejection_status

    persisted = load_run_state(run_id)
    if persisted is None:
        chosen = memory
    elif persisted_state_preferred(persisted, memory):
        chosen = persisted
    else:
        chosen = memory
    stale_patch = clear_stale_shell_rejection_status(chosen)
    if stale_patch:
        chosen = {**chosen, **stale_patch}  # type: ignore[typeddict-item]
        save_run_state(chosen)
    return chosen
