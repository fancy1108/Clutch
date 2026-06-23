"""Orchestrator routing — workflow edges first, LLM fallback (M1-04)."""

from __future__ import annotations

from typing import Any, Callable, Literal

RouteMethod = Literal["edge", "llm"]
LLMSuggest = Callable[[dict[str, Any], str, dict[str, Any]], str]


class RoutingError(ValueError):
    """Raised when neither workflow edges nor LLM can resolve the next hop."""


def _edges_from(workflow: dict[str, Any], source: str) -> list[dict[str, Any]]:
    return [edge for edge in workflow["edges"] if edge["source"] == source]


def _node_type(workflow: dict[str, Any], node_id: str) -> str:
    if node_id == "start":
        return "start"
    for node in workflow["nodes"]:
        if node["id"] == node_id:
            return node["type"]
    raise ValueError(f"Unknown node: {node_id}")


def routing_signal(workflow: dict[str, Any], source: str, state: dict[str, Any]) -> str | None:
    """Derive branch key from node type and runtime state."""
    node_type = _node_type(workflow, source)
    if node_type == "check":
        return state.get("check_result") or "passed"
    if node_type == "human_gate":
        return state.get("human_decision") or "approve"
    return None


def _outgoing_groups(
    workflow: dict[str, Any], source: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    outgoing = _edges_from(workflow, source)
    conditional = [edge for edge in outgoing if edge.get("data", {}).get("when")]
    unconditional = [edge for edge in outgoing if not edge.get("data", {}).get("when")]
    if conditional and unconditional:
        raise ValueError(f"Node {source} mixes conditional and unconditional edges")
    return conditional, unconditional


def resolve_from_edges(workflow: dict[str, Any], source: str, state: dict[str, Any]) -> str | None:
    """Return target node id from workflow edges, or None when LLM fallback is needed."""
    conditional, unconditional = _outgoing_groups(workflow, source)
    if not conditional and not unconditional:
        return None

    if unconditional:
        if len(unconditional) != 1:
            raise ValueError(f"Node {source} has multiple unconditional edges")
        return str(unconditional[0]["target"])

    path_map = {edge["data"]["when"]: edge["target"] for edge in conditional}
    signal = routing_signal(workflow, source, state)
    if signal is None:
        return None
    if signal in path_map:
        return str(path_map[signal])
    return None


def resolve_branch_from_edges(
    workflow: dict[str, Any], source: str, state: dict[str, Any]
) -> str | None:
    """Return edge.data.when branch key for conditional edges, or None for LLM fallback."""
    conditional, _unconditional = _outgoing_groups(workflow, source)
    if not conditional:
        return None

    path_map = {edge["data"]["when"]: edge["target"] for edge in conditional}
    signal = routing_signal(workflow, source, state)
    if signal is None:
        return None
    if signal in path_map:
        return signal
    return None


def route_next(
    workflow: dict[str, Any],
    source: str,
    state: dict[str, Any],
    llm_suggest: LLMSuggest | None = None,
) -> tuple[str, RouteMethod]:
    """Resolve next hop: workflow edges first, optional LLM fallback.

    For unconditional edges returns target node id.
    For conditional edges returns edge.data.when branch key.
    """
    edge_target = resolve_from_edges(workflow, source, state)
    if edge_target is not None:
        conditional, unconditional = _outgoing_groups(workflow, source)
        if unconditional:
            return edge_target, "edge"
        branch = resolve_branch_from_edges(workflow, source, state)
        if branch is not None:
            return branch, "edge"

    if llm_suggest is not None:
        return llm_suggest(workflow, source, state), "llm"

    raise RoutingError(f"No edge route from {source!r} and no LLM fallback configured")
