"""D22 — usage stats persisted on session history records."""

from __future__ import annotations

import pytest

from src import run_history
from src.chat_runner import _touch_session, _usage_fields_from_state
from src.state import initial_state


@pytest.fixture(autouse=True)
def isolated_history_dir(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path))
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "storage"))


def test_usage_fields_from_state_prefers_run_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    state = initial_state("run_usage", "")
    state["session_tokens"] = 900
    state["run_stats"] = {"tool_steps": 4, "session_tokens": 900}
    fields = _usage_fields_from_state(state)
    assert fields == {"session_tokens": 900, "tool_steps": 4}


def test_touch_session_persists_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.run_state_store import save_run_state

    run_id = "run_touch_usage"
    state = initial_state(run_id, "")
    state["messages"] = [{"id": "m1", "role": "user", "content": "hi"}]
    state["session_tokens"] = 1200
    state["run_stats"] = {"tool_steps": 2, "session_tokens": 1200}
    save_run_state(state)

    monkeypatch.setattr(
        "src.chat_runner._session_workspace_fields",
        lambda: {"workspace_id": "ws1", "workspace_name": "Demo"},
    )
    monkeypatch.setattr("src.chat_runner._get_or_create_run", lambda rid: state)

    _touch_session(run_id, status="idle")
    records = run_history.list_runs()
    assert len(records) == 1
    assert records[0]["session_tokens"] == 1200
    assert records[0]["tool_steps"] == 2
