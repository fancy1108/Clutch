"""Tests for external CLI agent config scanning."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from src import cli_agent_config as cfg


def test_normalize_cli_agent_type_aliases() -> None:
    assert cfg.normalize_cli_agent_type("claude-cli") == "claude-cli"
    assert cfg.normalize_cli_agent_type("opencode") == "opencode-cli"
    with pytest.raises(ValueError):
        cfg.normalize_cli_agent_type("codex-cli")


def test_scan_claude_code_models_without_cc_switch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    claude_settings = tmp_path / "settings.json"
    claude_settings.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_AUTH_TOKEN": "sk-test-key",
                    "ANTHROPIC_MODEL": "claude-sonnet-test",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cfg, "_CC_SWITCH_DIR", tmp_path / "missing-cc-switch")
    monkeypatch.setattr(cfg, "read_claude_code_env", lambda: {"ANTHROPIC_MODEL": "claude-sonnet-test"})
    monkeypatch.setattr(cfg, "resolve_anthropic_api_model", lambda: "claude-sonnet-test")

    payload = cfg.scan_claude_code_models()
    assert payload["agent_type"] == "claude-cli"
    assert payload["active_model_id"] == "claude-sonnet-test"
    assert payload["cc_switch_found"] is False


def test_scan_opencode_models_reads_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    opencode_dir = tmp_path / ".config" / "opencode"
    opencode_dir.mkdir(parents=True)
    config_path = opencode_dir / "opencode.json"
    config_path.write_text(
        json.dumps(
            {
                "model": "openai/gpt-4o",
                "provider": {
                    "custom": {
                        "models": {
                            "openai/gpt-4o": {"name": "GPT-4o"},
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cfg, "_OPENCODE_CONFIG_CANDIDATES", (config_path,))
    monkeypatch.setattr(cfg, "_CC_SWITCH_DIR", tmp_path / "missing-cc-switch")
    monkeypatch.setattr(cfg, "_OPENCODE_AUTH_PATH", tmp_path / "missing-auth.json")
    monkeypatch.setattr(cfg, "_OPENCODE_MODEL_STATE_PATH", tmp_path / "missing-model.json")
    monkeypatch.setattr(cfg, "_list_opencode_models_via_cli", lambda: [])

    payload = cfg.scan_opencode_models()
    assert payload["agent_type"] == "opencode-cli"
    assert payload["active_model_id"] == "openai/gpt-4o"
    assert len(payload["catalog"]) == 1


def test_scan_opencode_models_reads_auth_and_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "opencode.jsonc"
    config_path.write_text('{\n  "$schema": "https://opencode.ai/config.json"\n}\n', encoding="utf-8")
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(
        json.dumps({"deepseek": {"type": "api", "key": "sk-test"}}),
        encoding="utf-8",
    )
    state_path = tmp_path / "model.json"
    state_path.write_text(
        json.dumps({"recent": [{"providerID": "deepseek", "modelID": "deepseek-v4-pro"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(cfg, "_OPENCODE_CONFIG_CANDIDATES", (config_path,))
    monkeypatch.setattr(cfg, "_CC_SWITCH_DIR", tmp_path / "missing-cc-switch")
    monkeypatch.setattr(cfg, "_OPENCODE_AUTH_PATH", auth_path)
    monkeypatch.setattr(cfg, "_OPENCODE_MODEL_STATE_PATH", state_path)
    monkeypatch.setattr(
        cfg,
        "_list_opencode_models_via_cli",
        lambda: [
            {
                "provider": "opencode",
                "model_id": "deepseek-v4-flash-free",
                "name": "deepseek-v4-flash-free",
                "model_ref": "opencode/deepseek-v4-flash-free",
                "is_builtin": True,
            }
        ],
    )

    payload = cfg.scan_opencode_models()
    assert payload["active_model_id"] == "deepseek/deepseek-v4-pro"
    assert len(payload["auth_providers"]) == 1
    assert payload["auth_providers"][0]["id"] == "deepseek"
    assert any(item["model_ref"] == "opencode/deepseek-v4-flash-free" for item in payload["catalog"])


def test_activate_opencode_model_writes_config_and_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "opencode.jsonc"
    config_path.write_text('{"$schema": "https://opencode.ai/config.json"}\n', encoding="utf-8")
    state_path = tmp_path / "state" / "model.json"
    monkeypatch.setattr(cfg, "_OPENCODE_CONFIG_CANDIDATES", (config_path,))
    monkeypatch.setattr(cfg, "_OPENCODE_MODEL_STATE_PATH", state_path)

    result = cfg.activate_opencode_model("deepseek/deepseek-v4-pro")
    assert result["ok"] is True
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["model"] == "deepseek/deepseek-v4-pro"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["recent"][0]["providerID"] == "deepseek"


def test_list_cc_switch_providers_filters_official(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cc_dir = tmp_path / ".cc-switch"
    cc_dir.mkdir()
    db_path = cc_dir / "cc-switch.db"
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE providers (id TEXT, name TEXT, app_type TEXT, settings_config TEXT)"
    )
    conn.execute(
        "INSERT INTO providers VALUES (?, ?, ?, ?)",
        (
            "custom-1",
            "My Claude",
            "claude",
            json.dumps({"env": {"ANTHROPIC_MODEL": "claude-test"}}),
        ),
    )
    conn.execute(
        "INSERT INTO providers VALUES (?, ?, ?, ?)",
        ("claude-official", "Official", "claude", json.dumps({"env": {}})),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(cfg, "_CC_SWITCH_DIR", cc_dir)
    providers = cfg.list_cc_switch_providers(app_type="claude")
    assert len(providers) == 1
    assert providers[0]["id"] == "custom-1"
    assert providers[0]["model_id"] == "claude-test"


def test_resolve_cc_switch_cli_path_checks_local_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cli = bin_dir / "cc-switch"
    cli.write_text("#!/bin/sh\necho cc-switch-cli 1.0.0\n", encoding="utf-8")
    cli.chmod(0o755)

    monkeypatch.setattr(cfg.shutil, "which", lambda _name: None)
    monkeypatch.setattr(cfg, "_verify_cc_switch_cli", lambda path: path.endswith("cc-switch"))
    monkeypatch.setattr("src.tools_status._extra_cli_search_dirs", lambda: [bin_dir])

    assert cfg.resolve_cc_switch_cli_path() == str(cli)


def test_install_cc_switch_cli_short_circuits_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cfg, "resolve_cc_switch_cli_path", lambda: "/usr/local/bin/cc-switch")
    result = cfg.install_cc_switch_cli()
    assert result["ok"] is True
    assert result["method"] == "existing"


def test_install_cc_switch_cli_copies_cached_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "cached-cc-switch"
    source.write_text("#!/bin/sh\necho cc-switch-cli 1.0.0\n", encoding="utf-8")
    source.chmod(0o755)
    target = tmp_path / ".local" / "bin" / "cc-switch"

    monkeypatch.setattr(cfg.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(cfg, "prefetch_cc_switch_cli_bundle", lambda: {"ok": True, "path": str(source)})
    monkeypatch.setattr(cfg, "_verify_cc_switch_cli", lambda _path: True)

    seen: list[str | None] = [None]

    def resolve_after_install() -> str | None:
        return seen[0]

    def copy2(src, dst):
        target.parent.mkdir(parents=True, exist_ok=True)
        Path(dst).write_bytes(Path(src).read_bytes())
        Path(dst).chmod(0o755)
        seen[0] = str(dst)

    monkeypatch.setattr(cfg, "resolve_cc_switch_cli_path", resolve_after_install)
    monkeypatch.setattr(cfg.shutil, "copy2", copy2)

    result = cfg.install_cc_switch_cli()
    assert result["ok"] is True
    assert result["method"] == "cached_bundle"
    assert target.is_file()


def test_activate_cc_switch_provider_without_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cfg, "resolve_cc_switch_cli_path", lambda: None)
    monkeypatch.setattr(cfg, "_CC_SWITCH_DIR", Path("/nonexistent/.cc-switch"))
    result = cfg.activate_cc_switch_provider("p1", app_type="claude")
    assert result["ok"] is False


def test_mcp_from_claude_json_reads_project_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    claude_json = home / ".claude.json"
    claude_json.write_text(
        json.dumps(
            {
                "projects": {
                    "/workspace/demo": {
                        "mcpServers": {
                            "demo-mcp": {
                                "command": "node",
                                "args": ["server.js"],
                            }
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cfg.Path, "home", classmethod(lambda cls: home))
    servers = cfg._mcp_from_claude_json(workspace_path="/workspace/demo")
    assert any(s["name"] == "demo-mcp" for s in servers)


def test_mcp_from_cc_switch_marks_disabled_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cc_dir = tmp_path / ".cc-switch"
    cc_dir.mkdir()
    db_path = cc_dir / "cc-switch.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE mcp_servers (id TEXT, name TEXT, server_config TEXT, enabled_claude INTEGER, enabled_opencode INTEGER)"
    )
    conn.execute(
        "INSERT INTO mcp_servers VALUES (?, ?, ?, ?, ?)",
        (
            "node-repl",
            "node_repl",
            json.dumps({"command": "npx", "args": ["-y", "@modelcontextprotocol/server-everything"]}),
            0,
            1,
        ),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(cfg, "_CC_SWITCH_DIR", cc_dir)

    servers = cfg._mcp_from_cc_switch(enabled_field="enabled_claude", include_all=True)
    assert len(servers) == 1
    assert servers[0]["name"] == "node_repl"
    assert servers[0]["enabled_for_agent"] is False
