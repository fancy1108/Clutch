"""Tests for OpenCode Zen adapter helpers."""

from __future__ import annotations

from src.adapters.opencode_zen_adapter import opencode_model_id, resolve_transport


def test_resolve_transport_openai_compatible() -> None:
    assert resolve_transport("deepseek-v4-flash-free") == "chat_completions"
    assert resolve_transport("big-pickle") == "chat_completions"


def test_resolve_transport_anthropic_messages() -> None:
    assert resolve_transport("claude-sonnet-4-6") == "anthropic_messages"
    assert resolve_transport("qwen3.7-max") == "anthropic_messages"


def test_resolve_transport_unsupported() -> None:
    assert resolve_transport("gpt-5.4") == "unsupported"
    assert resolve_transport("gemini-3-flash") == "unsupported"


def test_opencode_model_id_slug() -> None:
    assert opencode_model_id("deepseek-v4-flash-free") == "opencode-deepseek-v4-flash-free"
