"""Parse embedded chat image markers for multimodal LLM requests."""

from __future__ import annotations

import re
from typing import Any

_IMAGE_MARKER_RE = re.compile(
    r"\[image:\s*(data:image/[^\]]+)\]\s*",
    re.IGNORECASE,
)


def extract_image_data_urls(text: str) -> tuple[str, list[str]]:
    """Strip `[image: data:...]` markers and return remaining text plus image URLs."""
    urls = [url.strip() for url in _IMAGE_MARKER_RE.findall(text)]
    plain = _IMAGE_MARKER_RE.sub("", text).strip()
    return plain, urls


def user_message_content_for_llm(
    text: str,
    *,
    vision_enabled: bool,
) -> str | list[dict[str, Any]]:
    """Build OpenAI-compatible user content (plain text or text + image_url parts)."""
    plain, image_urls = extract_image_data_urls(text)
    if not image_urls:
        return plain or text
    if not vision_enabled:
        note = "[Attached image(s) omitted — this model does not support vision.]"
        return f"{note}\n{plain}".strip() if plain else note
    parts: list[dict[str, Any]] = []
    if plain:
        parts.append({"type": "text", "text": plain})
    for url in image_urls:
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts
