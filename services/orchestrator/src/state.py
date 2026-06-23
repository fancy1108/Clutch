"""ClutchState — LangGraph SSOT contract (aligned with packages/shared-types)."""

from __future__ import annotations

from typing import Literal, TypedDict

ClutchRunStatus = Literal["running", "failed", "passed", "awaiting_human"]


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


def initial_state(run_id: str, workflow_id: str = "video-production") -> ClutchState:
    return ClutchState(
        run_id=run_id,
        workflow_id=workflow_id,
        current_instruction="",
        active_node_id="start",
        active_agent="Orchestrator",
        status="running",
        messages=[],
        terminal_logs=["[ORCHESTRATOR] Sidecar connected. Awaiting instruction."],
        changed_files=[],
        session_tokens=0,
        session_cost_usd=0.0,
        token_input=0,
        token_output=0,
    )
