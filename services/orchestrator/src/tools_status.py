"""Local AI tool detection and user connection preferences."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

TOOLS_ENV = "CLUTCH_TOOLS_CONFIG"

TOOL_CATALOG: dict[str, dict[str, str]] = {
    "claude-cli": {
        "name": "Claude Code CLI",
        "description": "Terminal-based Claude Code for scripting and local agent execution.",
        "icon": "terminal",
    },
    "cursor": {
        "name": "Cursor",
        "description": "Open the authorized workspace in Cursor for IDE-based agent work.",
        "icon": "edit_document",
    },
}


def config_path() -> Path:
    override = os.environ.get(TOOLS_ENV)
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "clutch" / "tools.json"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "clutch" / "tools.json"
    return Path.home() / ".local" / "share" / "clutch" / "tools.json"


def _is_claude_installed() -> bool:
    return shutil.which("claude") is not None


def _is_cursor_installed() -> bool:
    if shutil.which("cursor"):
        return True
    if sys.platform == "darwin":
        return Path("/Applications/Cursor.app").is_dir()
    return False


def _installed(tool_id: str) -> bool:
    if tool_id == "claude-cli":
        return _is_claude_installed()
    if tool_id == "cursor":
        return _is_cursor_installed()
    return False


def load_connected_ids() -> set[str]:
    path = config_path()
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    connected = data.get("connected")
    if not isinstance(connected, list):
        return set()
    return {str(item) for item in connected if item in TOOL_CATALOG}


def save_connected_ids(connected: set[str]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"connected": sorted(connected)}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def list_tools_status() -> list[dict[str, Any]]:
    connected = load_connected_ids()
    tools: list[dict[str, Any]] = []
    for tool_id, meta in TOOL_CATALOG.items():
        installed = _installed(tool_id)
        is_connected = tool_id in connected and installed
        if not installed:
            continue
        tools.append(
            {
                "id": tool_id,
                "name": meta["name"],
                "description": meta["description"],
                "icon": meta["icon"],
                "installed": True,
                "connected": is_connected,
            }
        )
    return tools


def connect_tool(tool_id: str) -> dict[str, Any]:
    if tool_id not in TOOL_CATALOG:
        raise ValueError(f"Unknown tool: {tool_id}")
    if not _installed(tool_id):
        raise ValueError(f"Tool not installed: {tool_id}")
    connected = load_connected_ids()
    connected.add(tool_id)
    save_connected_ids(connected)
    return {"id": tool_id, "connected": True}


def disconnect_tool(tool_id: str) -> dict[str, Any]:
    if tool_id not in TOOL_CATALOG:
        raise ValueError(f"Unknown tool: {tool_id}")
    connected = load_connected_ids()
    connected.discard(tool_id)
    save_connected_ids(connected)
    return {"id": tool_id, "connected": False}
