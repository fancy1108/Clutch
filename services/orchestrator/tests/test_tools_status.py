"""Tests for local AI tool detection and connection preferences."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.tools_status import (
    connect_tool,
    disconnect_tool,
    list_tools_status,
    load_connected_ids,
    save_connected_ids,
)


@pytest.fixture
def tools_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config = tmp_path / "tools.json"
    monkeypatch.setenv("CLUTCH_TOOLS_CONFIG", str(config))
    return config


def test_list_tools_empty_when_none_installed(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.tools_status._is_claude_installed", lambda: False)
    monkeypatch.setattr("src.tools_status._is_cursor_installed", lambda: False)
    assert list_tools_status() == []


def test_connect_persists_only_installed_tools(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.tools_status._is_claude_installed", lambda: True)
    monkeypatch.setattr("src.tools_status._is_cursor_installed", lambda: False)

    connect_tool("claude-cli")
    assert load_connected_ids() == {"claude-cli"}

    tools = list_tools_status()
    assert len(tools) == 1
    assert tools[0]["id"] == "claude-cli"
    assert tools[0]["connected"] is True


def test_connect_rejects_missing_binary(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.tools_status._is_claude_installed", lambda: False)
    with pytest.raises(ValueError, match="not installed"):
        connect_tool("claude-cli")


def test_disconnect_clears_preference(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.tools_status._is_claude_installed", lambda: True)
    save_connected_ids({"claude-cli"})
    disconnect_tool("claude-cli")
    assert load_connected_ids() == set()
    tools = list_tools_status()
    assert tools[0]["connected"] is False


def test_connected_flag_false_when_binary_removed(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_connected_ids({"claude-cli"})
    tools_config.write_text(json.dumps({"connected": ["claude-cli"]}), encoding="utf-8")
    monkeypatch.setattr("src.tools_status._is_claude_installed", lambda: False)
    monkeypatch.setattr("src.tools_status._is_cursor_installed", lambda: False)
    assert list_tools_status() == []
