"""Cap-D25 — persisted scheduled/loop tasks (extension D25 scheduler, ≠ Hybrid D25)."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from src.preferences_storage import tr
from src.storage_helper import get_storage_dir

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_tasks: dict[str, dict[str, Any]] = {}
_loaded = False
_notifier: Callable[[dict[str, Any]], None] | None = None


@dataclass
class ScheduledTask:
    id: str
    title: str
    prompt: str
    interval_sec: int
    enabled: bool = False
    run_agent_turn: bool = False
    agent_id: str = ""
    workspace_path: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_fired_at: str | None = None
    next_fire_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _storage_path() -> Path:
    return get_storage_dir() / "scheduled_tasks.json"


def _persist() -> None:
    path = _storage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(_tasks.values()), indent=2), encoding="utf-8")


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    path = _storage_path()
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict) and item.get("id"):
                        _tasks[str(item["id"])] = item
        except Exception:
            logger.exception("scheduled_tasks load failed")
    _loaded = True


def set_scheduled_task_notifier(notifier: Callable[[dict[str, Any]], None] | None) -> None:
    global _notifier
    _notifier = notifier


def list_scheduled_tasks() -> list[dict[str, Any]]:
    _ensure_loaded()
    with _lock:
        return sorted(_tasks.values(), key=lambda item: item.get("created_at", ""))


def get_scheduled_task(task_id: str) -> dict[str, Any] | None:
    _ensure_loaded()
    with _lock:
        item = _tasks.get(task_id)
        return dict(item) if item else None


def create_scheduled_task(
    *,
    title: str,
    prompt: str,
    interval_sec: int,
    enabled: bool = False,
    run_agent_turn: bool = False,
    agent_id: str = "",
    workspace_path: str = "",
) -> dict[str, Any]:
    _ensure_loaded()
    if interval_sec < 30:
        raise ValueError(tr("Interval must be at least 30 seconds.", "间隔至少 30 秒。"))
    task = ScheduledTask(
        id=f"sched_{uuid.uuid4().hex[:10]}",
        title=title.strip() or tr("Scheduled task", "定时任务"),
        prompt=prompt.strip(),
        interval_sec=int(interval_sec),
        enabled=bool(enabled),
        run_agent_turn=bool(run_agent_turn),
        agent_id=agent_id.strip(),
        workspace_path=workspace_path.strip(),
    )
    if task.enabled:
        task.next_fire_at = time.time() + task.interval_sec
    with _lock:
        payload = task.to_dict()
        _tasks[task.id] = payload
        _persist()
        return dict(payload)


def delete_scheduled_task(task_id: str) -> bool:
    _ensure_loaded()
    with _lock:
        if task_id not in _tasks:
            return False
        del _tasks[task_id]
        _persist()
        return True


def confirm_enable_scheduled_task(task_id: str) -> dict[str, Any] | None:
    _ensure_loaded()
    with _lock:
        item = _tasks.get(task_id)
        if item is None:
            return None
        item = dict(item)
        item["enabled"] = True
        item["next_fire_at"] = time.time() + int(item.get("interval_sec") or 60)
        _tasks[task_id] = item
        _persist()
        return dict(item)


def _fire_task(item: dict[str, Any]) -> None:
    event = {
        "task_id": item.get("id"),
        "title": item.get("title"),
        "prompt": item.get("prompt"),
        "run_agent_turn": bool(item.get("run_agent_turn")),
        "agent_id": item.get("agent_id") or "",
        "workspace_path": item.get("workspace_path") or "",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if _notifier:
        try:
            _notifier(event)
        except Exception:
            logger.exception("scheduled task notifier failed task_id=%s", item.get("id"))
    if event["run_agent_turn"] and event["prompt"]:
        try:
            from src.headless_agent import run_headless_agent_sync

            run_headless_agent_sync(
                prompt=str(event["prompt"]),
                workspace_path=str(event["workspace_path"] or ""),
                agent_id=str(event["agent_id"] or ""),
            )
        except Exception:
            logger.exception("scheduled agent turn failed task_id=%s", item.get("id"))


def tick_scheduled_tasks() -> list[dict[str, Any]]:
    """Check due tasks; return fired task summaries."""
    _ensure_loaded()
    now = time.time()
    fired: list[dict[str, Any]] = []
    with _lock:
        for task_id, item in list(_tasks.items()):
            if not item.get("enabled"):
                continue
            next_at = item.get("next_fire_at")
            if next_at is None or float(next_at) > now:
                continue
            fired.append(dict(item))
            item = dict(item)
            item["last_fired_at"] = datetime.now(UTC).isoformat()
            item["next_fire_at"] = now + int(item.get("interval_sec") or 60)
            _tasks[task_id] = item
        if fired:
            _persist()
    for item in fired:
        _fire_task(item)
    return fired
