"""Tests for runtime_config hybrid gating."""

from __future__ import annotations

import os

import pytest

from src.runtime_config import hybrid_eligible, runtime_mode


@pytest.fixture(autouse=True)
def _clear_runtime_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLUTCH_RUNTIME_MODE", raising=False)


def test_runtime_mode_defaults_legacy() -> None:
    assert runtime_mode() == "legacy"


def test_runtime_mode_hybrid_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    assert runtime_mode() == "hybrid"


def test_hybrid_eligible_requires_all_conditions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    assert hybrid_eligible(source="plain_chat", agent_type="claude-cli") is True
    assert hybrid_eligible(source="flow", agent_type="claude-cli") is False
    assert hybrid_eligible(source="plain_chat", agent_type="antigravity-cli") is False


def test_hybrid_eligible_false_when_legacy() -> None:
    assert hybrid_eligible(source="plain_chat", agent_type="claude-cli") is False
