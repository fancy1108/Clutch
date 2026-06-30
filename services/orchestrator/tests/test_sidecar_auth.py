"""Sidecar session token auth (OSR-08)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("CLUTCH_SIDECAR_TOKEN", raising=False)
    monkeypatch.delenv("CLUTCH_E2E_SANDBOX", raising=False)
    return TestClient(app)


def test_health_always_public(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_SIDECAR_TOKEN", "secret-token")
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_api_open_without_token_env(client: TestClient) -> None:
    response = client.get("/api/preferences")
    assert response.status_code == 200


def test_api_rejects_missing_token_when_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLUTCH_E2E_SANDBOX", raising=False)
    monkeypatch.setenv("CLUTCH_SIDECAR_TOKEN", "secret-token")
    authed = TestClient(app)
    response = authed.get("/api/preferences")
    assert response.status_code == 401


def test_api_accepts_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLUTCH_E2E_SANDBOX", raising=False)
    monkeypatch.setenv("CLUTCH_SIDECAR_TOKEN", "secret-token")
    authed = TestClient(app)
    response = authed.get(
        "/api/preferences",
        headers={"Authorization": "Bearer secret-token"},
    )
    assert response.status_code == 200


def test_e2e_sandbox_skips_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_SIDECAR_TOKEN", "secret-token")
    monkeypatch.setenv("CLUTCH_E2E_SANDBOX", "/tmp/e2e-sandbox")
    authed = TestClient(app)
    response = authed.get("/api/preferences")
    assert response.status_code == 200
