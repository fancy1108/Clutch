"""Tests for interactive PTY runtime."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
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
from src.windows_pty import _env_block


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
        with patch("src.tools_status._extra_cli_search_dirs", return_value=[]):
            with pytest.raises(InteractivePtyError):
                interactive_pty_manager.resolve_binary("claude-cli")


def test_resolve_binary_falls_back_to_tools_status_search_dirs() -> None:
    nvm_bin = Path("/Users/me/.nvm/versions/node/v24/bin")
    opencode = nvm_bin / "opencode"
    with patch("src.interactive_pty_runtime.shutil.which", return_value=None):
        with patch("src.tools_status._extra_cli_search_dirs", return_value=[nvm_bin]):
            with patch.object(Path, "is_file", lambda self: self == opencode):
                with patch("src.interactive_pty_runtime.os.access", return_value=True):
                    assert interactive_pty_manager.resolve_binary("opencode-cli") == str(opencode)


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
def test_reattach_after_detach_reuses_process() -> None:
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
            assert second.pid == first_pid
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
    with patch("src.interactive_pty_runtime.os.name", "posix"):
        with patch("src.interactive_pty_runtime.subprocess.check_output", return_value=ps_output):
            rows = scan_system_cli_processes({"opencode", "claude"})
    assert len(rows) == 2
    assert {row["binary"] for row in rows} == {"opencode"}


def test_list_alive_for_run_includes_configured_system_processes() -> None:
    ps_output = "99999 /usr/local/bin/codex exec\n"
    with patch("src.interactive_pty_runtime.os.name", "posix"):
        with patch("src.interactive_pty_runtime.configured_cli_binaries", return_value={"codex"}):
            with patch("src.interactive_pty_runtime.subprocess.check_output", return_value=ps_output):
                alive = interactive_pty_manager.list_alive_for_run("run_x", include_system=True)
    assert any(item["cli_tool"] == "codex" and item["source"] == "system" for item in alive)


def test_windows_pty_env_block_formats_createprocess_environment() -> None:
    block = _env_block({"A": "1", "B": "two"})
    assert block == "A=1\0B=two\0"
    assert _env_block(None) is None


@pytest.mark.skipif(os.name != "nt", reason="Windows PTY backend requires Windows")
def test_attach_windows_pty_backend(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    instances: list[object] = []

    class _FakeWindowsPty:
        pid = 4321

        def __init__(self, command: list[str], *, cwd: str | None = None, env: dict[str, str] | None = None) -> None:
            self.command = command
            self.cwd = cwd
            self.env = env or {}
            self.writes: list[str] = []
            self.resizes: list[tuple[int, int]] = []
            self.closed_force: bool | None = None
            self._alive = True
            instances.append(self)

        def isalive(self) -> bool:
            return self._alive

        def read(self, *, wait_s: float = 0.0) -> str:
            return ""

        def write(self, text: str) -> None:
            self.writes.append(text)

        def resize(self, cols: int, rows: int) -> None:
            self.resizes.append((cols, rows))

        def close(self, *, force: bool = False) -> None:
            self.closed_force = force
            self._alive = False

    import src.windows_pty as windows_pty

    monkeypatch.setattr(windows_pty, "WindowsPty", _FakeWindowsPty)
    monkeypatch.setattr("src.interactive_pty_runtime.shutil.which", lambda name: f"C:\\Tools\\{name}.exe")
    monkeypatch.setattr("src.tools_status._extra_cli_search_dirs", lambda: [tmp_path / "bin"])

    session = interactive_pty_manager.attach(
        "run_win::lane_primary",
        workspace_path=str(tmp_path),
        cli_tool="claude-cli",
        cli_session_id="session-123",
    )

    fake = instances[0]
    assert session.status == InteractivePtyStatus.READY
    assert session.pid == 4321
    assert fake.command == ["C:\\Tools\\claude.exe", "--session-id", "session-123"]
    assert fake.cwd == str(tmp_path)
    assert str(tmp_path / "bin") in fake.env["PATH"]
    assert interactive_pty_manager.list_alive_for_run("run_win")[0]["source"] == "tracked"

    interactive_pty_manager.write_input("run_win::lane_primary", "hello\r\n")
    interactive_pty_manager.resize("run_win::lane_primary", 120, 40)
    assert fake.writes == ["hello\r\n"]
    assert fake.resizes == [(120, 40)]

    interactive_pty_manager.close("run_win::lane_primary")
    assert fake.closed_force is True
    assert session.status == InteractivePtyStatus.EXITED


@pytest.mark.skipif(os.name == "nt", reason="PTY spawn requires Unix")
def test_spawn_ollama_uses_run_subcommand(monkeypatch: pytest.MonkeyPatch) -> None:
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    captured: dict[str, list[str]] = {}

    class _FakeProc:
        pid = 4242

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            return None

        def wait(self, timeout: float | None = None) -> int:
            return 0

        def kill(self) -> None:
            return None

    def fake_popen(argv: list[str], **kwargs: object) -> _FakeProc:
        captured["argv"] = list(argv)
        return _FakeProc()

    with patch.dict(
        "src.interactive_pty_runtime.CLI_BINARY_MAP",
        {"ollama-cli": os.path.basename(bash)},
        clear=False,
    ):
        with patch("src.interactive_pty_runtime.shutil.which", return_value=bash):
            with patch("src.interactive_pty_runtime.subprocess.Popen", fake_popen):
                with patch("src.interactive_pty_runtime.pty.openpty", return_value=(3, 4)):
                    with patch("src.interactive_pty_runtime.os.close"):
                        with patch("src.interactive_pty_runtime.fcntl.ioctl"):
                            session = interactive_pty_manager.attach(
                                "run_ollama::lane_a",
                                workspace_path="/tmp",
                                cli_tool="ollama-cli",
                                ollama_model="qwen2.5-coder",
                            )
                            assert session.alive()
                            assert captured["argv"] == [bash, "run", "qwen2.5-coder"]
                            interactive_pty_manager.close("run_ollama::lane_a")


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
