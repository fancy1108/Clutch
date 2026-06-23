"""Resolve Anthropic credentials from Claude Code CLI settings (M4-04)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.llm.router import LLMProviderRouter, ModelSpec

_CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
_DEFAULT_CLAUDE_MODEL = "claude-3-7-sonnet"


def read_claude_code_env() -> dict[str, str]:
    if not _CLAUDE_SETTINGS.is_file():
        return {}
    try:
        data = json.loads(_CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    env = data.get("env")
    if not isinstance(env, dict):
        return {}
    return {str(key): str(value) for key, value in env.items() if value}


def resolve_anthropic_api_key() -> tuple[str | None, str]:
    """Return API key and source label. Never log the key itself."""
    for env_name, source in (
        ("CLUTCH_ANTHROPIC_API_KEY", "clutch_env"),
        ("ANTHROPIC_API_KEY", "anthropic_env"),
        ("ANTHROPIC_AUTH_TOKEN", "anthropic_auth_token_env"),
    ):
        value = os.environ.get(env_name)
        if value:
            return value, source

    token = read_claude_code_env().get("ANTHROPIC_AUTH_TOKEN")
    if token:
        return token, "claude_code_settings"
    return None, ""


def resolve_anthropic_base_url() -> str | None:
    for source in (read_claude_code_env(), os.environ):
        if isinstance(source, dict):
            base = source.get("ANTHROPIC_BASE_URL")
        else:
            base = os.environ.get("ANTHROPIC_BASE_URL")
        if base:
            return str(base)
    return None


def bootstrap_claude_credentials(router: LLMProviderRouter) -> dict[str, Any]:
    """Import Claude Code CLI credentials when Clutch has no explicit Anthropic key."""
    if router.get_api_key("anthropic"):
        return {"anthropic": {"configured": True, "source": "clutch_models_config"}}

    api_key, source = resolve_anthropic_api_key()
    if not api_key:
        return {"anthropic": {"configured": False, "source": None}}

    router.set_api_key("anthropic", api_key)
    base_url = (resolve_anthropic_base_url() or "https://api.anthropic.com/v1").rstrip("/")
    router.register_model(
        ModelSpec(
            id=_DEFAULT_CLAUDE_MODEL,
            name="Claude 3.7 Sonnet",
            provider_id="anthropic",
            api_model="claude-3-7-sonnet-latest",
            base_url=base_url,
        )
    )
    router.set_active_model(_DEFAULT_CLAUDE_MODEL)
    return {"anthropic": {"configured": True, "source": source}}


def credential_status(router: LLMProviderRouter) -> dict[str, Any]:
    key, source = resolve_anthropic_api_key()
    configured = bool(router.get_api_key("anthropic") or key)
    resolved_source = source or (
        "clutch_models_config" if router.get_api_key("anthropic") else None
    )
    return {
        "anthropic": {
            "configured": configured,
            "source": resolved_source,
            "active_model_id": router.active_model_id,
        },
        "deepseek": {
            "configured": bool(router.get_api_key("deepseek")),
            "source": "clutch_env" if os.environ.get("CLUTCH_DEEPSEEK_API_KEY") else None,
        },
    }
