"""Tests for Codex-compatible apply_patch."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.apply_patch import (
    ApplyPatchError,
    apply_patch_in_workspace,
    extract_patch_paths,
    parse_patch,
)
from src.builtin_tools import execute_builtin_tool
from src.mcp_risk import extract_mcp_file_path, is_risky_mcp_tool


def test_parse_patch_add_and_delete() -> None:
    patch = (
        "*** Begin Patch\n"
        "*** Add File: path/add.py\n"
        "+abc\n"
        "+def\n"
        "*** Delete File: path/delete.py\n"
        "*** End Patch"
    )
    hunks = parse_patch(patch)
    assert len(hunks) == 2
    assert hunks[0].kind == "add"
    assert hunks[0].path == "path/add.py"
    assert hunks[0].contents == "abc\ndef\n"
    assert hunks[1].kind == "delete"
    assert hunks[1].path == "path/delete.py"


def test_parse_patch_update_with_move() -> None:
    patch = (
        "*** Begin Patch\n"
        "*** Update File: path/update.py\n"
        "*** Move to: path/update2.py\n"
        "@@ def f():\n"
        "-    pass\n"
        "+    return 123\n"
        "*** End Patch"
    )
    hunks = parse_patch(patch)
    assert len(hunks) == 1
    hunk = hunks[0]
    assert hunk.kind == "update"
    assert hunk.path == "path/update.py"
    assert hunk.move_path == "path/update2.py"
    assert hunk.chunks[0].old_lines == ["    pass"]
    assert hunk.chunks[0].new_lines == ["    return 123"]


def test_extract_patch_paths_lists_all_targets() -> None:
    patch = (
        "*** Begin Patch\n"
        "*** Delete File: test.txt\n"
        "*** Add File: other.txt\n"
        "*** End Patch"
    )
    assert extract_patch_paths(patch) == ["test.txt", "other.txt"]
    assert extract_mcp_file_path("apply_patch", {"patch": patch}) == "test.txt"
    assert is_risky_mcp_tool("apply_patch")


def test_apply_patch_add_update_delete(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    workspace_mod.add_workspace(str(tmp_path))

    target = tmp_path / "hello.txt"
    target.write_text("old line\n", encoding="utf-8")

    update_patch = (
        "*** Begin Patch\n"
        "*** Update File: hello.txt\n"
        "@@\n"
        "-old line\n"
        "+new line\n"
        "*** End Patch"
    )
    result = apply_patch_in_workspace(update_patch)
    assert result.ok
    assert target.read_text(encoding="utf-8") == "new line\n"
    assert "hello.txt" in result.changed_paths

    delete_patch = "*** Begin Patch\n*** Delete File: hello.txt\n*** End Patch"
    result = apply_patch_in_workspace(delete_patch)
    assert result.ok
    assert not target.exists()
    assert "hello.txt" in result.changed_paths

    add_patch = "*** Begin Patch\n*** Add File: fresh.txt\n+created\n*** End Patch"
    result = apply_patch_in_workspace(add_patch)
    assert (tmp_path / "fresh.txt").read_text(encoding="utf-8") == "created\n"


def test_apply_patch_delete_missing_file_is_ok(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    workspace_mod.add_workspace(str(tmp_path))

    patch = "*** Begin Patch\n*** Delete File: missing.txt\n*** End Patch"
    result = apply_patch_in_workspace(patch)
    assert result.ok


def test_builtin_apply_patch_tool(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    workspace_mod.add_workspace(str(tmp_path))

    patch = "*** Begin Patch\n*** Add File: via-tool.txt\n+ok\n*** End Patch"
    raw = execute_builtin_tool("apply_patch", {"patch": patch})
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert (tmp_path / "via-tool.txt").exists()


def test_parse_patch_rejects_invalid_boundaries() -> None:
    with pytest.raises(ApplyPatchError):
        parse_patch("not a patch")
