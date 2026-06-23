from fastapi.testclient import TestClient

from src.main import _run_states, app

client = TestClient(app)


def test_start_run_returns_run_id() -> None:
    response = client.post(
        "/api/runs/start",
        json={"workflow_id": "video-production", "instruction": "smoke test"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"].startswith("run_")
    assert body["status"] == "passed"


def test_start_run_advances_active_node_via_compiled_graph() -> None:
    response = client.post(
        "/api/runs/start",
        json={"workflow_id": "video-production", "instruction": "graph smoke"},
    )
    assert response.status_code == 200
    run_id = response.json()["run_id"]

    state = _run_states[run_id]
    assert state["active_node_id"] == "end"
    assert state["active_agent"] == "Orchestrator"
    assert state["status"] == "passed"


def test_stop_run_marks_failed() -> None:
    start = client.post("/api/runs/start", json={"workflow_id": "video-production"})
    run_id = start.json()["run_id"]

    response = client.post(f"/api/runs/{run_id}/stop")
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
