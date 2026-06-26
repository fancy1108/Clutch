"""Image model router tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.image_router import (
    format_image_reply,
    generate_image_for_model,
    is_image_model,
    resolve_image_backend,
    verify_image_model_connection,
)
from src.llm.router import BUILTIN_MODELS, ModelSpec


def test_is_image_model_uses_model_kind() -> None:
    assert is_image_model(BUILTIN_MODELS["agnes-image-2.1-flash"])
    assert not is_image_model(BUILTIN_MODELS["deepseek-v4pro"])


def test_resolve_image_backend_explicit() -> None:
    spec = ModelSpec(
        id="custom-img",
        name="Custom Image",
        provider_id="openai",
        api_model="dall-e-3",
        base_url="https://api.openai.com/v1",
        model_kind="image",
        image_backend="openai_images",
    )
    assert resolve_image_backend(spec) == "openai_images"


def test_resolve_image_backend_infers_agnes() -> None:
    assert resolve_image_backend(BUILTIN_MODELS["agnes-image-2.1-flash"]) == "agnes"


def test_resolve_image_backend_defaults_to_openai_images() -> None:
    spec = ModelSpec(
        id="dall-e-3",
        name="DALL-E 3",
        provider_id="openai",
        api_model="dall-e-3",
        base_url="https://api.openai.com/v1",
        model_kind="image",
    )
    assert resolve_image_backend(spec) == "openai_images"


def test_generate_image_for_model_dispatches_backend() -> None:
    spec = ModelSpec(
        id="dall-e-3",
        name="DALL-E 3",
        provider_id="openai",
        api_model="dall-e-3",
        base_url="https://api.openai.com/v1",
        model_kind="image",
        image_backend="openai_images",
    )
    with patch(
        "src.image_router._generator_for",
        return_value=lambda *_args, **_kwargs: {"url": "https://example.com/img.png"},
    ):
        result = generate_image_for_model(spec, "a white dog", api_key="sk-test")
    assert result["url"] == "https://example.com/img.png"


def test_format_image_reply_url() -> None:
    text = format_image_reply({"url": "https://example.com/dog.png"})
    assert "https://example.com/dog.png" in text


def test_verify_image_model_connection_agnes() -> None:
    with patch(
        "src.image_router._verifier_for",
        return_value=lambda **_kwargs: None,
    ):
        verify_image_model_connection(
            BUILTIN_MODELS["agnes-image-2.1-flash"],
            api_key="sk-test",
        )
