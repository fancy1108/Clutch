"""Risk classification for MCP tool calls (P2-19)."""

from __future__ import annotations

from typing import Any

_RISKY_TOKENS = (
    "write",
    "delete",
    "remove",
    "execute",
    "run",
    "shell",
    "command",
    "edit",
    "patch",
    "create",
    "move",
    "rename",
)


def is_risky_mcp_tool(tool_name: str) -> bool:
    key = tool_name.lower().replace("-", "_")
    return any(token in key for token in _RISKY_TOKENS)


_PATH_ARG_KEYS = ("path", "file_path", "filepath", "target")


def extract_mcp_file_path(tool_name: str, func_args: dict[str, Any]) -> str | None:
    """Return filesystem path from MCP write/edit tool arguments."""
    key = tool_name.lower().replace("-", "_")
    if not any(token in key for token in ("write", "edit", "create", "move", "rename")):
        return None
    for field in _PATH_ARG_KEYS:
        raw = func_args.get(field)
        if raw:
            return str(raw).strip()
    return None
