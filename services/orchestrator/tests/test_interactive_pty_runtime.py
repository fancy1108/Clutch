"""Tests for interactive PTY runtime."""

from __future__ import annotations

import os
import shutil
from unittest.mock import patch

import pytest

from src.interactive_pty_runtime import (
    InteractivePtyError,
    InteractivePtyStatus,
    interactive_pty_manager,
)


@pytest.fixture(autouse=True)
def _reset_manager() -> None:
    for run_id in list(interactive_pty_manager._sessions):  # noqa: SLF001
        interactive_pty_manager.close(run_id)
    yield
    for run_id in list(interactive_pty_manager._sessions):  # noqa: SLF001
        interactive_pty_manager.close(run_id)


def test_resolve_binary_maps_claude_cli() -> None:
    with patch("src.interactive_pty_runtime.shutil.which", return_value="/usr/bin/claude"):
        assert interactive_pty_manager.resolve_binary("claude-cli") == "/usr/bin/claude"


def test_resolve_binary_missing_raises() -> None:
    with patch("src.interactive_pty_runtime.shutil.which", return_value=None):
        with pytest.raises(InteractivePtyError):
            interactive_pty_manager.resolve_binary("claude-cli")


@pytest.mark.skipif(os.name == "nt", reason="PTY spawn requires Unix")
def test_attach_bash_smoke() -> None:
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    with patch.dict(
        "src.interactive_pty_runtime.CLI_BINARY_MAP",
        {"claude-cli": os.path.basename(bash)},
        clear=False,
    ):
        with patch("src.interactive_pty_runtime.shutil.which", return_value=bash):
            session = interactive_pty_manager.attach(
                "run_test",
                workspace_path="/tmp",
                cli_tool="claude-cli",
            )
            assert session.status == InteractivePtyStatus.READY
            assert session.alive()
            interactive_pty_manager.detach("run_test")
            assert session.status == InteractivePtyStatus.DETACHED
            assert session.alive()
            interactive_pty_manager.close("run_test")
