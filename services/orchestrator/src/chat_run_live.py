from __future__ import annotations

import contextvars
import logging
import threading
from copy import deepcopy
from typing import Any

from fastapi import WebSocket

from src.chat_messages import _chat_message
from src.chat_ws_events import _notify_run_state, _send_message_event
from src.state import ClutchState, initial_state
from src.terminal_logs import stamp_log_line

logger = logging.getLogger(__name__)

_run_states: dict[str, ClutchState] = {}

_run_sessions: dict[str, Any] = {}

_human_decision_locks: dict[str, threading.Lock] = {}

_human_decision_inflight: set[str] = set()


def _tool_step_live_patch(
    state: ClutchState, step: dict[str, Any]
) -> dict[str, Any]:
    """Upsert pending tool step + D9 run_stats for Chat-visible counters."""
    from src.run_control import DEFAULT_MAX_TOOL_STEPS, build_run_stats
    from src.tool_steps import upsert_tool_step

    steps = upsert_tool_step(list(state.get("pending_tool_steps") or []), step)
    stats = build_run_stats(
        tool_steps=len(steps),
        max_steps=DEFAULT_MAX_TOOL_STEPS,
        session_tokens=int(state.get("session_tokens") or 0),
    )
    return {"pending_tool_steps": steps, "run_stats": stats}


def _reasoning_live_patch(reasoning: str) -> dict[str, Any]:
    return {"live_reasoning": reasoning}


def _subtask_live_patch(
    state: ClutchState, card: dict[str, Any]
) -> dict[str, Any]:
    from src.subagent_runner import upsert_subtask

    subtasks = upsert_subtask(list(state.get("pending_subtasks") or []), card)
    return {"pending_subtasks": subtasks}


def _bg_jobs_live_patch(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    return {"bg_jobs": list(jobs)}


def _foreground_shell_live_patch(payload: dict[str, Any] | None) -> dict[str, Any]:
    return {"foreground_shell": payload}


def _worktree_isolation_live_patch(payload: dict[str, Any] | None) -> dict[str, Any]:
    return {"worktree_isolation": payload}


def _bind_worktree_from_state(state: ClutchState) -> tuple[contextvars.Token | None, contextvars.Token | None]:
    """Bind effective workspace root when D32 worktree isolation is active."""
    from src.workspace import bind_effective_workspace_root

    info = state.get("worktree_isolation")
    if not isinstance(info, dict) or not info.get("enabled"):
        return None, None
    wt_path = str(info.get("path") or "").strip()
    if not wt_path:
        return None, None
    from pathlib import Path

    root_token = bind_effective_workspace_root(Path(wt_path))
    from src.worktree_isolation import bind_worktree_context

    wt_token = bind_worktree_context(dict(info))
    return root_token, wt_token


def _release_worktree_bindings(
    root_token: contextvars.Token | None,
    wt_token: contextvars.Token | None,
) -> None:
    if root_token is not None:
        from src.workspace import release_effective_workspace_root

        release_effective_workspace_root(root_token)
    if wt_token is not None:
        from src.worktree_isolation import release_worktree_context

        release_worktree_context(wt_token)


async def _apply_foreground_shell_update(
    websocket: WebSocket,
    run_id: str,
    payload: dict[str, Any] | None,
) -> None:
    state = _get_or_create_run(run_id)
    patch: dict[str, Any] = _foreground_shell_live_patch(payload)
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    await _notify_run_state(websocket, run_id, state, patch)


def _merge_patch(state: ClutchState, patch: dict[str, Any]) -> ClutchState:
    merged = deepcopy(state)
    optional_keys = frozenset({
        "hybrid_executions",
        "shell_session_status",
        "shell_pool_blocker_run_ids",
        "shell_pool_blockers",
        "shell_pool_queue_position",
        "shell_pool_queue_depth",
        "pty_lanes",
        "dispatch_log",
        "dispatch_edges",
        "pending_handoff_drafts",
        "focused_lane_id",
        "pending_tool_steps",
        "live_reasoning",
        "pending_subtasks",
        "bg_jobs",
        "foreground_shell",
        "agent_todos",
        "agent_goal",
        "verification_report",
        "diff_summary",
        "refining_node_id",
        "refine_draft_output",
        "refine_agent_id",
        "pending_pty_inject",
        "run_stats",
        "awaiting_continue",
    })
    for key, value in patch.items():
        if key in merged or key in optional_keys:
            merged[key] = value  # type: ignore[literal-required, index]
    return merged


def _persist_run_log(run_id: str, line: str, node_id: str) -> None:
    state = _get_or_create_run(run_id)
    logs = list(state["terminal_logs"]) + [stamp_log_line(line)]
    patch: dict[str, Any] = {"terminal_logs": logs}
    if node_id:
        patch["active_node_id"] = node_id
    _commit_run_state(run_id, _merge_patch(state, patch))


def _setup_run_log_forwarder(run_id: str) -> None:
    from src.run_log_forwarder import get_forwarder

    get_forwarder(run_id).set_persist(
        lambda line, node_id: _persist_run_log(run_id, line, node_id)
    )


async def _apply_bg_jobs_update(
    websocket: WebSocket,
    run_id: str,
    jobs: list[dict[str, Any]],
    finished: dict[str, Any] | None = None,
) -> None:
    from src.bg_jobs_monitor import format_bg_job_monitor_message

    state = _get_or_create_run(run_id)
    patch: dict[str, Any] = _bg_jobs_live_patch(jobs)
    monitor_text = format_bg_job_monitor_message(finished or {})
    if monitor_text:
        supervisor = _chat_message(
            "Supervisor",
            monitor_text,
            bg_job=dict(finished) if finished else None,
        )
        patch["messages"] = list(state["messages"]) + [supervisor]
        await _send_message_event(websocket, run_id, supervisor, "")
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    await _notify_run_state(websocket, run_id, state, patch)


def _get_or_create_run(run_id: str) -> ClutchState:
    if run_id not in _run_states:
        from src.run_state_store import load_run_state

        persisted = load_run_state(run_id)
        _run_states[run_id] = persisted if persisted else initial_state(run_id)
    return _run_states[run_id]


def _commit_run_state(run_id: str, state: ClutchState) -> ClutchState:
    from src.run_state_store import save_run_state

    _run_states[run_id] = state
    save_run_state(state)
    return state

