"""Tests for runtime_registry dispatch."""

from __future__ import annotations

import pytest

from src.engine_router import EngineResult
from src.runtime_registry import try_shell_exec_hybrid


def test_try_shell_exec_hybrid_uses_hybrid_when_eligible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    logs: list[str] = []

    def hybrid() -> EngineResult:
        return EngineResult(engine="Hybrid", output="ok", logs=[])

    def legacy() -> EngineResult:
        raise AssertionError("legacy should not run")

    result = try_shell_exec_hybrid(
        agent_type="claude-cli",
        source="plain_chat",
        run_id="run-1",
        workspace_path="/tmp",
        provider_spec=None,
        hybrid_route=hybrid,
        legacy_route=legacy,
        logs=logs,
        on_log=None,
        emit_log=lambda _logs, _on, msg: _logs.append(msg),
    )
    assert result.output == "ok"


def test_try_shell_exec_hybrid_falls_back_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")

    def hybrid() -> EngineResult:
        raise RuntimeError("pty died")

    def legacy() -> EngineResult:
        return EngineResult(engine="Legacy", output="fallback", logs=[])

    logs: list[str] = []
    result = try_shell_exec_hybrid(
        agent_type="claude-cli",
        source="plain_chat",
        run_id="run-1",
        workspace_path="/tmp",
        provider_spec=None,
        hybrid_route=hybrid,
        legacy_route=legacy,
        logs=logs,
        on_log=None,
        emit_log=lambda _logs, _on, msg: _logs.append(msg),
    )
    assert result.engine == "Legacy"
    assert any("fallback to legacy" in line for line in logs)


def test_try_shell_exec_hybrid_runs_for_flow_when_eligible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")

    def hybrid() -> EngineResult:
        return EngineResult(engine="Hybrid", output="x", logs=[])

    result = try_shell_exec_hybrid(
        agent_type="claude-cli",
        source="flow",
        run_id="run-1",
        workspace_path="/tmp",
        provider_spec=None,
        hybrid_route=hybrid,
        legacy_route=lambda: EngineResult(engine="Legacy", output="y", logs=[]),
        logs=[],
        on_log=None,
        emit_log=lambda *_args: None,
    )
    assert result.engine == "Hybrid"
