"""D23 — fork Chat session from a message index."""

from __future__ import annotations

import uuid
from typing import Any

from src.run_history import upsert_session
from src.run_state_store import load_run_state, save_run_state
from src.state import initial_state
from src.workspace import get_workspace


def fork_session(parent_run_id: str, message_index: int) -> dict[str, Any]:
    parent = load_run_state(parent_run_id)
    if parent is None:
        raise ValueError(f"Session not found: {parent_run_id}")
    messages = list(parent.get("messages") or [])
    if message_index < 0 or message_index >= len(messages):
        raise ValueError(f"message_index out of range: {message_index}")

    child_run_id = f"run_{uuid.uuid4().hex[:12]}"
    workflow_id = str(parent.get("workflow_id") or "")
    child = initial_state(child_run_id, workflow_id)
    child["messages"] = messages[: message_index + 1]
    child["status"] = "idle"
    child["active_agent"] = str(parent.get("active_agent") or child["active_agent"])
    child["cli_session_id"] = ""
    child["cli_session_agent_id"] = ""

    for key in (
        "agent_todos",
        "agent_goal",
        "session_tokens",
        "token_input",
        "token_output",
    ):
        if key in parent:
            child[key] = parent[key]

    save_run_state(child)

    workspace = get_workspace()
    from src.run_history import list_runs

    parent_title = ""
    for record in list_runs():
        if record.get("run_id") == parent_run_id:
            parent_title = str(record.get("title") or parent_run_id)
            break

    title = f"Fork: {parent_title[:40]}" if parent_title else f"Fork @ {message_index + 1}"
    record_payload: dict[str, Any] = {
        "run_id": child_run_id,
        "title": title[:80],
        "workflow_id": workflow_id,
        "mode": "coding",
        "status": "idle",
        "parent_run_id": parent_run_id,
        "fork_message_index": message_index,
    }
    if workspace:
        record_payload["workspace_id"] = workspace.get("id")
        record_payload["workspace_name"] = workspace.get("name")

    from datetime import datetime, timezone

    record_payload["started_at"] = datetime.now(timezone.utc).isoformat()
    upsert_session(record_payload)

    return {
        "run_id": child_run_id,
        "parent_run_id": parent_run_id,
        "message_index": message_index,
        "title": title,
    }
