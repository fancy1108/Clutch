"""Route video-generation models to the correct adapter backend."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.llm.router import ModelSpec
from src.preferences_storage import tr

GenerateFn = Callable[..., dict[str, Any]]
VerifyFn = Callable[..., None]


def is_video_model(spec: ModelSpec) -> bool:
    return spec.model_kind == "video"


def resolve_video_backend(spec: ModelSpec) -> str:
    if spec.video_backend:
        return spec.video_backend
    base = spec.base_url.lower()
    if "agnes-ai.com" in base:
        return "agnes"
    raise RuntimeError(f"No video backend configured for model {spec.id!r}")


def _generator_for(backend: str) -> GenerateFn:
    if backend == "agnes":
        from src.adapters.agnes_video_adapter import generate_agnes_video

        return generate_agnes_video
    raise RuntimeError(f"Unsupported video backend: {backend!r}")


def _verifier_for(backend: str) -> VerifyFn:
    if backend == "agnes":
        from src.adapters.agnes_video_adapter import verify_agnes_video_connection

        return verify_agnes_video_connection
    raise RuntimeError(f"Unsupported video backend: {backend!r}")


def generate_video_for_model(
    spec: ModelSpec,
    prompt: str,
    *,
    api_key: str,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    backend = resolve_video_backend(spec)
    return _generator_for(backend)(
        prompt,
        api_key=api_key,
        model=spec.api_model,
        base_url=spec.base_url,
        on_log=on_log,
    )


def verify_video_model_connection(
    spec: ModelSpec,
    *,
    api_key: str,
) -> None:
    backend = resolve_video_backend(spec)
    _verifier_for(backend)(api_key=api_key, model=spec.api_model, base_url=spec.base_url)


def format_video_reply(result: dict[str, Any]) -> str:
    video_url = str(result.get("video_url") or result.get("url") or "").strip()
    if video_url:
        label = tr("Generated video", "生成的视频")
        return f"[video: {video_url}]\n\n{label}"
    return tr(
        "Video generation completed but no video URL was returned.",
        "视频生成已完成，但未返回视频地址。",
    )
