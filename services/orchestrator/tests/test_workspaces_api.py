"""Multi-workspace API — M2-09."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.main import app


def test_list_empty_workspaces() -> None:
    client = TestClient(app)
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    body = response.json()
    assert body["workspaces"] == []
    assert body["active_id"] is None


def test_add_and_list_workspaces(tmp_path: Path) -> None:
    client = TestClient(app)
    first = tmp_path / "alpha"
    second = tmp_path / "beta"
    first.mkdir()
    second.mkdir()

    add_first = client.post("/api/workspaces", json={"path": str(first)})
    assert add_first.status_code == 200
    first_body = add_first.json()
    assert first_body["name"] == "alpha"

    add_second = client.post("/api/workspaces", json={"path": str(second)})
    assert add_second.status_code == 200

    listed = client.get("/api/workspaces").json()
    assert len(listed["workspaces"]) == 2
    assert listed["active_id"] == add_second.json()["id"]

    activate = client.post(f"/api/workspaces/{first_body['id']}/activate")
    assert activate.status_code == 200
    assert client.get("/api/workspaces").json()["active_id"] == first_body["id"]
    assert client.get("/api/workspace").json()["workspace_path"] == str(first)


def test_add_existing_path_activates_without_duplicate(tmp_path: Path) -> None:
    client = TestClient(app)
    project = tmp_path / "clutch"
    project.mkdir()

    first = client.post("/api/workspaces", json={"path": str(project)}).json()
    other = tmp_path / "other"
    other.mkdir()
    client.post("/api/workspaces", json={"path": str(other)})
    second = client.post("/api/workspaces", json={"path": str(project)}).json()

    assert first["id"] == second["id"]
    listed = client.get("/api/workspaces").json()
    assert len(listed["workspaces"]) == 2
    assert listed["active_id"] == first["id"]
