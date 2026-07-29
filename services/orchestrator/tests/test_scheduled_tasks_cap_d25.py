"""Cap-D25 — scheduled / loop tasks."""

from __future__ import annotations

import time

import pytest


@pytest.fixture(autouse=True)
def _isolated_scheduled_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    import src.scheduled_tasks as mod

    mod._loaded = False
    mod._tasks.clear()


def test_create_list_delete_default_off() -> None:
    from src.scheduled_tasks import (
        create_scheduled_task,
        delete_scheduled_task,
        list_scheduled_tasks,
    )

    task = create_scheduled_task(title="ping", prompt="hello", interval_sec=60, enabled=False)
    assert task["enabled"] is False
    rows = list_scheduled_tasks()
    assert len(rows) == 1
    assert delete_scheduled_task(task["id"])
    assert list_scheduled_tasks() == []


def test_create_enabled_requires_confirm_api() -> None:
    from src.scheduled_tasks import create_scheduled_task, confirm_enable_scheduled_task

    task = create_scheduled_task(title="t", prompt="p", interval_sec=60, enabled=False)
    enabled = confirm_enable_scheduled_task(task["id"])
    assert enabled and enabled["enabled"] is True


def test_tick_fires_due_task(monkeypatch) -> None:
    from src.scheduled_tasks import confirm_enable_scheduled_task, create_scheduled_task, tick_scheduled_tasks

    fired: list[dict] = []

    def _notify(event: dict) -> None:
        fired.append(event)

    import src.scheduled_tasks as mod

    mod.set_scheduled_task_notifier(_notify)
    task = create_scheduled_task(title="due", prompt="notify me", interval_sec=30, enabled=False)
    item = confirm_enable_scheduled_task(task["id"])
    assert item
    item["next_fire_at"] = time.time() - 1
    mod._tasks[task["id"]] = item
    out = tick_scheduled_tasks()
    assert out
    assert fired and fired[0]["task_id"] == task["id"]
