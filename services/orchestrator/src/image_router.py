"""Route image-generation models to the correct adapter backend."""

from __future__ import annotations

import base64
import urllib.request
from collections.abc import Callable
from typing import Any

from src.llm.router import ModelSpec
from src.preferences_storage import tr

GenerateFn = Callable[..., dict[str, Any]]
VerifyFn = Callable[..., None]
_FETCH_TIMEOUT_SEC = 60.0


def is_image_model(spec: ModelSpec) -> bool:
    return spec.model_kind == "image"


def resolve_image_backend(spec: ModelSpec) -> str:
    if spec.image_backend:
        return spec.image_backend
    base = spec.base_url.lower()
    if "agnes-ai.com" in base:
        return "agnes"
    return "openai_images"


def _generator_for(backend: str) -> GenerateFn:
    if backend == "agnes":
        from src.adapters.agnes_image_adapter import generate_agnes_image

        return generate_agnes_image
    if backend == "openai_images":
        from src.adapters.openai_images_adapter import generate_openai_image

        return generate_openai_image
    raise RuntimeError(f"Unsupported image backend: {backend!r}")


def _verifier_for(backend: str) -> VerifyFn:
    if backend == "agnes":
        from src.adapters.agnes_image_adapter import verify_agnes_image_connection

        return verify_agnes_image_connection
    if backend == "openai_images":
        from src.adapters.openai_images_adapter import verify_openai_image_connection

        return verify_openai_image_connection
    raise RuntimeError(f"Unsupported image backend: {backend!r}")


def _fetch_url_as_b64(url: str) -> str:
    with urllib.request.urlopen(url, timeout=_FETCH_TIMEOUT_SEC) as resp:
        payload = resp.read()
        headers = resp.headers
        if hasattr(headers, "get_content_type"):
            content_type = headers.get_content_type()
        else:
            content_type = headers.get("Content-Type", "image/png")
        content_type = (content_type or "image/png").split(";")[0].strip()
    if not payload:
        raise RuntimeError("Image URL returned empty body")
    return f"data:{content_type};base64,{base64.b64encode(payload).decode('ascii')}"


def _ensure_inline_image(result: dict[str, Any]) -> dict[str, Any]:
    """Providers often return CDN URLs even when base64 was requested — fetch for Tauri CSP."""
    if str(result.get("b64_json") or "").strip():
        return result
    url = str(result.get("url") or "").strip()
    if not url:
        return result
    try:
        return {**result, "b64_json": _fetch_url_as_b64(url)}
    except Exception:
        return result


def generate_image_for_model(
    spec: ModelSpec,
    prompt: str,
    *,
    api_key: str,
    on_log: Callable[[str], None] | None = None,
    response_format: str = "b64_json",
) -> dict[str, Any]:
    """Generate an image. Defaults to base64 so Tauri WebView CSP (data:) can render it."""
    backend = resolve_image_backend(spec)
    result = _generator_for(backend)(
        prompt,
        api_key=api_key,
        model=spec.api_model,
        base_url=spec.base_url,
        on_log=on_log,
        response_format=response_format,
    )
    if response_format == "b64_json":
        result = _ensure_inline_image(result)
    return result


def verify_image_model_connection(
    spec: ModelSpec,
    *,
    api_key: str,
) -> None:
    backend = resolve_image_backend(spec)
    _verifier_for(backend)(api_key=api_key, model=spec.api_model, base_url=spec.base_url)


def format_image_reply(result: dict[str, Any]) -> str:
    """Prefer inline base64 so Tauri WebView CSP (data:) can render without remote img-src."""
    b64_json = str(result.get("b64_json") or "").strip()
    image_url = str(result.get("url") or "").strip()
    if b64_json:
        data_uri = b64_json if b64_json.startswith("data:") else f"data:image/png;base64,{b64_json}"
        return f"![{tr('Generated image', '生成的图片')}]({data_uri})"
    if image_url:
        return f"![{tr('Generated image', '生成的图片')}]({image_url})"
    return tr(
        "Image generation completed but no image was returned.",
        "图片生成已完成，但未返回图像数据。",
    )
