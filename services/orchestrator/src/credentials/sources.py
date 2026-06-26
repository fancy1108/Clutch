"""Human-readable credential source resolution per provider."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.credentials.claude_code import _CC_SWITCH_DIR, resolve_anthropic_api_key
from src.llm.router import LLMProviderRouter, ProviderId, ModelSpec

SOURCE_LABELS: dict[str, str] = {
    "claude_code_settings": "Claude Code CLI (~/.claude/settings.json)",
    "cc_switch_settings": "CC Switch database (~/.cc-switch/cc-switch.db)",
    "clutch_models_config": "Clutch app storage (models.json)",
    "clutch_env": "CLUTCH_* environment variable",
    "anthropic_env": "ANTHROPIC_API_KEY environment variable",
    "anthropic_auth_token_env": "ANTHROPIC_AUTH_TOKEN environment variable",
    "ollama_local": "Local Ollama (no API key required)",
}


def _config_path() -> Path:
    from src.models_config import config_path

    return config_path()


def _saved_api_keys() -> dict[str, str]:
    path = _config_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    raw = data.get("api_keys")
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items() if value}


def _label(source_key: str | None) -> str | None:
    if not source_key:
        return None
    return SOURCE_LABELS.get(source_key, source_key)


def resolve_provider_credential_source(
    router: LLMProviderRouter, provider_id: ProviderId
) -> dict[str, Any]:
    """Return configured flag plus source key/label for a provider."""
    if provider_id == "ollama" and router.get_api_key("ollama") is not None:
        return {
            "configured": True,
            "source": "ollama_local",
            "source_label": SOURCE_LABELS["ollama_local"],
        }

    saved = _saved_api_keys()
    if saved.get(provider_id):
        return {
            "configured": True,
            "source": "clutch_models_config",
            "source_label": SOURCE_LABELS["clutch_models_config"],
        }

    if provider_id == "anthropic":
        _, source = resolve_anthropic_api_key()
        if source:
            return {"configured": True, "source": source, "source_label": _label(source)}
        if router.get_api_key("anthropic"):
            return {
                "configured": True,
                "source": "clutch_models_config",
                "source_label": SOURCE_LABELS["clutch_models_config"],
            }
        return {"configured": False, "source": None, "source_label": None}

    env_name = f"CLUTCH_{provider_id.upper()}_API_KEY"
    if os.environ.get(env_name):
        return {
            "configured": True,
            "source": "clutch_env",
            "source_label": f"{SOURCE_LABELS['clutch_env']} ({env_name})",
        }

    if router.get_api_key(provider_id):
        return {
            "configured": True,
            "source": "clutch_env",
            "source_label": SOURCE_LABELS["clutch_env"],
        }

    return {"configured": False, "source": None, "source_label": None}


def cc_switch_has_key_for_provider(provider_id: ProviderId) -> bool:
    """Return True when CC Switch stores a key for this provider family."""
    db_path = _CC_SWITCH_DIR / "cc-switch.db"
    if not db_path.is_file():
        return False
    try:
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT app_type, settings_config FROM providers").fetchall()
        conn.close()
    except Exception:
        return False
    for _app_type, settings_str in rows:
        if not settings_str:
            continue
        try:
            config = json.loads(settings_str)
        except Exception:
            continue
        if provider_id == "anthropic" and config.get("env", {}).get("ANTHROPIC_AUTH_TOKEN"):
            return True
        if provider_id == "openai" and (config.get("auth") or {}).get("OPENAI_API_KEY"):
            return True
        if provider_id in ("custom", "ollama") and config.get("api_key"):
            return True
    return False


def model_source_summary(cred: dict[str, Any], *, is_cc_switch: bool) -> str:
    """Short label for UI — no file paths or env var names."""
    if is_cc_switch:
        return "Imported from CC Switch"
    source = cred.get("source")
    summaries = {
        "clutch_models_config": "API key saved in Clutch",
        "clutch_env": "Environment variable",
        "cc_switch_settings": "CC Switch",
        "claude_code_settings": "Claude Code",
        "ollama_local": "Local Ollama",
        "anthropic_env": "ANTHROPIC_API_KEY",
        "anthropic_auth_token_env": "ANTHROPIC_AUTH_TOKEN",
    }
    return summaries.get(str(source), "Credentials configured")


def resolve_model_credential_hint(router: LLMProviderRouter, spec: ModelSpec) -> str | None:
    """Explain likely credential mismatch when a key works elsewhere but not in Clutch."""
    from src.image_router import is_image_model

    cred = resolve_provider_credential_source(router, spec.provider_id)
    hints: list[str] = []
    if cred["source"] == "clutch_models_config" and cc_switch_has_key_for_provider(spec.provider_id):
        hints.append(
            "A Clutch-saved key overrides CC Switch — remove it to use CC Switch instead."
        )
    if spec.base_url:
        host = urlparse(spec.base_url).netloc
        official_hosts = {
            "api.anthropic.com",
            "api.openai.com",
            "api.deepseek.com",
            "generativelanguage.googleapis.com",
            "localhost",
            "127.0.0.1",
        }
        if host and host not in official_hosts:
            hints.append(
                f"This gateway ({host}) needs its own API key — not the official {spec.provider_id} key."
            )
    if spec.provider_id == "openai" and spec.base_url and "agnes-ai.com" in spec.base_url:
        hints.append("Save your Agnes token under the OpenAI provider.")
    if is_image_model(spec) and spec.provider_id == "custom" and spec.base_url and "agnes-ai.com" in spec.base_url:
        hints.append("Save your Agnes API key under the Custom provider.")
    return " ".join(hints) if hints else None


def is_clutch_managed_credential(provider_id: ProviderId) -> bool:
    return bool(_saved_api_keys().get(provider_id))
