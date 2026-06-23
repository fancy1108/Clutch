"""Orchestrator routing tests — M1-04."""

from __future__ import annotations

from src.compiler.compiler import initial_compiler_state
from src.orchestrator.routing import RoutingError, route_next, resolve_from_edges
from src.workflow_validator import load_and_validate_workflow

VIDEO_PRODUCTION = load_and_validate_workflow("video-production")


def test_unconditional_edge_from_start() -> None:
    state = initial_compiler_state("run_route_start")
    target = resolve_from_edges(VIDEO_PRODUCTION, "start", state)
    assert target == "n1"


def test_check_passed_routes_to_end() -> None:
    state = initial_compiler_state("run_route_pass")
    state["check_result"] = "passed"
    target = resolve_from_edges(VIDEO_PRODUCTION, "n2", state)
    assert target == "end"


def test_check_failed_routes_to_human_gate() -> None:
    state = initial_compiler_state("run_route_fail")
    state["check_result"] = "failed"
    target = resolve_from_edges(VIDEO_PRODUCTION, "n2", state)
    assert target == "n3"


def test_human_gate_retry_routes_to_builder() -> None:
    state = initial_compiler_state("run_route_retry")
    state["human_decision"] = "retry"
    target = resolve_from_edges(VIDEO_PRODUCTION, "n3", state)
    assert target == "n1"


def test_edges_preferred_over_llm() -> None:
    state = initial_compiler_state("run_route_priority")
    state["check_result"] = "failed"
    llm_called = False

    def fake_llm(_workflow: dict, _source: str, _state: dict) -> str:
        nonlocal llm_called
        llm_called = True
        return "end"

    target, method = route_next(VIDEO_PRODUCTION, "n2", state, llm_suggest=fake_llm)
    assert target == "failed"
    assert method == "edge"
    assert llm_called is False


def test_llm_fallback_when_edge_signal_unknown() -> None:
    state = initial_compiler_state("run_route_llm")
    state["check_result"] = "unknown"

    target, method = route_next(
        VIDEO_PRODUCTION,
        "n2",
        state,
        llm_suggest=lambda _w, _s, _st: "failed",
    )
    assert target == "failed"
    assert method == "llm"
    assert resolve_from_edges(VIDEO_PRODUCTION, "n2", {**state, "check_result": "failed"}) == "n3"


def test_raises_without_edge_or_llm() -> None:
    state = initial_compiler_state("run_route_none")
    state["check_result"] = "unknown"

    try:
        route_next(VIDEO_PRODUCTION, "n2", state)
        raised = False
    except RoutingError:
        raised = True

    assert raised is True
