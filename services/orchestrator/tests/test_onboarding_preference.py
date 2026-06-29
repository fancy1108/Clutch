"""OSR-14 — onboarding_completed preference."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.preferences_storage import is_onboarding_completed, load_preferences

client = TestClient(app)


@pytest.fixture
def preferences_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "preferences"
    monkeypatch.setenv("CLUTCH_PREFERENCES_DIR", str(target))
    return target


def test_onboarding_defaults_false(preferences_data_dir: Path) -> None:
    prefs = load_preferences()
    assert prefs["onboarding_completed"] == "false"
    assert is_onboarding_completed() is False


def test_complete_onboarding_endpoint(preferences_data_dir: Path) -> None:
    response = client.post("/api/preferences/onboarding-complete")
    assert response.status_code == 200
    assert response.json()["onboarding_completed"] == "true"
    assert is_onboarding_completed() is True


def test_reset_onboarding_endpoint(preferences_data_dir: Path) -> None:
    client.post("/api/preferences/onboarding-complete")
    response = client.post("/api/preferences/onboarding-reset")
    assert response.status_code == 200
    assert response.json()["onboarding_completed"] == "false"
    assert is_onboarding_completed() is False


def test_get_preferences_includes_onboarding(preferences_data_dir: Path) -> None:
    client.post("/api/preferences/onboarding-complete")
    response = client.get("/api/preferences")
    assert response.status_code == 200
    assert response.json()["onboarding_completed"] == "true"
