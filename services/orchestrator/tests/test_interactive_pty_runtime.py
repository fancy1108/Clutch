"""Tests for interactive PTY runtime."""

from __future__ import annotations

import os
import shutil
from unittest.mock import patch

import pytest

from src.interactive_pty_runtime import (
    InteractivePtyError,
    InteractivePtyStatus,
    _binary_for_agent_type,
    _command_matches_binary,
    configured_cli_binaries,
    interactive_pty_manager,
    scan_system_cli_processes,
)


@pytest.fixture(autouse=True)
def _reset_manager() -> None:
    for run_id in list(interactive_pty_manager._sessions):  # noqa: SLF001
        interactive_pty_manager.close(run_id)
    interactive_pty_manager._spawned_pids.clear()  # noqa: SLF001
    yield
    for run_id in list(interactive_pty_manager._sessions):  # noqa: SLF001
        interactive_pty_manager.close(run_id)
    interactive_pty_manager._spawned_pids.clear()  # noqa: SLF001


def test_resolve_binary_maps_claude_cli() -> None:
    with patch("src.interactive_pty_runtime.shutil.which", return_value="/usr/bin/claude"):
        assert interactive_pty_manager.resolve_binary("claude-cli") == "/usr/bin/claude"


def test_resolve_binary_strips_cli_suffix_for_unknown_types() -> None:
    with patch("src.interactive_pty_runtime.shutil.which", return_value="/usr/bin/codex"):
        assert interactive_pty_manager.resolve_binary("codex-cli") == "/usr/bin/codex"


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


@pytest.mark.skipif(os.name == "nt", reason="PTY spawn requires Unix")
def test_reattach_after_detach_respawns_process() -> None:
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    with patch.dict(
        "src.interactive_pty_runtime.CLI_BINARY_MAP",
        {"claude-cli": os.path.basename(bash)},
        clear=False,
    ):
        with patch("src.interactive_pty_runtime.shutil.which", return_value=bash):
            first = interactive_pty_manager.attach(
                "run_test::lane_primary",
                workspace_path="/tmp",
                cli_tool="claude-cli",
            )
            first_pid = first.pid
            interactive_pty_manager.detach("run_test::lane_primary")
            second = interactive_pty_manager.attach(
                "run_test::lane_primary",
                workspace_path="/tmp",
                cli_tool="claude-cli",
            )
            assert second.pid != first_pid
            assert second.attached is True
            interactive_pty_manager.close("run_test::lane_primary")


@pytest.mark.skipif(os.name == "nt", reason="PTY spawn requires Unix")
def test_list_alive_for_run_counts_lane_sessions() -> None:
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    with patch.dict(
        "src.interactive_pty_runtime.CLI_BINARY_MAP",
        {"claude-cli": os.path.basename(bash), "codex-cli": os.path.basename(bash)},
        clear=False,
    ):
        with patch("src.interactive_pty_runtime.shutil.which", return_value=bash):
            with patch("src.interactive_pty_runtime.scan_system_cli_processes", return_value=[]):
                interactive_pty_manager.attach(
                    "run_a::lane_primary",
                    workspace_path="/tmp",
                    cli_tool="claude-cli",
                )
                interactive_pty_manager.attach(
                    "run_a::lane_b",
                    workspace_path="/tmp",
                    cli_tool="codex-cli",
                )
                alive = interactive_pty_manager.list_alive_for_run("run_a")
                assert len(alive) == 2
                interactive_pty_manager.close("run_a::lane_primary")
                interactive_pty_manager.close("run_a::lane_b")


@pytest.mark.skipif(os.name == "nt", reason="PTY spawn requires Unix")
def test_attach_respawns_when_cli_tool_changes() -> None:
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    with patch.dict(
        "src.interactive_pty_runtime.CLI_BINARY_MAP",
        {"claude-cli": os.path.basename(bash), "codex-cli": os.path.basename(bash)},
        clear=False,
    ):
        with patch("src.interactive_pty_runtime.shutil.which", return_value=bash):
            with patch("src.interactive_pty_runtime.scan_system_cli_processes", return_value=[]):
                first = interactive_pty_manager.attach(
                    "run_switch::lane_primary",
                    workspace_path="/tmp",
                    cli_tool="claude-cli",
                )
                first_pid = first.pid
                second = interactive_pty_manager.attach(
                    "run_switch::lane_primary",
                    workspace_path="/tmp",
                    cli_tool="codex-cli",
                )
                assert second.pid != first_pid
                assert len(interactive_pty_manager.list_alive_for_run("run_switch")) == 1
                interactive_pty_manager.close("run_switch::lane_primary")


def test_binary_for_agent_type_maps_known_clis() -> None:
    assert _binary_for_agent_type("claude-cli") == "claude"
    assert _binary_for_agent_type("opencode-cli") == "opencode"
    assert _binary_for_agent_type("codex-cli") == "codex"
    assert _binary_for_agent_type("clutch") is None


def test_command_matches_binary_node_wrapper() -> None:
    cmd = "/Users/me/.nvm/versions/node/v24/bin/opencode run --auto"
    assert _command_matches_binary(cmd, "opencode") is True
    assert _command_matches_binary("/usr/bin/python3 script.py", "opencode") is False


def test_scan_system_cli_processes_parses_ps_output() -> None:
    ps_output = "\n".join(
        [
            "84617 /Users/me/.nvm/versions/node/v24/bin/opencode",
            "85941 /Users/me/.nvm/versions/node/v24/bin/opencode",
            "86108 grep opencode",
        ]
    )
    with patch("src.interactive_pty_runtime.subprocess.check_output", return_value=ps_output):
        rows = scan_system_cli_processes({"opencode", "claude"})
    assert len(rows) == 2
    assert {row["binary"] for row in rows} == {"opencode"}


def test_list_alive_for_run_includes_configured_system_processes() -> None:
    ps_output = "99999 /usr/local/bin/codex exec\n"
    with patch("src.interactive_pty_runtime.configured_cli_binaries", return_value={"codex"}):
        with patch("src.interactive_pty_runtime.subprocess.check_output", return_value=ps_output):
            alive = interactive_pty_manager.list_alive_for_run("run_x")
    assert any(item["cli_tool"] == "codex" and item["source"] == "system" for item in alive)


def test_configured_cli_binaries_includes_saved_agents(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.agent_storage.list_agents",
        lambda: [
            {"id": "a1", "agentType": "opencode-cli"},
            {"id": "a2", "agentType": "claude-cli"},
            {"id": "builtin", "agentType": "clutch"},
        ],
    )
    monkeypatch.setattr("src.tools_status.load_connected_ids", lambda: {"codex-cli"})
    binaries = configured_cli_binaries()
    assert {"opencode", "claude", "codex"}.issubset(binaries)
