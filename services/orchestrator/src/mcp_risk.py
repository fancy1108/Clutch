"""Risk classification for MCP tool calls (P2-19)."""

from __future__ import annotations

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
