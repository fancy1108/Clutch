"""Tests for macOS Keychain credential storage (OSR-13)."""

from __future__ import annotations

import json
from pathlib import Path

import keyring
import pytest
from keyring.backend import KeyringBackend

from src.credentials.credential_store import maybe_migrate_config_file
from src.credentials.keychain_store import (
    get_provider_key,
    load_all_provider_keys,
    set_provider_key,
    use_keychain,
)
from src.llm.router import LLMProviderRouter
from src.models_config import save_router


class InMemoryKeyring(KeyringBackend):
    """Test double for keyring 25+ (UnitTestingBackend removed)."""

    priority = 10

    def __init__(self) -> None:
        super().__init__()
        self._passwords: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._passwords.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._passwords[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self._passwords.pop((service, username), None)


@pytest.fixture(autouse=True)
def keychain_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    keyring.set_keyring(InMemoryKeyring())
    monkeypatch.setenv("CLUTCH_USE_KEYCHAIN", "1")


def test_set_and_get_provider_key() -> None:
    set_provider_key("deepseek", "sk-test-keychain")
    assert get_provider_key("deepseek") == "sk-test-keychain"
    assert load_all_provider_keys()["deepseek"] == "sk-test-keychain"


def test_migrate_strips_plaintext_from_models_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "models.json"
    config.write_text(
        json.dumps(
            {
                "active_model_id": "deepseek-v4pro",
                "api_keys": {"deepseek": "sk-legacy-plain"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLUTCH_MODELS_CONFIG", str(config))

    data = json.loads(config.read_text(encoding="utf-8"))
    maybe_migrate_config_file(config, data)

    stored = json.loads(config.read_text(encoding="utf-8"))
    assert stored.get("api_keys") == {}
    assert stored.get("credential_storage") == "keychain"
    assert get_provider_key("deepseek") == "sk-legacy-plain"


def test_save_router_does_not_write_api_keys_to_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "models.json"
    config.write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("CLUTCH_MODELS_CONFIG", str(config))
    monkeypatch.setattr("src.credentials.claude_code._CLAUDE_SETTINGS", tmp_path / "no-claude.json")

    router = LLMProviderRouter()
    router.set_api_key("openai", "sk-openai-keychain")
    save_router(router)

    stored = json.loads(config.read_text(encoding="utf-8"))
    assert stored.get("api_keys") == {}
    assert stored.get("credential_storage") == "keychain"
    assert get_provider_key("openai") == "sk-openai-keychain"


def test_use_keychain_respects_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_USE_KEYCHAIN", "0")
    assert use_keychain() is False
