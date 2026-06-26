"""OpenAI-compatible /v1/images/generations (DALL-E, many gateways)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Literal

DEFAULT_IMAGE_SIZE = "1024x1024"
DEFAULT_TIMEOUT_SEC = 120.0
TEST_PROMPT = "A minimal red circle on a plain white background, flat vector style"


def _image_generations_url(base_url: str) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return f"{root}/images/generations"
    return f"{root}/v1/images/generations"


def generate_openai_image(
    prompt: str,
    *,
    api_key: str,
    model: str,
    size: str = DEFAULT_IMAGE_SIZE,
    response_format: Literal["url", "b64_json"] = "url",
    base_url: str,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    trimmed = prompt.strip()
    if not trimmed:
        raise ValueError("prompt is required")
    if not api_key.strip():
        raise ValueError("api_key is required")
    if not base_url.strip():
        raise ValueError("base_url is required")

    body: dict[str, Any] = {
        "model": model,
        "prompt": trimmed,
        "size": size,
        "response_format": response_format,
    }

    if on_log:
        on_log(f"[IMAGE] text2img backend=openai_images model={model} size={size}")

    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        _image_generations_url(base_url),
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Image API error {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to reach image API: {exc}") from exc

    items = data.get("data")
    if not isinstance(items, list) or not items:
        raise RuntimeError("Image API returned no image data")

    first = items[0]
    if not isinstance(first, dict):
        raise RuntimeError("Image API returned malformed data")

    if on_log:
        if first.get("url"):
            on_log("[IMAGE] Image URL received")
        elif first.get("b64_json"):
            on_log("[IMAGE] Base64 image received")

    return first


def verify_openai_image_connection(
    *,
    api_key: str,
    model: str,
    base_url: str,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> None:
    result = generate_openai_image(
        TEST_PROMPT,
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_sec=timeout_sec,
    )
    if not (result.get("url") or result.get("b64_json")):
        raise RuntimeError("Image API response missing url and b64_json")
