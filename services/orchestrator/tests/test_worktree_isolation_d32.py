"""D32 — git worktree isolation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from src.workspace import bind_effective_workspace_root, release_effective_workspace_root

_GIT_ENV_KEYS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in _GIT_ENV_KEYS:
        env.pop(key, None)
    return env


def test_worktree_git_integration_subprocess(tmp_path: Path) -> None:
    """Run git worktree ops in a clean subprocess (vitest can pollute GIT_* in-process)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    ws_file = tmp_path / "ws.json"
    orchestrator_root = Path(__file__).resolve().parents[1]
    script = f"""
import os
import subprocess
import sys
from pathlib import Path

repo = Path({str(repo)!r})
ws_file = {str(ws_file)!r}
os.environ["CLUTCH_WORKSPACES_FILE"] = ws_file
for key in {list(_GIT_ENV_KEYS)!r}:
    os.environ.pop(key, None)

os.environ.update({{
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}})
env = os.environ.copy()
subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, env=env)
(repo / "README.md").write_text("main\\n", encoding="utf-8")
subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True, env=env)
subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True, env=env)

sys.path.insert(0, {str(orchestrator_root)!r})
from src import workspace as workspace_mod
workspace_mod._loaded = False
workspace_mod._workspaces = {{}}
workspace_mod._active_id = None
workspace_mod.add_workspace(str(repo))

from src.worktree_isolation import (
    create_worktree,
    discard_worktree,
    merge_worktree,
    worktree_has_dirty_changes,
)

info = create_worktree(repo)
wt_path = Path(info["path"])
(wt_path / "dirty.txt").write_text("side\\n", encoding="utf-8")
assert worktree_has_dirty_changes(wt_path)
assert subprocess.run(["git", "diff", "--name-only"], cwd=repo, capture_output=True, text=True, env=env).stdout.strip() == ""

from src.worktree_isolation import resolve_view_root
from src.workspace import list_tree, list_uncommitted
wt_names = {{n["name"] for n in list_tree(root=resolve_view_root(info["id"]))}}
main_names = {{n["name"] for n in list_tree(root=resolve_view_root(None))}}
assert "dirty.txt" in wt_names
assert "dirty.txt" not in main_names
wt_changes = list_uncommitted(resolve_view_root(info["id"]))
main_changes = list_uncommitted(resolve_view_root(None))
assert any(f["name"] == "dirty.txt" for f in wt_changes)
assert not any(f["name"] == "dirty.txt" for f in main_changes)

(wt_path / "README.md").write_text("main\\n.\\n", encoding="utf-8")
merge_worktree(repo, info["id"])
assert wt_path.exists()
assert (repo / "README.md").read_text(encoding="utf-8") == "main\\n.\\n"
assert (repo / "dirty.txt").read_text(encoding="utf-8") == "side\\n"

discard_worktree(repo, info["id"])
assert not wt_path.exists()
assert subprocess.run(["git", "diff", "--name-only"], cwd=repo, capture_output=True, text=True, env=env).stdout.strip() == ""
"""
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=_clean_env(),
        cwd=str(tmp_path),
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"worktree subprocess failed ({proc.returncode}):\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )


def test_effective_workspace_root_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    main = tmp_path / "repo"
    main.mkdir()
    side = tmp_path / "side"
    side.mkdir()
    workspace_mod.add_workspace(str(main))

    token = bind_effective_workspace_root(side)
    try:
        assert workspace_mod.require_workspace() == side.resolve()
    finally:
        release_effective_workspace_root(token)
    assert workspace_mod.require_workspace() == main.resolve()


def test_apply_patch_writes_into_bound_worktree(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod
    from src.apply_patch import apply_patch_in_workspace
    from src.worktree_isolation import bind_worktree_context, release_worktree_context

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    main = tmp_path / "repo"
    wt = tmp_path / "repo" / ".clutch" / "worktrees" / "wt_test"
    wt.mkdir(parents=True)
    main.mkdir(exist_ok=True)
    workspace_mod.add_workspace(str(main))

    root_token = bind_effective_workspace_root(wt)
    ctx_token = bind_worktree_context(
        {
            "id": "wt_test",
            "path": str(wt.resolve()),
            "branch": "clutch/wt_test",
            "enabled": True,
            "workspace_root": str(main.resolve()),
        }
    )
    try:
        result = apply_patch_in_workspace(
            "*** Begin Patch\n*** Add File: clutch-fm11.txt\n+ok\n*** End Patch"
        )
        assert result.ok
        assert (wt / "clutch-fm11.txt").read_text(encoding="utf-8") == "ok\n"
        assert not (main / "clutch-fm11.txt").exists()
    finally:
        release_worktree_context(ctx_token)
        release_effective_workspace_root(root_token)


def test_apply_patch_rewrites_absolute_main_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod
    from src.apply_patch import apply_patch_in_workspace
    from src.worktree_isolation import bind_worktree_context, release_worktree_context

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    main = tmp_path / "repo"
    wt = tmp_path / "repo" / ".clutch" / "worktrees" / "wt_abs"
    wt.mkdir(parents=True)
    main.mkdir(exist_ok=True)
    workspace_mod.add_workspace(str(main))

    abs_main = str((main / "clutch-fm11.txt").resolve())
    root_token = bind_effective_workspace_root(wt)
    ctx_token = bind_worktree_context(
        {
            "id": "wt_abs",
            "path": str(wt.resolve()),
            "branch": "clutch/wt_abs",
            "enabled": True,
            "workspace_root": str(main.resolve()),
        }
    )
    try:
        result = apply_patch_in_workspace(
            f"*** Begin Patch\n*** Add File: {abs_main}\n+ok\n*** End Patch"
        )
        assert result.ok
        assert (wt / "clutch-fm11.txt").read_text(encoding="utf-8") == "ok\n"
        assert not (main / "clutch-fm11.txt").exists()
    finally:
        release_worktree_context(ctx_token)
        release_effective_workspace_root(root_token)


def test_resolve_view_root_main_or_named_worktree(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod
    from src.workspace import WorkspaceError
    from src.worktree_isolation import resolve_view_root, worktrees_parent

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    main = tmp_path / "repo"
    main.mkdir()
    workspace_mod.add_workspace(str(main))
    named = worktrees_parent(main) / "wt_view"
    named.mkdir(parents=True)

    assert resolve_view_root(None) == main.resolve()
    assert resolve_view_root("wt_view") == named.resolve()
    try:
        resolve_view_root("../escape")
        raise AssertionError("expected WorkspaceError")
    except WorkspaceError:
        pass
    try:
        resolve_view_root("missing")
        raise AssertionError("expected WorkspaceError")
    except WorkspaceError:
        pass
