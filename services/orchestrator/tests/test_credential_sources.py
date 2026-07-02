"""Credential source resolution tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.credentials import sources
from src.llm.router import LLMProviderRouter
from src.models_config import CONFIG_ENV


@pytest.fixture
def models_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "models.json"
    monkeypatch.setenv(CONFIG_ENV, str(path))
    return path


def test_saved_key_reports_clutch_models_config(models_json: Path) -> None:
    models_json.write_text(
        json.dumps({"api_keys": {"deepseek": "sk-from-file"}}),
        encoding="utf-8",
    )
    router = LLMProviderRouter()
    router.set_api_key("deepseek", "sk-from-file")
    cred = sources.resolve_provider_credential_source(router, "deepseek")
    assert cred["source"] == "clutch_models_config"
    assert "models.json" in (cred["source_label"] or "")


def test_keychain_label_uses_windows_credential_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources.sys, "platform", "win32")
    assert sources.clutch_credential_store_label() == "Windows Credential Manager (Clutch)"
