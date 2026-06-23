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


def normalize_anthropic_base_url(base_url: str) -> str:
    """Ensure Anthropic Messages API base ends with /v1 (Claude Code proxy omits it)."""
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return base
    return f"{base}/v1"


def resolve_anthropic_api_model() -> str | None:
    env = read_claude_code_env()
    for key in (
        "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_MODEL",
        "CLAUDE_CODE_SUBAGENT_MODEL",
    ):
        value = env.get(key)
        if value:
            return str(value)
    for key in (
        "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_MODEL",
    ):
        value = os.environ.get(key)
        if value:
            return str(value)
    return None


def resolve_anthropic_transport(
    *, base_url: str, api_model: str, api_key: str
) -> tuple[str, str, str]:
    """Apply Claude Code CLI proxy URL + mapped model names when configured."""
    cli_env = read_claude_code_env()
    cli_key, _source = resolve_anthropic_api_key()
    resolved_key = api_key or (cli_key or "")
    resolved_base = base_url
    cli_base = resolve_anthropic_base_url()
    if cli_base and (cli_key == api_key or api_key == cli_env.get("ANTHROPIC_AUTH_TOKEN")):
        resolved_base = cli_base
    elif cli_base and not api_key and cli_key:
        resolved_base = cli_base
        resolved_key = cli_key

    resolved_model = api_model
    cli_model = resolve_anthropic_api_model()
    if cli_model and (
        cli_key == api_key
        or api_key == cli_env.get("ANTHROPIC_AUTH_TOKEN")
        or api_model.startswith("claude-")
    ):
        resolved_model = cli_model

    return normalize_anthropic_base_url(resolved_base), resolved_model, resolved_key


def bootstrap_claude_credentials(router: LLMProviderRouter) -> dict[str, Any]:
    """Import Claude Code CLI credentials when Clutch has no explicit Anthropic key."""
    if router.get_api_key("anthropic"):
        return {"anthropic": {"configured": True, "source": "clutch_models_config"}}

    api_key, source = resolve_anthropic_api_key()
    if not api_key:
        return {"anthropic": {"configured": False, "source": None}}

    router.set_api_key("anthropic", api_key)
    base_url = normalize_anthropic_base_url(
        resolve_anthropic_base_url() or "https://api.anthropic.com/v1"
    )
    api_model = resolve_anthropic_api_model() or "claude-3-7-sonnet-latest"
    display_name = (
        "Claude Sonnet"
        if api_model != "claude-3-7-sonnet-latest"
        else "Claude 3.7 Sonnet"
    )
    router.register_model(
        ModelSpec(
            id=_DEFAULT_CLAUDE_MODEL,
            name=display_name,
            provider_id="anthropic",
            api_model=api_model,
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
