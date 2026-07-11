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
    assert any("→" in line for line in logs)


def test_file_exists_outside_workspace_is_forbidden_not_crash(tmp_path: Path) -> None:
    """Absolute host paths like /tmp/... must fail cleanly (#53), not raise."""
    outside = Path("/tmp/clutch-pipeline-demo-does-not-need-to-exist.json")
    result, logs = run_checks([{"type": "file_exists", "path": str(outside)}])
    assert result == "failed"
    assert any("FORBIDDEN" in line for line in logs)


def test_file_exists_workspace_relative_tmp_looks_under_workspace(tmp_path: Path) -> None:
    """Path 'tmp/x' resolves under workspace, not host /tmp (#53)."""
    result, logs = run_checks([{"type": "file_exists", "path": "tmp/clutch-pipeline-demo/kp.json"}])
    assert result == "failed"
    joined = "\n".join(logs)
    assert str(tmp_path / "tmp" / "clutch-pipeline-demo" / "kp.json") in joined
    assert "workspace-relative" in joined
