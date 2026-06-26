"""Tests for session_snapshot."""

from __future__ import annotations

from datetime import datetime, timezone

from src.session_snapshot import (
    SessionSnapshot,
    format_handoff_prefix,
    load_snapshot,
    prune_stale_snapshots,
    save_snapshot,
)


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


def test_prune_stale_snapshots(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("src.session_snapshot.snapshot_dir", lambda: tmp_path)
    snap = SessionSnapshot(run_id="old-run", workspace_path="/p", cwd="/p")
    path = save_snapshot(snap)
    old_ts = datetime.now(timezone.utc).timestamp() - (40 * 86400)
    import os

    os.utime(path, (old_ts, old_ts))
    removed = prune_stale_snapshots(max_age_days=30)
    assert removed == ["old-run"]
    assert load_snapshot("old-run") is None


def test_prune_disabled_when_zero_days(tmp_path, monkeypatch) -> None:
    from src.session_snapshot import prune_stale_snapshots

    monkeypatch.setattr("src.session_snapshot.snapshot_dir", lambda: tmp_path)
    save_snapshot(SessionSnapshot(run_id="keep", workspace_path="/p", cwd="/p"))
    assert prune_stale_snapshots(max_age_days=0) == []
    assert load_snapshot("keep") is not None
