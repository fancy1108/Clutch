"""Unit tests for MCP JSON configuration save and Claude config import API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.mcp_storage import load_servers, save_servers

client = TestClient(app)


@pytest.fixture
def mcp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "mcp"
    monkeypatch.setenv("CLUTCH_MCP_DIR", str(target))
    return target


def test_save_raw_config_api(mcp_data_dir: Path) -> None:
    res = client.post(
        "/api/mcp/config/save",
        json={
            "servers": [
                {
                    "name": "Custom Server",
                    "transport": "stdio",
                    "endpoint": "echo 123",
                    "env": {"KEY": "VAL"},
                }
            ]
        },
    )
    assert res.status_code == 200
    servers = res.json()["servers"]
    custom = next(s for s in servers if s.get("name") == "Custom Server")
    assert custom["endpoint"] == "echo 123"
    assert custom["env"] == {"KEY": "VAL"}
    save_servers([])


def test_import_from_claude_api(mcp_data_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    claude_json_path = fake_home / ".claude.json"
    claude_json_path.write_text(
        '{"mcpServers": {"git": {"command": "npx", "args": ["-y", "@mcp/git"], "env": {"A": "B"}}}}',
        encoding="utf-8",
    )

    res = client.post("/api/mcp/import/claude")
    assert res.status_code == 200
    servers = res.json()["servers"]
    git = next(s for s in servers if s.get("name") == "Claude git")
    assert git["endpoint"] == "npx -y @mcp/git"
    assert git["env"] == {"A": "B"}
    save_servers([])
