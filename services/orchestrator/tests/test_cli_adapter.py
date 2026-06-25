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


def test_run_cli_streams_stdout_lines() -> None:
    streamed: list[tuple[str, str]] = []

    result = run_cli(
        ["python3", "-c", "import time; print('line-one'); time.sleep(0.05); print('line-two')"],
        on_line=lambda stream, line: streamed.append((stream, line)),
    )

    assert result.ok
    assert "line-one" in result.stdout
    assert "line-two" in result.stdout
    assert ("stdout", "line-one") in streamed
    assert ("stdout", "line-two") in streamed
