"""Authorized workspace paths, multi-repo list, and path whitelist (M2-09 / M4-05)."""

from __future__ import annotations

import contextvars
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from src.preferences_storage import tr

_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "target"}
# Dot-dirs normally hidden in Files tree; Clutch design/handoff artifacts must stay visible.
_VISIBLE_DOT_DIRS = {".clutch"}
WORKSPACES_ENV = "CLUTCH_WORKSPACES_FILE"

_workspaces: dict[str, dict[str, str]] = {}
_repository_groups: dict[str, dict[str, Any]] = {}
_active_id: str | None = None
_loaded = False
_persistence_disabled = False

logger = logging.getLogger(__name__)


class WorkspaceError(PermissionError):
    """Raised when workspace is missing or path is outside whitelist."""


def _store_path() -> Path:
    override = os.environ.get(WORKSPACES_ENV)
    if override:
        return Path(override)
    from src.storage_helper import get_storage_dir
    return get_storage_dir() / "workspaces.json"


def stable_workspace_id(resolved: Path) -> str:
    """Deterministic id for a resolved workspace path (same path → same id)."""
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:12]
    return f"ws_{digest}"


def _temp_roots() -> list[Path]:
    roots: list[Path] = []
    for raw in (
        os.environ.get("TMPDIR"),
        os.environ.get("TMP"),
        os.environ.get("TEMP"),
        tempfile.gettempdir(),
        "/tmp",
        "/private/var/folders",
        "/var/folders",
    ):
        if not raw:
            continue
        try:
            roots.append(Path(raw).expanduser().resolve())
        except OSError:
            continue
    return roots


def _is_ephemeral_path(resolved: Path) -> bool:
    text = str(resolved)
    if "clutch-e2e" in text:
        return True
    name = resolved.name
    if name.startswith("tmp") and len(name) >= 6:
        for root in _temp_roots():
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
    return False


def _using_isolated_store() -> bool:
    return bool(
        os.environ.get("CLUTCH_STORAGE_DIR")
        or os.environ.get(WORKSPACES_ENV)
        or os.environ.get("CLUTCH_E2E_SANDBOX")
    )


def _guard_ephemeral_authorize(resolved: Path) -> None:
    """Block temp/e2e sandboxes from polluting the default Application Support store."""
    if _using_isolated_store() or os.environ.get("CLUTCH_ALLOW_TEMP_WORKSPACE") == "1":
        return
    if not _is_ephemeral_path(resolved):
        return
    raise WorkspaceError(
        tr(
            "Refusing to authorize a temporary folder in the default Clutch store "
            "(likely a test sandbox). Re-open your real project folder, or set "
            "CLUTCH_ALLOW_TEMP_WORKSPACE=1 to override.",
            "拒绝将临时目录写入默认 Clutch 存储（多为测试沙箱）。请重新选择真实项目文件夹，"
            "或设置 CLUTCH_ALLOW_TEMP_WORKSPACE=1 覆盖。",
        )
    )


def _remap_history_workspace_ids(id_map: dict[str, str]) -> None:
    if not id_map:
        return
    try:
        from src import run_history
    except Exception:
        return
    remap = getattr(run_history, "remap_workspace_ids", None)
    if callable(remap):
        remap(id_map)


