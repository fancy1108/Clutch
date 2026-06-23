"""Run history persistence tests — M2-07."""

from __future__ import annotations

import pytest

from src import run_history


@pytest.fixture(autouse=True)
def isolated_history_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path))
    monkeypatch.setattr(run_history, "_HISTORY_DIR", tmp_path)
    monkeypatch.setattr(run_history, "_HISTORY_FILE", tmp_path / "history.json")


def test_append_and_list_run_records() -> None:
    run_history.append_run_record(
        {
            "run_id": "run_abc123",
            "workflow_id": "video-production",
            "status": "passed",
            "started_at": "2026-06-23T10:00:00+00:00",
        }
    )

    records = run_history.list_runs()
    assert len(records) == 1
    assert records[0]["run_id"] == "run_abc123"
    assert records[0]["workflow_id"] == "video-production"


def test_update_run_record_status() -> None:
    run_history.append_run_record(
        {
            "run_id": "run_update_me",
            "workflow_id": "video-production",
            "status": "running",
            "started_at": "2026-06-23T10:00:00+00:00",
        }
    )

    updated = run_history.update_run_record("run_update_me", {"status": "failed"})
    assert updated is not None
    assert updated["status"] == "failed"
    assert run_history.list_runs()[0]["status"] == "failed"


def test_history_api_returns_records(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from src.main import app

    run_history.append_run_record(
        {
            "run_id": "run_api",
            "workflow_id": "video-production",
            "status": "passed",
            "started_at": "2026-06-23T11:00:00+00:00",
        }
    )

    response = TestClient(app).get("/api/runs/history")
    assert response.status_code == 200
    body = response.json()
    assert body["runs"][0]["run_id"] == "run_api"
