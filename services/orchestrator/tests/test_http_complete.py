"""HTTP chat completion parsing tests."""

from __future__ import annotations

import json
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
            base_url="https://api.deepseek.com/v1",
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
