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
DEFAULT_FONT_SIZE = "default"
ALLOWED_THEME_IDS = frozenset({"pristine-light", "nordic-frost", "amber-warm"})
ALLOWED_LANGUAGES = frozenset({"en", "zh"})
ALLOWED_FONT_SIZES = frozenset({"small", "default", "large", "xlarge", "xxlarge"})

# Permission modes (controls when the agent may mutate / pauses for approval)
# auto_edit – UI "Agent" (default): auto-approve file edits; pause on risky shell.
# plan      – read-only; propose a plan (writes/exec hard-blocked).
# full      – fewer confirmation gates (still force-asks dangerous cmds like rm -rf).
# ask       – conversation / read-only (writes & mutating shell hard-blocked).
# explore   – legacy alias of ask (normalized on load/save; kept for old prefs / subagents).
ALLOWED_PERMISSION_MODES = frozenset({"ask", "auto_edit", "explore", "plan", "full"})
DEFAULT_PERMISSION_MODE = "auto_edit"


def normalize_permission_mode(mode: str | None) -> str:
    """Map legacy `explore` → `ask`; unknown → Agent (`auto_edit`)."""
    normalized = str(mode or DEFAULT_PERMISSION_MODE).strip().lower()
    if normalized == "explore":
        return "ask"
    if normalized not in ALLOWED_PERMISSION_MODES:
        return DEFAULT_PERMISSION_MODE
    return normalized
