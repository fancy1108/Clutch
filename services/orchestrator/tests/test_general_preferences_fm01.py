"""FM-01 General preferences: default workspace + high-risk stop confirm."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.preferences_storage import load_high_risk_confirm, load_preferences

client = TestClient(app)


@pytest.fixture
def preferences_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("CLUTCH_PREFERENCES_DIR", str(tmp_path / "preferences"))
    return tmp_path / "preferences"


def test_default_workspace_round_trip(preferences_data_dir: Path) -> None:
    assert client.get("/api/preferences/default-workspace").json()["workspace_id"] == ""
    saved = client.post("/api/preferences/default-workspace", json={"workspace_id": "ws_abc"})
    assert saved.status_code == 200
    assert saved.json()["default_workspace_id"] == "ws_abc"
    assert client.get("/api/preferences/default-workspace").json()["workspace_id"] == "ws_abc"
    assert load_preferences()["default_workspace_id"] == "ws_abc"


def test_high_risk_confirm_default_on_and_toggle(preferences_data_dir: Path) -> None:
    assert client.get("/api/preferences/high-risk-confirm").json()["high_risk_confirm"] is True
    assert load_high_risk_confirm() is True
    saved = client.post("/api/preferences/high-risk-confirm", json={"enabled": False})
    assert saved.status_code == 200
    assert saved.json()["high_risk_confirm"] == "false"
    assert client.get("/api/preferences/high-risk-confirm").json()["high_risk_confirm"] is False
