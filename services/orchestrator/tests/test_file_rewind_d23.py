"""D23 — file rewind shadow snapshots."""

from __future__ import annotations

from src.bg_jobs import bind_bg_job_context, release_bg_job_context
from src.builtin_tools import execute_builtin_tool
from src.file_rewind import rewind_last_writes, snapshot_before_write, snapshot_count


def test_rewind_restores_previous_content(tmp_path, monkeypatch) -> None:
    run_id = "run_test_d23_rewind"
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "storage"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    ws = tmp_path / "ws"
    ws.mkdir()
    workspace_mod.add_workspace(str(ws))

    target = ws / "note.txt"
    target.write_text("original\n", encoding="utf-8")
    snapshot_before_write(run_id, "note.txt")
    target.write_text("agent edit\n", encoding="utf-8")

    restored = rewind_last_writes(run_id, 1)
    assert restored == [{"path": "note.txt", "restored": True}]
    assert target.read_text(encoding="utf-8") == "original\n"
    assert snapshot_count(run_id) == 0


def test_search_replace_snapshots_before_write(tmp_path, monkeypatch) -> None:
    run_id = "run_test_d23_sr"
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "storage"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    ws = tmp_path / "ws"
    ws.mkdir()
    workspace_mod.add_workspace(str(ws))

    target = ws / "a.txt"
    target.write_text("old value\n", encoding="utf-8")

    token = bind_bg_job_context({"run_id": run_id})
    try:
        out = execute_builtin_tool(
            "search_replace",
            {"path": "a.txt", "old_string": "old", "new_string": "new"},
        )
        assert "ok" in out.lower() or '"ok"' in out
        assert target.read_text(encoding="utf-8") == "new value\n"
        assert snapshot_count(run_id) == 1
        rewind_last_writes(run_id, 1)
        assert target.read_text(encoding="utf-8") == "old value\n"
    finally:
        release_bg_job_context(token)
