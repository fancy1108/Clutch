"""Unit tests for minimal LangGraph runtime."""

from src.graph import run_minimal_graph


def test_minimal_graph_advances_node() -> None:
    result = run_minimal_graph("run_graph_test")
    assert result["active_node_id"] == "n1"
    assert result["active_agent"] == "Builder"
    assert result["status"] == "running"
