"""Resolve MCP Hub servers bound to an agent profile (P2-17 / D19)."""

from __future__ import annotations

from typing import Any

from src.mcp_storage import load_servers

LOCAL_FS_SERVER_ID = "local-fs"
CLUTCH_TOOLS_SERVER_ID = "clutch-tools"


def resolve_local_fs_server() -> dict[str, Any] | None:
    from src.workspace import get_workspace

    workspace = get_workspace()
    if not workspace:
        return None
    workspace_path = str(workspace.get("workspace_path", "")).strip()
    if not workspace_path:
        return None
    return {
        "id": LOCAL_FS_SERVER_ID,
        "name": "Local Filesystem MCP Server",
        "type": "local",
        "transport": "stdio",
        "endpoint": f"npx -y @modelcontextprotocol/server-filesystem {workspace_path}",
        "enabled": True,
        "builtin": True,
    }


def resolve_agent_mcp_servers(agent: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not agent:
        return []
    raw_ids = agent.get("mcpServerIds") or []
    wanted = {str(item).strip() for item in raw_ids if str(item).strip()}
    if not wanted:
        return []
    resolved: list[dict[str, Any]] = []
    if LOCAL_FS_SERVER_ID in wanted:
        local_fs = resolve_local_fs_server()
        if local_fs:
            resolved.append(local_fs)
        from src.builtin_tools import resolve_clutch_tools_server

        clutch_tools = resolve_clutch_tools_server()
        if clutch_tools:
            resolved.append(clutch_tools)
    for server in load_servers():
        server_id = str(server.get("id", "")).strip()
        if server_id not in wanted:
            continue
        if not server.get("enabled", True):
            continue
        endpoint = str(server.get("endpoint", "")).strip()
        if not endpoint:
            continue
        resolved.append(server)
    return resolved
