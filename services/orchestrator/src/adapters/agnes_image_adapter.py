"""Agnes Image 2.1 Flash — text-to-image / image-to-image via apihub.agnes-ai.com."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Literal

AGNES_IMAGE_API_BASE = "https://apihub.agnes-ai.com"
AGNES_IMAGE_MODEL = "agnes-image-2.1-flash"
DEFAULT_IMAGE_SIZE = "1024x768"
DEFAULT_TIMEOUT_SEC = 120.0
TEST_PROMPT = "A minimal red circle on a plain white background, flat vector style"


def _image_generations_url(base_url: str = AGNES_IMAGE_API_BASE) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return f"{root}/images/generations"
    return f"{root}/v1/images/generations"


def generate_agnes_image(
    prompt: str,
    *,
    api_key: str,
    model: str = AGNES_IMAGE_MODEL,
    size: str = DEFAULT_IMAGE_SIZE,
    response_format: Literal["url", "b64_json"] = "url",
    input_images: list[str] | None = None,
    base_url: str = AGNES_IMAGE_API_BASE,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Generate or edit an image. Returns the first item from response data[]."""
    trimmed = prompt.strip()
    if not trimmed:
        raise ValueError("prompt is required")
    if not api_key.strip():
        raise ValueError("api_key is required")

    body: dict[str, Any] = {
        "model": model,
        "prompt": trimmed,
        "size": size,
    }

    if input_images:
        body["extra_body"] = {
            "image": input_images,
            "response_format": response_format,
        }
    elif response_format == "b64_json":
        body["return_base64"] = True
    else:
        body["extra_body"] = {"response_format": "url"}

    if on_log:
        mode = "img2img" if input_images else "text2img"
        on_log(f"[AGNES IMAGE] {mode} model={model} size={size}")

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
        raise RuntimeError(f"Agnes Image API error {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to reach Agnes Image API: {exc}") from exc

    items = data.get("data")
    if not isinstance(items, list) or not items:
        raise RuntimeError("Agnes Image API returned no image data")

    first = items[0]
    if not isinstance(first, dict):
        raise RuntimeError("Agnes Image API returned malformed data")

    if on_log:
        if first.get("url"):
            on_log("[AGNES IMAGE] Image URL received")
        elif first.get("b64_json"):
            on_log("[AGNES IMAGE] Base64 image received")

    return first


def verify_agnes_image_connection(
    *,
    api_key: str,
    model: str = AGNES_IMAGE_MODEL,
    base_url: str = AGNES_IMAGE_API_BASE,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> None:
    """Smoke-test credentials with a tiny text-to-image request."""
    result = generate_agnes_image(
        TEST_PROMPT,
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_sec=timeout_sec,
    )
    if not (result.get("url") or result.get("b64_json")):
        raise RuntimeError("Agnes Image API response missing url and b64_json")
