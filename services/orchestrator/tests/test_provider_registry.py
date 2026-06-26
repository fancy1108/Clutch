"""Tests for provider_registry."""

from __future__ import annotations

from src.provider_registry import resolve_provider_spec
from src.runtime_strategy import RuntimeStrategy


def test_claude_is_shell_exec() -> None:
    spec = resolve_provider_spec("claude-cli")
    assert spec.runtime_strategy == RuntimeStrategy.SHELL_EXEC


def test_ollama_is_http_daemon() -> None:
    spec = resolve_provider_spec("ollama-cli")
    assert spec.runtime_strategy == RuntimeStrategy.HTTP_DAEMON
