"""ClutchState — LangGraph SSOT contract (aligned with packages/shared-types)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypedDict

ClutchRunStatus = Literal["idle", "running", "failed", "passed", "awaiting_human"]


class ClutchState(TypedDict):
    run_id: str
    workflow_id: str
    current_instruction: str
    active_node_id: str
    active_agent: str
    status: ClutchRunStatus
    messages: list[dict[str, object]]
    terminal_logs: list[str]
    changed_files: list[str]
    session_tokens: int
    session_cost_usd: float
    token_input: int
    token_output: int
    cli_session_id: str
    cli_session_agent_id: str


def read_cli_session_id(state: Mapping[str, Any]) -> str:
    """Read CLI session id; accepts legacy `claude_session_id` from older state files."""
    return str(state.get("cli_session_id") or state.get("claude_session_id", "")).strip()


def read_cli_session_agent_id(state: Mapping[str, Any]) -> str:
    """Read owning agent id; accepts legacy `claude_session_agent_id`."""
    return str(
        state.get("cli_session_agent_id") or state.get("claude_session_agent_id", "")
    ).strip()


def cli_session_patch(session_id: str | None, agent_id: str) -> dict[str, str]:
    if session_id:
        return {"cli_session_id": session_id, "cli_session_agent_id": agent_id}
    return {"cli_session_id": "", "cli_session_agent_id": ""}


def initial_state(run_id: str, workflow_id: str = "") -> ClutchState:
    return ClutchState(
        run_id=run_id,
        workflow_id=workflow_id,
        current_instruction="",
        active_node_id="",
        active_agent="",
        status="idle",
        messages=[],
        terminal_logs=[],
        changed_files=[],
        session_tokens=0,
        session_cost_usd=0.0,
        token_input=0,
        token_output=0,
        cli_session_id="",
        cli_session_agent_id="",
    )
