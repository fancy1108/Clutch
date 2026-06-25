"""Resolve Anthropic credentials from Claude Code CLI settings (M4-04)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.llm.router import LLMProviderRouter, ModelSpec

_CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
_CC_SWITCH_DIR = Path.home() / ".cc-switch"
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
    if token == "PROXY_MANAGED":
        cc_env = read_cc_switch_active_provider_env()
        cc_token = cc_env.get("ANTHROPIC_AUTH_TOKEN")
        if cc_token and cc_token != "PROXY_MANAGED":
            return cc_token, "cc_switch_settings"
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
            if "127.0.0.1" in str(base) or "localhost" in str(base):
                cc_env = read_cc_switch_active_provider_env()
                cc_base = cc_env.get("ANTHROPIC_BASE_URL")
                if cc_base:
                    return str(cc_base)
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
    cc_env = read_cc_switch_active_provider_env()
    for source in (cc_env, env, os.environ):
        for key in (
            "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME",
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "ANTHROPIC_MODEL",
            "CLAUDE_CODE_SUBAGENT_MODEL",
        ):
            value = source.get(key)
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
    if "glm" in api_model.lower():
        display_name = api_model.replace("-", " ").upper()
    elif "claude" in api_model.lower():
        display_name = (
            "Claude 3.7 Sonnet"
            if api_model == "claude-3-7-sonnet-latest"
            else "Claude Sonnet"
        )
    else:
        display_name = api_model.replace("-", " ").title()
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


def read_cc_switch_active_provider_env() -> dict[str, str]:
    db_path = _CC_SWITCH_DIR / "cc-switch.db"
    settings_path = _CC_SWITCH_DIR / "settings.json"
    if not (db_path.is_file() and settings_path.is_file()):
        return {}
    try:
        # Read active provider ID
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        active_id = settings.get("currentProviderClaude")
        if not active_id:
            return {}
        # Query database
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT settings_config FROM providers WHERE id = ?", (active_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return {}
        config = json.loads(row[0])
        env = config.get("env")
        if isinstance(env, dict):
            return {str(k): str(v) for k, v in env.items() if v}
    except Exception:
        pass
    return {}


def bootstrap_cc_switch_credentials(router: LLMProviderRouter) -> None:
    """Bootstrap dynamic custom models and credentials directly from cc-switch database."""
    db_path = _CC_SWITCH_DIR / "cc-switch.db"
    if not db_path.is_file():
        return
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT id, name, app_type, settings_config FROM providers")
        rows = c.fetchall()
        conn.close()
        
        for pid, name, app_type, settings_str in rows:
            if not settings_str or pid in ("default", "claude-official", "claude-desktop-official", "codex-official", "gemini-official"):
                continue
            try:
                config = json.loads(settings_str)
            except Exception:
                continue
                
            api_key = None
            base_url = None
            api_model = None
            provider_id = "custom"
            
            if app_type == "claude":
                env = config.get("env") or {}
                api_key = env.get("ANTHROPIC_AUTH_TOKEN")
                base_url = env.get("ANTHROPIC_BASE_URL")
                api_model = env.get("CLAUDE_CODE_SUBAGENT_MODEL") or env.get("ANTHROPIC_DEFAULT_SONNET_MODEL")
                provider_id = "anthropic"
            elif app_type == "codex":
                auth = config.get("auth") or {}
                api_key = auth.get("OPENAI_API_KEY")
                if "apihub.agnes-ai.com" in settings_str:
                    base_url = "https://apihub.agnes-ai.com/v1"
                else:
                    base_url = "https://api.openai.com/v1"
                config_text = config.get("config") or ""
                for line in config_text.splitlines():
                    if line.strip().startswith("model ="):
                        parts = line.split("=")
                        if len(parts) >= 2:
                            api_model = parts[1].strip().strip('"').strip("'")
                if not api_model:
                    api_model = "gpt-4o"
                provider_id = "openai"
            elif app_type == "hermes":
                api_key = config.get("api_key")
                base_url = config.get("base_url")
                api_model = config.get("model")
                if base_url and "11434" in base_url:
                    provider_id = "ollama"
                else:
                    provider_id = "custom"
            
            if not api_model:
                continue
                
            if base_url:
                base_url = base_url.rstrip("/")
                if provider_id == "anthropic" and not base_url.endswith("/v1"):
                    base_url = f"{base_url}/v1"
                    
            if api_key == "PROXY_MANAGED":
                continue
                
            if api_key:
                model_slug = f"cc-switch-{pid.lower()[:8]}"
                router.register_model(
                    ModelSpec(
                        id=model_slug,
                        name=f"{name} ({api_model})",
                        provider_id=provider_id, # type: ignore
                        api_model=api_model,
                        base_url=base_url or "",
                    )
                )
                if not router.get_api_key(provider_id): # type: ignore
                    router.set_api_key(provider_id, api_key) # type: ignore
    except Exception:
        pass
