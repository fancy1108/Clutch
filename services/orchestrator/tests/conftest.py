"""Shared pytest fixtures — isolate module-level run/workspace state."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_orchestrator_globals(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.main import _run_sessions, _run_states
    from src.workspace import clear_workspace_for_tests

    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path))
    clear_workspace_for_tests()
    _run_states.clear()
    _run_sessions.clear()
    yield
    clear_workspace_for_tests()
    _run_states.clear()
    _run_sessions.clear()
