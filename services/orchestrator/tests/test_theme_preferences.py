"""P2-03 — theme preference persistence."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.preferences_storage import DEFAULT_THEME_ID, load_preferences, preferences_dir

client = TestClient(app)


@pytest.fixture
def preferences_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "preferences"
    monkeypatch.setenv("CLUTCH_PREFERENCES_DIR", str(target))
    return target


def test_default_theme_when_missing(preferences_data_dir: Path) -> None:
    response = client.get("/api/preferences/theme")
    assert response.status_code == 200
    assert response.json()["active_theme_id"] == DEFAULT_THEME_ID
    assert preferences_dir() == preferences_data_dir


def test_save_and_load_theme(preferences_data_dir: Path) -> None:
    save = client.post("/api/preferences/theme", json={"theme_id": "nordic-frost"})
    assert save.status_code == 200
    assert save.json()["active_theme_id"] == "nordic-frost"
    assert load_preferences()["active_theme_id"] == "nordic-frost"

    reload = client.get("/api/preferences/theme")
    assert reload.json()["active_theme_id"] == "nordic-frost"


def test_rejects_unknown_theme(preferences_data_dir: Path) -> None:
    response = client.post("/api/preferences/theme", json={"theme_id": "neon-hacker"})
    assert response.status_code == 400
