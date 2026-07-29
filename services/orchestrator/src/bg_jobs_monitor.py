"""D26 — Chat-visible background job monitor messages."""

from __future__ import annotations

from typing import Any

_TERMINAL_STATUSES = frozenset({"done", "failed", "killed"})


def format_bg_job_monitor_message(finished: dict[str, Any]) -> str | None:
    """Build a Supervisor Chat line when a background job reaches a terminal state."""
    status = str(finished.get("status") or "").strip().lower()
    if status not in _TERMINAL_STATUSES:
        return None
    cmd = str(finished.get("title") or finished.get("command") or "").strip()[:80]
    job_id = str(finished.get("id") or "job").strip()
    label = cmd or job_id
    if status == "failed":
        return f"[Monitor] Background job failed: {label}"
    if status == "killed":
        return f"[Monitor] Background job stopped: {label}"
    return f"[Monitor] Background job finished: {label}"
