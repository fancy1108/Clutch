"""Local AI tool detection and user connection preferences.

Scans a built-in candidate set covering both AI CLI binaries (via PATH) and
macOS desktop clients (via /Applications). Only candidates actually present on
the machine are surfaced. Connection state is a persisted preference flag — it
does not yet drive execution routing for desktop clients.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

CLI_CANDIDATES: list[dict[str, str]] = [
    {
        "id": "claude-cli",
        "name": "Claude Code CLI",
        "binary": "claude",
        "description": "Terminal-based Claude Code for scripting and local agent execution.",
        "icon": "terminal",
    },
    {
        "id": "agy-cli",
        "name": "Antigravity CLI",
        "binary": "agy",
        "description": "Antigravity command-line agent runtime.",
        "icon": "terminal",
    },
    {
        "id": "codex-cli",
        "name": "OpenAI Codex CLI",
        "binary": "codex",
        "description": "Codex command-line coding agent.",
        "icon": "terminal",
    },
    {
        "id": "code-cli",
        "name": "VS Code CLI",
        "binary": "code",
        "description": "Visual Studio Code command-line interface.",
        "icon": "terminal",
    },
    {
        "id": "codeium-cli",
        "name": "Codeium CLI",
        "binary": "codeium",
        "description": "Codeium command-line assistant.",
        "icon": "terminal",
    },
    {
        "id": "aider-cli",
        "name": "Aider",
        "binary": "aider",
        "description": "Aider AI pair programmer in the terminal.",
        "icon": "terminal",
    },
    {
        "id": "gemini-cli",
        "name": "Gemini CLI",
        "binary": "gemini",
        "description": "Google Gemini command-line interface.",
        "icon": "terminal",
    },
    {
        "id": "ollama-cli",
        "name": "Ollama",
        "binary": "ollama",
        "description": "Local model runner and CLI.",
        "icon": "terminal",
    },
    {
        "id": "cursor-cli",
        "name": "Cursor CLI",
        "binary": "cursor",
        "description": "Cursor command-line launcher.",
        "icon": "edit_document",
    },
]

# macOS desktop client candidates probed under /Applications and ~/Applications.
CLIENT_CANDIDATES: list[dict[str, str]] = []


TOOLS_ENV = "CLUTCH_TOOLS_CONFIG"

_CLI_EXTRA_BIN_DIRS: tuple[Path, ...] = (
    Path.home() / ".local" / "bin",
    Path.home() / ".npm-global" / "bin",
    Path.home() / "bin",
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
)


def _extra_cli_search_dirs() -> list[Path]:
    dirs = list(_CLI_EXTRA_BIN_DIRS)
    nvm_root = Path.home() / ".nvm" / "versions" / "node"
    if nvm_root.is_dir():
        for version_dir in sorted(nvm_root.iterdir(), reverse=True):
            if version_dir.is_dir():
                dirs.append(version_dir / "bin")
    return dirs


def config_path() -> Path:
    override = os.environ.get(TOOLS_ENV)
    if override:
        return Path(override)
    from src.storage_helper import get_storage_dir
    return get_storage_dir() / "tools.json"


def _cli_path(binary: str) -> str | None:
    found = shutil.which(binary)
    return found


def _client_path(app_name: str) -> str | None:
    if sys.platform != "darwin":
        return None
    candidates = [
        Path("/Applications") / app_name,
        Path.home() / "Applications" / app_name,
    ]
    for path in candidates:
        if path.is_dir():
            return str(path)
    return None


def _candidate_by_id(tool_id: str) -> dict[str, str] | None:
    for cand in CLI_CANDIDATES + CLIENT_CANDIDATES:
        if cand["id"] == tool_id:
            return cand
    return None


def _resolve_path(tool_id: str) -> str | None:
    cand = _candidate_by_id(tool_id)
    if cand is None:
        return None
    if "binary" in cand:
        return _cli_path(cand["binary"])
    return _client_path(cand["app_name"])


def resolve_tool_binary(tool_id: str) -> str | None:
    """Resolve CLI binary path, including common install dirs when PATH is narrow."""
    direct = _resolve_path(tool_id)
    if direct:
        return direct
    cand = _candidate_by_id(tool_id)
    if cand is None or "binary" not in cand:
        return None
    binary = cand["binary"]
    for directory in _extra_cli_search_dirs():
        candidate = directory / binary
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def tool_available_for_routing(tool_id: str) -> bool:
    if resolve_tool_binary(tool_id):
        return True
    return tool_id in load_connected_ids()


def _is_claude_installed() -> bool:
    return _cli_path("claude") is not None


def _is_cursor_installed() -> bool:
    if _cli_path("cursor"):
        return True
    return _client_path("Cursor.app") is not None


def _installed(tool_id: str) -> bool:
    cand = _candidate_by_id(tool_id)
    if cand is None:
        return False
    if "binary" in cand:
        return resolve_tool_binary(tool_id) is not None
    return _resolve_path(tool_id) is not None


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
    known = {cand["id"] for cand in CLI_CANDIDATES + CLIENT_CANDIDATES}
    return {str(item) for item in connected if item in known}


def save_connected_ids(connected: set[str]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"connected": sorted(connected)}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def list_tools_status() -> list[dict[str, Any]]:
    connected = load_connected_ids()
    tools: list[dict[str, Any]] = []
    for cand in CLI_CANDIDATES:
        path = resolve_tool_binary(cand["id"])
        if not path:
            continue
        tools.append(
            {
                "id": cand["id"],
                "name": cand["name"],
                "description": cand["description"],
                "icon": cand["icon"],
                "kind": "cli",
                "path": path,
                "installed": True,
                "connected": cand["id"] in connected,
            }
        )
    for cand in CLIENT_CANDIDATES:
        path = _client_path(cand["app_name"])
        if not path:
            continue
        tools.append(
            {
                "id": cand["id"],
                "name": cand["name"],
                "description": cand["description"],
                "icon": cand["icon"],
                "kind": "client",
                "path": path,
                "installed": True,
                "connected": cand["id"] in connected,
            }
        )
    return tools


def connect_tool(tool_id: str) -> dict[str, Any]:
    if _candidate_by_id(tool_id) is None:
        raise ValueError(f"Unknown tool: {tool_id}")
    if not _installed(tool_id):
        raise ValueError(f"Tool not installed: {tool_id}")
    connected = load_connected_ids()
    connected.add(tool_id)
    save_connected_ids(connected)
    return {"id": tool_id, "connected": True}


def disconnect_tool(tool_id: str) -> dict[str, Any]:
    if _candidate_by_id(tool_id) is None:
        raise ValueError(f"Unknown tool: {tool_id}")
    connected = load_connected_ids()
    connected.discard(tool_id)
    save_connected_ids(connected)
    return {"id": tool_id, "connected": False}
