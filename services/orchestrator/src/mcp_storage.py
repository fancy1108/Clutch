"""User MCP server registry persistence (P2-02)."""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

MCP_ENV = "CLUTCH_MCP_DIR"
VALID_TRANSPORTS = frozenset({"stdio", "sse"})


def mcp_dir() -> Path:
    override = os.environ.get(MCP_ENV)
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "clutch" / "mcp"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "clutch" / "mcp"
    return Path.home() / ".local" / "share" / "clutch" / "mcp"


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
        raise ValueError("名称不能为空")
    if mode not in VALID_TRANSPORTS:
        raise ValueError("传输类型须为 stdio 或 sse")
    if not cmd:
        raise ValueError("端点不能为空")
    if mode == "sse":
        parsed = urlparse(cmd)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("SSE 端点须为 http(s) URL")
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
        raise ValueError("未找到该 MCP 服务器")
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
        raise ValueError("未找到该 MCP 服务器")
    return save_servers(next_servers)


def serialize_server_status(server: dict[str, Any]) -> dict[str, Any]:
    enabled = bool(server.get("enabled", True))
    if not enabled:
        return {
            **server,
            "status": "failed",
            "toolsCount": 0,
            "lastHeartbeat": "Disabled",
        }
    return {
        **server,
        "status": "reconnecting",
        "toolsCount": 0,
        "lastHeartbeat": "Configured — connects on agent run",
    }


def build_mcp_status_payload() -> dict[str, Any]:
    from src.workspace import get_workspace

    workspace = get_workspace()
    connected = workspace is not None
    filesystem = {
        "id": "local-fs",
        "name": "Local Filesystem MCP Server",
        "type": "local",
        "transport": "stdio",
        "endpoint": (
            f"npx -y @modelcontextprotocol/server-filesystem {workspace['workspace_path']}"
            if workspace
            else "npx -y @modelcontextprotocol/server-filesystem"
        ),
        "status": "connected" if connected else "failed",
        "toolsCount": 5 if connected else 0,
        "lastHeartbeat": "Workspace authorized" if connected else "Authorize a workspace first",
        "builtin": True,
    }
    user_servers = [serialize_server_status(item) for item in load_servers()]
    return {
        "filesystem": {
            "connected": connected,
            "tools": filesystem["toolsCount"],
            "workspace_path": workspace["workspace_path"] if workspace else None,
        },
        "servers": [filesystem, *user_servers],
    }
