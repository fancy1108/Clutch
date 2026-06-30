"""Subprocess isolation tests — M3-07."""

from __future__ import annotations

import sys

from src.subprocess_isolation import run_isolated


def test_isolated_run_captures_failure_without_raising() -> None:
    result = run_isolated([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert result.exit_code == 3
    assert result.crashed is True


def test_isolated_run_success() -> None:
    result = run_isolated([sys.executable, "-c", "print('ok')"])
    assert result.exit_code == 0
    assert result.crashed is False
    assert "ok" in result.stdout
