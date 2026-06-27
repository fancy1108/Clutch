"""User avatar preference persistence and endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.preferences_storage import load_preferences, preferences_dir

client = TestClient(app)


@pytest.fixture
def preferences_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "preferences"
    monkeypatch.setenv("CLUTCH_PREFERENCES_DIR", str(target))
    return target


def test_default_avatar_is_empty(preferences_data_dir: Path) -> None:
    response = client.get("/api/preferences")
    assert response.status_code == 200
    assert response.json()["user_avatar"] == ""


def test_save_and_load_avatar(preferences_data_dir: Path) -> None:
    fake_avatar = "data:image/png;base64,iVBORw0KGgoAAAANS"
    response = client.post("/api/preferences/avatar", json={"avatar": fake_avatar})
    assert response.status_code == 200
    body = response.json()
    assert body["user_avatar"] == fake_avatar
    assert load_preferences()["user_avatar"] == fake_avatar
    assert preferences_dir() == preferences_data_dir

    # Reload check
    reload = client.get("/api/preferences")
    assert reload.json()["user_avatar"] == fake_avatar


def test_default_name_is_user(preferences_data_dir: Path) -> None:
    response = client.get("/api/preferences")
    assert response.status_code == 200
    assert response.json()["user_name"] == "User"


def test_save_and_load_name(preferences_data_dir: Path) -> None:
    fake_name = "Fancy User"
    response = client.post("/api/preferences/name", json={"user_name": fake_name})
    assert response.status_code == 200
    body = response.json()
    assert body["user_name"] == fake_name
    assert load_preferences()["user_name"] == fake_name

    # Reload check
    reload = client.get("/api/preferences")
    assert reload.json()["user_name"] == fake_name
