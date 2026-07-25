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

env = os.environ.copy()
env.update({{
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}})
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
    worktree_has_dirty_changes,
    worktrees_parent,
)

info = create_worktree(repo)
wt_path = Path(info["path"])
(wt_path / "dirty.txt").write_text("side\\n", encoding="utf-8")
assert worktree_has_dirty_changes(wt_path)
assert subprocess.run(["git", "diff", "--name-only"], cwd=repo, capture_output=True, text=True, env=env).stdout.strip() == ""
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
