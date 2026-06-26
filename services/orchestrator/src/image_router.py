"""Route image-generation models to the correct adapter backend."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.llm.router import ModelSpec
from src.preferences_storage import tr

GenerateFn = Callable[..., dict[str, Any]]
VerifyFn = Callable[..., None]


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


def generate_image_for_model(
    spec: ModelSpec,
    prompt: str,
    *,
    api_key: str,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    backend = resolve_image_backend(spec)
    return _generator_for(backend)(
        prompt,
        api_key=api_key,
        model=spec.api_model,
        base_url=spec.base_url,
        on_log=on_log,
    )


def verify_image_model_connection(
    spec: ModelSpec,
    *,
    api_key: str,
) -> None:
    backend = resolve_image_backend(spec)
    _verifier_for(backend)(api_key=api_key, model=spec.api_model, base_url=spec.base_url)


def format_image_reply(result: dict[str, Any]) -> str:
    image_url = str(result.get("url") or "").strip()
    b64_json = str(result.get("b64_json") or "").strip()
    if image_url:
        return (
            f"![{tr('Generated image', '生成的图片')}]({image_url})\n\n"
            f"[{tr('Open image', '打开图片')}]({image_url})"
        )
    if b64_json:
        data_uri = b64_json if b64_json.startswith("data:") else f"data:image/png;base64,{b64_json}"
        return f"![{tr('Generated image', '生成的图片')}]({data_uri})"
    return tr(
        "Image generation completed but no image was returned.",
        "图片生成已完成，但未返回图像数据。",
    )
