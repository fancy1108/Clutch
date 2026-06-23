"""CLI adapter tests — M3-01."""

from __future__ import annotations

import pytest

from src.adapters.cli_adapter import CliAdapterError, run_cli


def test_run_cli_success() -> None:
    result = run_cli(["python3", "-c", "print('hello')"])
    assert result.ok
    assert "hello" in result.stdout


def test_run_cli_nonzero_exit_fails() -> None:
    with pytest.raises(CliAdapterError, match="退出码"):
        run_cli(["python3", "-c", "import sys; sys.exit(2)"])
