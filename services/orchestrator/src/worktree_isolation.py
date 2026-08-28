"""D32 — optional git worktree isolation for Agent edits."""

from __future__ import annotations

import contextvars
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any

from src.preferences_storage import tr

_GIT_ENV_KEYS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in _GIT_ENV_KEYS:
        env.pop(key, None)
    return env

_worktree_context: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "worktree_isolation_context", default=None
)


def bind_worktree_context(ctx: dict[str, Any] | None) -> contextvars.Token[dict[str, Any] | None]:
    return _worktree_context.set(ctx)


def release_worktree_context(token: contextvars.Token[dict[str, Any] | None]) -> None:
    _worktree_context.reset(token)


def get_worktree_context() -> dict[str, Any] | None:
    return _worktree_context.get()


def worktrees_parent(workspace_root: Path) -> Path:
    return workspace_root / ".clutch" / "worktrees"


def _run_git(workspace_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(workspace_root),
        capture_output=True,
        text=True,
        check=False,
        env=_git_env(),
    )


def _is_git_repo(workspace_root: Path) -> bool:
    result = _run_git(workspace_root, ["rev-parse", "--git-dir"])
    return result.returncode == 0


def create_worktree(workspace_root: Path, *, worktree_id: str | None = None) -> dict[str, Any]:
    if not _is_git_repo(workspace_root):
        raise RuntimeError(
            tr(
                "Workspace is not a git repository; worktree isolation requires git.",
                "工作区不是 git 仓库，无法创建隔离 worktree。",
            )
        )
    wt_id = (worktree_id or f"wt_{uuid.uuid4().hex[:8]}").strip()
    branch = f"clutch/{wt_id}"
    parent = worktrees_parent(workspace_root)
    wt_path = parent / wt_id
    if wt_path.exists():
        raise RuntimeError(tr(f"Worktree already exists: {wt_id}", f"Worktree 已存在：{wt_id}"))
    parent.mkdir(parents=True, exist_ok=True)
    result = _run_git(
        workspace_root,
        ["worktree", "add", "-b", branch, str(wt_path)],
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            tr(f"git worktree add failed: {detail}", f"git worktree add 失败：{detail}")
        )
    return {
        "id": wt_id,
        "path": str(wt_path.resolve()),
        "branch": branch,
        "enabled": True,
    }


def discard_worktree(workspace_root: Path, wt_id: str) -> None:
    wt_path = worktrees_parent(workspace_root) / wt_id
    if wt_path.exists():
        result = _run_git(workspace_root, ["worktree", "remove", "--force", str(wt_path)])
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                tr(f"git worktree remove failed: {detail}", f"git worktree remove 失败：{detail}")
            )
    branch = f"clutch/{wt_id}"
    _run_git(workspace_root, ["branch", "-D", branch])


def merge_worktree(workspace_root: Path, wt_id: str) -> str:
    """Merge isolation branch into the main checkout. Keep the worktree (Discard removes it)."""
    branch = f"clutch/{wt_id}"
    wt_path = worktrees_parent(workspace_root) / wt_id
    if not wt_path.is_dir():
        raise RuntimeError(tr("Worktree not found", "Worktree 不存在"))

    if worktree_has_dirty_changes(wt_path):
        added = _run_git(wt_path, ["add", "-A"])
        if added.returncode != 0:
            detail = (added.stderr or added.stdout or "").strip()
            raise RuntimeError(tr(f"git add failed: {detail}", f"git add 失败：{detail}"))
        committed = _run_git(wt_path, ["commit", "-m", f"clutch: merge worktree {wt_id}"])
        if committed.returncode != 0:
            detail = (committed.stderr or committed.stdout or "").strip()
            raise RuntimeError(
                tr(f"git commit failed: {detail}", f"git commit 失败：{detail}")
            )

    result = _run_git(workspace_root, ["merge", branch, "--no-edit"])
    if result.returncode != 0:
        _run_git(workspace_root, ["merge", "--abort"])
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(tr(f"git merge failed: {detail}", f"git merge 失败：{detail}"))
    return (result.stdout or "").strip() or tr("Merged worktree branch.", "已合并 worktree 分支。")


def list_worktrees(workspace_root: Path) -> list[dict[str, Any]]:
    parent = worktrees_parent(workspace_root)
    if not parent.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for child in sorted(parent.iterdir()):
        if not child.is_dir():
            continue
        info = {
            "id": child.name,
            "path": str(child.resolve()),
            "branch": f"clutch/{child.name}",
            "enabled": True,
        }
        rows.append(describe_worktree(info, workspace_root))
    return rows


def resolve_view_root(wt_id: str | None) -> Path:
    """Files/Changes view root: main checkout, or `.clutch/worktrees/<id>`."""
    from src.workspace import WorkspaceError, require_authorized_workspace

    main = require_authorized_workspace()
    key = (wt_id or "").strip()
    if not key:
        return main
    if "/" in key or "\\" in key or key in {".", ".."}:
        raise WorkspaceError(tr("Worktree not found", "Worktree 不存在"))
    parent = worktrees_parent(main).resolve()
    candidate = (parent / key).resolve()
    if not candidate.is_dir() or candidate.parent != parent:
        raise WorkspaceError(tr("Worktree not found", "Worktree 不存在"))
    return candidate


def worktree_has_dirty_changes(wt_path: Path) -> bool:
    if not wt_path.is_dir():
        return False
    result = _run_git(wt_path, ["status", "--porcelain"])
    return bool(result.stdout.strip())


def describe_worktree(info: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    wt_path = Path(str(info.get("path") or ""))
    dirty = worktree_has_dirty_changes(wt_path) if wt_path.is_dir() else False
    return {
        **info,
        "dirty": dirty,
        "workspace_root": str(workspace_root.resolve()),
    }
