"""D11 — background shell jobs."""

from __future__ import annotations

import json
import time

from src.bg_jobs import (
    bind_bg_job_context,
    get_job,
    kill_job,
    list_jobs,
    release_bg_job_context,
    start_job,
)
from src.builtin_tools import execute_builtin_tool


def test_start_sleep_wait_done() -> None:
    run_id = "run_test_bg_done"
    job = start_job(run_id, "sleep 1 && echo done-bg", "/tmp")
    assert job["status"] == "running"
    assert job["id"].startswith("bg_")

    deadline = time.time() + 5
    final = None
    while time.time() < deadline:
        current = get_job(run_id, job["id"])
        assert current is not None
        if current["status"] != "running":
            final = current
            break
        time.sleep(0.1)
    assert final is not None
    assert final["status"] == "done"
    assert "done-bg" in final.get("output", "")


def test_kill_while_running() -> None:
    run_id = "run_test_bg_kill"
    job = start_job(run_id, "sleep 30", "/tmp")
    assert job["status"] == "running"
    killed = kill_job(run_id, job["id"])
    assert killed is not None
    assert killed["status"] == "killed"
    current = get_job(run_id, job["id"])
    assert current is not None
    assert current["status"] == "killed"


def test_list_jobs() -> None:
    run_id = "run_test_bg_list"
    first = start_job(run_id, "sleep 5", "/tmp")
    second = start_job(run_id, "sleep 5", "/tmp")
    jobs = list_jobs(run_id)
    ids = {item["id"] for item in jobs}
    assert first["id"] in ids
    assert second["id"] in ids
    kill_job(run_id, first["id"])
    kill_job(run_id, second["id"])


def test_builtin_background_requires_context() -> None:
    out = execute_builtin_tool("run_terminal_cmd", {"command": "sleep 1", "background": True})
    assert out.startswith("Error executing tool:")


def test_builtin_background_and_list_kill(tmp_path, monkeypatch) -> None:
    run_id = "run_test_bg_builtin"
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    ws = tmp_path / "ws"
    ws.mkdir()
    workspace_mod.add_workspace(str(ws))

    token = bind_bg_job_context({"run_id": run_id})
    try:
        raw = execute_builtin_tool(
            "run_terminal_cmd",
            {"command": "sleep 2 && echo builtin-bg", "background": True},
        )
        assert not raw.startswith("Error"), raw
        payload = json.loads(raw)
        assert payload["ok"] is True
        assert payload["status"] == "running"
        job_id = payload["job_id"]

        listed = json.loads(execute_builtin_tool("list_background_jobs", {}))
        assert any(item["id"] == job_id for item in listed)

        killed = json.loads(
            execute_builtin_tool("kill_background_job", {"job_id": job_id})
        )
        assert killed["status"] == "killed"
    finally:
        release_bg_job_context(token)
