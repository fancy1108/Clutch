"""Persist LLM router selection and provider keys (M4-09 / M4-04 sidecar leg)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from src.llm.router import LLMProviderRouter, ProviderId

CONFIG_ENV = "CLUTCH_MODELS_CONFIG"


def config_path() -> Path:
    override = os.environ.get(CONFIG_ENV)
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "clutch" / "models.json"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "clutch" / "models.json"
    return Path.home() / ".local" / "share" / "clutch" / "models.json"


def load_router() -> LLMProviderRouter:
    router = LLMProviderRouter()
    path = config_path()
    if not path.is_file():
        return router
    data = json.loads(path.read_text(encoding="utf-8"))
    if model_id := data.get("active_model_id"):
        router.set_active_model(str(model_id))
    for provider_id, api_key in (data.get("api_keys") or {}).items():
        if api_key:
            router.set_api_key(provider_id, str(api_key))  # type: ignore[arg-type]
    return router


def save_router(router: LLMProviderRouter) -> dict[str, Any]:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "active_model_id": router.active_model_id,
        "api_keys": {
            provider: router.get_api_key(provider)  # type: ignore[arg-type]
            for provider in ("deepseek", "openai", "anthropic", "google", "ollama", "custom")
            if router.get_api_key(provider)  # type: ignore[arg-type]
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return payload


_router = load_router()


def get_router() -> LLMProviderRouter:
    return _router
