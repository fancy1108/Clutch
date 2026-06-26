"""Tests for session_snapshot."""

from __future__ import annotations

from src.session_snapshot import SessionSnapshot, format_handoff_prefix, load_snapshot, save_snapshot


def test_save_load_snapshot(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("src.session_snapshot.snapshot_dir", lambda: tmp_path)
    snap = SessionSnapshot(
        run_id="run-1",
        workspace_path="/proj",
        cwd="/proj/src",
        task_summary="Fix login bug",
        open_todos=["add test"],
    )
    save_snapshot(snap)
    loaded = load_snapshot("run-1")
    assert loaded is not None
    assert loaded.task_summary == "Fix login bug"
    assert loaded.open_todos == ["add test"]


def test_format_handoff_prefix() -> None:
    snap = SessionSnapshot(
        run_id="r",
        workspace_path="/p",
        cwd="/p",
        task_summary="Continue refactor",
        open_todos=["write tests"],
    )
    text = format_handoff_prefix(snap)
    assert "Continue refactor" in text
    assert "write tests" in text
