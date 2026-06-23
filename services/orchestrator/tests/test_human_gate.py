"""Human gate interrupt + resume tests — M2-05."""

from __future__ import annotations

from src.compiler import (
    WorkflowSession,
    begin_workflow,
    initial_compiler_state,
    resume_workflow,
)
from src.workflow_validator import load_and_validate_workflow

VIDEO_PRODUCTION = load_and_validate_workflow("video-production")


def test_failed_check_interrupts_before_human_gate() -> None:
    state = initial_compiler_state("run_gate_pause")
    state["check_result"] = "failed"

    session, result = begin_workflow(VIDEO_PRODUCTION, "run_gate_pause", initial_state=state)

    assert isinstance(session, WorkflowSession)
    assert result["status"] == "awaiting_human"
    assert result["active_node_id"] == "n3"
    assert result["active_agent"] == "Supervisor"


def test_human_decision_approve_resumes_to_end() -> None:
    state = initial_compiler_state("run_gate_approve")
    state["check_result"] = "failed"
    session, paused = begin_workflow(VIDEO_PRODUCTION, "run_gate_approve", initial_state=state)
    assert paused["status"] == "awaiting_human"

    result = resume_workflow(session, "run_gate_approve", "approve")

    assert result["active_node_id"] == "end"
    assert result["status"] == "passed"
    assert result["human_decision"] == "approve"


def test_human_decision_retry_routes_back_to_builder() -> None:
    state = initial_compiler_state("run_gate_retry")
    state["check_result"] = "failed"
    session, paused = begin_workflow(VIDEO_PRODUCTION, "run_gate_retry", initial_state=state)
    assert paused["status"] == "awaiting_human"

    result = resume_workflow(session, "run_gate_retry", "retry")

    assert result["active_node_id"] == "end"
    assert result["status"] == "passed"
    assert result["human_decision"] == "retry"