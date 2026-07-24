"""Parse embedded chat image markers for multimodal LLM requests."""

from __future__ import annotations

import re
from typing import Any

_IMAGE_MARKER_RE = re.compile(
    r"\[image:\s*(data:image/[^\]]+)\]\s*",
    re.IGNORECASE,
)

# Soft capability refusals from the model (EN + ZH). Keep tight to avoid false positives.
_VISION_ERROR_RE = re.compile(
    r"(?:"
    r"cannot\s+read|does\s+not\s+support\s+(?:image|vision)|"
    r"unable\s+to\s+(?:read|process|view)\s+(?:the\s+)?(?:image|picture|screenshot)|"
    r"inform\s+the\s+user|no\s+image\s+(?:input|support)|"
    r"(?:不支持|无法).{0,16}(?:图像|图片|视觉|看图|识图)|"
    r"(?:无法|不能).{0,12}(?:读取|识别|查看|处理).{0,12}(?:图像|图片|截图)|"
    r"(?:模型|当前模型).{0,20}(?:不支持|没有).{0,12}(?:视觉|图像|图片|多模态)"
    r")",
    re.IGNORECASE,
)

_VISION_API_ERROR_RE = re.compile(
    r"(?:"
    r"image_url|data:image|multimodal|vision|"
    r"invalid\s+image|unsupported\s+image|cannot\s+process\s+image|"
    r"media\s+type|image\s+input"
    r")",
    re.IGNORECASE,
)


def extract_image_data_urls(text: str) -> tuple[str, list[str]]:
    """Strip `[image: data:...]` markers and return remaining text plus image URLs."""
    urls = [url.strip() for url in _IMAGE_MARKER_RE.findall(text)]
    plain = _IMAGE_MARKER_RE.sub("", text).strip()
    return plain, urls


def looks_like_vision_error(text: str) -> bool:
    """True if LLM output looks like a vision-capability refusal, not real content."""
    if not text:
        return False
    return bool(_VISION_ERROR_RE.search(text[:800]))


def looks_like_vision_api_error(exc: BaseException | str) -> bool:
    """True if an API/transport error is likely about rejecting image input."""
    msg = str(exc)
    if not msg:
        return False
    return bool(_VISION_API_ERROR_RE.search(msg[:800]))


def _non_vision_image_fallback_text(image_urls: list[str], plain: str) -> str:
    """Describe attached images via local analysis after vision try failed."""
    fragments: list[str] = []
    try:
        from src.design.image_analysis import image_analysis_prompt_fragment_for_chat
    except ImportError:
        image_analysis_prompt_fragment_for_chat = None  # type: ignore[assignment]

    if image_analysis_prompt_fragment_for_chat is not None:
        for url in image_urls:
            fragment = (image_analysis_prompt_fragment_for_chat(url) or "").strip()
            if fragment:
                fragments.append(fragment)

    if fragments:
        analysis = "\n\n".join(fragments)
        header = (
            "[Attached image(s) — model could not process vision input; "
            "local image analysis (OCR/palette) follows.]"
        )
        body = f"{header}\n\n{analysis}"
    else:
        body = (
            "[Attached image(s) — model could not process vision input; "
            "local image analysis unavailable. Describe the image in text if needed.]"
        )
    return f"{body}\n{plain}".strip() if plain else body


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
        return _non_vision_image_fallback_text(image_urls, plain)
    parts: list[dict[str, Any]] = []
    if plain:
        parts.append({"type": "text", "text": plain})
    for url in image_urls:
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts


def normalize_text_content(content: Any) -> str:
    """Flatten OpenAI-style multimodal content to plain text for local CLIs."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                text = str(item.get("text", "")).strip()
                if text:
                    parts.append(text)
            elif item.get("type") == "image_url":
                parts.append("[image omitted]")
        return "\n".join(parts).strip()
    return str(content or "").strip()


def materialize_images_as_file_refs(text: str) -> str:
    """Persist ``[image: data:…]`` markers to ``.clutch/attachments/`` and reference paths.

    Local CLIs (Mimo, Claude Code, …) get ``@path`` / ``[file: path]`` so they can
    read the image themselves. Never puts base64 on the CLI argv.
    OCR is intentionally not included — that is a refusal fallback only.
    """
    plain, image_urls = extract_image_data_urls(text)
    if not image_urls:
        return (plain or text).strip()

    from src.workspace_attachments import save_attachment_data_url

    parts: list[str] = []
    for url in image_urls:
        saved = save_attachment_data_url(url, analyze=False)
        path = str(saved.get("path") or "").strip()
        if not path:
            continue
        parts.append(f"[file: {path}]")
        parts.append(f"@{path}")
    if not parts:
        return (plain or text).strip()
    body = "\n".join(parts)
    return f"{body}\n{plain}".strip() if plain else body


def ocr_fallback_prompt_for_engine(text: str) -> str:
    """Local OCR/palette text after the engine refused or could not read the image."""
    plain, image_urls = extract_image_data_urls(text)
    if not image_urls:
        return (plain or text).strip()
    return normalize_text_content(
        user_message_content_for_llm(text, vision_enabled=False)
    )


# Back-compat alias (was OCR-first; callers should prefer materialize / ocr_fallback).
def plain_user_prompt_for_engine(text: str) -> str:
    return ocr_fallback_prompt_for_engine(text)
