"""Persist user-defined models in models.json (image generation first)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.image_router import resolve_image_backend
from src.llm.router import BUILTIN_MODELS, DEFAULT_MODEL_ID, LLMProviderRouter, ModelKind, ModelSpec, ProviderId
from src.preferences_storage import tr

CONFIG_ENV = "CLUTCH_MODELS_CONFIG"

_VALID_IMAGE_BACKENDS = frozenset({"", "agnes", "openai_images"})
_VALID_PROVIDERS: frozenset[str] = frozenset(
    {"deepseek", "openai", "anthropic", "google", "ollama", "custom"}
)


def config_path() -> Path:
    override = os.environ.get(CONFIG_ENV)
    if override:
        return Path(override)
    from src.storage_helper import get_storage_dir

    return get_storage_dir() / "models.json"


def _read_config() -> dict[str, Any]:
    path = config_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_config(data: dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def custom_model_ids() -> set[str]:
    return {
        str(entry.get("id", "")).strip()
        for entry in _read_config().get("custom_models", [])
        if isinstance(entry, dict) and entry.get("id")
    }


def is_custom_model_id(model_id: str) -> bool:
    return model_id in custom_model_ids()


def _slugify_id(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip().lower()).strip("-")
    slug = slug[:48] or "model"
    candidate = f"custom-{slug}"
    taken = set(BUILTIN_MODELS) | custom_model_ids()
    if candidate not in taken:
        return candidate
    index = 2
    while f"{candidate}-{index}" in taken:
        index += 1
    return f"{candidate}-{index}"


def _spec_from_entry(entry: dict[str, Any]) -> ModelSpec:
    provider_id = str(entry.get("provider_id", "custom")).strip()
    if provider_id not in _VALID_PROVIDERS:
        raise ValueError(tr(f"Unsupported provider: {provider_id}", f"不支持的提供商：{provider_id}"))
    model_kind = str(entry.get("model_kind", "image")).strip()
    if model_kind not in {"chat", "image"}:
        raise ValueError(tr("model_kind must be chat or image", "model_kind 必须是 chat 或 image"))
    image_backend = str(entry.get("image_backend", "")).strip()
    if image_backend not in _VALID_IMAGE_BACKENDS:
        raise ValueError(tr("Unsupported image backend", "不支持的生图后端"))
    base_url = str(entry.get("base_url", "")).strip().rstrip("/")
    if not base_url:
        raise ValueError(tr("base_url is required", "base_url 不能为空"))
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(tr("base_url must be a valid http(s) URL", "base_url 必须是有效的 http(s) URL"))
    api_model = str(entry.get("api_model", "")).strip()
    if not api_model:
        raise ValueError(tr("api_model is required", "api_model 不能为空"))
    model_id = str(entry.get("id", "")).strip() or _slugify_id(str(entry.get("name", api_model)))
    name = str(entry.get("name", "")).strip() or api_model
    return ModelSpec(
        id=model_id,
        name=name,
        provider_id=provider_id,  # type: ignore[arg-type]
        api_model=api_model,
        base_url=base_url,
        model_kind=model_kind,  # type: ignore[arg-type]
        image_backend=image_backend,
    )


def register_custom_models(router: LLMProviderRouter) -> None:
    for raw in _read_config().get("custom_models", []):
        if not isinstance(raw, dict):
            continue
        try:
            spec = _spec_from_entry(raw)
        except ValueError:
            continue
        router.register_model(spec)


def add_custom_model(
    router: LLMProviderRouter,
    *,
    name: str,
    api_model: str,
    base_url: str,
    provider_id: str = "custom",
    model_kind: ModelKind = "image",
    image_backend: str = "",
    model_id: str = "",
    api_key: str | None = None,
) -> ModelSpec:
    if model_kind != "image":
        raise ValueError(tr("Only image models can be added from the UI for now.", "当前 UI 仅支持添加生图模型。"))
    entry = {
        "id": model_id.strip() or _slugify_id(name),
        "name": name.strip(),
        "api_model": api_model.strip(),
        "base_url": base_url.strip().rstrip("/"),
        "provider_id": provider_id.strip() or "custom",
        "model_kind": model_kind,
        "image_backend": image_backend.strip(),
    }
    spec = _spec_from_entry(entry)
    if spec.id in BUILTIN_MODELS:
        raise ValueError(tr("Model id conflicts with a built-in model.", "模型 id 与内置模型冲突。"))
    if spec.id in custom_model_ids():
        raise ValueError(tr("A custom model with this id already exists.", "已存在相同 id 的自定义模型。"))
    # Validate backend resolves
    resolve_image_backend(spec)

    data = _read_config()
    custom_models = [item for item in data.get("custom_models", []) if isinstance(item, dict)]
    custom_models.append(entry)
    data["custom_models"] = custom_models
    if api_key and api_key.strip():
        keys = data.get("api_keys")
        if not isinstance(keys, dict):
            keys = {}
        keys[spec.provider_id] = api_key.strip()
        data["api_keys"] = keys
        router.set_api_key(spec.provider_id, api_key.strip())  # type: ignore[arg-type]
    _write_config(data)
    router.register_model(spec)
    return spec


def delete_custom_model(router: LLMProviderRouter, model_id: str) -> None:
    if not is_custom_model_id(model_id):
        raise ValueError(tr("Only custom models can be removed here.", "只能删除自定义模型。"))
    data = _read_config()
    custom_models = [
        item
        for item in data.get("custom_models", [])
        if isinstance(item, dict) and str(item.get("id")) != model_id
    ]
    data["custom_models"] = custom_models
    if router.active_model_id == model_id:
        data["active_model_id"] = DEFAULT_MODEL_ID
        router._active_model_id = DEFAULT_MODEL_ID
    _write_config(data)
    router._models.pop(model_id, None)


def hide_model_from_list(router: LLMProviderRouter, model_id: str) -> None:
    if model_id not in router._models:
        raise ValueError(tr("Unknown model.", "未知模型。"))
    if model_id.startswith("cc-switch-"):
        raise ValueError(
            tr(
                "CC Switch models cannot be removed here. Change them in CC Switch instead.",
                "无法在此删除 CC Switch 导入的模型，请在 CC Switch 中管理。",
            )
        )
    if is_custom_model_id(model_id):
        delete_custom_model(router, model_id)
        return

    data = _read_config()
    hidden = [str(item) for item in data.get("hidden_model_ids", []) if isinstance(item, str)]
    if model_id not in hidden:
        hidden.append(model_id)
    data["hidden_model_ids"] = hidden
    if router.active_model_id == model_id:
        data["active_model_id"] = DEFAULT_MODEL_ID
        router._active_model_id = DEFAULT_MODEL_ID
    _write_config(data)


def remove_model_from_list(router: LLMProviderRouter, model_id: str) -> None:
    """Delete custom models or hide built-in / imported catalog entries."""
    hide_model_from_list(router, model_id)
