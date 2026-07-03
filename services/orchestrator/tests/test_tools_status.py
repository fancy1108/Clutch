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
    resolve_agent_type_for_tool,
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


def test_list_tools_include_all_omits_non_recommended_uninstalled(
    tools_config: Path, nothing_installed: None
) -> None:
    tools = list_tools_status(include_all=True)
    ids = {tool["id"] for tool in tools}
    assert "claude-cli" in ids
    assert "ollama-cli" in ids
    assert "codex-cli" in ids
    assert "agy-cli" in ids
    assert "aider-cli" not in ids
    assert "rivet-cli" not in ids
    assert "opencode-cli" in ids
    assert "codebuddy-cli" in ids
    assert all(tool["recommended"] for tool in tools)


def test_list_tools_include_all_includes_non_recommended_when_installed(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.tools_status._extra_cli_search_dirs", lambda: [])
    monkeypatch.setattr(
        "src.tools_status._cli_path",
        lambda binary: "/usr/local/bin/rivet" if binary == "rivet" else None,
    )
    monkeypatch.setattr("src.tools_status._client_path", lambda app_name: None)

    tools = list_tools_status(include_all=True)
    rivet = next(item for item in tools if item["id"] == "rivet-cli")
    assert rivet["installed"] is True
    assert rivet["recommended"] is False


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
    assert codex["registered"] is True
    assert codex["agentType"] == "codex-cli"


def test_resolve_agent_type_for_tool_maps_tool_ids() -> None:
    assert resolve_agent_type_for_tool("agy-cli") == "antigravity-cli"
    assert resolve_agent_type_for_tool("codex-cli") == "codex-cli"
    assert resolve_agent_type_for_tool("claude-cli") == "claude-cli"
    assert resolve_agent_type_for_tool("ollama-cli") == "ollama-cli"
    assert resolve_agent_type_for_tool("rivet-cli") == "rivet-cli"
    assert resolve_agent_type_for_tool("opencode-cli") == "opencode-cli"
    assert resolve_agent_type_for_tool("codebuddy-cli") == "codebuddy-cli"
    assert resolve_agent_type_for_tool("unknown-cli") is None


def test_list_tools_ollama_has_agent_type(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.tools_status._extra_cli_search_dirs", lambda: [])
    monkeypatch.setattr(
        "src.tools_status._cli_path",
        lambda binary: "/usr/local/bin/ollama" if binary == "ollama" else None,
    )
    connect_tool("ollama-cli")
    tools = list_tools_status()
    ollama = next(item for item in tools if item["id"] == "ollama-cli")
    assert ollama["connected"] is True
    assert ollama["registered"] is True
    assert ollama["agentType"] == "ollama-cli"


def test_list_tools_includes_agent_type_when_connected(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.tools_status._extra_cli_search_dirs", lambda: [])
    monkeypatch.setattr(
        "src.tools_status._cli_path",
        lambda binary: f"/usr/local/bin/{binary}" if binary == "codex" else None,
    )
    connect_tool("codex-cli")
    tools = list_tools_status()
    codex = next(item for item in tools if item["id"] == "codex-cli")
    assert codex["connected"] is True
    assert codex["registered"] is True
    assert codex["agentType"] == "codex-cli"


def test_list_includes_installed_client_with_path(
    tools_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_clients = [
        {
            "id": "cursor-app",
            "name": "Cursor",
            "app_name": "Cursor.app",
            "description": "Cursor AI IDE.",
            "icon": "edit_document",
        }
    ]
    monkeypatch.setattr("src.tools_status.CLIENT_CANDIDATES", mock_clients)
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


def test_resolve_tool_binary_finds_opencode_default_bin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opencode_bin_dir = tmp_path / ".opencode" / "bin"
    opencode_bin_dir.mkdir(parents=True)
    opencode_bin = opencode_bin_dir / "opencode"
    opencode_bin.write_text("#!/bin/sh\necho opencode\n", encoding="utf-8")
    opencode_bin.chmod(0o755)

    monkeypatch.setattr("src.tools_status._cli_path", lambda binary: None)
    monkeypatch.setattr(
        "src.tools_status._extra_cli_search_dirs",
        lambda: [opencode_bin_dir],
    )

    assert resolve_tool_binary("opencode-cli") == str(opencode_bin)


def test_cli_candidates_include_mainstream_agent_clis() -> None:
    ids = {c["id"] for c in CLI_CANDIDATES}
    expected = {
        "claude-cli",
        "codex-cli",
        "codebuddy-cli",
        "rivet-cli",
        "opencode-cli",
        "goose-cli",
        "copilot-cli",
        "continue-cli",
        "amazon-q-cli",
        "kiro-cli",
        "amp-cli",
        "qwen-code-cli",
        "gptme-cli",
        "openclaw-cli",
        "droid-cli",
        "crush-cli",
    }
    assert expected.issubset(ids)


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


def test_auto_configure_cli_via_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess
    from src.tools_status import auto_configure_cli_via_llm

    class MockCompletedProcess:
        stdout = "usage: gemini-cli [--version] [--help] [-p PROMPT]\n\nOptions:\n  -p, --prompt   Prompt string"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: MockCompletedProcess())

    # Mock the LLM router call to return a valid JSON configuration string
    class MockRouterSpec:
        id = "test-model"
        name = "DeepSeek"
        provider_id = "deepseek"
        model_kind = "chat"

    class MockRouter:
        def get_active_model(self):
            return MockRouterSpec()

        def list_models(self):
            return [MockRouterSpec()]

        def get_api_key(self, provider_id):
            return "fake-key"

        def chat(self, history, model_id=None):
            return """
            {
                "binary_name": "gemini",
                "conversation_mode": "none",
                "prepend_system_prompt": true,
                "extra_args": [],
                "prompt_flag": "-p"
            }
            """

    monkeypatch.setattr("src.models_config.get_router", lambda: MockRouter())

    config = auto_configure_cli_via_llm("gemini-cli", "/usr/local/bin/gemini")
    assert config["binary_name"] == "gemini"
    assert config["prompt_flag"] == "-p"
    assert config["conversation_mode"] == "none"
    assert config["prepend_system_prompt"] is True



