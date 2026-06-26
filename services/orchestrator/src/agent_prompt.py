"""Shared agent system prompt composition for chat and Flow."""

from __future__ import annotations

from typing import Any


def compose_agent_system_prompt(
    agent: dict[str, Any],
    *,
    model_name: str,
    model_api: str,
    mcp_servers_bound: bool = True,
    clutch_mcp_path: bool = True,
) -> str:
    from src.agent_skills import compose_skills_section
    from src.agent_type import is_clutch_agent

    protocol = str(agent.get("markdownDoc", "")).strip()
    agent_name = str(agent.get("name", "Clutch Agent"))
    header = (
        f"You are {agent_name}, the active agent in the user's Clutch workspace.\n"
        f"When asked who you are, identify yourself as {agent_name}. "
        f"Do not claim to be a different product, vendor, or base model.\n"
        f"Runtime model: {model_name} ({model_api}).\n"
        "Treat every instruction in the agent protocol below as mandatory.\n"
    )
    parts = [header.strip()]
    if protocol:
        parts.append(protocol)
    if clutch_mcp_path and is_clutch_agent(agent):
        if not mcp_servers_bound:
            parts.append(
                "No MCP tools are bound for this agent in this run. "
                "You cannot create, modify, or delete files on disk. "
                "Never claim a file operation succeeded without MCP tool evidence."
            )
        else:
            from src.workspace import get_workspace

            workspace = get_workspace()
            workspace_path = workspace.get("workspace_path") if workspace else None
            if workspace_path:
                parts.append(f"Workspace root: {workspace_path}")
        skills_block = compose_skills_section(list(agent.get("skills") or []))
        if skills_block:
            parts.append(skills_block)
    return "\n\n".join(parts)
