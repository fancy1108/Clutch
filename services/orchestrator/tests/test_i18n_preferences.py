"""P2-04 — language preference persistence."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.preferences_storage import load_preferences, preferences_dir, save_theme

client = TestClient(app)


@pytest.fixture
def preferences_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "preferences"
    monkeypatch.setenv("CLUTCH_PREFERENCES_DIR", str(target))
    return target


def test_save_language_persists_alongside_theme(preferences_data_dir: Path) -> None:
    save_theme("amber-warm")
    response = client.post("/api/preferences/language", json={"language": "zh"})
    assert response.status_code == 200
    body = response.json()
    assert body["active_language"] == "zh"
    assert body["active_theme_id"] == "amber-warm"
    assert load_preferences() == body
    assert preferences_dir() == preferences_data_dir


def test_get_language_defaults_to_en(preferences_data_dir: Path) -> None:
    response = client.get("/api/preferences/language")
    assert response.status_code == 200
    assert response.json()["active_language"] == "en"


def test_rejects_invalid_language(preferences_data_dir: Path) -> None:
    response = client.post("/api/preferences/language", json={"language": "fr"})
    assert response.status_code == 400
