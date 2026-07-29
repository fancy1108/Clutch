"""D23 — session fork from message index."""

from __future__ import annotations

from src.run_history import list_runs
from src.run_state_store import load_run_state, save_run_state
from src.session_fork import fork_session
from src.state import initial_state


def test_fork_copies_messages_and_preserves_parent(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "storage"))

    parent_id = "run_parent_fork"
    parent = initial_state(parent_id, "")
    parent["messages"] = [
        {"id": "m1", "agent": "User", "text": "hello"},
        {"id": "m2", "agent": "Clutch Agent", "text": "hi"},
        {"id": "m3", "agent": "User", "text": "fork here"},
    ]
    save_run_state(parent)

    result = fork_session(parent_id, 1)
    child_id = result["run_id"]
    assert child_id != parent_id
    assert result["parent_run_id"] == parent_id
    assert result["message_index"] == 1

    child = load_run_state(child_id)
    assert child is not None
    assert len(child["messages"]) == 2
    assert child["messages"][-1]["text"] == "hi"

    parent_after = load_run_state(parent_id)
    assert parent_after is not None
    assert len(parent_after["messages"]) == 3

    records = list_runs()
    child_record = next(r for r in records if r.get("run_id") == child_id)
    assert child_record.get("parent_run_id") == parent_id
