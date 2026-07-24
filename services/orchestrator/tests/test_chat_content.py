"""Tests for chat image marker parsing."""

from __future__ import annotations

from src.chat_content import extract_image_data_urls, user_message_content_for_llm
from src.chat_runner import _history_for_llm

_DATA_URL = "data:image/png;base64,abc123"


def test_extract_image_data_urls() -> None:
    text = f"[image: {_DATA_URL}]\n这个图片写了什么"
    plain, urls = extract_image_data_urls(text)
    assert plain == "这个图片写了什么"
    assert urls == [_DATA_URL]


def test_user_message_content_for_llm_with_vision() -> None:
    text = f"[image: {_DATA_URL}]\n描述图片"
    content = user_message_content_for_llm(text, vision_enabled=True)
    assert isinstance(content, list)
    assert content[0] == {"type": "text", "text": "描述图片"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == _DATA_URL


def test_user_message_content_for_llm_without_vision_uses_analysis(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "src.design.image_analysis.image_analysis_prompt_fragment_for_chat",
        lambda _url: "Visible text (OCR): Hello.",
    )
    text = f"[image: {_DATA_URL}]\n描述图片"
    content = user_message_content_for_llm(text, vision_enabled=False)
    assert isinstance(content, str)
    assert "local image analysis" in content
    assert "Visible text (OCR): Hello." in content
    assert "描述图片" in content
    assert "JSON spec" not in content


def test_looks_like_vision_api_error() -> None:
    from src.chat_content import looks_like_vision_api_error

    assert looks_like_vision_api_error(RuntimeError("LLM API error 400: invalid image_url"))
    assert looks_like_vision_api_error("cannot process image input")
    assert not looks_like_vision_api_error(RuntimeError("connection timed out"))


def test_history_for_llm_preserves_multimodal_when_vision_enabled() -> None:
    text = f"[image: {_DATA_URL}]\n描述图片"
    history = _history_for_llm(
        [{"agent": "User", "text": text}],
        vision_enabled=True,
    )
    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert isinstance(history[0]["content"], list)
    assert history[0]["content"][1]["type"] == "image_url"


def test_history_for_llm_flattens_when_vision_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.design.image_analysis.image_analysis_prompt_fragment_for_chat",
        lambda _url: "OCR hint",
    )
    text = f"[image: {_DATA_URL}]\n描述图片"
    history = _history_for_llm(
        [{"agent": "User", "text": text}],
        vision_enabled=False,
    )
    assert len(history) == 1
    assert isinstance(history[0]["content"], str)
    assert "OCR hint" in history[0]["content"]
