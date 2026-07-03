"""OpenCode Zen model discovery and transport hints (https://opencode.ai/docs/zen)."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Literal

ZEN_BASE_URL = "https://opencode.ai/zen/v1"
ZEN_MODELS_URL = f"{ZEN_BASE_URL}/models"
ZEN_DEFAULT_MODEL_ID = "opencode-deepseek-v4-flash-free"
_TIMEOUT_SEC = 20.0
_HTTP_USER_AGENT = "ClutchSidecar/1.0"

# Curated free chat models shipped in Clutch (refresh can extend the picker).
BUILTIN_FREE_MODELS: tuple[str, ...] = (
    "deepseek-v4-flash-free",
    "big-pickle",
    "mimo-v2.5-free",
    "north-mini-code-free",
    "nemotron-3-ultra-free",
)

TransportKind = Literal["chat_completions", "anthropic_messages", "unsupported"]


def opencode_model_id(api_model: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", api_model.lower()).strip("-")
    return f"opencode-{slug}" if slug else "opencode-unknown"


def opencode_display_name(api_model: str) -> str:
    label = re.sub(r"[-_]+", " ", api_model).strip().title()
    return f"{label} (OpenCode Zen)"


def resolve_transport(api_model: str) -> TransportKind:
    model = api_model.lower()
    if model.startswith("gpt-"):
        return "unsupported"
    if model.startswith("gemini-"):
        return "unsupported"
    if model.startswith(("claude-", "qwen")):
        return "anthropic_messages"
    return "chat_completions"


def _parse_models_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise RuntimeError("Unexpected OpenCode Zen models response.")
    return [row for row in rows if isinstance(row, dict) and row.get("id")]


def _fetch_models(*, api_key: str | None = None) -> list[dict[str, Any]]:
    headers: dict[str, str] = {"User-Agent": _HTTP_USER_AGENT}
    if api_key and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    req = urllib.request.Request(ZEN_MODELS_URL, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        if exc.code in {401, 403} and headers.get("Authorization"):
            raise RuntimeError(
                "OpenCode Zen API key was rejected. Create a key at "
                "https://opencode.ai/auth (Zen → API Keys). "
                "Do not use DeepSeek/OpenAI/Anthropic keys here."
            ) from exc
        if exc.code == 403:
            raise RuntimeError(
                "OpenCode Zen blocked the request (HTTP 403). Try again or check your network."
            ) from exc
        raise RuntimeError(f"OpenCode Zen models API error {exc.code}: {detail}") from exc
    return _parse_models_payload(payload)


def fetch_opencode_zen_catalog(*, include_unsupported: bool = False) -> list[dict[str, Any]]:
    """Public model catalog — opencode.ai/zen/v1/models does not require auth."""
    models: list[dict[str, Any]] = []
    for row in _fetch_models():
        api_model = str(row["id"])
        transport = resolve_transport(api_model)
        if transport == "unsupported" and not include_unsupported:
            continue
        models.append(
            {
                "id": opencode_model_id(api_model),
                "api_model": api_model,
                "name": opencode_display_name(api_model),
                "transport": transport,
                "supported": transport != "unsupported",
            }
        )
    models.sort(key=lambda item: (0 if item["api_model"].endswith("-free") else 1, item["name"]))
    return models


def list_opencode_zen_models(api_key: str | None = None, *, include_unsupported: bool = False) -> list[dict[str, Any]]:
    """Return model metadata for UI selection (catalog is public; key optional)."""
    _ = api_key
    return fetch_opencode_zen_catalog(include_unsupported=include_unsupported)


def verify_opencode_zen_api_key(api_key: str, *, api_model: str = "big-pickle") -> None:
    """Validate key with a minimal chat completion (matches real usage)."""
    from src.llm.http_complete import http_chat_complete

    key = api_key.strip()
    if not key:
        raise RuntimeError("OpenCode Zen API key is required.")
    try:
        http_chat_complete(
            provider_id="opencode",
            base_url=ZEN_BASE_URL,
            api_model=api_model,
            api_key=key,
            messages=[{"role": "user", "content": "ok"}],
            timeout_sec=45,
            max_tokens=8,
        )
    except Exception as exc:
        raw = str(exc).lower()
        if "invalid api key" in raw or "401" in str(exc):
            raise RuntimeError(
                "OpenCode Zen API key was rejected. Create a key at "
                "https://opencode.ai/auth (Zen → API Keys). "
                "Do not use DeepSeek/OpenAI/Anthropic keys here."
            ) from exc
        raise


def validate_opencode_zen_save(api_key: str, model_id: str, router: Any) -> None:
    """Ensure the model is still on Zen and the API key can call it."""
    spec = router._models.get(model_id)
    if not spec or spec.provider_id != "opencode":
        raise ValueError(f"Unknown OpenCode Zen model: {model_id}")

    try:
        catalog = fetch_opencode_zen_catalog()
    except Exception as exc:
        raise ValueError(f"Could not reach OpenCode Zen to verify models: {exc}") from exc

    live_api_models = {str(entry["api_model"]) for entry in catalog}
    if spec.api_model not in live_api_models:
        raise ValueError(
            f"Model {spec.name!r} is no longer listed on OpenCode Zen. "
            "Press Refresh next to Model and pick another."
        )

    verify_opencode_zen_api_key(api_key, api_model=spec.api_model)