def _migrate_to_stable_ids() -> bool:
    """Rewrite legacy random workspace ids to path-stable ids; remap session history."""
    global _workspaces, _active_id
    id_map: dict[str, str] = {}
    rewritten: dict[str, dict[str, str]] = {}
    changed = False
    for old_id, entry in list(_workspaces.items()):
        raw_path = str(entry.get("workspace_path") or "").strip()
        if not raw_path:
            rewritten[old_id] = entry
            continue
        try:
            resolved = Path(raw_path).expanduser().resolve()
        except OSError:
            rewritten[old_id] = entry
            continue
        new_id = stable_workspace_id(resolved)
        new_entry = {
            "id": new_id,
            "workspace_path": str(resolved),
            "name": str(entry.get("name") or resolved.name),
        }
        if old_id != new_id:
            id_map[old_id] = new_id
            changed = True
        if str(entry.get("workspace_path")) != str(resolved) or entry.get("id") != new_id:
            changed = True
        if new_id in rewritten and rewritten[new_id]["workspace_path"] != new_entry["workspace_path"]:
            # Path collision on hash — keep the first; drop duplicate key.
            continue
        rewritten[new_id] = new_entry
    if not changed:
        return False
    _workspaces = rewritten
    if _active_id in id_map:
        _active_id = id_map[_active_id]
    elif _active_id not in _workspaces:
        _active_id = next(iter(_workspaces), None)
    for group in _repository_groups.values():
        workspace_ids = group.get("workspace_ids")
        if isinstance(workspace_ids, list):
            group["workspace_ids"] = [id_map.get(str(item), str(item)) for item in workspace_ids]
            changed = True
    _remap_history_workspace_ids(id_map)
    return True


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
    except (OSError, json.JSONDecodeError) as exc:
        logger.error(
            "workspaces.json unreadable (%s); leaving in-memory empty and quarantining file",
            exc,
        )
        try:
            quarantine = path.with_name(path.name + ".corrupt")
            path.replace(quarantine)
        except OSError:
            pass
        _loaded = True
        return
    _workspaces = {item["id"]: item for item in data.get("workspaces", []) if "id" in item}
    _repository_groups = {
        item["id"]: item for item in data.get("repository_groups", []) if "id" in item
    }
    active = data.get("active_id")
    _active_id = active if active in _workspaces else None
    _loaded = True
    if _migrate_to_stable_ids():
        _persist()


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
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


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


def is_workspace_path_available(path: str) -> bool:
    """True when path exists and is a directory (does not mutate registry)."""
    if not str(path or "").strip():
        return False
    try:
        resolved = Path(path).expanduser().resolve()
    except OSError:
        return False
    return resolved.is_dir()


def workspace_path_missing_message(path: str) -> str:
    return tr(
        f"Workspace folder no longer exists: {path}. Re-add the project folder in the sidebar.",
        f"项目文件夹已不存在：{path}。请在侧栏重新添加项目文件夹。",
    )


