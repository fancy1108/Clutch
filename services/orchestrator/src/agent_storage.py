"""Agent configuration persistence (M4-02)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

AGENTS_ENV = "CLUTCH_AGENTS_DIR"


def agents_dir() -> Path:
    override = os.environ.get(AGENTS_ENV)
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "clutch" / "agents"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "clutch" / "agents"
    return Path.home() / ".local" / "share" / "clutch" / "agents"


def _ensure_dir() -> Path:
    path = agents_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _agents_file() -> Path:
    return _ensure_dir() / "agents.json"


def list_agents() -> list[dict[str, Any]]:
    path = _agents_file()
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_agents(agents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = _agents_file()
    path.write_text(json.dumps(agents, indent=2, ensure_ascii=False), encoding="utf-8")
    return agents
