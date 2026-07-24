"""Tests for chat image marker parsing."""

from __future__ import annotations

import base64
from pathlib import Path

from src import workspace
from src.chat_content import (
    extract_image_data_urls,
    materialize_images_as_file_refs,
    ocr_fallback_prompt_for_engine,
    plain_user_prompt_for_engine,
    user_message_content_for_llm,
)
from src.chat_runner import _history_for_llm
from src.engine_router import _cli_prompt_from_history
from src.workspace_attachments import ATTACHMENTS_REL

_DATA_URL = "data:image/png;base64,abc123"
# Large-ish payload that would blow CLI argv if re-appended raw (regression for Mimo hang).
_FAT_DATA_URL = "data:image/png;base64," + ("A" * 8000)
_PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-png-bytes"
_PNG_DATA_URL = f"data:image/png;base64,{base64.b64encode(_PNG_BYTES).decode('ascii')}"


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


def test_materialize_images_as_file_refs_writes_attachment(tmp_path: Path) -> None:
    workspace.clear_workspace_for_tests()
    workspace.set_workspace(str(tmp_path))
    text = f"[image: {_PNG_DATA_URL}]\n@Mimo 图片里面有什么"
    prompt = materialize_images_as_file_refs(text)
    assert "data:image" not in prompt
    assert "[file: .clutch/attachments/" in prompt
    assert "@.clutch/attachments/" in prompt
    assert "图片里面有什么" in prompt
    rel = prompt.split("[file: ", 1)[1].split("]", 1)[0]
    assert (tmp_path / rel).is_file()
    assert (tmp_path / rel).read_bytes() == _PNG_BYTES


def test_history_paths_delivery_for_cli(tmp_path: Path) -> None:
    workspace.clear_workspace_for_tests()
    workspace.set_workspace(str(tmp_path))
    text = f"[image: {_PNG_DATA_URL}]\n@Mimo 图片里面有什么"
    history = _history_for_llm(
        [{"agent": "User", "text": text}],
        image_delivery="paths",
    )
    assert len(history) == 1
    content = history[0]["content"]
    assert isinstance(content, str)
    assert "data:image" not in content
    assert ATTACHMENTS_REL in content
    assert "OCR" not in content


def test_cli_prompt_uses_paths_not_raw_data_url(tmp_path: Path) -> None:
    workspace.clear_workspace_for_tests()
    workspace.set_workspace(str(tmp_path))
    raw = f"[image: {_PNG_DATA_URL}]\n@Mimo 图片里面有什么"
    history = _history_for_llm(
        [{"agent": "User", "text": raw}],
        image_delivery="paths",
    )
    engine_prompt = materialize_images_as_file_refs(raw)
    # Bug path: raw data URL would be re-appended
    buggy = _cli_prompt_from_history(raw, history)
    assert "data:image" in buggy

    fixed = _cli_prompt_from_history(engine_prompt, history)
    assert "data:image" not in fixed
    assert "@.clutch/attachments/" in fixed
    assert "图片里面有什么" in fixed


def test_ocr_fallback_prompt_for_engine_strips_data_url(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.design.image_analysis.image_analysis_prompt_fragment_for_chat",
        lambda _url: "Visible text (OCR): Hello.",
    )
    text = f"[image: {_FAT_DATA_URL}]\n@Mimo 图片里面有什么"
    prompt = ocr_fallback_prompt_for_engine(text)
    assert prompt == plain_user_prompt_for_engine(text)
    assert "data:image" not in prompt
    assert "Visible text (OCR): Hello." in prompt
