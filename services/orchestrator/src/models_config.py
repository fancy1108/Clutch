"""Persist LLM router selection and provider keys (M4-09 / M4-04 sidecar leg)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from src.llm.http_complete import http_chat_complete
from src.llm.router import LLMProviderRouter, ProviderId

from src.credentials.claude_code import bootstrap_claude_credentials, bootstrap_cc_switch_credentials
from src.credentials.sources import resolve_provider_credential_source

CONFIG_ENV = "CLUTCH_MODELS_CONFIG"


def config_path() -> Path:
    override = os.environ.get(CONFIG_ENV)
    if override:
        return Path(override)
    from src.storage_helper import get_storage_dir
    return get_storage_dir() / "models.json"


def load_router() -> LLMProviderRouter:
    router = LLMProviderRouter()
    router._chat = http_chat_complete  # type: ignore[method-assign]
    bootstrap_claude_credentials(router)
    bootstrap_cc_switch_credentials(router)
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


def is_model_available(router: LLMProviderRouter, model_id: str) -> bool:
    if model_id not in router._models:
        return False
    provider_id: ProviderId = router._models[model_id].provider_id
    return bool(router.get_api_key(provider_id))


def serialize_models_config(router: LLMProviderRouter) -> dict[str, Any]:
    providers: dict[str, Any] = {}
    models: list[dict[str, Any]] = []
    for spec in router.list_models():
        cred = resolve_provider_credential_source(router, spec.provider_id)
        providers.setdefault(
            spec.provider_id,
            {
                "configured": cred["configured"],
                "source": cred["source"],
                "source_label": cred["source_label"],
            },
        )
        models.append(
            {
                "id": spec.id,
                "name": spec.name,
                "provider_id": spec.provider_id,
                "available": is_model_available(router, spec.id),
                "credential_source": cred["source"],
                "credential_source_label": cred["source_label"],
            }
        )
    return {
        "active_model_id": router.active_model_id,
        "providers": providers,
        "models": models,
    }


_TEST_PROMPT = "Reply with exactly: ok"
_TEST_TIMEOUT_SEC = 20.0


def test_model_connection(router: LLMProviderRouter, model_id: str) -> dict[str, Any]:
    if not is_model_available(router, model_id):
        return {
            "ok": False,
            "model_id": model_id,
            "message": "No credentials configured for this model.",
        }
    spec, api_key = router.resolve_for_model(model_id)
    try:
        if router._chat is None:
            raise RuntimeError("Chat backend not configured")
        router._chat(
            provider_id=spec.provider_id,
            base_url=spec.base_url,
            api_model=spec.api_model,
            api_key=router._require_api_key(spec.provider_id, api_key),
            messages=[{"role": "user", "content": _TEST_PROMPT}],
            timeout_sec=_TEST_TIMEOUT_SEC,
        )
        return {
            "ok": True,
            "model_id": model_id,
            "message": "Provider accepted the API call.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "model_id": model_id,
            "message": str(exc)[:300],
        }


_router = load_router()
_E2E_ROUTER: LLMProviderRouter | None = None


def _e2e_fake_router() -> LLMProviderRouter:
    global _E2E_ROUTER
    if _E2E_ROUTER is None:
        router = LLMProviderRouter()

        def _fake_chat(
            *,
            provider_id: ProviderId,
            base_url: str,
            api_model: str,
            api_key: str,
            messages: list[dict[str, Any]],
            tools: list[dict[str, Any]] | None = None,
            timeout_sec: float = 20.0,
        ) -> dict[str, Any] | str:
            _ = (provider_id, base_url, api_model, api_key, tools, timeout_sec)
            # If the last message is a tool response, we can just echo it
            last_msg = messages[-1]
            if last_msg["role"] == "tool":
                return f"Echo Tool Response: {last_msg['content']}"
            return f"Echo: {last_msg['content']}"

        router._chat = _fake_chat  # type: ignore[method-assign]
        _E2E_ROUTER = router
    return _E2E_ROUTER


def get_router() -> LLMProviderRouter:
    if os.environ.get("CLUTCH_E2E_FAKE_LLM") == "1":
        return _e2e_fake_router()
    return _router
