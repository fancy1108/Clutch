"""Check branch routing tests — M3-06."""

from __future__ import annotations

from src.compiler import begin_workflow, initial_compiler_state, resume_workflow
from src.workflow_validator import load_and_validate_workflow

VIDEO = load_and_validate_workflow("video-production")


from types import SimpleNamespace


class _FakeRouter:
    def get_active_model(self) -> SimpleNamespace:
        return SimpleNamespace(name="Test Model")

    def chat(self, history: list[dict[str, str]]) -> str:
        return f"Done: {history[-1]['content'][:40]}"


def test_failed_check_routes_to_human_gate_interrupt() -> None:
    state = initial_compiler_state("branch_failed")
    state["check_result"] = "failed"
    _session, paused = begin_workflow(VIDEO, "branch_failed", initial_state=state)
    assert paused["status"] == "awaiting_human"
    assert paused["active_node_id"] == "n3"


def test_retry_branch_returns_to_builder_path(monkeypatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())
    state = initial_compiler_state("branch_retry")
    state["check_result"] = "failed"
    session, paused = begin_workflow(VIDEO, "branch_retry", initial_state=state)
    assert paused["status"] == "awaiting_human"

    result = resume_workflow(session, "branch_retry", "retry")
    assert result["human_decision"] == "retry"
    assert result["status"] == "passed"
