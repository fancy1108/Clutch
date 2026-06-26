"""Tests for the local Ollama adapter."""

from __future__ import annotations

import json
from io import BytesIO
import pytest

from src.adapters.ollama_adapter import (
    chat_ollama,
    get_ollama_models,
    model_supports_tool_calling,
    ollama_model_supports_tools,
    pick_best_ollama_model,
)
from src.llm.router import ModelSpec

class MockHTTPResponse:
    def __init__(self, data: bytes, code: int = 200):
        self.data = data
        self.code = code

    def read(self) -> bytes:
        return self.data

    def decode(self, *args, **kwargs) -> str:
        return self.data.decode(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def test_pick_best_ollama_model() -> None:
    # Prioritizes qwen3.6
    models = ["qwen2.5vl:7b", "qwen3.6:35b", "llama3:latest"]
    assert pick_best_ollama_model(models) == "qwen3.6:35b"

    # Prioritizes qwen2.5-coder
    models = ["qwen2.5vl:7b", "qwen2.5-coder:7b", "llama3:latest"]
    assert pick_best_ollama_model(models) == "qwen2.5-coder:7b"

    # Prioritizes llama3 if qwen3.6 and qwen2.5-coder are absent
    models = ["qwen2.5vl:7b", "llama3:latest", "other:latest"]
    assert pick_best_ollama_model(models) == "llama3:latest"

    # Falls back to first if nothing matches priority list
    models = ["some-model:latest", "another-model:latest"]
    assert pick_best_ollama_model(models) == "some-model:latest"

    # Raises RuntimeError on empty models
    with pytest.raises(RuntimeError, match="No models found in Ollama"):
        pick_best_ollama_model([])


def test_get_ollama_models(monkeypatch) -> None:
    called_url = None

    def mock_urlopen(req, timeout=None):
        nonlocal called_url
        if isinstance(req, str):
            called_url = req
        else:
            called_url = req.get_full_url()
        mock_data = {
            "models": [
                {"name": "qwen3.6:35b"},
                {"name": "qwen2.5vl:7b"},
            ]
        }
        return MockHTTPResponse(json.dumps(mock_data).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    models = get_ollama_models()
    assert models == ["qwen3.6:35b", "qwen2.5vl:7b"]
    assert called_url == "http://localhost:11434/api/tags"


def test_ollama_model_supports_tools(monkeypatch) -> None:
    mock_data = {
        "models": [
            {"name": "qwen3.6:35b", "capabilities": ["vision", "completion", "tools"]},
            {"name": "qwen2.5vl:7b", "capabilities": ["vision", "completion"]},
        ]
    }

    def mock_urlopen(req, timeout=None):
        return MockHTTPResponse(json.dumps(mock_data).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    assert ollama_model_supports_tools("qwen3.6:35b") is True
    assert ollama_model_supports_tools("qwen2.5vl:7b") is False
    assert model_supports_tool_calling(
        ModelSpec(
            id="qwen2.5vl-7b",
            name="Qwen 2.5 VL 7B (Ollama)",
            provider_id="ollama",
            api_model="qwen2.5vl:7b",
            base_url="http://localhost:11434/v1",
        )
    ) is False


def test_ollama_model_supports_vision(monkeypatch) -> None:
    mock_data = {
        "models": [
            {"name": "qwen3.6:35b", "capabilities": ["vision", "completion", "tools"]},
            {"name": "qwen2.5vl:7b", "capabilities": ["vision", "completion"]},
        ]
    }

    def mock_urlopen(req, timeout=None):
        return MockHTTPResponse(json.dumps(mock_data).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    from src.adapters.ollama_adapter import model_supports_vision, ollama_model_supports_vision

    assert ollama_model_supports_vision("qwen2.5vl:7b") is True
    assert model_supports_vision(
        ModelSpec(
            id="qwen2.5vl-7b",
            name="Qwen 2.5 VL 7B (Ollama)",
            provider_id="ollama",
            api_model="qwen2.5vl:7b",
            base_url="http://localhost:11434/v1",
        )
    ) is True


def test_chat_ollama(monkeypatch) -> None:
    tags_called = False
    chat_called = False
    chat_payload = None

    def mock_urlopen(req, timeout=None):
        nonlocal tags_called, chat_called, chat_payload
        url = req if isinstance(req, str) else req.get_full_url()
        if "api/tags" in url:
            tags_called = True
            mock_data = {"models": [{"name": "qwen3.6:35b"}]}
            return MockHTTPResponse(json.dumps(mock_data).encode("utf-8"))
        elif "chat/completions" in url:
            chat_called = True
            chat_payload = json.loads(req.data.decode("utf-8"))
            mock_data = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Hello! I am qwen3.6.",
                        }
                    }
                ]
            }
            return MockHTTPResponse(json.dumps(mock_data).encode("utf-8"))
        raise ValueError(f"Unexpected url call: {url}")

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    logs = []
    model, output = chat_ollama(
        prompt="Who are you?",
        system_prompt="You are helpful.",
        on_log=logs.append,
    )

    assert model == "qwen3.6:35b"
    assert output == "Hello! I am qwen3.6."
    assert tags_called is True
    assert chat_called is True
    assert chat_payload is not None
    assert chat_payload["model"] == "qwen3.6:35b"
    assert chat_payload["messages"] == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Who are you?"},
    ]
    assert any("Discovering local Ollama models..." in log for log in logs)
    assert any("Selected best Ollama model: qwen3.6:35b" in log for log in logs)
