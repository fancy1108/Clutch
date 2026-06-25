"""Risk classification for MCP tool calls (P2-19)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
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


def _tool_basename(tool_name: str) -> str:
    if "__" in tool_name:
        return tool_name.split("__", 1)[1]
    return tool_name


def _normalize_path_for_approval(path: str) -> str:
    raw = str(path).strip()
    if not raw:
        return raw
    try:
        from src.workspace import to_workspace_relative

        rel = to_workspace_relative(raw)
        if rel is not None:
            return rel
    except Exception:
        pass
    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        return str(candidate.resolve())
    return raw


def normalize_mcp_func_args_for_display(func_args: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of tool args with workspace-relative paths for approval UI."""
    if not func_args:
        return {}
    out = dict(func_args)
    for field in _PATH_ARG_KEYS:
        raw = out.get(field)
        if raw:
            out[field] = _normalize_path_for_approval(str(raw))
    return out


def mcp_approval_key(tool_name: str, func_args: dict[str, Any]) -> str:
    """Stable key for deduplicating risky tool approvals within a run."""
    basename = _tool_basename(tool_name).lower().replace("-", "_")
    paths = [
        _normalize_path_for_approval(path)
        for path in extract_mcp_file_paths(tool_name, func_args)
    ]
    paths.sort()
    payload: dict[str, Any] = {"paths": paths}
    if "content" in func_args:
        payload["content"] = str(func_args.get("content", ""))
    if "patch" in func_args:
        from src.apply_patch import normalize_patch_text

        payload["patch"] = normalize_patch_text(str(func_args.get("patch", "")))
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"{basename}|{digest}"


def move_file_delete_workaround_message(tool_name: str, func_args: dict[str, Any]) -> str | None:
    """Block move/rename patterns that mimic delete instead of using apply_patch."""
    key = tool_name.lower().replace("-", "_")
    if "move" not in key and "rename" not in key:
        return None
    source = str(func_args.get("source", "")).strip()
    destination = str(func_args.get("destination", "")).strip()
    if not source or not destination:
        return None
    src_name = Path(source).name
    dest_name = Path(destination).name
    if dest_name.startswith(".deleted"):
        return (
            "move_file to `.deleted_*` is not a real delete. "
            "Use clutch-tools__apply_patch with `*** Delete File: <path>` instead."
        )
    if src_name.startswith(".") and not dest_name.startswith(".") and src_name.lstrip(".") == dest_name:
        return (
            f"move_file from `{src_name}` to `{dest_name}` only removes the leading dot; "
            f"use clutch-tools__apply_patch with `*** Delete File: {source}` to delete the file."
        )
    return None
