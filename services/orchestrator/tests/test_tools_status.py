"""Tests for local AI tool detection and connection preferences."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from src.tools_status import (
    CLI_CANDIDATES,
    CLIENT_CANDIDATES,
    connect_tool,
    disconnect_tool,
    list_tools_status,
    load_connected_ids,
    resolve_tool_binary,
    save_connected_ids,
)


@pytest.fixture
def tools_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config = tmp_path / "tools.json"
    monkeypatch.setenv("CLUTCH_TOOLS_CONFIG", str(config))
    return config


@pytest.fixture
def nothing_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every probe report the tool as absent."""
    monkeypatch.setattr("src.tools_status._cli_path", lambda binary: None)
    monkeypatch.setattr("src.tools_status._client_path", lambda app_name: None)
    monkeypatch.setattr("src.tools_status._extra_cli_search_dirs", lambda: [])


def test_list_tools_empty_when_none_installed(
    tools_config: Path, nothing_installed: None
) -> None:
    assert list_tools_status() == []


def test_connect_persists_only_installed_tools(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.tools_status._extra_cli_search_dirs", lambda: [])
    monkeypatch.setattr(
        "src.tools_status._cli_path",
        lambda binary: "/usr/local/bin/claude" if binary == "claude" else None,
    )
    monkeypatch.setattr("src.tools_status._client_path", lambda app_name: None)

    connect_tool("claude-cli")
    assert load_connected_ids() == {"claude-cli"}

    tools = list_tools_status()
    assert len(tools) == 1
    assert tools[0]["id"] == "claude-cli"
    assert tools[0]["connected"] is True
    assert tools[0]["kind"] == "cli"


def test_connect_rejects_missing_binary(
    tools_config: Path, nothing_installed: None
) -> None:
    with pytest.raises(ValueError, match="not installed"):
        connect_tool("claude-cli")


def test_disconnect_clears_preference(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "src.tools_status._cli_path",
        lambda binary: "/usr/local/bin/claude" if binary == "claude" else None,
    )
    monkeypatch.setattr("src.tools_status._client_path", lambda app_name: None)
    save_connected_ids({"claude-cli"})
    disconnect_tool("claude-cli")
    assert load_connected_ids() == set()
    tools = list_tools_status()
    assert tools[0]["connected"] is False


def test_connected_flag_false_when_binary_removed(
    tools_config: Path, nothing_installed: None
) -> None:
    save_connected_ids({"claude-cli"})
    tools_config.write_text(json.dumps({"connected": ["claude-cli"]}), encoding="utf-8")
    assert list_tools_status() == []


def test_list_includes_installed_cli_with_path(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.tools_status._extra_cli_search_dirs", lambda: [])
    monkeypatch.setattr(
        "src.tools_status._cli_path",
        lambda binary: f"/usr/local/bin/{binary}" if binary == "codex" else None,
    )
    monkeypatch.setattr("src.tools_status._client_path", lambda app_name: None)

    tools = list_tools_status()
    assert len(tools) == 1
    codex = tools[0]
    assert codex["id"] == "codex-cli"
    assert codex["kind"] == "cli"
    assert codex["path"] == "/usr/local/bin/codex"
    assert codex["connected"] is False


def test_list_includes_installed_client_with_path(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.tools_status._extra_cli_search_dirs", lambda: [])
    monkeypatch.setattr("src.tools_status._cli_path", lambda binary: None)
    monkeypatch.setattr(
        "src.tools_status._client_path",
        lambda app_name: "/Applications/Cursor.app" if app_name == "Cursor.app" else None,
    )

    tools = list_tools_status()
    assert len(tools) == 1
    cursor = tools[0]
    assert cursor["id"] == "cursor-app"
    assert cursor["kind"] == "client"
    assert cursor["path"] == "/Applications/Cursor.app"


def test_client_not_detected_on_non_darwin(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.tools_status._extra_cli_search_dirs", lambda: [])
    monkeypatch.setattr("src.tools_status._cli_path", lambda binary: None)
    monkeypatch.setattr(sys, "platform", "linux")

    assert list_tools_status() == []


def test_connect_rejects_unknown_tool(
    tools_config: Path, nothing_installed: None
) -> None:
    with pytest.raises(ValueError, match="Unknown tool"):
        connect_tool("not-a-real-tool")


def test_candidate_catalogs_have_unique_ids() -> None:
    ids = [c["id"] for c in CLI_CANDIDATES + CLIENT_CANDIDATES]
    assert len(ids) == len(set(ids))


def test_resolve_tool_binary_checks_extra_bin_dirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    homebrew = tmp_path / "opt" / "homebrew" / "bin"
    homebrew.mkdir(parents=True)
    claude_bin = homebrew / "claude"
    claude_bin.write_text("#!/bin/sh\necho claude\n", encoding="utf-8")
    claude_bin.chmod(0o755)

    monkeypatch.setattr("src.tools_status._cli_path", lambda binary: None)
    monkeypatch.setattr("src.tools_status._extra_cli_search_dirs", lambda: [homebrew])

    assert resolve_tool_binary("claude-cli") == str(claude_bin)


def test_resolve_tool_binary_finds_nvm_node_bin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    nvm_bin = tmp_path / "nvm" / "versions" / "node" / "v24.16.0" / "bin"
    nvm_bin.mkdir(parents=True)
    claude_bin = nvm_bin / "claude"
    claude_bin.write_text("#!/bin/sh\necho claude\n", encoding="utf-8")
    claude_bin.chmod(0o755)

    monkeypatch.setattr("src.tools_status._cli_path", lambda binary: None)
    monkeypatch.setattr(
        "src.tools_status._extra_cli_search_dirs",
        lambda: [nvm_bin],
    )

    assert resolve_tool_binary("claude-cli") == str(claude_bin)
