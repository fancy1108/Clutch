"""Claude Code credential bootstrap tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.credentials import claude_code
from src.llm import LLMProviderRouter


@pytest.fixture(autouse=True)
def reset_claude_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claude_code, "_CLAUDE_SETTINGS", Path("/nonexistent/settings.json"))
    monkeypatch.setattr(claude_code, "_CC_SWITCH_DIR", Path("/nonexistent/.cc-switch"))
    # Unset env vars that would shadow file-based settings in tests
    for key in ("CLUTCH_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(key, raising=False)


def test_resolve_anthropic_from_claude_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"env": {"ANTHROPIC_AUTH_TOKEN": "sk-test-token"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(claude_code, "_CLAUDE_SETTINGS", settings)

    key, source = claude_code.resolve_anthropic_api_key()
    assert key == "sk-test-token"
    assert source == "claude_code_settings"


def test_bootstrap_sets_claude_active_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_AUTH_TOKEN": "sk-test-token",
                    "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
                    "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": "agnes-2.0-flash",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(claude_code, "_CLAUDE_SETTINGS", settings)

    router = LLMProviderRouter()
    result = claude_code.bootstrap_claude_credentials(router)
    assert result["anthropic"]["configured"] is True
    assert router.active_model_id == "claude-3-7-sonnet"
    assert router.get_api_key("anthropic") == "sk-test-token"
    model = router.get_active_model()
    assert model.base_url == "https://api.anthropic.com/v1"
    assert model.api_model == "agnes-2.0-flash"


def test_normalize_anthropic_base_url_adds_v1_suffix() -> None:
    assert claude_code.normalize_anthropic_base_url("http://127.0.0.1:15721") == "http://127.0.0.1:15721/v1"
    assert claude_code.normalize_anthropic_base_url("https://api.anthropic.com/v1") == "https://api.anthropic.com/v1"


def test_resolve_anthropic_transport_uses_claude_code_proxy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_AUTH_TOKEN": "PROXY_MANAGED",
                    "ANTHROPIC_BASE_URL": "http://127.0.0.1:15721",
                    "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": "agnes-2.0-flash",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(claude_code, "_CLAUDE_SETTINGS", settings)

    base, model, key = claude_code.resolve_anthropic_transport(
        base_url="https://api.anthropic.com/v1",
        api_model="claude-3-7-sonnet-latest",
        api_key="PROXY_MANAGED",
    )
    assert base == "http://127.0.0.1:15721/v1"
    assert model == "agnes-2.0-flash"
    assert key == "PROXY_MANAGED"


def test_bootstrap_cc_switch_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cc_dir = tmp_path / ".cc-switch"
    cc_dir.mkdir()
    settings_file = cc_dir / "settings.json"
    settings_file.write_text(json.dumps({
        "currentProviderClaude": "test-prov-id"
    }))
    
    import sqlite3
    db_file = cc_dir / "cc-switch.db"
    conn = sqlite3.connect(str(db_file))
    c = conn.cursor()
    c.execute("CREATE TABLE providers (id TEXT, name TEXT, app_type TEXT, settings_config TEXT)")
    c.execute(
        "INSERT INTO providers VALUES (?, ?, ?, ?)",
        (
            "test-prov-id",
            "Mock Provider",
            "claude",
            json.dumps({
                "env": {
                    "ANTHROPIC_AUTH_TOKEN": "sk-cc-test",
                    "ANTHROPIC_BASE_URL": "https://api.cc-test.com",
                    "CLAUDE_CODE_SUBAGENT_MODEL": "glm-cc-model"
                }
            })
        )
    )
    conn.commit()
    conn.close()
    
    monkeypatch.setattr(claude_code, "_CC_SWITCH_DIR", cc_dir)
    
    router = LLMProviderRouter()
    claude_code.bootstrap_cc_switch_credentials(router)
    
    models = router.list_models()
    matching = [m for m in models if m.id == "cc-switch-test-pro"]
    assert len(matching) == 1
    model = matching[0]
    assert model.name == "Mock Provider (glm-cc-model)"
    assert model.api_model == "glm-cc-model"
    assert model.base_url == "https://api.cc-test.com/v1"
    assert router.get_api_key("anthropic") == "sk-cc-test"
