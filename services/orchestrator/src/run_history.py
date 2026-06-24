"""Persist project-bound chat / workflow sessions (M2-07)."""

from __future__ import annotations

import json
import os
import sys
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
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "clutch" / "sessions"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "clutch" / "sessions"
    return Path.home() / ".local" / "share" / "clutch" / "sessions"


def _history_file() -> Path:
    return _history_dir() / "history.json"


def _load_records() -> list[dict[str, Any]]:
    path = _history_file()
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_records(records: list[dict[str, Any]]) -> None:
    directory = _history_dir()
    directory.mkdir(parents=True, exist_ok=True)
    directory.joinpath("history.json").write_text(
        json.dumps(records[:_MAX_RECORDS], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def append_run_record(record: dict[str, Any]) -> dict[str, Any]:
    return upsert_session(record)


def upsert_session(record: dict[str, Any]) -> dict[str, Any]:
    records = _load_records()
    run_id = record.get("run_id")
    for index, existing in enumerate(records):
        if existing.get("run_id") == run_id:
            updated = {**existing, **record}
            records[index] = updated
            _save_records(records)
            return updated
    records.insert(0, record)
    _save_records(records)
    return record


def update_run_record(run_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    records = _load_records()
    for index, record in enumerate(records):
        if record.get("run_id") == run_id:
            updated = {**record, **patch}
            records[index] = updated
            _save_records(records)
            return updated
    return None


def list_runs(*, workspace_id: str | None = None) -> list[dict[str, Any]]:
    records = _load_records()
    if workspace_id is None:
        return records
    return [record for record in records if record.get("workspace_id") == workspace_id]


def delete_session(run_id: str) -> None:
    records = _load_records()
    records = [r for r in records if r.get("run_id") != run_id]
    _save_records(records)
