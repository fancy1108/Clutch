"""Repository group CRUD — P2-05."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.main import app


def test_repository_group_crud(tmp_path: Path) -> None:
    client = TestClient(app)
    project = tmp_path / "demo"
    project.mkdir()

    add_ws = client.post("/api/workspaces", json={"path": str(project)})
    assert add_ws.status_code == 200
    workspace_id = add_ws.json()["id"]

    listed = client.get("/api/repository-groups")
    assert listed.status_code == 200
    assert listed.json()["groups"] == []

    created = client.post("/api/repository-groups", json={"name": "Side Projects"})
    assert created.status_code == 200
    group = created.json()
    assert group["name"] == "Side Projects"
    assert group["collapsed"] is False
    group_id = group["id"]

    updated = client.patch(
        f"/api/repository-groups/{group_id}",
        json={"collapsed": True, "workspace_ids": [workspace_id]},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["collapsed"] is True
    assert body["workspace_ids"] == [workspace_id]

    groups = client.get("/api/repository-groups").json()["groups"]
    assert len(groups) == 1
    assert groups[0]["id"] == group_id

    deleted = client.delete(f"/api/repository-groups/{group_id}")
    assert deleted.status_code == 200
    assert client.get("/api/repository-groups").json()["groups"] == []


def test_repository_group_rejects_empty_name() -> None:
    client = TestClient(app)
    response = client.post("/api/repository-groups", json={"name": "   "})
    assert response.status_code == 400
