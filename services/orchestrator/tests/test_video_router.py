"""Video model router tests."""

from __future__ import annotations

from pathlib import Path

import pytest

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


def test_format_video_reply_uses_workspace_media_when_persisted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    video_bytes = b"\x00\x00\x00\x18ftypmp42"
    rel = ".clutch/generated/videos/vid_test.mp4"

    class FakeResp:
        def read(self, _n: int) -> bytes:
            return video_bytes

        def __enter__(self) -> "FakeResp":
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

    monkeypatch.setattr(
        "src.video_router.urllib.request.urlopen",
        lambda *_a, **_k: FakeResp(),
    )
    monkeypatch.setattr(
        "src.workspace.get_workspace",
        lambda: {"workspace_path": str(tmp_path)},
    )
    monkeypatch.setattr("src.workspace.require_workspace", lambda: tmp_path)

    def fake_resolve_allowed_path(path: str) -> Path:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    monkeypatch.setattr("src.workspace.resolve_allowed_path", fake_resolve_allowed_path)

    text = format_video_reply(
        {"video_url": "https://cdn.example.com/a.mp4", "video_id": "vid_test"},
    )
    assert "[video: /api/workspace/media?path=" in text
    assert rel.replace("/", "%2F") in text or ".clutch" in text
    assert (tmp_path / rel).is_file()
