"""Video model router tests."""

from __future__ import annotations

from src.llm.router import BUILTIN_MODELS, ModelSpec
from src.video_router import (
    format_video_reply,
    is_video_model,
    resolve_video_backend,
)


def test_is_video_model_uses_model_kind() -> None:
    assert is_video_model(BUILTIN_MODELS["agnes-video-v2.0"])
    assert not is_video_model(BUILTIN_MODELS["agnes-image-2.1-flash"])
    assert not is_video_model(BUILTIN_MODELS["agnes-2.0-flash"])


def test_resolve_video_backend_explicit() -> None:
    spec = ModelSpec(
        id="custom-vid",
        name="Custom Video",
        provider_id="custom",
        api_model="agnes-video-v2.0",
        base_url="https://apihub.agnes-ai.com",
        model_kind="video",
        video_backend="agnes",
    )
    assert resolve_video_backend(spec) == "agnes"


def test_resolve_video_backend_infers_agnes() -> None:
    assert resolve_video_backend(BUILTIN_MODELS["agnes-video-v2.0"]) == "agnes"


def test_format_video_reply() -> None:
    text = format_video_reply({"video_url": "https://cdn.example.com/a.mp4"})
    assert "[video: https://cdn.example.com/a.mp4]" in text
