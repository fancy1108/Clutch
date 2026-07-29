"""Auto-invoke configured image/video models for visual deliverable intents.

Chat models research with tools; the harness then calls the user's configured
Agnes (or other) image/video model. If none is configured, the final chat reply
states clearly that the last step failed.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from src.deliverable_intent import classify_deliverable_intent
from src.preferences_storage import tr


def _tool_ok_with_path(content: str, *, fragment: str) -> bool:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict) or not payload.get("ok"):
        return False
    path = str(payload.get("local_media_path") or "").replace("\\", "/")
    return fragment in path


def _already_has_image(files_changed: list[str], chat_messages: list[dict[str, Any]]) -> bool:
    for path in files_changed:
        if "generated/images" in (path or "").replace("\\", "/"):
            return True
    for message in chat_messages:
        if message.get("role") != "tool":
            continue
        if _tool_ok_with_path(str(message.get("content") or ""), fragment="generated/images"):
            return True
    return False


def _already_has_video(files_changed: list[str], chat_messages: list[dict[str, Any]]) -> bool:
    for path in files_changed:
        if "generated/videos" in (path or "").replace("\\", "/"):
            return True
    for message in chat_messages:
        if message.get("role") != "tool":
            continue
        if _tool_ok_with_path(str(message.get("content") or ""), fragment="generated/videos"):
            return True
    return False


def _media_prompt(user_text: str, chat_messages: list[dict[str, Any]]) -> str:
    base = (user_text or "").strip()
    # Prefer a short assistant summary if present (after research).
    for message in reversed(chat_messages):
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        if content.strip().startswith("{"):
            continue
        snippet = content.strip()
        if len(snippet) > 80:
            return f"{base}\n\nContext for the visual:\n{snippet[:1200]}"
    return base[:2000] or "Create a clear, high-quality visual."


def _fail_image_unconfigured() -> str:
    return tr(
        "**Last step failed: could not generate the image.**\n\n"
        "No image-model API key is configured. Open **Settings → Models**, save a key "
        "for Agnes Image (or another image model), then ask again to generate the image.",
        "**最后一步失败：未能生成图片。**\n\n"
        "未配置可用的图像模型 API Key。请打开 **设置 → 模型**，为 Agnes Image"
        "（或其它图像模型）保存 Key，然后再说一次「继续生成图片」。",
    )


def _fail_video_unconfigured() -> str:
    return tr(
        "**Last step failed: could not generate the video.**\n\n"
        "No video-model API key is configured. Open **Settings → Models**, save a key "
        "for Agnes Video (or another video model), then ask again to generate the video.",
        "**最后一步失败：未能生成视频。**\n\n"
        "未配置可用的视频模型 API Key。请打开 **设置 → 模型**，为 Agnes Video"
        "（或其它视频模型）保存 Key，然后再说一次「继续生成视频」。",
    )


def _fail_image_error(exc: BaseException) -> str:
    return tr(
        f"**Last step failed: image generation error.**\n\n{exc}\n\n"
        "Check your Agnes Image (or image model) settings and try again.",
        f"**最后一步失败：图片生成出错。**\n\n{exc}\n\n"
        "请检查 Agnes Image（或其它图像模型）配置后重试。",
    )


def _fail_video_error(exc: BaseException) -> str:
    return tr(
        f"**Last step failed: video generation error.**\n\n{exc}\n\n"
        "Check your Agnes Video (or video model) settings and try again.",
        f"**最后一步失败：视频生成出错。**\n\n{exc}\n\n"
        "请检查 Agnes Video（或其它视频模型）配置后重试。",
    )


def finalize_media_deliverables(
    *,
    output: str,
    user_text: str | None,
    chat_messages: list[dict[str, Any]],
    files_changed: list[str],
    logs: list[str],
    log_prefix: str,
    on_log: Callable[[str], None] | None = None,
) -> str:
    """After the ReAct loop, ensure image/video intent actually produces media."""
    kind = classify_deliverable_intent(user_text)
    needs_image = kind in {"image", "mixed"}
    needs_video = kind == "video"
    if not needs_image and not needs_video:
        return output

    def _emit(line: str) -> None:
        logs.append(line)
        if on_log:
            on_log(line)

    text_out = (output or "").strip()
    prompt = _media_prompt(user_text or "", chat_messages)

    if needs_image and not _already_has_image(files_changed, chat_messages):
        from src.image_router import (
            format_image_reply,
            generate_image_for_model,
            persist_generated_image,
            resolve_configured_image_model,
        )

        resolved = resolve_configured_image_model()
        if resolved is None:
            _emit(f"[{log_prefix}] Media finalize: image model not configured")
            fail = _fail_image_unconfigured()
            return f"{text_out}\n\n{fail}".strip() if text_out else fail
        spec, api_key = resolved
        _emit(f"[{log_prefix}] Media finalize: calling image model {spec.id}")
        try:
            result = generate_image_for_model(spec, prompt, api_key=api_key)
            result = persist_generated_image(result, filename_stem="deliverable")
        except Exception as exc:
            _emit(f"[{log_prefix}] Media finalize: image error {exc}")
            fail = _fail_image_error(exc)
            return f"{text_out}\n\n{fail}".strip() if text_out else fail
        local = str(result.get("local_media_path") or "").strip()
        if local and local not in files_changed:
            files_changed.append(local)
        media_md = format_image_reply(result)
        return f"{text_out}\n\n{media_md}".strip() if text_out else media_md

    if needs_video and not _already_has_video(files_changed, chat_messages):
        from src.video_router import (
            format_video_reply,
            generate_video_for_model,
            persist_generated_video,
            resolve_configured_video_model,
        )

        resolved = resolve_configured_video_model()
        if resolved is None:
            _emit(f"[{log_prefix}] Media finalize: video model not configured")
            fail = _fail_video_unconfigured()
            return f"{text_out}\n\n{fail}".strip() if text_out else fail
        spec, api_key = resolved
        _emit(f"[{log_prefix}] Media finalize: calling video model {spec.id}")
        try:
            result = generate_video_for_model(spec, prompt, api_key=api_key)
            result = persist_generated_video(result)
        except Exception as exc:
            _emit(f"[{log_prefix}] Media finalize: video error {exc}")
            fail = _fail_video_error(exc)
            return f"{text_out}\n\n{fail}".strip() if text_out else fail
        local = str(result.get("local_media_path") or "").strip()
        if local and local not in files_changed:
            files_changed.append(local)
        media_md = format_video_reply(result)
        return f"{text_out}\n\n{media_md}".strip() if text_out else media_md

    return output
