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
    "apply_patch",
)


def is_risky_mcp_tool(tool_name: str) -> bool:
    key = tool_name.lower().replace("-", "_")
    return any(token in key for token in _RISKY_TOKENS)


_PATH_ARG_KEYS = ("path", "file_path", "filepath", "target", "source", "destination", "patch")


def extract_mcp_file_path(tool_name: str, func_args: dict[str, Any]) -> str | None:
    """Return filesystem path from MCP write/edit tool arguments."""
    key = tool_name.lower().replace("-", "_")
    if key == "apply_patch" or "apply_patch" in key:
        from src.apply_patch import extract_patch_paths

        patch = str(func_args.get("patch", "")).strip()
        paths = extract_patch_paths(patch) if patch else []
        return paths[0] if paths else None
    if not any(token in key for token in ("write", "edit", "create", "move", "rename", "delete")):
        return None
    for field in _PATH_ARG_KEYS:
        raw = func_args.get(field)
        if raw:
            return str(raw).strip()
    return None


def extract_mcp_file_paths(tool_name: str, func_args: dict[str, Any]) -> list[str]:
    """Return all filesystem paths referenced by a tool call."""
    key = tool_name.lower().replace("-", "_")
    if key == "apply_patch" or "apply_patch" in key:
        from src.apply_patch import extract_patch_paths

        patch = str(func_args.get("patch", "")).strip()
        return extract_patch_paths(patch) if patch else []
    single = extract_mcp_file_path(tool_name, func_args)
    return [single] if single else []
