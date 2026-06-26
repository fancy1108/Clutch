"""Custom image model persistence API."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.custom_models import is_custom_model_id
from src.llm.router import LLMProviderRouter
from src.main import app


@pytest.fixture
def models_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config = tmp_path / "models.json"
    monkeypatch.setenv("CLUTCH_MODELS_CONFIG", str(config))
    monkeypatch.setattr("src.credentials.claude_code._CLAUDE_SETTINGS", tmp_path / "no-claude.json")
    router = LLMProviderRouter()
    router._chat = lambda **_kwargs: "ok"  # type: ignore[method-assign, assignment]
    monkeypatch.setattr("src.models_config.get_router", lambda: router)
    return config


def test_add_custom_image_model_persists(models_config: Path) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/models/custom/image",
        json={
            "name": "My Flux",
            "api_model": "flux-pro",
            "base_url": "https://gateway.example.com",
            "provider_id": "custom",
            "image_backend": "openai_images",
            "api_key": "sk-test",
        },
    )
    assert response.status_code == 200
    body = response.json()
    model_id = body["model_id"]
    assert model_id.startswith("custom-")
    assert is_custom_model_id(model_id)

    stored = models_config.read_text(encoding="utf-8")
    assert "flux-pro" in stored
    assert "custom_models" in stored

    listed = client.get("/api/models/config").json()
    created = next(m for m in listed["models"] if m["id"] == model_id)
    assert created["model_kind"] == "image"
    assert created["is_custom"] is True
    assert created["available"] is True


def test_delete_custom_image_model(models_config: Path) -> None:
    client = TestClient(app)
    created = client.post(
        "/api/models/custom/image",
        json={
            "name": "Temp Image",
            "api_model": "temp-img",
            "base_url": "https://api.example.com",
            "provider_id": "custom",
            "image_backend": "openai_images",
            "api_key": "sk-test",
        },
    )
    assert created.status_code == 200
    model_id = created.json()["model_id"]
    deleted = client.delete(f"/api/models/custom/{model_id}")
    assert deleted.status_code == 200
    assert not is_custom_model_id(model_id)
    listed = client.get("/api/models/config").json()
    assert not any(m["id"] == model_id for m in listed["models"])


def test_hide_builtin_image_model(models_config: Path) -> None:
    client = TestClient(app)
    response = client.delete("/api/models/custom/agnes-image-2.1-flash")
    assert response.status_code == 200
    listed = client.get("/api/models/config").json()
    assert not any(m["id"] == "agnes-image-2.1-flash" for m in listed["models"])
    stored = models_config.read_text(encoding="utf-8")
    assert "agnes-image-2.1-flash" in stored


def test_custom_model_not_deduped_against_builtin(models_config: Path) -> None:
    client = TestClient(app)
    client.post(
        "/api/models/config",
        json={"provider_id": "custom", "api_key": "sk-test"},
    )
    created = client.post(
        "/api/models/custom/image",
        json={
            "name": "My Agnes Copy",
            "api_model": "agnes-image-2.1-flash",
            "base_url": "https://apihub.agnes-ai.com",
            "provider_id": "custom",
            "image_backend": "agnes",
        },
    )
    assert created.status_code == 200
    custom_id = created.json()["model_id"]
    listed = client.get("/api/models/config").json()
    ids = {m["id"] for m in listed["models"] if m.get("model_kind") == "image"}
    assert custom_id in ids
    assert "agnes-image-2.1-flash" in ids


def test_add_custom_image_model_rejects_invalid_backend(models_config: Path) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/models/custom/image",
        json={
            "name": "Bad",
            "api_model": "x",
            "base_url": "https://api.example.com",
            "image_backend": "unknown-backend",
        },
    )
    assert response.status_code == 400
