from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_start_run_returns_run_id() -> None:
    response = client.post(
        "/api/runs/start",
        json={"workflow_id": "video-production", "instruction": "smoke test"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"].startswith("run_")
    assert body["status"] == "running"


def test_stop_run_marks_failed() -> None:
    start = client.post("/api/runs/start", json={"workflow_id": "video-production"})
    run_id = start.json()["run_id"]

    response = client.post(f"/api/runs/{run_id}/stop")
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
