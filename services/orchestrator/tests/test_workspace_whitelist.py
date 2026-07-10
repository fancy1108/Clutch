"""Workspace whitelist tests — M4-05."""

from __future__ import annotations

from pathlib import Path

import pytest

from src import workspace


@pytest.fixture(autouse=True)
def reset_workspace(tmp_path: Path) -> None:
    workspace.clear_workspace_for_tests()
    workspace.set_workspace(str(tmp_path))


def test_read_file_inside_workspace(tmp_path: Path) -> None:
    sample = tmp_path / "docs" / "verify.md"
    sample.parent.mkdir(parents=True)
    sample.write_text("# ok", encoding="utf-8")

    content = workspace.read_file("docs/verify.md")
    assert content == "# ok"


def test_read_outside_workspace_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(workspace.WorkspaceError, match="工作区外"):
        workspace.read_file(f"../{outside.name}")


def test_list_tree_includes_clutch_design_artifacts(tmp_path: Path) -> None:
    design_file = tmp_path / ".clutch" / "design" / "sessions" / "run1" / "DESIGN.md"
    design_file.parent.mkdir(parents=True)
    design_file.write_text("# Design\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.ts").write_text("export {}\n", encoding="utf-8")

    nodes = workspace.list_tree()
    names = {n["name"] for n in nodes}
    assert ".clutch" in names
    assert ".env" not in names
    assert "src" in names

    clutch = next(n for n in nodes if n["name"] == ".clutch")
    design = next(c for c in clutch["children"] if c["name"] == "design")
    sessions = next(c for c in design["children"] if c["name"] == "sessions")
    run = next(c for c in sessions["children"] if c["name"] == "run1")
    files = {c["name"] for c in run["children"]}
    assert "DESIGN.md" in files
