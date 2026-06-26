"""Resolve agent_task input from workflow graph state (D23)."""

from __future__ import annotations

from typing import Any


def upstream_node_ids(workflow: dict[str, Any], node_id: str) -> list[str]:
    return [str(edge["source"]) for edge in workflow.get("edges", []) if str(edge["target"]) == node_id]


def resolve_agent_task_input(
    state: dict[str, Any],
    node: dict[str, Any],
    workflow: dict[str, Any],
) -> str:
    """Auto input rule: start upstream → user instruction; else upstream output."""
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
    elif len(upstreams) == 1:
        body = str(outputs.get(upstreams[0], "")).strip()
    elif len(upstreams) == 0:
        body = user_instruction
    else:
        chunks = [str(outputs.get(node_id, "")).strip() for node_id in upstreams]
        body = "\n\n".join(chunk for chunk in chunks if chunk)
        if not body:
            body = user_instruction

    if not body:
        return node_instruction

    if node_instruction:
        return f"{node_instruction}\n\n{body}"
    return body
