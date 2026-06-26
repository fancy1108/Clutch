"""Plain chat with image-generation models (Agnes Image)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.llm.router import BUILTIN_MODELS
from src.main import _llm_chat_reply, app, initial_state

client = TestClient(app)


class _FakeImageRouter:
    _models = BUILTIN_MODELS

    def get_active_model(self):
        return BUILTIN_MODELS["agnes-image-2.1-flash"]

    @property
    def active_model_id(self) -> str:
        return "agnes-image-2.1-flash"

    def resolve_for_model(self, model_id: str | None = None):
        return BUILTIN_MODELS["agnes-image-2.1-flash"], "sk-test"

    def _require_api_key(self, _provider_id: str, api_key: str | None) -> str:
        return api_key or ""


@pytest.mark.asyncio
async def test_llm_chat_reply_image_model_rejects_vision_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeImageRouter())

    data_url = "data:image/png;base64,abc"
    (
        _label,
        engine,
        reply_text,
        _logs,
        _session_id,
        _pause,
        _files,
    ) = await _llm_chat_reply(
        initial_state("run_img_vision"),
        f"[image: {data_url}]\n这个图片说了什么",
    )

    assert engine == "Agnes Image 2.1 Flash"
    assert "cannot read uploaded" in reply_text.lower()


@pytest.mark.asyncio
async def test_llm_chat_reply_uses_image_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeImageRouter())

    with patch(
        "src.image_router.generate_image_for_model",
        return_value={"url": "https://example.com/white-dog.png"},
    ) as mocked:
        (
            _label,
            engine,
            reply_text,
            _logs,
            _session_id,
            _pause,
            _files,
        ) = await _llm_chat_reply(initial_state("run_img"), "生成一张白色的狗的照片")

    mocked.assert_called_once()
    assert engine == "Agnes Image 2.1 Flash"
    assert "https://example.com/white-dog.png" in reply_text


def test_ws_plain_chat_image_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: False)
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeImageRouter())

    with patch(
        "src.image_router.generate_image_for_model",
        return_value={"url": "https://example.com/white-dog.png"},
    ):
        with client.websocket_connect("/ws/runs/run_image_chat") as ws:
            ws.receive_json()
            ws.send_json({"text": "生成一张白色的狗的照片"})
            events = []
            while True:
                event = ws.receive_json()
                events.append(event)
                if (
                    event.get("event") == "state_patch"
                    and event.get("data", {}).get("patch", {}).get("status") == "idle"
                ):
                    break

    reply = next(
        event["data"]["message"]
        for event in events
        if event.get("event") == "message"
        and event["data"]["message"]["agent"] == "Clutch Agent"
    )
    assert "https://example.com/white-dog.png" in reply["text"]
    assert reply.get("runtimeEngine") == "Agnes Image 2.1 Flash"
    assert not any(
        event.get("event") == "log" and "[CHAT] Starting MCP ReAct" in event["data"].get("message", "")
        for event in events
    )
