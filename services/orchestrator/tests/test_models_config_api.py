"""Models config API — availability and activation guards."""

from __future__ import annotations

import json
from pathlib import Path

from unittest.mock import patch

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


def test_serialize_dedupes_same_endpoint_and_api_model() -> None:
    from src.llm.router import ModelSpec

    router = LLMProviderRouter()
    agnes_url = "https://apihub.agnes-ai.com/v1"
    agnes_model = "agnes-2.0-flash"
    router.register_model(
        ModelSpec(
            id="claude-3-7-sonnet",
            name="Agnes 2.0 Flash",
            provider_id="anthropic",
            api_model=agnes_model,
            base_url=agnes_url,
        )
    )
    router.register_model(
        ModelSpec(
            id="cc-switch-agnes1",
            name="agnes-ai (agnes-2.0-flash)",
            provider_id="openai",
            api_model=agnes_model,
            base_url=agnes_url,
        )
    )
    router.register_model(
        ModelSpec(
            id="cc-switch-agnes2",
            name="Agnes AI (Cloud) (agnes-2.0-flash)",
            provider_id="custom",
            api_model=agnes_model,
            base_url=agnes_url,
        )
    )
    router.set_api_key("anthropic", "key-anthropic")
    router.set_api_key("openai", "key-openai")
    router.set_api_key("custom", "key-custom")

    payload = serialize_models_config(router)
    agnes_ids = {"claude-3-7-sonnet", "cc-switch-agnes1", "cc-switch-agnes2"}
    listed = [model for model in payload["models"] if model["id"] in agnes_ids]
    assert len(listed) == 1
    assert listed[0]["id"] == "claude-3-7-sonnet"

    router.set_active_model("cc-switch-agnes1")
    payload_active = serialize_models_config(router)
    listed_active = [model for model in payload_active["models"] if model["id"] in agnes_ids]
    assert len(listed_active) == 1
    assert listed_active[0]["id"] == "cc-switch-agnes1"


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
    assert "rejected" in result["message"].lower()


def test_agnes_image_model_listed_with_kind(models_config: Path) -> None:
    client = TestClient(app)
    body = client.get("/api/models/config").json()
    agnes = next(m for m in body["models"] if m["id"] == "agnes-image-2.1-flash")
    assert agnes["name"] == "Agnes Image 2.1 Flash"
    assert agnes["provider_id"] == "custom"
    assert agnes["model_kind"] == "image"
    assert agnes["endpoint"] == "https://apihub.agnes-ai.com"


def test_agnes_image_model_test_uses_image_adapter(models_config: Path) -> None:
    client = TestClient(app)
    client.post("/api/models/config", json={"provider_id": "custom", "api_key": "sk-test-agnes"})
    with patch("src.models_config.verify_image_model_connection") as mocked:
        result = client.post("/api/models/test", json={"model_id": "agnes-image-2.1-flash"}).json()
    assert result["ok"] is True
    assert "image" in result["message"].lower()
    mocked.assert_called_once()


def test_delete_provider_credential(models_config: Path) -> None:
    client = TestClient(app)
    client.post("/api/models/config", json={"provider_id": "deepseek", "api_key": "sk-test-deepseek"})
    listed = client.get("/api/models/config").json()
    deepseek = next(m for m in listed["models"] if m["id"] == "deepseek-v4pro")
    assert deepseek["clutch_managed"] is True
    assert deepseek.get("source_summary") == "API key saved in Clutch"

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


def test_rehydrate_cc_switch_missing_db(models_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.Path.home", lambda: models_config.parent)
    client = TestClient(app)
    response = client.post("/api/models/rehydrate-cc-switch")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["cc_switch_found"] is False
    assert "not found" in body["message"].lower()


def test_rehydrate_cc_switch_imports_models(
    models_config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sqlite3

    from src.models_config import get_router

    cc_dir = tmp_path / ".cc-switch"
    cc_dir.mkdir()
    db_file = cc_dir / "cc-switch.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        "CREATE TABLE providers (id TEXT, name TEXT, app_type TEXT, settings_config TEXT)"
    )
    conn.execute(
        "INSERT INTO providers VALUES (?, ?, ?, ?)",
        (
            "test-pro",
            "Test Pro",
            "claude",
            json.dumps(
                {
                    "env": {
                        "ANTHROPIC_AUTH_TOKEN": "sk-cc-test",
                        "ANTHROPIC_BASE_URL": "https://example.com",
                        "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-test",
                    }
                }
            ),
        ),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr("src.credentials.claude_code._CC_SWITCH_DIR", cc_dir)
    monkeypatch.setattr("src.models_config.Path.home", lambda: tmp_path)

    client = TestClient(app)
    response = client.post("/api/models/rehydrate-cc-switch")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["models_imported"] == 1
    assert "Imported 1 model" in body["message"]

    listed = client.get("/api/models/config").json()
    imported = next(m for m in listed["models"] if m["id"] == "cc-switch-test-pro")
    assert imported["is_cc_switch"] is True
    assert imported["available"] is True
    assert get_router().get_api_key("anthropic") == "sk-cc-test"
