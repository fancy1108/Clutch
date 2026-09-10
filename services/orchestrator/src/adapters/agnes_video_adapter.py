"""Agnes Video 2.5 Flash — async text/image-to-video via apihub.agnes-ai.com."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any, Literal

from src.preferences_storage import tr

AGNES_VIDEO_API_BASE = "https://apihub.agnes-ai.com"
AGNES_VIDEO_MODEL = "agnes-video-2.5-flash"
DEFAULT_SECONDS = "5"
DEFAULT_SIZE = "720P"
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_POLL_INTERVAL_SEC = 5.0
DEFAULT_POLL_TIMEOUT_SEC = 900.0
CREATE_TIMEOUT_SEC = 180.0
POLL_REQUEST_TIMEOUT_SEC = 60.0

RUNNING_STATES = frozenset({"queued", "in_progress", "processing", "submitted", "pending"})
DONE_STATES = frozenset({"completed", "succeeded", "success"})
FAILED_STATES = frozenset({"failed", "cancelled", "canceled", "error"})

TEST_PROMPT = "A minimal red circle on a plain white background, subtle zoom, 2 seconds"
AGNES_VIDEO_TRANSLATE_MODEL = "agnes-3.0-flash"


def _contains_cjk(text: str) -> bool:
    for char in text:
        if "\u4e00" <= char <= "\u9fff":
            return True
        if "\u3040" <= char <= "\u30ff" or "\uac00" <= char <= "\ud7af":
            return True
    return False


def _extract_chat_text(result: object) -> str:
    if isinstance(result, dict):
        content = result.get("content")
        if content is not None:
            return str(content).strip()
    return str(result).strip()


def prepare_video_prompt(
    prompt: str,
    *,
    api_key: str,
    base_url: str = AGNES_VIDEO_API_BASE,
    on_log: Callable[[str], None] | None = None,
    translate_model: str = AGNES_VIDEO_TRANSLATE_MODEL,
) -> str:
    """Normalize user text and translate CJK prompts to English for Agnes video."""
    trimmed = prompt.strip()
    if not trimmed:
        return trimmed
    if on_log:
        on_log(f"[AGNES VIDEO] user prompt={trimmed[:300]!r}")
    if not _contains_cjk(trimmed):
        if on_log:
            on_log(f"[AGNES VIDEO] api prompt={trimmed[:300]!r}")
        return trimmed
    try:
        from src.llm.http_complete import http_chat_complete

        chat_base = f"{_api_root(base_url)}/v1"
        result = http_chat_complete(
            provider_id="openai",
            base_url=chat_base,
            api_model=translate_model,
            api_key=api_key,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Translate the following video-generation prompt to concise English. "
                        "Output ONLY the English prompt, no quotes or explanation:\n\n"
                        + trimmed
                    ),
                }
            ],
            timeout_sec=45,
            max_tokens=128,
        )
        translated = _extract_chat_text(result)
        if translated:
            if on_log:
                on_log(f"[AGNES VIDEO] api prompt (zh→en)={translated[:300]!r}")
            return translated
    except Exception as exc:
        if on_log:
            on_log(f"[AGNES VIDEO] translation skipped: {exc}")
    if on_log:
        on_log(f"[AGNES VIDEO] api prompt (original)={trimmed[:300]!r}")
    return trimmed


def _api_root(base_url: str = AGNES_VIDEO_API_BASE) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return root[: -len("/v1")]
    return root


def _videos_url(base_url: str = AGNES_VIDEO_API_BASE) -> str:
    return f"{_api_root(base_url)}/v1/videos"


def _models_url(base_url: str = AGNES_VIDEO_API_BASE) -> str:
    return f"{_api_root(base_url)}/v1/models"


def _video_rate_limit_message() -> str:
    return tr(
        "Agnes Video allows 1 generation per minute. Wait about 60 seconds, then try again "
        "(the Models Test button no longer starts a render).",
        "Agnes 视频接口限制为每分钟 1 次。请等待约 60 秒后再试（模型「测试」按钮已不再发起渲染）。",
    )


def _http_error_message(exc: urllib.error.HTTPError, detail: str) -> str:
    if exc.code == 429:
        lower = detail.lower()
        if "video" in lower or "rate limit" in lower:
            return _video_rate_limit_message()
        return tr(
            "Rate limit reached — wait a moment and try again.",
            "请求过于频繁，请稍后再试。",
        )
    if exc.code in {401, 403}:
        return tr(
            "API key was rejected — check your Agnes key in Models Config.",
            "API Key 被拒绝，请在模型配置中检查 Agnes Key。",
        )
    return f"Agnes Video API error {exc.code}: {detail}"


def _video_status_url(
    video_id: str,
    base_url: str = AGNES_VIDEO_API_BASE,
    model: str = AGNES_VIDEO_MODEL,
) -> str:
    query = urllib.parse.urlencode({"video_id": video_id, "model_name": model})
    return f"{_api_root(base_url)}/agnesapi?{query}"


def _request_json(
    method: str,
    url: str,
    *,
    api_key: str,
    payload: dict[str, Any] | None = None,
    timeout_sec: float = CREATE_TIMEOUT_SEC,
) -> dict[str, Any]:
    data = None
    headers = {"Authorization": f"Bearer {api_key.strip()}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(_http_error_message(exc, detail)) from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to reach Agnes Video API: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Agnes Video API returned malformed JSON")
    if parsed.get("error"):
        err = parsed["error"]
        message = err.get("message") if isinstance(err, dict) else str(err)
        raise RuntimeError(message or "Agnes Video API returned an error")
    return parsed


def _extract_video_id(response: dict[str, Any]) -> str:
    """Use video_id only — do not poll with task_id (Agnes docs)."""
    for container in (response, response.get("data")):
        if not isinstance(container, dict):
            continue
        value = container.get("video_id")
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise RuntimeError("Agnes Video API response missing video_id")


def _extract_status(response: dict[str, Any]) -> str:
    value = response.get("status")
    if isinstance(value, str):
        return value.lower()
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("status"), str):
        return data["status"].lower()
    return "unknown"


def _extract_video_url(response: dict[str, Any]) -> str | None:
    # Agnes V2.0 puts the playable URL in remixed_from_video_id when status=completed.
    for key in ("video_url", "url", "remixed_from_video_id"):
        value = response.get(key)
        if isinstance(value, str) and value.strip().startswith(("http://", "https://")):
            return value.strip()
    for nested_key in ("data", "output", "result"):
        nested = response.get(nested_key)
        if isinstance(nested, dict):
            found = _extract_video_url(nested)
            if found:
                return found
    return None


def _normalize_seconds(value: str | int | float | None) -> str:
    raw = DEFAULT_SECONDS if value is None else str(value).strip()
    try:
        seconds = int(float(raw))
    except ValueError as exc:
        raise ValueError("seconds must be an integer from 4 to 12") from exc
    if seconds < 4 or seconds > 12:
        raise ValueError("seconds must be an integer from 4 to 12")
    return str(seconds)


def _resolve_video_mode(mode: str | None, image_urls: list[str]) -> Literal["text", "keyframe", "reference"]:
    if mode in {"keyframe", "keyframes"}:
        return "keyframe"
    if mode in {"reference", "multi-image"}:
        return "reference"
    if image_urls:
        return "reference"
    return "text"


def create_agnes_video_task(
    prompt: str,
    *,
    api_key: str,
    model: str = AGNES_VIDEO_MODEL,
    seconds: str | int = DEFAULT_SECONDS,
    size: str = DEFAULT_SIZE,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    input_images: list[str] | None = None,
    mode: str | None = None,
    base_url: str = AGNES_VIDEO_API_BASE,
    timeout_sec: float = CREATE_TIMEOUT_SEC,
) -> dict[str, Any]:
    trimmed = prompt.strip()
    if not trimmed:
        raise ValueError("prompt is required")
    if not api_key.strip():
        raise ValueError("api_key is required")
    if size.strip().upper() != DEFAULT_SIZE:
        raise ValueError("size must be 720P")

    image_urls = [url.strip() for url in (input_images or []) if url.strip()]
    resolved_mode = _resolve_video_mode(mode, image_urls)
    if resolved_mode == "keyframe" and not image_urls:
        raise ValueError("keyframe mode requires at least one input image")
    if resolved_mode == "reference" and not image_urls:
        raise ValueError("reference mode requires at least one input image")
    if len(image_urls) > 5:
        raise ValueError("images length must not exceed 5")

    body: dict[str, Any] = {
        "model": model,
        "prompt": trimmed,
        "seconds": _normalize_seconds(seconds),
        "mode": resolved_mode,
        "size": DEFAULT_SIZE,
        "aspect_ratio": aspect_ratio or DEFAULT_ASPECT_RATIO,
    }
    if resolved_mode == "keyframe":
        body["first_frame"] = image_urls[0]
        if len(image_urls) > 1:
            body["last_frame"] = image_urls[1]
    elif resolved_mode == "reference":
        body["images"] = image_urls

    return _request_json(
        "POST",
        _videos_url(base_url),
        api_key=api_key,
        payload=body,
        timeout_sec=timeout_sec,
    )


def poll_agnes_video(
    video_id: str,
    *,
    api_key: str,
    model: str = AGNES_VIDEO_MODEL,
    base_url: str = AGNES_VIDEO_API_BASE,
    poll_interval_sec: float = DEFAULT_POLL_INTERVAL_SEC,
    poll_timeout_sec: float = DEFAULT_POLL_TIMEOUT_SEC,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Poll by video_id + model_name (recommended). Do not use task_id — it queues much longer."""
    deadline = time.monotonic() + poll_timeout_sec
    last_response: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        last_response = _request_json(
            "GET",
            _video_status_url(video_id, base_url, model),
            api_key=api_key,
            timeout_sec=POLL_REQUEST_TIMEOUT_SEC,
        )
        status = _extract_status(last_response)
        progress = last_response.get("progress")
        if progress is None and isinstance(last_response.get("data"), dict):
            progress = last_response["data"].get("progress")
        if on_log:
            on_log(f"[AGNES VIDEO] video_id={video_id} status={status} progress={progress}")
        if status in DONE_STATES:
            video_url = _extract_video_url(last_response)
            if not video_url:
                raise RuntimeError("Video completed but no video_url was returned")
            return {**last_response, "video_url": video_url, "video_id": video_id}
        if status in FAILED_STATES:
            raise RuntimeError(f"Video generation failed with status {status!r}")
        if status not in RUNNING_STATES and status != "unknown" and on_log:
            on_log(f"[AGNES VIDEO] Unknown status {status!r}, continuing poll")
        time.sleep(poll_interval_sec)
    raise RuntimeError(f"Timed out waiting for video {video_id!r}")


