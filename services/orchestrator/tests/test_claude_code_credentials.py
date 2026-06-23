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
