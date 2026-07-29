"""Tests for OpenCode Zen adapter helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.adapters.opencode_zen_adapter import (
    opencode_model_id,
    resolve_transport,
    validate_opencode_zen_save,
)


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


def test_validate_opencode_zen_save_allows_ssl_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    router = SimpleNamespace(
        _models={
            "opencode-big-pickle": SimpleNamespace(
                provider_id="opencode",
                api_model="big-pickle",
                name="Big Pickle Free (OpenCode Zen)",
            )
        }
    )
    monkeypatch.setattr(
        "src.adapters.opencode_zen_adapter.fetch_opencode_zen_catalog",
        lambda **_: (_ for _ in ()).throw(
            RuntimeError("<urlopen error [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred>")
        ),
    )
    monkeypatch.setattr(
        "src.adapters.opencode_zen_adapter.verify_opencode_zen_api_key",
        lambda *_a, **_k: (_ for _ in ()).throw(
            RuntimeError("SSL: UNEXPECTED_EOF_WHILE_READING")
        ),
    )
    validate_opencode_zen_save("sk-test", "opencode-big-pickle", router)


def test_validate_opencode_zen_save_still_rejects_bad_key(monkeypatch: pytest.MonkeyPatch) -> None:
    router = SimpleNamespace(
        _models={
            "opencode-big-pickle": SimpleNamespace(
                provider_id="opencode",
                api_model="big-pickle",
                name="Big Pickle Free (OpenCode Zen)",
            )
        }
    )
    monkeypatch.setattr(
        "src.adapters.opencode_zen_adapter.fetch_opencode_zen_catalog",
        lambda **_: [{"api_model": "big-pickle"}],
    )
    monkeypatch.setattr(
        "src.adapters.opencode_zen_adapter.verify_opencode_zen_api_key",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("OpenCode Zen API key was rejected.")),
    )
    with pytest.raises(ValueError, match="rejected"):
        validate_opencode_zen_save("bad", "opencode-big-pickle", router)
