from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_validate_builtin_workflow_by_id() -> None:
    response = client.post(
        "/api/workflows/validate",
        json={"workflow_id": "video-production"},
    )
    assert response.status_code == 200
    assert response.json() == {"valid": True, "workflow_id": "video-production"}


def test_validate_workflow_body() -> None:
    response = client.post(
        "/api/workflows/validate",
        json={
            "workflow": {
                "id": "smoke",
                "name": "Smoke",
                "version": 1,
                "nodes": [
                    {
                        "id": "end",
                        "type": "end",
                        "data": {"label": "完成"},
                    }
                ],
                "edges": [{"id": "e1", "source": "start", "target": "end"}],
            }
        },
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_validate_returns_chinese_errors_for_invalid_workflow() -> None:
    response = client.post(
        "/api/workflows/validate",
        json={"workflow": {"id": "bad"}},
    )
    assert response.status_code == 422
    body = response.json()["detail"]
    assert "Schema" in body["message"]
    assert body["errors"]


def test_start_run_rejects_unknown_workflow() -> None:
    response = client.post(
        "/api/runs/start",
        json={"workflow_id": "missing-workflow"},
    )
    assert response.status_code == 422
    assert "未找到工作流模板" in response.json()["detail"]["message"]
