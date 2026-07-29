"""Persist project-bound chat / workflow sessions (M2-07)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from src.platform_lock import file_lock

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
        with file_lock(handle):
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
        with file_lock(handle, exclusive=False):
            raw = handle.read().strip()
            if not raw:
                return []
            return json.loads(raw)


def _save_records(records: list[dict[str, Any]]) -> None:
    path = _history_path_ready()
    with path.open("w", encoding="utf-8") as handle:
        with file_lock(handle):
            handle.write(json.dumps(records[:_MAX_RECORDS], indent=2, ensure_ascii=False))
            handle.write("\n")


def append_run_record(record: dict[str, Any]) -> dict[str, Any]:
    return upsert_session(record)


def _iso_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def session_activity_at(record: dict[str, Any]) -> str:
    """Most recent activity timestamp for sidebar / history ordering."""
    return str(
        record.get("updated_at")
        or record.get("ended_at")
        or record.get("started_at")
        or ""
    )


def upsert_session(record: dict[str, Any]) -> dict[str, Any]:
    run_id = record.get("run_id")
    # Bump activity so re-chatting an old session floats to the top of the sidebar.
    payload = dict(record)
    if not str(payload.get("updated_at") or "").strip():
        payload["updated_at"] = _iso_now()

    def mutate(records: list[dict[str, Any]]) -> dict[str, Any]:
        for index, existing in enumerate(records):
            if existing.get("run_id") == run_id:
                updated = {**existing, **payload}
                records.pop(index)
                records.insert(0, updated)
                return updated
        records.insert(0, payload)
        return payload

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


_DEFAULT_SESSION_TITLES = frozenset(
    {"New session", "New Chat", "新建会话", "New Design", "新建设计"}
)


def _design_session_has_artifacts(run_id: str) -> bool:
    """True when Design mode left workspace artifacts for this run."""
    try:
        from src.design import service as design_service
        from src.workspace import WorkspaceError

        status = design_service.session_status_for_run(run_id)
        if status in {
            "ready",
            "crafting_spec",
            "generating_ui",
            "iterating",
            "prototype_approved",
            "error",
        }:
            return True
        thumb = design_service.thumbnail_data_url_for_run(run_id)
        return bool(thumb)
    except Exception:
        return False


def _is_default_session_title(title: str) -> bool:
    return (not title) or title in _DEFAULT_SESSION_TITLES


def _should_keep_session_record(record: dict[str, Any], state: dict[str, Any] | None) -> bool:
    from src.session_content import session_has_persistable_content

    if state is not None and session_has_persistable_content(state):
        return True
    status = str(record.get("status") or "").strip().lower()
    if status in {"running", "refining", "awaiting_human"}:
        return True
    mode = str(record.get("mode") or "coding").strip().lower()
    title = str(record.get("title") or "").strip()
    if mode == "design":
        run_id = str(record.get("run_id") or "").strip()
        has_artifacts = bool(run_id and _design_session_has_artifacts(run_id))
        if status in {
            "crafting_spec",
            "generating_ui",
            "iterating",
        }:
            return True
        if has_artifacts:
            return True
        # Empty Design draft: keep temporarily (at most one per workspace via collapse below)
        # so the sidebar can show a welcome row; frontend New Design creates a fresh run_id.
        if _is_default_session_title(title) and status in {
            "",
            "idle",
            "draft",
            "ready",  # false-ready from welcome mount — still treat as empty draft
        }:
            return True
        return bool(title) and not _is_default_session_title(title)
    if title and title not in _DEFAULT_SESSION_TITLES:
        return True
    return False


def _prune_empty_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from src.run_state_store import load_run_state

    kept: list[dict[str, Any]] = []
    changed = False
    for record in records:
        run_id = str(record.get("run_id") or "").strip()
        if not run_id:
            changed = True
            continue
        try:
            state = load_run_state(run_id)
        except (json.JSONDecodeError, OSError, ValueError):
            # State file missing or corrupt — keep the record, don't silently delete
            kept.append(record)
            continue
        if not _should_keep_session_record(record, state):
            # Session has no persistable content but record exists — keep it
            kept.append(record)
            continue
        kept.append(record)

    # At most one empty Design draft (default title, no artifacts) per workspace.
    empty_design_by_ws: dict[str, list[int]] = {}
    for index, record in enumerate(kept):
        mode = str(record.get("mode") or "coding").strip().lower()
        if mode != "design":
            continue
        title = str(record.get("title") or "").strip()
        if not _is_default_session_title(title):
            continue
        run_id = str(record.get("run_id") or "").strip()
        if run_id and _design_session_has_artifacts(run_id):
            continue
        status = str(record.get("status") or "").strip().lower()
        if status not in {"", "idle", "draft", "ready"}:
            continue
        ws = str(record.get("workspace_id") or "")
        empty_design_by_ws.setdefault(ws, []).append(index)

    drop_indexes: set[int] = set()
    for indexes in empty_design_by_ws.values():
        if len(indexes) <= 1:
            continue
        ranked = sorted(
            indexes,
            key=lambda i: str(kept[i].get("started_at") or ""),
            reverse=True,
        )
        drop_indexes.update(ranked[1:])

    if drop_indexes:
        kept = [record for i, record in enumerate(kept) if i not in drop_indexes]

    # Never persist during list — dedup is a view filter, not a deletion
    return kept


def list_runs(
    *,
    workspace_id: str | None = None,
    mode: str | None = None,
) -> list[dict[str, Any]]:
    records = _prune_empty_records(_load_records())
    if workspace_id is not None:
        records = [record for record in records if record.get("workspace_id") == workspace_id]
    if mode is not None:
        wanted = mode.strip().lower()
        if wanted in {"coding", "design"}:
            records = [
                record
                for record in records
                if str(record.get("mode") or "coding").strip().lower() == wanted
            ]
    records.sort(key=session_activity_at, reverse=True)
    return records


def remap_workspace_ids(id_map: dict[str, str]) -> int:
    """Rewrite session workspace_id values after stable-id migration. Returns rows touched."""
    if not id_map:
        return 0

    def mutate(records: list[dict[str, Any]]) -> int:
        touched = 0
        for record in records:
            old = record.get("workspace_id")
            if isinstance(old, str) and old in id_map:
                record["workspace_id"] = id_map[old]
                touched += 1
        return touched

    return int(_mutate_records(mutate) or 0)


def delete_session(run_id: str) -> None:
    records = _load_records()
    records = [r for r in records if r.get("run_id") != run_id]
    _save_records(records)
