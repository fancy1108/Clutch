"""D26 — background job failure monitor lines in Chat."""

from __future__ import annotations

from src.bg_jobs_monitor import format_bg_job_monitor_message


def test_format_bg_job_monitor_failed() -> None:
    text = format_bg_job_monitor_message(
        {
            "id": "bg_abcd1234",
            "status": "failed",
            "title": "sleep 1 && false",
            "command": "sleep 1 && false",
        }
    )
    assert text == "[Monitor] Background job failed: sleep 1 && false"


def test_format_bg_job_monitor_done() -> None:
    text = format_bg_job_monitor_message(
        {"id": "bg_done", "status": "done", "title": "echo ok"}
    )
    assert text == "[Monitor] Background job finished: echo ok"


def test_format_bg_job_monitor_ignores_running() -> None:
    assert format_bg_job_monitor_message({"id": "bg_x", "status": "running"}) is None
