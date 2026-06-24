"""Persist full ClutchState per run_id for session resume (conversation history)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.run_history import sessions_data_dir
from src.state import ClutchState, initial_state

_SAFE_RUN_ID = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


def _states_dir() -> Path:
    return sessions_data_dir() / "states"


def _state_path(run_id: str) -> Path:
    if not _SAFE_RUN_ID.match(run_id):
        raise ValueError(f"Invalid run_id: {run_id!r}")
    return _states_dir() / f"{run_id}.json"


def _coerce_state(data: dict[str, Any], run_id: str) -> ClutchState:
    workflow_id = str(data.get("workflow_id", ""))
    state = initial_state(run_id, workflow_id)
    for key in state:
        if key in data:
            state[key] = data[key]  # type: ignore[literal-required]
    state["run_id"] = run_id
    return state


def load_run_state(run_id: str) -> ClutchState | None:
    path = _state_path(run_id)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return _coerce_state(data, run_id)


def save_run_state(state: ClutchState) -> None:
    directory = _states_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = _state_path(state["run_id"])
    path.write_text(
        json.dumps(dict(state), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def delete_run_state(run_id: str) -> None:
    try:
        path = _state_path(run_id)
        if path.is_file():
            path.unlink()
    except ValueError:
        pass
