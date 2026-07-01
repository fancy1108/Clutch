"""Native credential storage for Clutch-managed provider API keys (OSR-13)."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

KEYRING_SERVICE = "com.clutch.app"
_MANAGED_PROVIDERS = frozenset({"deepseek", "openai", "anthropic", "google", "ollama", "agnes", "custom"})
_cached_provider_keys: dict[str, str] | None = None
_acl_stabilized = False


def invalidate_provider_keys_cache() -> None:
    global _cached_provider_keys, _acl_stabilized
    _cached_provider_keys = None
    _acl_stabilized = False


def _acl_migration_flag_path() -> Path:
    from src.storage_helper import get_storage_dir

    return get_storage_dir() / ".keychain_acl_migrated"


def use_keychain() -> bool:
    """Use the native macOS or Windows credential store unless explicitly disabled."""
    flag = os.environ.get("CLUTCH_USE_KEYCHAIN", "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return True
    return sys.platform in {"darwin", "win32"}


def _account(provider_id: str) -> str:
    return f"provider:{provider_id}"


def _keyring():
    import keyring  # lazy: optional on non-mac dev until enabled

    return keyring


def _use_acl_any_app() -> bool:
    """Use Keychain ACL that survives adhoc-signed PyInstaller rebuilds (D31 / pre-OSR-11)."""
    if sys.platform != "darwin":
        return False
    flag = os.environ.get("CLUTCH_KEYCHAIN_ACL", "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    return True


def _security_find_password(service: str, account: str) -> str | None:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 44:  # errSecItemNotFound
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"security find failed ({result.returncode})")
    value = result.stdout.rstrip("\n")
    return value or None


def _security_store_password(service: str, account: str, password: str) -> None:
    """Store via security(1) with -A so unsigned sidecar rebuilds do not re-prompt."""
    delete = subprocess.run(
        ["security", "delete-generic-password", "-s", service, "-a", account],
        capture_output=True,
        text=True,
    )
    if delete.returncode not in (0, 44):  # 44 = errSecItemNotFound
        raise RuntimeError(delete.stderr.strip() or f"security delete failed ({delete.returncode})")
    add = subprocess.run(
        ["security", "add-generic-password", "-A", "-s", service, "-a", account, "-w", password],
        capture_output=True,
        text=True,
    )
    if add.returncode != 0:
        raise RuntimeError(add.stderr.strip() or f"security add failed ({add.returncode})")


def _security_delete_password(service: str, account: str) -> None:
    result = subprocess.run(
        ["security", "delete-generic-password", "-s", service, "-a", account],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 44):
        raise RuntimeError(result.stderr.strip() or f"security delete failed ({result.returncode})")


def _store_password(service: str, account: str, password: str) -> None:
    if _use_acl_any_app():
        _security_store_password(service, account, password)
        return
    _keyring().set_password(service, account, password)


def _delete_password(service: str, account: str) -> None:
    if _use_acl_any_app():
        _security_delete_password(service, account)
        return
    _keyring().delete_password(service, account)


def _read_password(service: str, account: str) -> str | None:
    if _use_acl_any_app():
        try:
            return _security_find_password(service, account)
        except Exception as exc:
            logger.warning(
                "keychain security read failed",
                extra={"account": account, "source": "keychain_store", "error": str(exc)},
            )
            return None
    try:
        return _keyring().get_password(service, account)
    except Exception as exc:
        logger.warning(
            "keychain read failed",
            extra={"account": account, "source": "keychain_store", "error": str(exc)},
        )
        return None


def _stabilize_keychain_acl(keys: dict[str, str]) -> None:
    """Re-save legacy keyring entries with -A ACL once per machine (survives sidecar rebuilds)."""
    global _acl_stabilized
    if _acl_stabilized or not _use_acl_any_app() or not keys:
        return
    _acl_stabilized = True
    flag = _acl_migration_flag_path()
    if flag.is_file():
        return
    migrated = 0
    for provider_id, api_key in keys.items():
        try:
            _security_store_password(KEYRING_SERVICE, _account(provider_id), api_key)
            migrated += 1
        except Exception as exc:
            logger.warning(
                "keychain ACL stabilize failed",
                extra={"provider_id": provider_id, "source": "keychain_store", "error": str(exc)},
            )
    if migrated:
        try:
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.write_text("1\n", encoding="utf-8")
            flag.chmod(0o600)
        except OSError:
            pass


def get_provider_key(provider_id: str) -> str | None:
    if provider_id not in _MANAGED_PROVIDERS:
        return None
    if _cached_provider_keys is not None and provider_id in _cached_provider_keys:
        return _cached_provider_keys[provider_id]
    value = _read_password(KEYRING_SERVICE, _account(provider_id))
    return value if value else None


def set_provider_key(provider_id: str, api_key: str) -> None:
    if provider_id not in _MANAGED_PROVIDERS:
        raise ValueError(f"Unsupported provider for keychain: {provider_id}")
    _store_password(KEYRING_SERVICE, _account(provider_id), api_key)
    invalidate_provider_keys_cache()


def delete_provider_key(provider_id: str) -> None:
    if provider_id not in _MANAGED_PROVIDERS:
        return
    try:
        _delete_password(KEYRING_SERVICE, _account(provider_id))
    except Exception:
        pass
    invalidate_provider_keys_cache()


def load_all_provider_keys(*, force_reload: bool = False) -> dict[str, str]:
    global _cached_provider_keys
    if not force_reload and _cached_provider_keys is not None:
        return dict(_cached_provider_keys)
    out: dict[str, str] = {}
    for provider_id in _MANAGED_PROVIDERS:
        if key := get_provider_key(provider_id):
            out[provider_id] = key
    _cached_provider_keys = out
    _stabilize_keychain_acl(out)
    return dict(out)


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
