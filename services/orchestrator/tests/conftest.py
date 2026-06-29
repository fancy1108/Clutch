"""Shared pytest fixtures — isolate module-level run/workspace state."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def isolate_orchestrator_globals(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.main import _run_sessions, _run_states
    from src.mcp_pending import _approved_keys, _pending
    from src.workspace import clear_workspace_for_tests
    from src.shell_session import get_shell_session_manager

    def clean_sessions():
        manager = get_shell_session_manager()
        with manager._lock:
            run_ids = list(manager._sessions.keys())
        for run_id in run_ids:
            try:
                manager.release(run_id)
            except Exception:
                pass

    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path))
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("CLUTCH_USE_KEYCHAIN", "0")
    monkeypatch.setenv("CLUTCH_E2E_FAKE_LLM", "1")
    clear_workspace_for_tests()
    clean_sessions()
    _run_states.clear()
    _run_sessions.clear()
    _pending.clear()
    _approved_keys.clear()
    yield
    clear_workspace_for_tests()
    clean_sessions()
    _run_states.clear()
    _run_sessions.clear()
    _pending.clear()
    _approved_keys.clear()


@pytest.fixture(autouse=True)
def mock_route_engine_for_workflow_tests(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("real_route_engine"):
        return

    def fake_route_engine(
        agent_name: str,
        prompt: str,
        system_prompt: str | None = None,
        history: list[dict[str, str]] | None = None,
        *,
        source: str = "flow",
        **_kwargs,
    ):
        from src.engine_router import EngineResult

        if os.environ.get("CLUTCH_E2E_FAKE_LLM") == "1" and source in {"plain_chat", "flow_refine"}:
            from src.models_config import get_router

            router = get_router()
            model = router.get_active_model()
            chat_history = list(history or [])
            if not chat_history:
                chat_history = [{"role": "user", "content": prompt}]
            output = router.chat(chat_history)
            return EngineResult(engine=model.name, output=output, logs=["[ROUTER] mocked"])

        return EngineResult(
            engine=f"Mock ({agent_name})",
            output=f"Mocked output for: {prompt[:120]}",
            logs=["[ROUTER] mocked"],
        )

    monkeypatch.setattr("src.engine_router.route_engine", fake_route_engine)
