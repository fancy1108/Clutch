"""Persist LLM router selection and provider keys (M4-09 / M4-04 sidecar leg)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from src.llm.http_complete import http_chat_complete
from src.llm.router import LLMProviderRouter, ModelSpec, ProviderId

from src.credentials.claude_code import bootstrap_claude_credentials, bootstrap_cc_switch_credentials
from src.credentials.sources import (
    cc_switch_has_key_for_provider,
    is_clutch_managed_credential,
    model_source_summary,
    resolve_model_credential_hint,
    resolve_provider_credential_source,
)

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


def _normalize_endpoint_base(url: str) -> str:
    base = (url or "").strip().rstrip("/").lower()
    if base.endswith("/v1"):
        base = base[:-3]
    return base


def _model_identity_key(spec: ModelSpec) -> str:
    return f"{_normalize_endpoint_base(spec.base_url)}|{spec.api_model.strip().lower()}"


def _pick_canonical_model(specs: list[ModelSpec], *, active_model_id: str) -> ModelSpec:
    def sort_key(spec: ModelSpec) -> tuple[int, int, int, str]:
        return (
            0 if spec.id == active_model_id else 1,
            0 if not spec.id.startswith("cc-switch-") else 1,
            len(spec.name),
            spec.id,
        )

    return min(specs, key=sort_key)


def _dedupe_model_specs(specs: list[ModelSpec], *, active_model_id: str) -> list[ModelSpec]:
    """Collapse CC Switch / Claude Code duplicates that share endpoint + api_model."""
    groups: dict[str, list[ModelSpec]] = {}
    order: list[str] = []
    for spec in specs:
        key = _model_identity_key(spec)
        if key not in groups:
            order.append(key)
        groups.setdefault(key, []).append(spec)
    return [_pick_canonical_model(groups[key], active_model_id=active_model_id) for key in order]


def serialize_models_config(router: LLMProviderRouter) -> dict[str, Any]:
    providers: dict[str, Any] = {}
    models: list[dict[str, Any]] = []
    for spec in _dedupe_model_specs(router.list_models(), active_model_id=router.active_model_id):
        cred = resolve_provider_credential_source(router, spec.provider_id)
        providers.setdefault(
            spec.provider_id,
            {
                "configured": cred["configured"],
                "source": cred["source"],
                "source_label": cred["source_label"],
                "clutch_managed": is_clutch_managed_credential(spec.provider_id),
                "cc_switch_fallback_available": (
                    is_clutch_managed_credential(spec.provider_id)
                    and cc_switch_has_key_for_provider(spec.provider_id)
                ),
            },
        )
        is_cc_switch = spec.id.startswith("cc-switch-")
        models.append(
            {
                "id": spec.id,
                "name": spec.name,
                "provider_id": spec.provider_id,
                "available": is_model_available(router, spec.id),
                "credential_source": cred["source"],
                "credential_source_label": cred["source_label"],
                "source_summary": model_source_summary(cred, is_cc_switch=is_cc_switch),
                "credential_hint": resolve_model_credential_hint(router, spec),
                "endpoint": spec.base_url or None,
                "clutch_managed": is_clutch_managed_credential(spec.provider_id),
                "is_cc_switch": is_cc_switch,
            }
        )
    return {
        "active_model_id": router.active_model_id,
        "providers": providers,
        "models": models,
    }


_TEST_PROMPT = "Reply with exactly: ok"
_TEST_TIMEOUT_SEC = 20.0


def format_connection_error(exc: Exception) -> str:
    """Turn provider exceptions into short, user-facing copy."""
    raw = str(exc)
    lower = raw.lower()
    if "429" in raw or "rate limit" in lower:
        return "Rate limit reached — wait a moment, switch models, or upgrade your provider plan."
    if "401" in raw or "403" in raw or "unauthorized" in lower:
        return "API key was rejected — check it matches this provider or gateway."
    if "404" in raw or "not found" in lower:
        return "Model or endpoint not found — the key may work but this model ID is wrong."
    if "timeout" in lower or "timed out" in lower:
        return "Connection timed out — check your network or try again."
    if len(raw) > 120 or raw.strip().startswith("{"):
        return "Connection failed — check your API key and press Test again."
    return raw[:200]


def clear_provider_credential(router: LLMProviderRouter, provider_id: ProviderId) -> None:
    """Remove a Clutch-managed provider key and rehydrate external sources (CC Switch, etc.)."""
    if not is_clutch_managed_credential(provider_id):
        raise ValueError("Only Clutch-managed credentials (models.json) can be removed here.")

    router._api_keys.pop(provider_id, None)  # type: ignore[arg-type]
    path = config_path()
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        keys = data.get("api_keys")
        if isinstance(keys, dict):
            keys.pop(provider_id, None)
            data["api_keys"] = keys
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass

    bootstrap_cc_switch_credentials(router)
    if provider_id == "anthropic" and not router.get_api_key("anthropic"):
        from src.credentials.claude_code import resolve_anthropic_api_key

        key, _ = resolve_anthropic_api_key()
        if key:
            router.set_api_key("anthropic", key)


def rehydrate_cc_switch_models(router: LLMProviderRouter) -> dict[str, Any]:
    """Re-import CC Switch providers without restarting the sidecar."""
    from pathlib import Path

    from src.llm.router import DEFAULT_MODEL_ID

    db_path = Path.home() / ".cc-switch" / "cc-switch.db"
    if not db_path.is_file():
        return {
            "ok": False,
            "cc_switch_found": False,
            "models_imported": 0,
            "message": "CC Switch not found. Install CC Switch or check ~/.cc-switch on this machine.",
        }

    for model_id in [mid for mid in router._models if mid.startswith("cc-switch-")]:
        router._models.pop(model_id, None)
    if router.active_model_id not in router._models:
        router._active_model_id = DEFAULT_MODEL_ID

    bootstrap_cc_switch_credentials(router)
    cc_models = [spec for spec in router.list_models() if spec.id.startswith("cc-switch-")]
    if not cc_models:
        return {
            "ok": True,
            "cc_switch_found": True,
            "models_imported": 0,
            "message": "CC Switch is installed but no models could be imported (missing keys or unsupported providers).",
        }

    names = [spec.name for spec in cc_models]
    return {
        "ok": True,
        "cc_switch_found": True,
        "models_imported": len(cc_models),
        "model_names": names,
        "message": f"Imported {len(cc_models)} model(s) from CC Switch.",
    }


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
            "message": "Connection OK — this model is ready to use.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "model_id": model_id,
            "message": format_connection_error(exc),
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
