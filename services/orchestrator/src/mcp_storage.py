"""User MCP server registry persistence (P2-02)."""

from __future__ import annotations

import asyncio
import json
import os
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


# D39 — stdio (local command) and sse (Streamable HTTP URL) are both runnable.
RUNNABLE_TRANSPORTS = frozenset({"stdio", "sse"})


def validate_server_payload(
    *,
    name: str,
    transport: str,
    endpoint: str,
    allow_legacy_sse: bool = False,
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
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = validate_server_payload(name=name, transport=transport, endpoint=endpoint)
    servers = load_servers()
    entry: dict[str, Any] = {
        "id": f"mcp_{uuid.uuid4().hex[:8]}",
        "enabled": True,
        **payload,
    }
    if env:
        entry["env"] = {str(k): str(v) for k, v in env.items() if str(k).strip()}
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


def clear_tools_cache(endpoint: str | None = None) -> None:
    if endpoint is None:
        _cached_tools.clear()
        return
    _cached_tools.pop(endpoint, None)


_oauth_login_url: str | None = None


def peek_oauth_login_url() -> str | None:
    return _oauth_login_url


def _set_oauth_login_url(url: str) -> None:
    global _oauth_login_url
    _oauth_login_url = url


def _probe_endpoint_sync(
    endpoint: str,
    *,
    env: dict[str, str] | None = None,
    name: str = "probe",
) -> dict[str, Any]:
    """Connect once and list tools; return readable ok/error (D38)."""
    from src import mcp_client as mcp_client_mod
    from src.mcp_client import McpClient

    if not (endpoint or "").strip():
        return {
            "ok": False,
            "toolsCount": 0,
            "tools": [],
            "error": "Missing MCP endpoint / command",
        }

    global _oauth_login_url
    _oauth_login_url = None
    mcp_client_mod.login_url_hook = _set_oauth_login_url
    client = McpClient(name, endpoint, env=env)
    try:
        started = client.start(oauth_proxy=True)
    finally:
        mcp_client_mod.login_url_hook = None
    if not started:
        error = client.last_error or "Failed to start MCP server"
        if _oauth_login_url and _oauth_login_url not in error:
            error = f"{error} Login URL: {_oauth_login_url}"
        return {
            "ok": False,
            "toolsCount": 0,
            "tools": [],
            "error": error,
            "loginUrl": _oauth_login_url,
        }
    try:
        tools = client.list_tools()
    except Exception as exc:
        client.close()
        return {
            "ok": False,
            "toolsCount": 0,
            "tools": [],
            "error": str(exc).strip() or "tools/list failed",
        }
    client.close()
    if not tools:
        return {
            "ok": False,
            "toolsCount": 0,
            "tools": [],
            "error": "Connected but server exposed 0 tools",
        }
    clear_tools_cache(endpoint)
    _cached_tools[endpoint] = tools
    return {
        "ok": True,
        "toolsCount": len(tools),
        "tools": tools,
        "error": None,
    }


async def probe_server_by_id(server_id: str) -> dict[str, Any]:
    """D38 — test connection for a registered (or builtin local-fs) server."""
    from src.workspace import get_workspace

    sid = (server_id or "").strip()
    if not sid:
        raise ValueError(tr("MCP server id is required", "需要 MCP 服务器 id"))

    if sid == "local-fs":
        workspace = get_workspace()
        if not workspace:
            return {
                "id": sid,
                "name": "Local Filesystem MCP Server",
                "ok": False,
                "toolsCount": 0,
                "tools": [],
                "error": "Authorize a workspace first",
            }
        endpoint = (
            f"npx -y @modelcontextprotocol/server-filesystem {workspace['workspace_path']}"
        )
        result = await asyncio.to_thread(_probe_endpoint_sync, endpoint, name="local-fs")
        return {"id": sid, "name": "Local Filesystem MCP Server", **result}

    for item in load_servers():
        if item.get("id") == sid:
            env = item.get("env") if isinstance(item.get("env"), dict) else None
            env_str = (
                {str(k): str(v) for k, v in env.items()} if isinstance(env, dict) else None
            )
            result = await asyncio.to_thread(
                _probe_endpoint_sync,
                str(item.get("endpoint") or ""),
                env=env_str,
                name=str(item.get("name") or sid),
            )
            return {"id": sid, "name": item.get("name") or sid, **result}

    raise ValueError(tr("MCP server not found", "未找到该 MCP 服务器"))



def save_raw_config(servers_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validated = []
    for s in servers_list:
        if s.get("id") == "local-fs" or s.get("builtin"):
            continue
        payload = validate_server_payload(
            name=s.get("name", ""),
            transport=s.get("transport", "stdio"),
            endpoint=s.get("endpoint", ""),
            allow_legacy_sse=True,
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

