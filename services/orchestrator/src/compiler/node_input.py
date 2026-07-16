"""Resolve agent_task input from workflow graph state (D23)."""

from __future__ import annotations

from typing import Any


def upstream_node_ids(workflow: dict[str, Any], node_id: str) -> list[str]:
    return [str(edge["source"]) for edge in workflow.get("edges", []) if str(edge["target"]) == node_id]


def _find_node(workflow: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for n in workflow.get("nodes", []):
        if str(n.get("id")) == node_id:
            return n
    return None


def _resolve_upstream_data(
    outputs: dict[str, Any],
    node_id: str,
    workflow: dict[str, Any],
    default: str = "",
) -> str:
    """Walk upstream until we find a data-producing node (skip gates/checks)."""
    upstreams = upstream_node_ids(workflow, node_id)
    if not upstreams:
        return default
    # For single upstream, walk through gate/check nodes to find real data source
    if len(upstreams) == 1:
        src = upstreams[0]
        src_node = _find_node(workflow, src)
        if src_node and src_node.get("type") in ("human_gate", "check"):
            return _resolve_upstream_data(outputs, src, workflow, default)
    data = str(outputs.get(node_id, "")).strip()
    if data:
        return data
    # Try walking through upstreams for the data
    parts: list[str] = []
    for src in upstreams:
        src_node = _find_node(workflow, src)
        if src_node and src_node.get("type") in ("human_gate", "check"):
            parts.append(_resolve_upstream_data(outputs, src, workflow, default))
        else:
            parts.append(str(outputs.get(src, "")).strip())
    return "\n\n".join(p for p in parts if p) or default


def resolve_agent_task_input(
    state: dict[str, Any],
    node: dict[str, Any],
    workflow: dict[str, Any],
) -> str:
    """Auto input rule: start upstream → user instruction; else upstream output.
    
    Gate/check nodes are transparent for data flow — we walk through them
    to find the real data-producing agent_task upstream.
    """
    data = node.get("data", {})
    if not isinstance(data, dict):
        data = {}
    node_instruction = str(data.get("instruction", "")).strip()
    user_instruction = str(state.get("current_instruction", "")).strip()
    outputs = state.get("node_outputs") or {}
    if not isinstance(outputs, dict):
        outputs = {}

    upstreams = upstream_node_ids(workflow, str(node["id"]))
    body = ""

    if len(upstreams) == 1 and upstreams[0] == "start":
        body = user_instruction
    elif len(upstreams) == 0:
        body = user_instruction
    else:
        # Walk through gate/check nodes to find actual data
        chunks: list[str] = []
        for src_id in upstreams:
            src_node = _find_node(workflow, src_id)
            if src_node and src_node.get("type") in ("human_gate", "check"):
                chunk = _resolve_upstream_data(outputs, src_id, workflow, "")
            else:
                chunk = str(outputs.get(src_id, "")).strip()
            if chunk:
                chunks.append(chunk)
        body = "\n\n".join(chunks)
        if not body:
            body = user_instruction

    if not body:
        return node_instruction

    if node_instruction:
        return f"{node_instruction}\n\n{body}"
    return body
