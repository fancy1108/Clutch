"""Minimal LangGraph runtime — M1 skeleton."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class GraphState(TypedDict):
    run_id: str
    active_node_id: str
    active_agent: str
    status: str


def _orchestrator_node(state: GraphState) -> GraphState:
    return {
        **state,
        "active_node_id": "n1",
        "active_agent": "Builder",
        "status": "running",
    }


def build_minimal_graph():
    graph = StateGraph(GraphState)
    graph.add_node("orchestrator", _orchestrator_node)
    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", END)
    return graph.compile()


def run_minimal_graph(run_id: str) -> GraphState:
    compiled = build_minimal_graph()
    return compiled.invoke(
        {
            "run_id": run_id,
            "active_node_id": "start",
            "active_agent": "Orchestrator",
            "status": "running",
        }
    )
