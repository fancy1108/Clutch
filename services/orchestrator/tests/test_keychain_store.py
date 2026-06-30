"""Tests for macOS Keychain credential storage (OSR-13)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import keyring
import pytest
from keyring.backend import KeyringBackend

from src.credentials import keychain_store
from src.credentials.credential_store import maybe_migrate_config_file
from src.credentials.keychain_store import (
    KEYRING_SERVICE,
    get_provider_key,
    invalidate_provider_keys_cache,
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
    invalidate_provider_keys_cache()
    keyring.set_keyring(InMemoryKeyring())
    monkeypatch.setenv("CLUTCH_USE_KEYCHAIN", "1")
    monkeypatch.setenv("CLUTCH_KEYCHAIN_ACL", "0")
    yield
    invalidate_provider_keys_cache()


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


def test_use_keychain_defaults_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLUTCH_USE_KEYCHAIN", raising=False)
    monkeypatch.setattr(keychain_store.sys, "platform", "win32")
    assert use_keychain() is True


def test_get_provider_key_logs_keychain_failure_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenKeyring(InMemoryKeyring):
        def get_password(self, service: str, username: str) -> str | None:
            raise RuntimeError("keychain unavailable")

    keyring.set_keyring(BrokenKeyring())
    assert get_provider_key("deepseek") is None
    assert load_all_provider_keys() == {}


def test_load_all_provider_keys_uses_cache_until_invalidated() -> None:
    calls = {"count": 0}

    class CountingKeyring(InMemoryKeyring):
        def get_password(self, service: str, username: str) -> str | None:
            calls["count"] += 1
            return super().get_password(service, username)

    keyring.set_keyring(CountingKeyring())
    set_provider_key("openai", "sk-count-test")
    invalidate_provider_keys_cache()

    load_all_provider_keys()
    first_pass = calls["count"]
    load_all_provider_keys()
    assert calls["count"] == first_pass

    set_provider_key("deepseek", "sk-count-test-2")
    load_all_provider_keys()
    assert calls["count"] > first_pass


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS security(1) ACL")
def test_set_provider_key_uses_security_acl_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_KEYCHAIN_ACL", "1")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("src.credentials.keychain_store.subprocess.run", fake_run)
    set_provider_key("openai", "sk-acl-test")
    assert calls[0][:4] == ["security", "delete-generic-password", "-s", KEYRING_SERVICE]
    assert "-A" in calls[1]
    assert calls[1][:3] == ["security", "add-generic-password", "-A"]


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS security(1) ACL")
def test_load_all_stabilizes_acl_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLUTCH_KEYCHAIN_ACL", "1")
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    stabilize_calls = {"count": 0}
    original = keychain_store._stabilize_keychain_acl

    def counting_stabilize(keys: dict[str, str]) -> None:
        stabilize_calls["count"] += 1
        original(keys)

    monkeypatch.setattr(keychain_store, "_stabilize_keychain_acl", counting_stabilize)
    monkeypatch.setattr(
        keychain_store,
        "get_provider_key",
        lambda provider_id: "sk-stabilize" if provider_id == "openai" else None,
    )

    load_all_provider_keys()
    load_all_provider_keys()
    assert stabilize_calls["count"] == 1

    flag = tmp_path / ".keychain_acl_migrated"
    assert flag.is_file()

    invalidate_provider_keys_cache()
    load_all_provider_keys()
    assert stabilize_calls["count"] == 2


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS security(1) ACL")
def test_get_provider_key_uses_security_find_when_acl_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_KEYCHAIN_ACL", "1")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if "find-generic-password" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "sk-from-security\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("src.credentials.keychain_store.subprocess.run", fake_run)
    assert get_provider_key("deepseek") == "sk-from-security"
    assert calls[0][:4] == ["security", "find-generic-password", "-s", KEYRING_SERVICE]
