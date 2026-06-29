"""macOS Keychain storage for Clutch-managed provider API keys (OSR-13)."""

from __future__ import annotations

import logging
import os
import sys
from typing import Iterable

logger = logging.getLogger(__name__)

KEYRING_SERVICE = "com.clutch.app"
_MANAGED_PROVIDERS = frozenset({"deepseek", "openai", "anthropic", "google", "ollama", "custom"})


def use_keychain() -> bool:
    """Keychain is the default credential store on macOS unless explicitly disabled."""
    flag = os.environ.get("CLUTCH_USE_KEYCHAIN", "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return True
    return sys.platform == "darwin"


def _account(provider_id: str) -> str:
    return f"provider:{provider_id}"


def _keyring():
    import keyring  # lazy: optional on non-mac dev until enabled

    return keyring


def get_provider_key(provider_id: str) -> str | None:
    if provider_id not in _MANAGED_PROVIDERS:
        return None
    try:
        value = _keyring().get_password(KEYRING_SERVICE, _account(provider_id))
    except Exception as exc:
        logger.warning(
            "keychain read failed",
            extra={"provider_id": provider_id, "source": "keychain_store", "message": str(exc)},
        )
        return None
    return value if value else None


def set_provider_key(provider_id: str, api_key: str) -> None:
    if provider_id not in _MANAGED_PROVIDERS:
        raise ValueError(f"Unsupported provider for keychain: {provider_id}")
    _keyring().set_password(KEYRING_SERVICE, _account(provider_id), api_key)


def delete_provider_key(provider_id: str) -> None:
    if provider_id not in _MANAGED_PROVIDERS:
        return
    try:
        _keyring().delete_password(KEYRING_SERVICE, _account(provider_id))
    except Exception:
        pass


def load_all_provider_keys() -> dict[str, str]:
    out: dict[str, str] = {}
    for provider_id in _MANAGED_PROVIDERS:
        if key := get_provider_key(provider_id):
            out[provider_id] = key
    return out


def migrate_plaintext_api_keys(api_keys: dict[str, str]) -> int:
    """Import keys from legacy models.json api_keys; returns count migrated."""
    migrated = 0
    for provider_id, api_key in api_keys.items():
        if provider_id not in _MANAGED_PROVIDERS or not api_key:
            continue
        set_provider_key(provider_id, str(api_key))
        migrated += 1
    return migrated


def clear_provider_keys(provider_ids: Iterable[str]) -> None:
    for provider_id in provider_ids:
        delete_provider_key(provider_id)
