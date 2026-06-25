"""Models config API — availability and activation guards."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.llm.http_complete import http_chat_complete
from src.llm.router import LLMProviderRouter
from src.main import app
from src.models_config import serialize_models_config


@pytest.fixture
def models_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config = tmp_path / "models.json"
    monkeypatch.setenv("CLUTCH_MODELS_CONFIG", str(config))
    monkeypatch.setattr("src.credentials.claude_code._CLAUDE_SETTINGS", tmp_path / "no-claude.json")
    router = LLMProviderRouter()
    router._chat = http_chat_complete  # type: ignore[method-assign]
    monkeypatch.setattr("src.models_config.get_router", lambda: router)
    return config


def test_models_mark_unavailable_without_api_key(models_config: Path) -> None:
    client = TestClient(app)
    response = client.get("/api/models/config")
    assert response.status_code == 200
    body = response.json()
    assert all(model["available"] is False for model in body["models"])


def test_connect_provider_enables_model(models_config: Path) -> None:
    client = TestClient(app)
    save = client.post(
        "/api/models/config",
        json={"provider_id": "deepseek", "api_key": "sk-test-deepseek"},
    )
    assert save.status_code == 200

    listed = client.get("/api/models/config").json()
    deepseek = next(m for m in listed["models"] if m["id"] == "deepseek-v4pro")
    assert deepseek["available"] is True


def test_activate_rejects_unavailable_model(models_config: Path) -> None:
    client = TestClient(app)
    response = client.post("/api/models/config", json={"active_model_id": "deepseek-v4pro"})
    assert response.status_code == 400


def test_activate_available_model(models_config: Path) -> None:
    client = TestClient(app)
    client.post("/api/models/config", json={"provider_id": "deepseek", "api_key": "sk-test-deepseek"})
    response = client.post("/api/models/config", json={"active_model_id": "deepseek-v4pro"})
    assert response.status_code == 200
    assert response.json()["active_model_id"] == "deepseek-v4pro"


def test_serialize_models_config_flags_availability() -> None:
    router = LLMProviderRouter()
    router.set_api_key("anthropic", "sk-ant-test")
    payload = serialize_models_config(router)
    claude = next(m for m in payload["models"] if m["id"] == "claude-3-7-sonnet")
    deepseek = next(m for m in payload["models"] if m["id"] == "deepseek-v4pro")
    assert claude["available"] is True
    assert deepseek["available"] is False
    assert claude["credential_source_label"] is not None


def test_config_includes_source_for_saved_key(models_config: Path) -> None:
    client = TestClient(app)
    client.post("/api/models/config", json={"provider_id": "deepseek", "api_key": "sk-test-deepseek"})
    body = client.get("/api/models/config").json()
    deepseek = next(m for m in body["models"] if m["id"] == "deepseek-v4pro")
    assert deepseek["credential_source"] == "clutch_models_config"
    assert "models.json" in (deepseek["credential_source_label"] or "")


def test_model_test_endpoint_success(models_config: Path) -> None:
    from src.models_config import get_router

    client = TestClient(app)
    client.post("/api/models/config", json={"provider_id": "deepseek", "api_key": "sk-test-deepseek"})
    get_router()._chat = lambda **_kwargs: "ok"  # type: ignore[method-assign, assignment]
    result = client.post("/api/models/test", json={"model_id": "deepseek-v4pro"}).json()
    assert result["ok"] is True


def test_model_test_endpoint_failure(models_config: Path) -> None:
    from src.models_config import get_router

    client = TestClient(app)
    client.post("/api/models/config", json={"provider_id": "deepseek", "api_key": "sk-test-deepseek"})

    def boom(**_kwargs: object) -> str:
        raise RuntimeError("401 unauthorized")

    get_router()._chat = boom  # type: ignore[method-assign]
    result = client.post("/api/models/test", json={"model_id": "deepseek-v4pro"}).json()
    assert result["ok"] is False
    assert "401" in result["message"]


def test_delete_provider_credential(models_config: Path) -> None:
    client = TestClient(app)
    client.post("/api/models/config", json={"provider_id": "deepseek", "api_key": "sk-test-deepseek"})
    listed = client.get("/api/models/config").json()
    deepseek = next(m for m in listed["models"] if m["id"] == "deepseek-v4pro")
    assert deepseek["clutch_managed"] is True

    removed = client.delete("/api/models/credentials/deepseek")
    assert removed.status_code == 200

    listed = client.get("/api/models/config").json()
    deepseek = next(m for m in listed["models"] if m["id"] == "deepseek-v4pro")
    assert deepseek["available"] is False
    assert deepseek["clutch_managed"] is False


def test_delete_rejects_external_only_credential(models_config: Path) -> None:
    from src.models_config import get_router

    client = TestClient(app)
    get_router().set_api_key("anthropic", "sk-ant-external")
    response = client.delete("/api/models/credentials/anthropic")
    assert response.status_code == 400
