"""HTTP chat completion parsing tests."""

from __future__ import annotations

import json
import urllib.request
from typing import Any
from unittest.mock import MagicMock, patch

from src.llm.http_complete import http_chat_complete


def test_openai_compatible_response_parsing() -> None:
    payload = {"choices": [{"message": {"content": "Hello from model"}}]}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode()
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        text = http_chat_complete(
            provider_id="deepseek",
            base_url="https://api.deepseek.com",
            api_model="deepseek-chat",
            api_key="sk-test",
            messages=[{"role": "user", "content": "hi"}],
        )
    assert text == "Hello from model"


def test_anthropic_response_parsing() -> None:
    payload = {"content": [{"type": "text", "text": "Bonjour"}]}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode()
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        text = http_chat_complete(
            provider_id="anthropic",
            base_url="https://api.anthropic.com/v1",
            api_model="claude-3-7-sonnet-latest",
            api_key="sk-ant",
            messages=[{"role": "user", "content": "salut"}],
        )
    assert text == "Bonjour"


def test_gateway_anthropic_with_tools_uses_openai_transport() -> None:
    """Agnes-style gateways need OpenAI tool schema on /chat/completions."""
    captured: dict[str, Any] = {}

    def fake_urlopen(req: urllib.request.Request, timeout: float = 0) -> MagicMock:
        _ = timeout
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "ok"}}]}
        ).encode()
        mock_resp.__enter__.return_value = mock_resp
        return mock_resp

    tools = [
        {
            "type": "function",
            "function": {
                "name": "srv__read_file",
                "description": "Read a file",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        text = http_chat_complete(
            provider_id="anthropic",
            base_url="https://apihub.agnes-ai.com/v1",
            api_model="agnes-2.0-flash",
            api_key="sk-agnes",
            messages=[{"role": "user", "content": "hi"}],
            tools=tools,
        )
    assert text == "ok"
    assert captured["url"].endswith("/chat/completions")
    assert captured["body"]["tools"][0]["type"] == "function"


def test_openai_tool_roundtrip_normalizes_assistant_and_tool_messages() -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(req: urllib.request.Request, timeout: float = 0) -> MagicMock:
        _ = timeout
        captured["body"] = json.loads(req.data.decode())
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "deleted"}}]}
        ).encode()
        mock_resp.__enter__.return_value = mock_resp
        return mock_resp

    messages = [
        {"role": "user", "content": "delete test.txt"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "local-fs__move_file",
                        "arguments": {"source": "/test.txt", "destination": "/tmp/x"},
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "ok"},
    ]

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        text = http_chat_complete(
            provider_id="anthropic",
            base_url="https://apihub.agnes-ai.com/v1",
            api_model="agnes-2.0-flash",
            api_key="sk-agnes",
            messages=messages,
            tools=[{"type": "function", "function": {"name": "x", "parameters": {}}}],
        )
    assert text == "deleted"
    sent = captured["body"]["messages"]
    assert sent[1]["content"] == ""
    assert sent[1]["tool_calls"][0]["type"] == "function"
    assert sent[1]["tool_calls"][0]["function"]["arguments"] == json.dumps(
        {"source": "/test.txt", "destination": "/tmp/x"}
    )
    assert sent[2]["role"] == "tool"
    assert sent[2]["content"] == "ok"
