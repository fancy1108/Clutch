"""Tests for hybrid concurrency rejections (HRT-08)."""

from __future__ import annotations

import pytest

from src.engine_router import EngineResult
from src.hybrid_concurrency import HybridPlainChatRejected, hybrid_rejection_for_exception
from src.runtime_registry import try_shell_exec_hybrid
from src.shell_session import ShellSessionBusyError, ShellSessionPoolFullError


def test_hybrid_rejection_for_pool_full() -> None:
    rejection = hybrid_rejection_for_exception(
        ShellSessionPoolFullError("ShellSession pool full (8); all sessions busy")
    )
    assert rejection is not None
    assert rejection.code == "pool_full"


def test_try_shell_exec_hybrid_does_not_fallback_on_pool_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")

    def hybrid() -> EngineResult:
        raise ShellSessionPoolFullError("pool full")

    def legacy() -> EngineResult:
        raise AssertionError("legacy must not run on pool full")

    with pytest.raises(HybridPlainChatRejected) as exc_info:
        try_shell_exec_hybrid(
            agent_type="claude-cli",
            source="plain_chat",
            run_id="run-pool",
            workspace_path="/tmp",
            provider_spec=None,
            hybrid_route=hybrid,
            legacy_route=legacy,
            logs=[],
            on_log=None,
            emit_log=lambda *_args: None,
        )
    assert exc_info.value.code == "pool_full"


def test_try_shell_exec_hybrid_does_not_fallback_on_session_busy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")

    def hybrid() -> EngineResult:
        raise ShellSessionBusyError("ShellSession run-a is busy")

    with pytest.raises(HybridPlainChatRejected) as exc_info:
        try_shell_exec_hybrid(
            agent_type="claude-cli",
            source="plain_chat",
            run_id="run-busy",
            workspace_path="/tmp",
            provider_spec=None,
            hybrid_route=hybrid,
            legacy_route=lambda: EngineResult(engine="Legacy", output="x", logs=[]),
            logs=[],
            on_log=None,
            emit_log=lambda *_args: None,
        )
    assert exc_info.value.code == "session_busy"
