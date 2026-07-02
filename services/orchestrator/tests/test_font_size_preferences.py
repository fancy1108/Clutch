"""Font size preference persistence and endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.preferences_storage import DEFAULT_FONT_SIZE, load_preferences, preferences_dir

client = TestClient(app)


@pytest.fixture
def preferences_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "preferences"
    monkeypatch.setenv("CLUTCH_PREFERENCES_DIR", str(target))
    return target


def test_default_font_size_when_missing(preferences_data_dir: Path) -> None:
    response = client.get("/api/preferences")

    assert response.status_code == 200
    assert response.json()["font_size"] == DEFAULT_FONT_SIZE
    assert preferences_dir() == preferences_data_dir


def test_save_and_load_font_size(preferences_data_dir: Path) -> None:
    response = client.post("/api/preferences/font-size", json={"font_size": "xxlarge"})

    assert response.status_code == 200
    assert response.json()["font_size"] == "xxlarge"
    assert load_preferences()["font_size"] == "xxlarge"

    reload = client.get("/api/preferences")
    assert reload.json()["font_size"] == "xxlarge"


def test_rejects_unknown_font_size(preferences_data_dir: Path) -> None:
    response = client.post("/api/preferences/font-size", json={"font_size": "giant"})

    assert response.status_code == 400
    assert load_preferences()["font_size"] == DEFAULT_FONT_SIZE


def test_legacy_px_font_size_falls_back_to_default(preferences_data_dir: Path) -> None:
    preferences_data_dir.mkdir(parents=True)
    (preferences_data_dir / "preferences.json").write_text(
        json.dumps({"font_size": "14px"}),
        encoding="utf-8",
    )

    response = client.get("/api/preferences")

    assert response.status_code == 200
    assert response.json()["font_size"] == DEFAULT_FONT_SIZE