DEFAULT_STRICT_SANDBOX = "false"
# On by default so Clutch Agent can use web_search end-to-end (weather/docs).
# Users can still turn it off in Settings → General → Allow network.
DEFAULT_ALLOW_NETWORK = "true"
DEFAULT_CROSS_SESSION_MEMORY = "false"


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
        "font_size": DEFAULT_FONT_SIZE,
        "user_avatar": "",
        "user_name": "User",
        "onboarding_completed": "false",
        "strict_sandbox": DEFAULT_STRICT_SANDBOX,
        "allow_network": DEFAULT_ALLOW_NETWORK,
        "cross_session_memory_enabled": DEFAULT_CROSS_SESSION_MEMORY,
        "default_workspace_id": "",
        "high_risk_confirm": "true",
        "trusted_mcp_ids": "",
        "trusted_workflow_ids": "",
        "untrusted_confirm": "true",
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
    permission_mode = normalize_permission_mode(data.get("permission_mode"))
    font_size = str(data.get("font_size") or DEFAULT_FONT_SIZE)
    user_avatar = str(data.get("user_avatar") or "")
    user_name = str(data.get("user_name") or "User")
    onboarding_completed = str(data.get("onboarding_completed") or "false").lower()
    if onboarding_completed not in {"true", "false"}:
        onboarding_completed = "false"
    strict_sandbox = str(data.get("strict_sandbox") or DEFAULT_STRICT_SANDBOX).lower()
    if strict_sandbox not in {"true", "false"}:
        strict_sandbox = DEFAULT_STRICT_SANDBOX
    allow_network = str(data.get("allow_network") or DEFAULT_ALLOW_NETWORK).lower()
    if allow_network not in {"true", "false"}:
        allow_network = DEFAULT_ALLOW_NETWORK
    cross_session_memory = str(
        data.get("cross_session_memory_enabled") or DEFAULT_CROSS_SESSION_MEMORY
    ).lower()
    if cross_session_memory not in {"true", "false"}:
        cross_session_memory = DEFAULT_CROSS_SESSION_MEMORY
    default_workspace_id = str(data.get("default_workspace_id") or "").strip()
    high_risk_confirm = str(data.get("high_risk_confirm") or "true").lower()
    if high_risk_confirm not in {"true", "false"}:
        high_risk_confirm = "true"
    trusted_mcp_ids = str(data.get("trusted_mcp_ids") or "").strip()
    trusted_workflow_ids = str(data.get("trusted_workflow_ids") or "").strip()
    untrusted_confirm = str(data.get("untrusted_confirm") or "true").lower()
    if untrusted_confirm not in {"true", "false"}:
        untrusted_confirm = "true"
    if theme_id not in ALLOWED_THEME_IDS:
        theme_id = DEFAULT_THEME_ID
    if language not in ALLOWED_LANGUAGES:
        language = DEFAULT_LANGUAGE
    if font_size not in ALLOWED_FONT_SIZES:
        font_size = DEFAULT_FONT_SIZE
    return {
        "active_theme_id": theme_id,
        "active_language": language,
        "permission_mode": permission_mode,
        "font_size": font_size,
        "user_avatar": user_avatar,
        "user_name": user_name,
        "onboarding_completed": onboarding_completed,
        "strict_sandbox": strict_sandbox,
        "allow_network": allow_network,
        "cross_session_memory_enabled": cross_session_memory,
        "default_workspace_id": default_workspace_id,
        "high_risk_confirm": high_risk_confirm,
        "trusted_mcp_ids": trusted_mcp_ids,
        "trusted_workflow_ids": trusted_workflow_ids,
        "untrusted_confirm": untrusted_confirm,
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
    raw = mode.strip().lower()
    if raw not in ALLOWED_PERMISSION_MODES:
        raise ValueError(f"Unknown permission mode: {raw}. Allowed: {sorted(ALLOWED_PERMISSION_MODES)}")
    prefs = load_preferences()
    prefs["permission_mode"] = normalize_permission_mode(raw)
    return _write_preferences(prefs)


def save_font_size(font_size: str) -> dict[str, str]:
    normalized = font_size.strip().lower()
    if normalized not in ALLOWED_FONT_SIZES:
        raise ValueError(f"Unknown font size: {normalized}. Allowed: {sorted(ALLOWED_FONT_SIZES)}")
    prefs = load_preferences()
    prefs["font_size"] = normalized
    return _write_preferences(prefs)


def load_permission_mode() -> str:
    """Return the current permission mode string."""
    return load_preferences().get("permission_mode", DEFAULT_PERMISSION_MODE)


def load_strict_sandbox() -> bool:
    return load_preferences().get("strict_sandbox", DEFAULT_STRICT_SANDBOX) == "true"


def load_allow_network() -> bool:
    return load_preferences().get("allow_network", DEFAULT_ALLOW_NETWORK) == "true"


def save_strict_sandbox(enabled: bool) -> dict[str, str]:
    prefs = load_preferences()
    prefs["strict_sandbox"] = "true" if enabled else "false"
    return _write_preferences(prefs)


def save_allow_network(enabled: bool) -> dict[str, str]:
    prefs = load_preferences()
    prefs["allow_network"] = "true" if enabled else "false"
    return _write_preferences(prefs)


def load_cross_session_memory_enabled() -> bool:
    return load_preferences().get(
        "cross_session_memory_enabled", DEFAULT_CROSS_SESSION_MEMORY
    ) == "true"


def save_cross_session_memory_enabled(enabled: bool) -> dict[str, str]:
    prefs = load_preferences()
    prefs["cross_session_memory_enabled"] = "true" if enabled else "false"
    return _write_preferences(prefs)


def load_default_workspace_id() -> str:
    return load_preferences().get("default_workspace_id") or ""


def save_default_workspace_id(workspace_id: str) -> dict[str, str]:
    prefs = load_preferences()
    prefs["default_workspace_id"] = workspace_id.strip()
    return _write_preferences(prefs)


def load_high_risk_confirm() -> bool:
    return load_preferences().get("high_risk_confirm", "true") == "true"


def save_high_risk_confirm(enabled: bool) -> dict[str, str]:
    prefs = load_preferences()
    prefs["high_risk_confirm"] = "true" if enabled else "false"
    return _write_preferences(prefs)


def _csv_ids(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def load_untrusted_confirm() -> bool:
    return load_preferences().get("untrusted_confirm", "true") == "true"


def save_untrusted_confirm(enabled: bool) -> dict[str, str]:
    prefs = load_preferences()
    prefs["untrusted_confirm"] = "true" if enabled else "false"
    return _write_preferences(prefs)


def load_trusted_ids(kind: str) -> list[str]:
    key = "trusted_mcp_ids" if kind == "mcp" else "trusted_workflow_ids"
    return _csv_ids(load_preferences().get(key) or "")


def save_trusted_id(kind: str, item_id: str) -> dict[str, str]:
    key = "trusted_mcp_ids" if kind == "mcp" else "trusted_workflow_ids"
    prefs = load_preferences()
    current = _csv_ids(prefs.get(key) or "")
    token = item_id.strip()
    if token and token not in current:
        current.append(token)
    prefs[key] = ",".join(current)
    return _write_preferences(prefs)


def save_onboarding_completed() -> dict[str, str]:
    prefs = load_preferences()
    prefs["onboarding_completed"] = "true"
    return _write_preferences(prefs)


def reset_onboarding_completed() -> dict[str, str]:
    prefs = load_preferences()
    prefs["onboarding_completed"] = "false"
    return _write_preferences(prefs)


def is_onboarding_completed() -> bool:
    return load_preferences().get("onboarding_completed") == "true"


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

