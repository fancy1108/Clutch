"""D26 — background job failure monitor lines in Chat."""

from __future__ import annotations

from src.bg_jobs_monitor import format_bg_job_monitor_message
from src.chat_runner import _chat_message


def test_monitor_message_seals_bg_job_card() -> None:
    job = {
        "id": "bg_seal1",
        "status": "done",
        "title": "echo ok",
        "command": "echo ok",
        "output": "ok\n",
    }
    msg = _chat_message(
        "Supervisor",
        format_bg_job_monitor_message(job) or "",
        bg_job=job,
    )
    assert msg["bgJob"]["id"] == "bg_seal1"
    assert msg["bgJob"]["status"] == "done"
    assert "finished" in msg["text"]


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
