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
