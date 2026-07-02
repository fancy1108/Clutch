"""Unified load/save for Clutch-managed provider API keys (Keychain or legacy file)."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from src.credentials.keychain_store import (
    delete_provider_key,
    load_all_provider_keys,
    migrate_plaintext_api_keys,
    set_provider_key,
    use_keychain,
)
from src.llm.router import LLMProviderRouter, ProviderId

_MANAGED_PROVIDERS: tuple[ProviderId, ...] = (
    "deepseek",
    "openai",
    "anthropic",
    "google",
    "ollama",
    "custom",
)


def storage_label() -> str:
    if not use_keychain():
        return "models.json"
    if sys.platform == "win32":
        return "Windows Credential Manager"
    return "macOS Keychain"


def read_plaintext_api_keys(data: dict[str, Any]) -> dict[str, str]:
    raw = data.get("api_keys")
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if v}


def maybe_migrate_config_file(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Move legacy api_keys into Keychain and strip them from models.json."""
    if not use_keychain():
        return data
    plaintext = read_plaintext_api_keys(data)
    if not plaintext:
        if data.get("credential_storage") != "keychain":
            data = {**data, "credential_storage": "keychain", "api_keys": {}}
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            try:
                path.chmod(0o600)
            except OSError:
                pass
        return data
    migrated = migrate_plaintext_api_keys(plaintext)
    data = {**data, "credential_storage": "keychain", "api_keys": {}}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    if migrated:
        logger.info(
            "migrated provider API keys to Keychain",
            extra={"count": migrated, "source": "credential_store"},
        )
    return data


def load_keys_into_router(router: LLMProviderRouter, data: dict[str, Any]) -> None:
    if use_keychain():
        for provider_id, api_key in load_all_provider_keys().items():
            router.set_api_key(provider_id, api_key)  # type: ignore[arg-type]
        return
    for provider_id, api_key in read_plaintext_api_keys(data).items():
        if api_key:
            router.set_api_key(provider_id, str(api_key))  # type: ignore[arg-type]


def persist_router_keys(router: LLMProviderRouter) -> None:
    for provider_id in _MANAGED_PROVIDERS:
        key = router.get_api_key(provider_id)
        if not key:
            if use_keychain():
                delete_provider_key(provider_id)
            continue
        if use_keychain():
            set_provider_key(provider_id, key)
        # plaintext path handled in save_router payload
