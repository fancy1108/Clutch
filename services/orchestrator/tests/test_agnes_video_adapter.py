"""Agnes Video V2.0 adapter tests."""

from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from src.adapters.agnes_video_adapter import (
    _extract_video_id,
    create_agnes_video_task,
    generate_agnes_video,
    poll_agnes_video,
    prepare_video_prompt,
    verify_agnes_video_connection,
)


def test_extract_video_id_from_top_level() -> None:
    assert _extract_video_id({"video_id": "vid_abc"}) == "vid_abc"


def test_extract_video_id_rejects_task_id_only() -> None:
    with pytest.raises(RuntimeError, match="missing video_id"):
        _extract_video_id({"id": "task_123", "task_id": "task_123"})


def test_extract_video_id_from_data() -> None:
    assert _extract_video_id({"data": {"video_id": "vid_nested"}}) == "vid_nested"


def test_extract_video_url_from_remixed_from_video_id() -> None:
    from src.adapters.agnes_video_adapter import _extract_video_url

    payload = {
        "video_id": "video_abc",
        "status": "completed",
        "progress": 100,
        "remixed_from_video_id": "https://storage.googleapis.com/agnes-aigc/videos/out.mp4",
    }
    assert _extract_video_url(payload) == "https://storage.googleapis.com/agnes-aigc/videos/out.mp4"


def test_create_agnes_video_task_posts_payload() -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req, timeout=0):  # noqa: ANN001
        captured["url"] = req.full_url
        captured["method"] = req.method
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse({"video_id": "vid_test", "status": "queued"})

    with patch("urllib.request.urlopen", fake_urlopen):
        result = create_agnes_video_task("A cat on the beach", api_key="sk-test")

    assert result["video_id"] == "vid_test"
    assert captured["method"] == "POST"
    assert "https://apihub.agnes-ai.com/v1/videos" in str(captured["url"])
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "agnes-video-v2.0"
    assert body["prompt"] == "A cat on the beach"


def test_poll_agnes_video_uses_video_id_endpoint() -> None:
    calls: list[str] = []
    responses = [
        {"status": "processing", "progress": 10},
        {
            "status": "completed",
            "progress": 100,
            "remixed_from_video_id": "https://cdn.example.com/out.mp4",
        },
    ]

    def fake_urlopen(req, timeout=0):  # noqa: ANN001
        calls.append(req.full_url)
        return _FakeResponse(responses[len(calls) - 1])

    with patch("urllib.request.urlopen", fake_urlopen), patch("time.sleep"):
        result = poll_agnes_video("vid_abc", api_key="sk-test", poll_interval_sec=0.01)

    assert result["video_url"] == "https://cdn.example.com/out.mp4"
    assert all("video_id=vid_abc" in url for url in calls)
    assert "/agnesapi?" in calls[0]


def test_prepare_video_prompt_passthrough_english() -> None:
    logs: list[str] = []
    assert prepare_video_prompt("A dog dancing", api_key="sk-test", on_log=logs.append) == "A dog dancing"
    assert any("user prompt='A dog dancing'" in line for line in logs)
    assert any("api prompt='A dog dancing'" in line for line in logs)


def test_prepare_video_prompt_translates_chinese() -> None:
    logs: list[str] = []

    with patch(
        "src.llm.http_complete.http_chat_complete",
        return_value={"content": "A dog dancing happily"},
    ):
        result = prepare_video_prompt("生成一个狗跳舞的视频", api_key="sk-test", on_log=logs.append)

    assert result == "A dog dancing happily"
    assert any("user prompt='生成一个狗跳舞的视频'" in line for line in logs)
    assert any("api prompt (zh→en)='A dog dancing happily'" in line for line in logs)


def test_generate_agnes_video_sends_translated_prompt() -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req, timeout=0):  # noqa: ANN001
        if req.method == "POST":
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse({"video_id": "vid_gen"})
        return _FakeResponse({"status": "completed", "remixed_from_video_id": "https://cdn.example.com/v.mp4"})

    with patch("urllib.request.urlopen", fake_urlopen), patch("time.sleep"), patch(
        "src.llm.http_complete.http_chat_complete",
        return_value={"content": "A dog dancing"},
    ):
        generate_agnes_video("狗跳舞", api_key="sk-test", poll_interval_sec=0.01)

    body = captured["body"]
    assert isinstance(body, dict)
    assert body["prompt"] == "A dog dancing"


def test_generate_agnes_video_create_and_poll() -> None:
    seen: list[str] = []

    def fake_urlopen(req, timeout=0):  # noqa: ANN001
        if req.method == "POST":
            seen.append("create")
            return _FakeResponse({"video_id": "vid_gen"})
        seen.append("poll")
        return _FakeResponse({"status": "completed", "remixed_from_video_id": "https://cdn.example.com/v.mp4"})

    with patch("urllib.request.urlopen", fake_urlopen), patch("time.sleep"):
        result = generate_agnes_video("prompt", api_key="sk-test", poll_interval_sec=0.01)

    assert result["video_url"] == "https://cdn.example.com/v.mp4"
    assert seen == ["create", "poll"]


def test_verify_agnes_video_connection_uses_models_list() -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req, timeout=0):  # noqa: ANN001
        captured["url"] = req.full_url
        captured["method"] = req.method
        return _FakeResponse({"data": []})

    with patch("urllib.request.urlopen", fake_urlopen):
        verify_agnes_video_connection(api_key="sk-test")

    assert captured["method"] == "GET"
    assert str(captured["url"]).endswith("/v1/models")


def test_http_error_429_video_rate_limit() -> None:
    body = json.dumps(
        {"error": {"message": "video generation rate limit exceeded: allows 1 requests per 1 minute(s)"}}
    ).encode("utf-8")

    def fake_urlopen(req, timeout=0):  # noqa: ANN001
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", hdrs=None, fp=io.BytesIO(body))

    with patch("urllib.request.urlopen", fake_urlopen):
        with pytest.raises(RuntimeError, match="1 generation per minute|每分钟"):
            create_agnes_video_task("A cat dancing", api_key="sk-test")


def test_create_requires_prompt() -> None:
    with pytest.raises(ValueError, match="prompt"):
        create_agnes_video_task("  ", api_key="sk-test")


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None