def generate_agnes_video(
    prompt: str,
    *,
    api_key: str,
    model: str = AGNES_VIDEO_MODEL,
    seconds: str | int = DEFAULT_SECONDS,
    size: str = DEFAULT_SIZE,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    input_images: list[str] | None = None,
    mode: str | None = None,
    base_url: str = AGNES_VIDEO_API_BASE,
    poll_interval_sec: float = DEFAULT_POLL_INTERVAL_SEC,
    poll_timeout_sec: float = DEFAULT_POLL_TIMEOUT_SEC,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Create a video task, poll by video_id, return {video_url, video_id, ...}."""
    api_prompt = prepare_video_prompt(
        prompt,
        api_key=api_key,
        base_url=base_url,
        on_log=on_log,
    )
    duration = _normalize_seconds(seconds)
    if on_log:
        on_log(f"[AGNES VIDEO] Creating task model={model} seconds={duration} size={DEFAULT_SIZE}")
    created = create_agnes_video_task(
        api_prompt,
        api_key=api_key,
        model=model,
        seconds=duration,
        size=size,
        aspect_ratio=aspect_ratio,
        input_images=input_images,
        mode=mode,
        base_url=base_url,
    )
    video_id = _extract_video_id(created)
    if on_log:
        on_log(f"[AGNES VIDEO] Task created video_id={video_id}")
    return poll_agnes_video(
        video_id,
        api_key=api_key,
        model=model,
        base_url=base_url,
        poll_interval_sec=poll_interval_sec,
        poll_timeout_sec=poll_timeout_sec,
        on_log=on_log,
    )


def verify_agnes_video_connection(
    *,
    api_key: str,
    model: str = AGNES_VIDEO_MODEL,
    base_url: str = AGNES_VIDEO_API_BASE,
) -> None:
    """Verify credentials without creating a video task (video API allows ~1 req/min)."""
    del model  # same Agnes key as chat/image; kept for call-site parity
    if not api_key.strip():
        raise ValueError("api_key is required")
    req = urllib.request.Request(
        _models_url(base_url),
        headers={"Authorization": f"Bearer {api_key.strip()}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(_http_error_message(exc, detail)) from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to reach Agnes API: {exc}") from exc
    if isinstance(parsed, dict) and parsed.get("error"):
        err = parsed["error"]
        message = err.get("message") if isinstance(err, dict) else str(err)
        raise RuntimeError(message or "Agnes API returned an error")
