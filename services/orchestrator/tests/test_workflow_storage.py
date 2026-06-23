"""M1-09 — user workflow persistence API tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.workflow_storage import (
    delete_user_workflow,
    get_template,
    get_user_workflow,
    list_templates,
    list_user_workflows,
    resolve_workflow,
    save_user_workflow,
    user_workflows_dir,
)
from src.workflow_validator import workflows_dir

client = TestClient(app)

MINIMAL_WORKFLOW = {
    "id": "user-smoke",
    "name": "User Smoke",
    "version": 1,
    "nodes": [{"id": "end", "type": "end", "data": {"label": "完成"}}],
    "edges": [{"id": "e1", "source": "start", "target": "end"}],
}


@pytest.fixture
def user_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    workflows = tmp_path / "user-workflows"
    monkeypatch.setenv("CLUTCH_USER_WORKFLOWS_DIR", str(workflows))
    return workflows


def test_templates_read_from_repo_workflows_dir() -> None:
    templates = list_templates()
    assert "video-production" in templates
    template = get_template("video-production")
    assert template["id"] == "video-production"
    assert workflows_dir().joinpath("video-production.json").is_file()


def test_user_crud_uses_configured_data_dir(user_dir: Path) -> None:
    assert user_workflows_dir() == user_dir
    assert list_user_workflows() == []

    save_user_workflow(MINIMAL_WORKFLOW)
    assert list_user_workflows() == ["user-smoke"]
    assert (user_dir / "user-smoke.json").is_file()

    loaded = get_user_workflow("user-smoke")
    assert loaded["name"] == "User Smoke"

    delete_user_workflow("user-smoke")
    assert list_user_workflows() == []


def test_user_workflow_overrides_template(user_dir: Path) -> None:
    custom = {
        **MINIMAL_WORKFLOW,
        "id": "video-production",
        "name": "Custom Video Production",
    }
    save_user_workflow(custom)

    workflow, source = resolve_workflow("video-production")
    assert source == "user"
    assert workflow["name"] == "Custom Video Production"


def test_api_list_and_crud_user_workflows(user_dir: Path) -> None:
    list_resp = client.get("/api/workflows/templates")
    assert list_resp.status_code == 200
    assert "video-production" in list_resp.json()["workflow_ids"]

    create_resp = client.post("/api/workflows/user", json={"workflow": MINIMAL_WORKFLOW})
    assert create_resp.status_code == 200
    assert create_resp.json()["workflow_id"] == "user-smoke"

    get_resp = client.get("/api/workflows/user/user-smoke")
    assert get_resp.status_code == 200
    assert get_resp.json()["workflow"]["name"] == "User Smoke"

    delete_resp = client.delete("/api/workflows/user/user-smoke")
    assert delete_resp.status_code == 200
    assert client.get("/api/workflows/user/user-smoke").status_code == 422


def test_template_endpoint_is_read_only(user_dir: Path) -> None:
    get_resp = client.get("/api/workflows/templates/video-production")
    assert get_resp.status_code == 200
    assert get_resp.json()["source"] == "template"

    delete_resp = client.delete("/api/workflows/user/video-production")
    assert delete_resp.status_code == 422
    assert "未找到用户工作流" in delete_resp.json()["detail"]["message"]
    assert not (user_dir / "video-production.json").exists()
