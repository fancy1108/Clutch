"""D34 — foreground shell transfer to bg_jobs."""

from __future__ import annotations

import json
import sys
import tempfile
import time

from src.bg_jobs import bind_bg_job_context, get_job, list_jobs, release_bg_job_context
from src.builtin_tools import execute_builtin_tool
from src.foreground_shell import (
    bind_foreground_context,
    get_foreground,
    release_foreground_context,
    start_foreground,
    transfer_to_background,
    wait_foreground,
)

_BG_DIR = tempfile.gettempdir()
if sys.platform == "win32":
    _FG_LONG = "timeout /t 30 /nobreak >nul && echo FG_DONE"
    _FG_LONG_PLAIN = "timeout /t 30 /nobreak >nul"
    _BUILTIN_LONG = "timeout /t 30 /nobreak >nul && echo builtin-fg"
else:
    _FG_LONG = "sleep 30 && echo FG_DONE"
    _FG_LONG_PLAIN = "sleep 30"
    _BUILTIN_LONG = "sleep 30 && echo builtin-fg"


def test_transfer_running_foreground_to_bg() -> None:
    run_id = "run_test_d34_transfer"
    proc = start_foreground(run_id, _FG_LONG, _BG_DIR)
    assert proc.command
    assert get_foreground(run_id) is not None

    # Transfer while still running
    job = transfer_to_background(run_id)
    assert job is not None
    assert job["id"].startswith("bg_")
    assert job["status"] == "running"
    assert get_foreground(run_id) is None

    jobs = list_jobs(run_id)
    assert any(item["id"] == job["id"] for item in jobs)

    from src.bg_jobs import kill_job

    kill_job(run_id, job["id"])


def test_wait_returns_transferred_flag() -> None:
    from threading import Thread

    run_id = "run_test_d34_wait"
    start_foreground(run_id, _FG_LONG_PLAIN, _BG_DIR)
    outcomes: list[tuple[str, bool, int | None]] = []

    def waiter() -> None:
        outcomes.append(wait_foreground(run_id, timeout_sec=5.0))

    thread = Thread(target=waiter, daemon=True)
    thread.start()
    time.sleep(0.2)
    transfer_to_background(run_id)
    thread.join(timeout=3)
    assert outcomes
    output, transferred, exit_code = outcomes[0]
    assert transferred
    assert exit_code is None


def test_builtin_foreground_with_transfer(tmp_path, monkeypatch) -> None:
    run_id = "run_test_d34_builtin"
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    ws = tmp_path / "ws"
    ws.mkdir()
    workspace_mod.add_workspace(str(ws))

    fg_token = bind_foreground_context({"run_id": run_id})
    bg_token = bind_bg_job_context({"run_id": run_id})
    try:
        import contextvars
        from threading import Thread

        result_holder: list[str] = []
        ctx = contextvars.copy_context()

        def run_tool() -> None:
            result_holder.append(
                execute_builtin_tool(
                    "run_terminal_cmd",
                    {"command": _BUILTIN_LONG, "timeout_sec": 60},
                )
            )

        thread = Thread(target=lambda: ctx.run(run_tool), daemon=True)
        thread.start()
        deadline = time.time() + 3
        while time.time() < deadline and get_foreground(run_id) is None:
            time.sleep(0.05)
        assert get_foreground(run_id) is not None
        job = transfer_to_background(run_id)
        assert job is not None
        thread.join(timeout=5)
        assert result_holder
        payload = json.loads(result_holder[0])
        assert payload.get("transferred_to_background") is True
    finally:
        release_bg_job_context(bg_token)
        release_foreground_context(fg_token)
