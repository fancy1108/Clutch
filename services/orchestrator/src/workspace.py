"""Authorized workspace path, file tree, and path whitelist (M2-09 / M4-05)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_workspace_path: Path | None = None
_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "target"}


class WorkspaceError(PermissionError):
    """Raised when workspace is missing or path is outside whitelist."""


def set_workspace(path: str) -> dict[str, str]:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise WorkspaceError(f"工作区路径不存在或不是目录：{path}")
    global _workspace_path
    _workspace_path = resolved
    return {"workspace_path": str(resolved), "name": resolved.name}


def get_workspace() -> dict[str, str] | None:
    if _workspace_path is None:
        return None
    return {"workspace_path": str(_workspace_path), "name": _workspace_path.name}


def require_workspace() -> Path:
    if _workspace_path is None:
        raise WorkspaceError("未授权工作区，请先在应用中选择一个项目根目录。")
    return _workspace_path


def resolve_allowed_path(relative_path: str) -> Path:
    root = require_workspace()
    target = (root / relative_path).resolve()
    if target != root and root not in target.parents:
        raise WorkspaceError(f"禁止访问工作区外的路径：{relative_path}")
    return target


def list_tree(max_depth: int = 3) -> list[dict[str, Any]]:
    root = require_workspace()

    def walk(directory: Path, depth: int) -> list[dict[str, Any]]:
        if depth > max_depth:
            return []
        nodes: list[dict[str, Any]] = []
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return nodes
        for entry in entries:
            if entry.name in _SKIP_DIRS or entry.name.startswith("."):
                continue
            rel = str(entry.relative_to(root))
            if entry.is_dir():
                nodes.append(
                    {
                        "name": entry.name,
                        "path": rel,
                        "type": "folder",
                        "children": walk(entry, depth + 1),
                    }
                )
            else:
                nodes.append({"name": entry.name, "path": rel, "type": "file"})
        return nodes

    return walk(root, 0)


def read_file(relative_path: str, *, max_bytes: int = 512_000) -> str:
    target = resolve_allowed_path(relative_path)
    if not target.is_file():
        raise WorkspaceError(f"文件不存在：{relative_path}")
    size = target.stat().st_size
    if size > max_bytes:
        raise WorkspaceError(f"文件过大（>{max_bytes} 字节）：{relative_path}")
    return target.read_text(encoding="utf-8", errors="replace")


def clear_workspace_for_tests() -> None:
    global _workspace_path
    _workspace_path = None
