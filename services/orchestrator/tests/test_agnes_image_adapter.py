"""Agnes Image 2.1 Flash adapter tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.agnes_image_adapter import (
    AGNES_IMAGE_MODEL,
    generate_agnes_image,
    verify_agnes_image_connection,
)


def test_generate_agnes_image_text_to_image_url() -> None:
    response = MagicMock()
    response.read.return_value = json.dumps(
        {
            "created": 1780000000,
            "data": [{"url": "https://example.com/out.png", "b64_json": None}],
        }
    ).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=response) as mocked:
        result = generate_agnes_image(
            "A red circle",
            api_key="sk-test",
            response_format="url",
        )

    assert result["url"] == "https://example.com/out.png"
    mocked.assert_called_once()
    request = mocked.call_args[0][0]
    body = json.loads(request.data.decode("utf-8"))
    assert body["model"] == AGNES_IMAGE_MODEL
    assert body["prompt"] == "A red circle"
    assert body["size"] == "1024x768"
    assert body["extra_body"] == {"response_format": "url"}
    assert request.get_header("Authorization") == "Bearer sk-test"


def test_generate_agnes_image_img2img() -> None:
    response = MagicMock()
    response.read.return_value = json.dumps(
        {"data": [{"url": "https://example.com/edited.png"}]}
    ).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=response):
        result = generate_agnes_image(
            "Make it cyberpunk",
            api_key="sk-test",
            input_images=["https://example.com/input.png"],
        )

    assert result["url"] == "https://example.com/edited.png"


def test_generate_agnes_image_requires_prompt() -> None:
    with pytest.raises(ValueError, match="prompt"):
        generate_agnes_image("  ", api_key="sk-test")


def test_verify_agnes_image_connection() -> None:
    with patch(
        "src.adapters.agnes_image_adapter.generate_agnes_image",
        return_value={"url": "https://example.com/out.png"},
    ) as mocked:
        verify_agnes_image_connection(api_key="sk-test")
    mocked.assert_called_once()
