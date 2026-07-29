"""Route video-generation models to the correct adapter backend."""

from __future__ import annotations

import uuid
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from src.llm.router import ModelSpec
from src.preferences_storage import tr

GenerateFn = Callable[..., dict[str, Any]]
VerifyFn = Callable[..., None]

CLUTCH_VIDEO_DIR = ".clutch/generated/videos"
_FETCH_TIMEOUT_SEC = 180.0
_MAX_VIDEO_BYTES = 500 * 1024 * 1024


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


def workspace_media_api_path(relative_path: str) -> str:
    encoded = urllib.parse.quote(relative_path.strip(), safe="")
    return f"/api/workspace/media?path={encoded}"


def persist_generated_video(result: dict[str, Any]) -> dict[str, Any]:
    """Download remote video into workspace so historical sessions keep a stable URL."""
    if str(result.get("local_media_path") or "").strip():
        return result
    video_url = str(result.get("video_url") or result.get("url") or "").strip()
    if not video_url.startswith(("http://", "https://")):
        return result
    try:
        from src.workspace import get_workspace, require_workspace, resolve_allowed_path

        ws = get_workspace()
        if not ws or not str(ws.get("workspace_path", "")).strip():
            return result
        require_workspace()
        video_id = str(result.get("video_id") or "").strip()
        filename = f"{video_id}.mp4" if video_id else f"video_{uuid.uuid4().hex[:12]}.mp4"
        rel = f"{CLUTCH_VIDEO_DIR}/{filename}"
        target = resolve_allowed_path(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(video_url, method="GET")
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT_SEC) as resp:
            payload = resp.read(_MAX_VIDEO_BYTES + 1)
        if not payload or len(payload) > _MAX_VIDEO_BYTES:
            return result
        target.write_bytes(payload)
        return {**result, "local_media_path": rel}
    except Exception:
        return result


def format_video_reply(result: dict[str, Any]) -> str:
    enriched = persist_generated_video(result)
    local_path = str(enriched.get("local_media_path") or "").strip()
    if local_path:
        video_ref = workspace_media_api_path(local_path)
    else:
        video_ref = str(enriched.get("video_url") or enriched.get("url") or "").strip()
    if video_ref:
        label = tr("Generated video", "生成的视频")
        body = f"[video: {video_ref}]\n\n{label}"
        if local_path:
            body += f"\n\n{tr('Saved to', '已保存至')} `{local_path}`"
        return body
    return tr(
        "Video generation completed but no video URL was returned.",
        "视频生成已完成，但未返回视频地址。",
    )


def resolve_configured_video_model() -> tuple[ModelSpec, str] | None:
    """Pick the first video model that has a configured API key."""
    try:
        from src.models_config import get_router

        router = get_router()
        preferred = ("agnes-video-v2.0",)
        ordered = list(router.list_models())
        ordered.sort(key=lambda s: (0 if s.id in preferred else 1, s.id))
        for spec in ordered:
            if getattr(spec, "model_kind", "chat") != "video":
                continue
            key = router.get_api_key(spec.provider_id)
            if key and str(key).strip():
                return spec, str(key).strip()
    except Exception:
        return None
    return None
