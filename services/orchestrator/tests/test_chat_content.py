"""Tests for chat image marker parsing."""

from __future__ import annotations

from src.chat_content import extract_image_data_urls, user_message_content_for_llm

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


def test_user_message_content_for_llm_without_vision() -> None:
    text = f"[image: {_DATA_URL}]\n描述图片"
    content = user_message_content_for_llm(text, vision_enabled=False)
    assert isinstance(content, str)
    assert "does not support vision" in content
    assert "描述图片" in content
