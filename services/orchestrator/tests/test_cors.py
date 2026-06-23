"""CORS allows Tauri desktop webview to call the sidecar."""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_cors_allows_tauri_localhost_origin() -> None:
    response = client.options(
        "/api/workspaces",
        headers={
            "Origin": "https://tauri.localhost",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://tauri.localhost"
