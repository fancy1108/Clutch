"""Persist project-bound chat / workflow sessions (M2-07)."""

from __future__ import annotations

import json
import os
import sys
import fcntl
from pathlib import Path
from typing import Any

_HISTORY_ENV = "CLUTCH_RUN_HISTORY_DIR"
_MAX_RECORDS = 200


def sessions_data_dir() -> Path:
    """Root directory for session metadata (history.json) and per-run state files."""
    return _history_dir()


def _history_dir() -> Path:
    override = os.environ.get(_HISTORY_ENV)
    if override:
        return Path(override)
    from src.storage_helper import get_storage_dir
    return get_storage_dir() / "sessions"


def _history_file() -> Path:
    return _history_dir() / "history.json"


def _history_path_ready() -> Path:
    directory = _history_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory.joinpath("history.json")
    if not path.is_file():
        path.write_text("[]\n", encoding="utf-8")
    return path


def _mutate_records(mutator) -> Any:
    path = _history_path_ready()
    with path.open("r+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        raw = handle.read().strip()
        records: list[dict[str, Any]] = json.loads(raw) if raw else []
        result = mutator(records)
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(records[:_MAX_RECORDS], indent=2, ensure_ascii=False))
        handle.write("\n")
        return result


def _load_records() -> list[dict[str, Any]]:
    path = _history_file()
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
        raw = handle.read().strip()
        if not raw:
            return []
        return json.loads(raw)


def _save_records(records: list[dict[str, Any]]) -> None:
    path = _history_path_ready()
    with path.open("w", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps(records[:_MAX_RECORDS], indent=2, ensure_ascii=False))
        handle.write("\n")


def append_run_record(record: dict[str, Any]) -> dict[str, Any]:
    return upsert_session(record)


def upsert_session(record: dict[str, Any]) -> dict[str, Any]:
    run_id = record.get("run_id")

    def mutate(records: list[dict[str, Any]]) -> dict[str, Any]:
        for index, existing in enumerate(records):
            if existing.get("run_id") == run_id:
                updated = {**existing, **record}
                records[index] = updated
                return updated
        records.insert(0, record)
        return record

    return _mutate_records(mutate)


def update_run_record(run_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    def mutate(records: list[dict[str, Any]]) -> dict[str, Any] | None:
        for index, record in enumerate(records):
            if record.get("run_id") == run_id:
                updated = {**record, **patch}
                records[index] = updated
                return updated
        return None

    return _mutate_records(mutate)


def list_runs(*, workspace_id: str | None = None) -> list[dict[str, Any]]:
    records = _load_records()
    if workspace_id is None:
        return records
    return [record for record in records if record.get("workspace_id") == workspace_id]


def delete_session(run_id: str) -> None:
    records = _load_records()
    records = [r for r in records if r.get("run_id") != run_id]
    _save_records(records)
