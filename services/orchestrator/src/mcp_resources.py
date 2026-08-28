"""D43 — MCP resources browse, read, and Chat pin injection."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from src.mcp_storage import load_servers, mcp_dir
from src.preferences_storage import tr

_MAX_PINS = 8
_MAX_INJECT_CHARS = 6000
_MAX_ONE_RESOURCE_CHARS = 2500


def _pins_file() -> Path:
    path = mcp_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path / "resource_pins.json"


def load_resource_pins() -> list[dict[str, Any]]:
    path = _pins_file()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        uri = str(item.get("uri") or "").strip()
        server_id = str(item.get("server_id") or "").strip()
        if not uri or not server_id:
            continue
        text = item.get("text")
        out.append(
            {
                "server_id": server_id,
                "uri": uri,
                "name": str(item.get("name") or uri).strip() or uri,
                "mimeType": str(item.get("mimeType") or "").strip() or None,
                "text": text if isinstance(text, str) else None,
            }
        )
    return out[:_MAX_PINS]


def save_resource_pins(pins: list[dict[str, Any]]) -> list[dict[str, Any]]:
    next_pins: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in pins:
        if not isinstance(item, dict):
            continue
        uri = str(item.get("uri") or "").strip()
        server_id = str(item.get("server_id") or "").strip()
        if not uri or not server_id:
            continue
        key = f"{server_id}::{uri}"
        if key in seen:
            continue
        seen.add(key)
        entry: dict[str, Any] = {
            "server_id": server_id,
            "uri": uri,
            "name": str(item.get("name") or uri).strip() or uri,
            "mimeType": str(item.get("mimeType") or "").strip() or None,
        }
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            entry["text"] = text.strip()[:_MAX_ONE_RESOURCE_CHARS]
        next_pins.append(entry)
        if len(next_pins) >= _MAX_PINS:
            break
    _pins_file().write_text(json.dumps(next_pins, ensure_ascii=False, indent=2), encoding="utf-8")
    return next_pins


def unpin_resource(*, server_id: str, uri: str) -> list[dict[str, Any]]:
    sid = server_id.strip()
    u = uri.strip()
    current = [p for p in load_resource_pins() if not (p["server_id"] == sid and p["uri"] == u)]
    return save_resource_pins(current)


def _resolve_server(server_id: str) -> dict[str, Any]:
    sid = (server_id or "").strip()
    if not sid:
        raise ValueError(tr("MCP server id is required", "需要 MCP 服务器 id"))
    if sid == "local-fs":
        from src.workspace import get_workspace

        workspace = get_workspace()
        if not workspace:
            raise ValueError(tr("Authorize a workspace first", "请先授权工作区"))
        return {
            "id": sid,
            "name": "Local Filesystem MCP Server",
            "endpoint": (
                f"npx -y @modelcontextprotocol/server-filesystem {workspace['workspace_path']}"
            ),
            "env": None,
            "transport": "stdio",
        }
    for item in load_servers():
        if item.get("id") == sid:
            env = item.get("env") if isinstance(item.get("env"), dict) else None
            return {
                "id": sid,
                "name": item.get("name") or sid,
                "endpoint": str(item.get("endpoint") or ""),
                "env": {str(k): str(v) for k, v in env.items()} if env else None,
                "transport": item.get("transport") or "stdio",
            }
    raise ValueError(tr("MCP server not found", "未找到该 MCP 服务器"))


def _list_resources_sync(server: dict[str, Any]) -> list[dict[str, Any]]:
    from src.mcp_client import McpClient

    client = McpClient(
        str(server.get("name") or "mcp"),
        str(server.get("endpoint") or ""),
        env=server.get("env"),
    )
    if not client.start(oauth_proxy=True):
        raise RuntimeError(client.last_error or "Failed to start MCP server")
    try:
        resources = client.list_resources()
    finally:
        client.close()
    out: list[dict[str, Any]] = []
    for item in resources:
        if not isinstance(item, dict):
            continue
        uri = str(item.get("uri") or "").strip()
        if not uri:
            continue
        out.append(
            {
                "uri": uri,
                "name": str(item.get("name") or uri).strip() or uri,
                "description": str(item.get("description") or "").strip() or None,
                "mimeType": str(item.get("mimeType") or "").strip() or None,
            }
        )
    return out


def _read_resource_sync(server: dict[str, Any], uri: str) -> dict[str, Any]:
    from src.mcp_client import McpClient

    client = McpClient(
        str(server.get("name") or "mcp"),
        str(server.get("endpoint") or ""),
        env=server.get("env"),
    )
    if not client.start(oauth_proxy=True):
        raise RuntimeError(client.last_error or "Failed to start MCP server")
    try:
        result = client.read_resource(uri)
    finally:
        client.close()
    contents = result.get("contents") if isinstance(result, dict) else None
    texts: list[str] = []
    if isinstance(contents, list):
        for block in contents:
            if not isinstance(block, dict):
                continue
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text)
            elif isinstance(block.get("blob"), str):
                texts.append(f"[binary blob omitted: {block.get('mimeType') or 'unknown'}]")
    body = "\n\n".join(texts).strip()
    if len(body) > _MAX_ONE_RESOURCE_CHARS:
        body = body[:_MAX_ONE_RESOURCE_CHARS] + "\n…[truncated]"
    return {"uri": uri, "text": body, "raw": result}


async def list_server_resources(server_id: str) -> dict[str, Any]:
    server = _resolve_server(server_id)
    resources = await asyncio.to_thread(_list_resources_sync, server)
    return {
        "server_id": server["id"],
        "name": server["name"],
        "resources": resources,
        "count": len(resources),
    }


async def read_server_resource(server_id: str, uri: str) -> dict[str, Any]:
    server = _resolve_server(server_id)
    u = (uri or "").strip()
    if not u:
        raise ValueError(tr("uri is required", "需要 uri"))
    payload = await asyncio.to_thread(_read_resource_sync, server, u)
    return {"server_id": server["id"], "name": server["name"], **payload}


async def pin_resource(pin: dict[str, Any]) -> list[dict[str, Any]]:
    uri = str(pin.get("uri") or "").strip()
    server_id = str(pin.get("server_id") or "").strip()
    if not uri or not server_id:
        raise ValueError(tr("server_id and uri are required", "需要 server_id 与 uri"))
    text = pin.get("text") if isinstance(pin.get("text"), str) else None
    if not text:
        try:
            payload = await read_server_resource(server_id, uri)
            text = str(payload.get("text") or "")
        except Exception as exc:
            text = f"(resource pinned but unread: {exc})"
    current = [p for p in load_resource_pins() if not (p["server_id"] == server_id and p["uri"] == uri)]
    current.insert(
        0,
        {
            "server_id": server_id,
            "uri": uri,
            "name": str(pin.get("name") or uri).strip() or uri,
            "mimeType": str(pin.get("mimeType") or "").strip() or None,
            "text": text,
        },
    )
    return save_resource_pins(current)


def format_pinned_resources_block() -> str:
    """Sync prompt layer from pinned snapshots (D43)."""
    pins = load_resource_pins()
    if not pins:
        return ""
    chunks: list[str] = [
        "Pinned MCP resources (user-selected; treat as trusted context for this Chat):"
    ]
    used = 0
    for pin in pins:
        text = str(pin.get("text") or "").strip()
        label = f"### {pin.get('name') or pin['uri']}\nURI: {pin['uri']}"
        if not text:
            chunks.append(f"{label}\n\n(empty)")
            continue
        remaining = _MAX_INJECT_CHARS - used
        if remaining <= 80:
            chunks.append("…[additional pinned resources omitted]")
            break
        snippet = text if len(text) <= remaining else text[: remaining - 20] + "\n…[truncated]"
        chunks.append(f"{label}\n\n{snippet}")
        used += len(snippet)
    return "\n\n".join(chunks)
