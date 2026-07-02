"""Authorized workspace paths, multi-repo list, and path whitelist (M2-09 / M4-05)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from src.preferences_storage import tr

_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "target"}
WORKSPACES_ENV = "CLUTCH_WORKSPACES_FILE"

_workspaces: dict[str, dict[str, str]] = {}
_repository_groups: dict[str, dict[str, Any]] = {}
_active_id: str | None = None
_loaded = False
_persistence_disabled = False


class WorkspaceError(PermissionError):
    """Raised when workspace is missing or path is outside whitelist."""


def _store_path() -> Path:
    override = os.environ.get(WORKSPACES_ENV)
    if override:
        return Path(override)
    from src.storage_helper import get_storage_dir
    return get_storage_dir() / "workspaces.json"


def _ensure_loaded() -> None:
    global _loaded, _workspaces, _repository_groups, _active_id
    if _loaded or _persistence_disabled:
        return
    path = _store_path()
    if not path.is_file():
        _loaded = True
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _loaded = True
        return
    _workspaces = {item["id"]: item for item in data.get("workspaces", []) if "id" in item}
    _repository_groups = {
        item["id"]: item for item in data.get("repository_groups", []) if "id" in item
    }
    active = data.get("active_id")
    _active_id = active if active in _workspaces else None
    _loaded = True


def _persist() -> None:
    if _persistence_disabled:
        return
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "workspaces": list(_workspaces.values()),
        "active_id": _active_id,
        "repository_groups": list(_repository_groups.values()),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _normalize_path(path: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise WorkspaceError(
            tr(
                f"Workspace path does not exist or is not a directory: {path}",
                f"工作区路径不存在或不是目录：{path}",
            )
        )
    return resolved


def _entry_for_path(resolved: Path) -> dict[str, str]:
    return {
        "id": f"ws_{uuid.uuid4().hex[:12]}",
        "workspace_path": str(resolved),
        "name": resolved.name,
    }


def list_workspaces() -> dict[str, Any]:
    _ensure_loaded()
    return {
        "workspaces": list(_workspaces.values()),
        "active_id": _active_id,
    }


def add_workspace(path: str) -> dict[str, str]:
    _ensure_loaded()
    resolved = _normalize_path(path)
    resolved_str = str(resolved)
    for entry in _workspaces.values():
        if entry["workspace_path"] == resolved_str:
            global _active_id
            _active_id = entry["id"]
            _persist()
            return entry
    entry = _entry_for_path(resolved)
    _workspaces[entry["id"]] = entry
    _active_id = entry["id"]
    _persist()
    return entry


def activate_workspace(workspace_id: str) -> dict[str, str]:
    _ensure_loaded()
    entry = _workspaces.get(workspace_id)
    if entry is None:
        raise WorkspaceError(
            tr(
                f"Workspace does not exist: {workspace_id}",
                f"工作区不存在：{workspace_id}",
            )
        )
    global _active_id
    _active_id = workspace_id
    _persist()
    return entry


def remove_workspace(workspace_id: str) -> None:
    _ensure_loaded()
    if workspace_id not in _workspaces:
        raise WorkspaceError(
            tr(
                f"Workspace does not exist: {workspace_id}",
                f"工作区不存在：{workspace_id}",
            )
        )
    global _active_id
    del _workspaces[workspace_id]
    for group in _repository_groups.values():
        workspace_ids = group.get("workspace_ids")
        if isinstance(workspace_ids, list) and workspace_id in workspace_ids:
            group["workspace_ids"] = [item for item in workspace_ids if item != workspace_id]
    if _active_id == workspace_id:
        _active_id = next(iter(_workspaces), None)
    _persist()


def list_repository_groups() -> dict[str, Any]:
    _ensure_loaded()
    return {"groups": list(_repository_groups.values())}


def create_repository_group(name: str) -> dict[str, Any]:
    _ensure_loaded()
    normalized = name.strip()
    if not normalized:
        raise ValueError(tr("Group name cannot be empty", "分组名称不能为空"))
    entry: dict[str, Any] = {
        "id": f"grp_{uuid.uuid4().hex[:12]}",
        "name": normalized,
        "collapsed": False,
        "workspace_ids": [],
    }
    _repository_groups[entry["id"]] = entry
    _persist()
    return entry


def update_repository_group(
    group_id: str,
    *,
    name: str | None = None,
    collapsed: bool | None = None,
    workspace_ids: list[str] | None = None,
) -> dict[str, Any]:
    _ensure_loaded()
    entry = _repository_groups.get(group_id)
    if entry is None:
        raise WorkspaceError(tr(f"Group does not exist: {group_id}", f"分组不存在：{group_id}"))
    if name is not None:
        normalized = name.strip()
        if not normalized:
            raise ValueError(tr("Group name cannot be empty", "分组名称不能为空"))
        entry["name"] = normalized
    if collapsed is not None:
        entry["collapsed"] = collapsed
    if workspace_ids is not None:
        valid_ids = [item for item in workspace_ids if item in _workspaces]
        entry["workspace_ids"] = valid_ids
    _persist()
    return entry


def delete_repository_group(group_id: str) -> None:
    _ensure_loaded()
    if group_id not in _repository_groups:
        raise WorkspaceError(tr(f"Group does not exist: {group_id}", f"分组不存在：{group_id}"))
    del _repository_groups[group_id]
    _persist()


def set_workspace(path: str) -> dict[str, str]:
    return add_workspace(path)


def get_workspace() -> dict[str, str] | None:
    _ensure_loaded()
    if _active_id is None:
        return None
    return _workspaces.get(_active_id)


def require_workspace() -> Path:
    info = get_workspace()
    if info is None:
        raise WorkspaceError(
            tr(
                "Workspace not authorized. Please select a project root in the app first.",
                "未授权工作区，请先在应用中选择一个项目根目录。"
            )
        )
    return Path(info["workspace_path"])


def resolve_allowed_path(relative_path: str) -> Path:
    root = require_workspace()
    target = (root / relative_path).resolve()
    if target != root and root not in target.parents:
        raise WorkspaceError(
            tr(
                f"Access to path outside workspace is forbidden: {relative_path}",
                f"禁止访问工作区外的路径：{relative_path}"
            )
        )
    return target


def to_workspace_relative(path: str) -> str | None:
    """Map an absolute or relative path to a workspace-relative path when possible."""
    root = require_workspace()
    raw = Path(path).expanduser()
    target = (root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    if target != root and root not in target.parents:
        return None
    rel = target.relative_to(root)
    return "." if str(rel) == "." else str(rel)


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


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    kwargs: dict[str, Any] = {}
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if creationflags:
            kwargs["creationflags"] = creationflags
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            **kwargs,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def get_git_info(root: Path | None = None) -> dict[str, Any]:
    """Return current branch and local branch names for a workspace root."""
    if root is None:
        try:
            root = require_workspace()
        except WorkspaceError:
            return {"is_git_repo": False, "branch": None, "branches": []}

    inside = _run_git(root, "rev-parse", "--is-inside-work-tree")
    if inside is None or inside.returncode != 0 or inside.stdout.strip() != "true":
        return {"is_git_repo": False, "branch": None, "branches": []}

    branch: str | None = None
    branch_result = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch_result and branch_result.returncode == 0:
        name = branch_result.stdout.strip()
        if name and name != "HEAD":
            branch = name
        elif name == "HEAD":
            sha = _run_git(root, "rev-parse", "--short", "HEAD")
            if sha and sha.returncode == 0 and sha.stdout.strip():
                branch = f"detached@{sha.stdout.strip()}"

    branches: list[str] = []
    branches_result = _run_git(root, "branch", "--format=%(refname:short)")
    if branches_result and branches_result.returncode == 0:
        branches = sorted({line.strip() for line in branches_result.stdout.splitlines() if line.strip()})

    if branch and branch.startswith("detached@"):
        detached_entries = [name for name in branches if name.startswith("(HEAD detached")]
        if detached_entries:
            branch = detached_entries[0]
        elif branch not in branches:
            branches = sorted(set(branches) | {branch})

    return {"is_git_repo": True, "branch": branch, "branches": branches}


def read_file(relative_path: str, *, max_bytes: int = 512_000) -> str:
    target = resolve_allowed_path(relative_path)
    if not target.is_file():
        raise WorkspaceError(
            tr(
                f"File does not exist: {relative_path}",
                f"文件不存在：{relative_path}"
            )
        )
    size = target.stat().st_size
    if size > max_bytes:
        raise WorkspaceError(
            tr(
                f"File is too large (>{max_bytes} bytes): {relative_path}",
                f"文件过大（>{max_bytes} 字节）：{relative_path}"
            )
        )
    return target.read_text(encoding="utf-8", errors="replace")


def clear_workspace_for_tests() -> None:
    global _workspaces, _repository_groups, _active_id, _loaded, _persistence_disabled
    _workspaces = {}
    _repository_groups = {}
    _active_id = None
    _loaded = True
    _persistence_disabled = True