def _entry_for_path(resolved: Path) -> dict[str, str]:
    return {
        "id": stable_workspace_id(resolved),
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
    _guard_ephemeral_authorize(resolved)
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
    if not is_workspace_path_available(entry["workspace_path"]):
        raise WorkspaceError(workspace_path_missing_message(entry["workspace_path"]))
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
    entry = _workspaces.get(_active_id)
    if entry is None:
        return None
    if not is_workspace_path_available(entry["workspace_path"]):
        return None
    return entry


def active_workspace_issue() -> str | None:
    """Human-readable reason when interactive PTY / cwd cannot use the active workspace."""
    _ensure_loaded()
    if _active_id is None:
        return tr(
            "No workspace authorized for interactive PTY. Select a project folder in the sidebar.",
            "未授权工作区，无法启动交互终端。请在侧栏选择项目文件夹。",
        )
    entry = _workspaces.get(_active_id)
    if entry is None:
        return tr(
            "No workspace authorized for interactive PTY. Select a project folder in the sidebar.",
            "未授权工作区，无法启动交互终端。请在侧栏选择项目文件夹。",
        )
    if not is_workspace_path_available(entry["workspace_path"]):
        return workspace_path_missing_message(entry["workspace_path"])
    return None


_effective_root: contextvars.ContextVar[Path | None] = contextvars.ContextVar(
    "workspace_effective_root", default=None
)


def bind_effective_workspace_root(path: Path | None) -> contextvars.Token[Path | None]:
    """D32 — override Agent tool cwd (e.g. git worktree path)."""
    return _effective_root.set(path)


def release_effective_workspace_root(token: contextvars.Token[Path | None]) -> None:
    _effective_root.reset(token)


def require_workspace() -> Path:
    override = _effective_root.get()
    if override is not None:
        return override.resolve()
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
    from src.preferences_storage import load_strict_sandbox

    if load_strict_sandbox():
        _assert_strict_sandbox_path(root, relative_path, target)
    return target


def _assert_strict_sandbox_path(root: Path, relative_path: str, target: Path) -> None:
    """Extra strict-sandbox checks after workspace bounds (D21)."""
    rel = str(relative_path).replace("\\", "/").strip()
    if rel.startswith("/") or rel.startswith("~"):
        raise WorkspaceError(
            tr(
                f"Strict sandbox: use workspace-relative paths only (got: {relative_path})",
                f"严格沙箱：仅允许工作区相对路径（收到：{relative_path}）",
            )
        )
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise WorkspaceError(
            tr(
                f"Strict sandbox: path resolves outside workspace: {relative_path}",
                f"严格沙箱：路径解析到工作区外：{relative_path}",
            )
        ) from exc


def assert_strict_sandbox_command(command: str, root: Path) -> None:
    from src.preferences_storage import load_strict_sandbox

    if not load_strict_sandbox():
        return
    trimmed = command.strip()
    if not trimmed:
        return
    if re.search(r"(?:^|[\s;&|])(?:\.\./)+", trimmed):
        raise WorkspaceError(
            tr(
                "Strict sandbox: shell command cannot use ../ to escape the workspace",
                "严格沙箱：shell 命令不能使用 ../ 逃出工作区",
            )
        )
    root_resolved = root.resolve()
    for match in re.finditer(r"(?:^|[\s'\"])(/[^\s'\";|&]+)", trimmed):
        try:
            candidate = Path(match.group(1)).expanduser().resolve()
        except OSError:
            continue
        if candidate != root_resolved and root_resolved not in candidate.parents:
            raise WorkspaceError(
                tr(
                    f"Strict sandbox: command references path outside workspace: {match.group(1)}",
                    f"严格沙箱：命令引用了工作区外路径：{match.group(1)}",
                )
            )


def to_workspace_relative(path: str) -> str | None:
    """Map an absolute or relative path to a workspace-relative path when possible."""
    root = require_workspace()
    raw = Path(path).expanduser()
    target = (root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    if target != root and root not in target.parents:
        return None
    rel = target.relative_to(root)
    return "." if str(rel) == "." else str(rel)


# Skip noisy / internal trees when detecting shell-side file mutations.
_SNAPSHOT_SKIP_DIRS = _SKIP_DIRS | {
    ".clutch",
    ".mimocode",
    ".workbuddy",
    ".rivet",
    ".idea",
    ".vscode",
}
_SNAPSHOT_MAX_FILES = 8000


def snapshot_workspace_mtimes(root: Path | None = None) -> dict[str, tuple[int, int]]:
    """Map workspace-relative path → (mtime_ns, size) for mutation detection."""
    base = (root or require_workspace()).resolve()
    out: dict[str, tuple[int, int]] = {}
    stack = [base]
    while stack and len(out) < _SNAPSHOT_MAX_FILES:
        directory = stack.pop()
        try:
            entries = list(directory.iterdir())
        except OSError:
            continue
        for entry in entries:
            name = entry.name
            if name in _SNAPSHOT_SKIP_DIRS:
                continue
            try:
                if entry.is_dir() and not entry.is_symlink():
                    stack.append(entry)
                    continue
                if not entry.is_file():
                    continue
                st = entry.stat()
                rel = str(entry.relative_to(base)).replace(os.sep, "/")
                out[rel] = (st.st_mtime_ns, st.st_size)
            except OSError:
                continue
    return out


def diff_workspace_snapshots(
    before: dict[str, tuple[int, int]],
    after: dict[str, tuple[int, int]],
) -> list[str]:
    """Return relative paths added, removed, or modified between snapshots."""
    changed: list[str] = []
    for path, meta in after.items():
        if before.get(path) != meta:
            changed.append(path)
    for path in before:
        if path not in after:
            changed.append(path)
    changed.sort()
    return changed


def list_tree(max_depth: int = 5) -> list[dict[str, Any]]:
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
            if entry.name in _SKIP_DIRS:
                continue
            if entry.name.startswith(".") and entry.name not in _VISIBLE_DOT_DIRS:
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
