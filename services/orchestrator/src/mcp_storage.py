"""User MCP server registry persistence (P2-02)."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.preferences_storage import tr

MCP_ENV = "CLUTCH_MCP_DIR"
VALID_TRANSPORTS = frozenset({"stdio", "sse"})


def mcp_dir() -> Path:
    override = os.environ.get(MCP_ENV)
    if override:
        return Path(override)
    from src.storage_helper import get_storage_dir
    return get_storage_dir() / "mcp"


def _servers_file() -> Path:
    path = mcp_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path / "servers.json"


def load_servers() -> list[dict[str, Any]]:
    path = _servers_file()
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("servers") or [])


def save_servers(servers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    _servers_file().write_text(
        json.dumps({"servers": servers}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return servers


def validate_server_payload(
    *,
    name: str,
    transport: str,
    endpoint: str,
) -> dict[str, Any]:
    label = name.strip()
    cmd = endpoint.strip()
    mode = transport.strip().lower()
    if not label:
        raise ValueError(tr("Name cannot be empty", "名称不能为空"))
    if mode not in VALID_TRANSPORTS:
        raise ValueError(tr("Transport type must be stdio or sse", "传输类型须为 stdio 或 sse"))
    if not cmd:
        raise ValueError(tr("Endpoint cannot be empty", "端点不能为空"))
    if mode == "sse":
        parsed = urlparse(cmd)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(tr("SSE endpoint must be an http(s) URL", "SSE 端点须为 http(s) URL"))
    server_type = "remote" if mode == "sse" else "local"
    return {
        "name": label,
        "type": server_type,
        "transport": mode,
        "endpoint": cmd,
    }


def register_server(
    *,
    name: str,
    transport: str,
    endpoint: str,
) -> dict[str, Any]:
    payload = validate_server_payload(name=name, transport=transport, endpoint=endpoint)
    servers = load_servers()
    entry = {
        "id": f"mcp_{uuid.uuid4().hex[:8]}",
        "enabled": True,
        **payload,
    }
    servers.append(entry)
    save_servers(servers)
    return entry


def remove_server(server_id: str) -> list[dict[str, Any]]:
    servers = load_servers()
    next_servers = [item for item in servers if item.get("id") != server_id]
    if len(next_servers) == len(servers):
        raise ValueError(tr("MCP server not found", "未找到该 MCP 服务器"))
    return save_servers(next_servers)


def toggle_server(server_id: str, *, enabled: bool) -> list[dict[str, Any]]:
    servers = load_servers()
    updated = False
    next_servers: list[dict[str, Any]] = []
    for item in servers:
        if item.get("id") == server_id:
            next_servers.append({**item, "enabled": enabled})
            updated = True
        else:
            next_servers.append(item)
    if not updated:
        raise ValueError(tr("MCP server not found", "未找到该 MCP 服务器"))
    return save_servers(next_servers)


_cached_tools: dict[str, list[dict[str, Any]]] = {}


async def get_server_tools(endpoint: str) -> list[dict[str, Any]]:
    if not endpoint:
        return []
    if endpoint in _cached_tools:
        return _cached_tools[endpoint]
    
    def _query():
        from src.mcp_client import McpClient
        client = McpClient("temp", endpoint)
        if client.start():
            tools = client.list_tools()
            client.close()
            return tools
        return []

    tools = await asyncio.to_thread(_query)
    if tools:
        _cached_tools[endpoint] = tools
    return tools



def save_raw_config(servers_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validated = []
    for s in servers_list:
        if s.get("id") == "local-fs" or s.get("builtin"):
            continue
        payload = validate_server_payload(
            name=s.get("name", ""),
            transport=s.get("transport", "stdio"),
            endpoint=s.get("endpoint", "")
        )
        server_id = s.get("id") or f"mcp_{uuid.uuid4().hex[:8]}"
        enabled = s.get("enabled", True)
        env = s.get("env")
        entry = {
            "id": server_id,
            "enabled": enabled,
            **payload
        }
        if isinstance(env, dict):
            entry["env"] = env
        validated.append(entry)
    save_servers(validated)
    return validated


def import_from_claude() -> list[dict[str, Any]]:
    imported_count = 0
    servers = load_servers()
    paths = []
    if sys.platform == "darwin":
        paths.append(Path.home() / "Library/Application Support/Claude/claude_desktop_config.json")
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(Path(appdata) / "Claude" / "claude_desktop_config.json")
    paths.append(Path.home() / ".claude.json")

    for path in paths:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            mcp_servers = data.get("mcpServers") or {}
            for name, cfg in mcp_servers.items():
                cmd = cfg.get("command")
                args = cfg.get("args") or []
                env = cfg.get("env") or {}
                if not cmd:
                    continue
                endpoint_cmd = cmd
                if args:
                    import shlex
                    endpoint_cmd = cmd + " " + " ".join(shlex.quote(arg) for arg in args)
                exists = any(s.get("endpoint") == endpoint_cmd for s in servers)
                if not exists:
                    entry = {
                        "id": f"mcp_{uuid.uuid4().hex[:8]}",
                        "name": f"Claude {name}",
                        "type": "local",
                        "transport": "stdio",
                        "endpoint": endpoint_cmd,
                        "enabled": True,
                    }
                    if env:
                        entry["env"] = env
                    servers.append(entry)
                    imported_count += 1
        except Exception:
            continue
    if imported_count > 0:
        save_servers(servers)
    return servers


async def serialize_server_status(server: dict[str, Any]) -> dict[str, Any]:
    enabled = bool(server.get("enabled", True))
    if not enabled:
        return {
            **server,
            "status": "failed",
            "toolsCount": 0,
            "lastHeartbeat": "Disabled",
            "tools": [],
        }
    tools = await get_server_tools(server["endpoint"])
    if tools:
        return {
            **server,
            "status": "connected",
            "toolsCount": len(tools),
            "lastHeartbeat": "Connected",
            "tools": tools,
        }
    return {
        **server,
        "status": "reconnecting",
        "toolsCount": 0,
        "lastHeartbeat": "Configured — connects on agent run",
        "tools": [],
    }


async def build_mcp_status_payload() -> dict[str, Any]:
    from src.workspace import get_workspace

    workspace = get_workspace()
    connected = workspace is not None
    endpoint = ""
    if workspace:
        endpoint = f"npx -y @modelcontextprotocol/server-filesystem {workspace['workspace_path']}"
    
    tools = []
    if connected and endpoint:
        tools = await get_server_tools(endpoint)

    filesystem = {
        "id": "local-fs",
        "name": "Local Filesystem MCP Server",
        "type": "local",
        "transport": "stdio",
        "endpoint": endpoint or "npx -y @modelcontextprotocol/server-filesystem",
        "status": "connected" if connected else "failed",
        "toolsCount": len(tools) if connected else 0,
        "lastHeartbeat": "Workspace authorized" if connected else "Authorize a workspace first",
        "builtin": True,
        "tools": tools,
    }
    user_servers = []
    for item in load_servers():
        serialized = await serialize_server_status(item)
        user_servers.append(serialized)
    return {
        "filesystem": {
            "connected": connected,
            "tools": filesystem["toolsCount"],
            "workspace_path": workspace["workspace_path"] if workspace else None,
        },
        "servers": [filesystem, *user_servers],
    }

