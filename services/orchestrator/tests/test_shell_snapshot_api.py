"""API tests for shell snapshot endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app


def test_shell_snapshot_upsert_and_get(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("src.session_snapshot.snapshot_dir", lambda: tmp_path)
    client = TestClient(app)

    put = client.put(
        "/api/shell-snapshots/run-api-1",
        json={"task_summary": "Resume login fix", "open_todos": ["add test"]},
    )
    assert put.status_code == 200
    body = put.json()
    assert body["task_summary"] == "Resume login fix"

    got = client.get("/api/shell-snapshots/run-api-1")
    assert got.status_code == 200
    assert got.json()["open_todos"] == ["add test"]

    missing = client.get("/api/shell-snapshots/missing")
    assert missing.status_code == 404
