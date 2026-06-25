"""P2-02 — MCP server registry CRUD and status aggregation."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.mcp_storage import load_servers, mcp_dir, save_servers

client = TestClient(app)


@pytest.fixture
def mcp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "mcp"
    monkeypatch.setenv("CLUTCH_MCP_DIR", str(target))
    return target


def test_register_stdio_and_sse_servers(mcp_data_dir: Path) -> None:
    stdio = client.post(
        "/api/mcp/servers/register",
        json={
            "name": "Git Tools",
            "transport": "stdio",
            "endpoint": "npx -y @modelcontextprotocol/server-git",
        },
    )
    assert stdio.status_code == 200
    git = next(s for s in stdio.json()["servers"] if s.get("name") == "Git Tools")
    assert git["transport"] == "stdio"
    assert git["type"] == "local"

    sse = client.post(
        "/api/mcp/servers/register",
        json={
            "name": "Remote Hub",
            "transport": "sse",
            "endpoint": "https://example.com/mcp/sse",
        },
    )
    assert sse.status_code == 200
    remote = next(s for s in sse.json()["servers"] if s.get("name") == "Remote Hub")
    assert remote["type"] == "remote"
    assert len(load_servers()) == 2
    assert mcp_dir() == mcp_data_dir


def test_status_lists_builtin_filesystem_and_user_servers(mcp_data_dir: Path) -> None:
    client.post(
        "/api/mcp/servers/register",
        json={
            "name": "Docs",
            "transport": "stdio",
            "endpoint": "uvx mcp-server-fetch",
        },
    )
    status = client.get("/api/mcp/status")
    assert status.status_code == 200
    body = status.json()
    assert body["filesystem"]["connected"] is False
    assert len(body["servers"]) == 2
    assert body["servers"][0]["id"] == "local-fs"
    assert body["servers"][1]["name"] == "Docs"
    assert body["servers"][1]["status"] in {"reconnecting", "connected", "failed"}


def test_remove_and_toggle(mcp_data_dir: Path) -> None:
    reg = client.post(
        "/api/mcp/servers/register",
        json={"name": "Tmp", "transport": "stdio", "endpoint": "echo mcp"},
    ).json()
    server_id = next(s["id"] for s in reg["servers"] if s.get("name") == "Tmp")

    off = client.post("/api/mcp/servers/toggle", json={"id": server_id, "enabled": False})
    assert off.status_code == 200
    disabled = next(s for s in off.json()["servers"] if s["id"] == server_id)
    assert disabled["status"] == "failed"

    removed = client.post("/api/mcp/servers/remove", json={"id": server_id})
    assert removed.status_code == 200
    assert all(s["id"] != server_id for s in removed.json()["servers"])
    save_servers([])
