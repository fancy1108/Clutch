"""Human-readable credential source resolution per provider."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.credentials.claude_code import resolve_anthropic_api_key
from src.llm.router import LLMProviderRouter, ProviderId

SOURCE_LABELS: dict[str, str] = {
    "claude_code_settings": "Claude Code CLI (~/.claude/settings.json)",
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
