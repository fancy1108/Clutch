"""Persist and list workflow run history (M2-07)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_HISTORY_DIR = Path(os.environ.get("CLUTCH_RUN_HISTORY_DIR", "/tmp/clutch-runs"))
_HISTORY_FILE = _HISTORY_DIR / "history.json"
_MAX_RECORDS = 200


def _load_records() -> list[dict[str, Any]]:
    if not _HISTORY_FILE.exists():
        return []
    return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))


def _save_records(records: list[dict[str, Any]]) -> None:
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(
        json.dumps(records[:_MAX_RECORDS], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def append_run_record(record: dict[str, Any]) -> dict[str, Any]:
    records = _load_records()
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


def list_runs() -> list[dict[str, Any]]:
    return _load_records()
