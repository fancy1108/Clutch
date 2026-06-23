"""Evaluator tests — M3-05."""

from __future__ import annotations

from pathlib import Path

import pytest

from src import workspace
from src.evaluator import run_checks


@pytest.fixture(autouse=True)
def reset_workspace(tmp_path: Path) -> None:
    workspace.clear_workspace_for_tests()
    workspace.set_workspace(str(tmp_path))


def test_file_exists_check_passes(tmp_path: Path) -> None:
    target = tmp_path / "docs" / "verify.md"
    target.parent.mkdir()
    target.write_text("ok", encoding="utf-8")

    result, logs = run_checks([{"type": "file_exists", "path": "docs/verify.md"}])
    assert result == "passed"
    assert any("OK" in line for line in logs)


def test_file_exists_check_fails_when_missing() -> None:
    result, logs = run_checks([{"type": "file_exists", "path": "docs/missing.md"}])
    assert result == "failed"
    assert any("FAILED" in line for line in logs)
