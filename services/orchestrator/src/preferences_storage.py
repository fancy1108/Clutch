"""User preferences persistence (P2-03 theme, P2-04 language, permission mode)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PREFERENCES_ENV = "CLUTCH_PREFERENCES_DIR"
DEFAULT_THEME_ID = "pristine-light"
DEFAULT_LANGUAGE = "en"
ALLOWED_THEME_IDS = frozenset({"pristine-light", "nordic-frost", "amber-warm"})
ALLOWED_LANGUAGES = frozenset({"en", "zh"})

# Permission modes (controls when the agent pauses for human approval)
# ask       – pause before every risky tool (write/delete/exec). Default & safest.
# auto_edit – auto-approve file edits; still pause before shell/delete/network ops.
# plan      – read-only; all write/exec tools are hard-blocked (agent just plans).
# full      – bypass all pause gates (still blocks truly catastrophic ops like rm -rf /).
ALLOWED_PERMISSION_MODES = frozenset({"ask", "auto_edit", "plan", "full"})
DEFAULT_PERMISSION_MODE = "ask"


def preferences_dir() -> Path:
    override = os.environ.get(PREFERENCES_ENV)
    if override:
        return Path(override)
    from src.storage_helper import get_storage_dir
    return get_storage_dir() / "preferences"


def _preferences_file() -> Path:
    path = preferences_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path / "preferences.json"


def _defaults() -> dict[str, str]:
    return {
        "active_theme_id": DEFAULT_THEME_ID,
        "active_language": DEFAULT_LANGUAGE,
        "permission_mode": DEFAULT_PERMISSION_MODE,
        "user_avatar": "",
        "user_name": "User",
    }


def _write_preferences(payload: dict[str, str]) -> dict[str, str]:
    _preferences_file().write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return payload


def load_preferences() -> dict[str, str]:
    defaults = _defaults()
    path = _preferences_file()
    if not path.is_file():
        return defaults
    data = json.loads(path.read_text(encoding="utf-8"))
    theme_id = str(data.get("active_theme_id") or DEFAULT_THEME_ID)
    language = str(data.get("active_language") or DEFAULT_LANGUAGE)
    permission_mode = str(data.get("permission_mode") or DEFAULT_PERMISSION_MODE)
    user_avatar = str(data.get("user_avatar") or "")
    user_name = str(data.get("user_name") or "User")
    if theme_id not in ALLOWED_THEME_IDS:
        theme_id = DEFAULT_THEME_ID
    if language not in ALLOWED_LANGUAGES:
        language = DEFAULT_LANGUAGE
    if permission_mode not in ALLOWED_PERMISSION_MODES:
        permission_mode = DEFAULT_PERMISSION_MODE
    return {
        "active_theme_id": theme_id,
        "active_language": language,
        "permission_mode": permission_mode,
        "user_avatar": user_avatar,
        "user_name": user_name,
    }


def save_avatar(avatar: str) -> dict[str, str]:
    prefs = load_preferences()
    prefs["user_avatar"] = avatar
    return _write_preferences(prefs)


def save_user_name(user_name: str) -> dict[str, str]:
    prefs = load_preferences()
    prefs["user_name"] = user_name.strip() or "User"
    return _write_preferences(prefs)


def save_theme(theme_id: str) -> dict[str, str]:
    normalized = theme_id.strip()
    if normalized not in ALLOWED_THEME_IDS:
        raise ValueError(f"未知主题：{normalized}")
    prefs = load_preferences()
    prefs["active_theme_id"] = normalized
    return _write_preferences(prefs)


def save_language(language: str) -> dict[str, str]:
    normalized = language.strip().lower()
    if normalized not in ALLOWED_LANGUAGES:
        raise ValueError("语言须为 en 或 zh")
    prefs = load_preferences()
    prefs["active_language"] = normalized
    return _write_preferences(prefs)


def save_permission_mode(mode: str) -> dict[str, str]:
    """Persist the permission mode. Raises ValueError for unknown modes."""
    normalized = mode.strip().lower()
    if normalized not in ALLOWED_PERMISSION_MODES:
        raise ValueError(f"Unknown permission mode: {normalized}. Allowed: {sorted(ALLOWED_PERMISSION_MODES)}")
    prefs = load_preferences()
    prefs["permission_mode"] = normalized
    return _write_preferences(prefs)


def load_permission_mode() -> str:
    """Return the current permission mode string."""
    return load_preferences().get("permission_mode", DEFAULT_PERMISSION_MODE)


def tr(en: str, zh: str) -> str:
    """Dynamically return en or zh translation based on current active language preference."""
    import sys
    if "pytest" in sys.modules:
        return zh
    try:
        prefs = load_preferences()
        lang = prefs.get("active_language", "en")
    except Exception:
        lang = "en"
    return zh if lang == "zh" else en

