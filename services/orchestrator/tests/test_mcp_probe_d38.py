"""D38 — MCP Hub test-connection probe returns readable errors / tool counts."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.mcp_storage import _probe_endpoint_sync, probe_server_by_id

client = TestClient(app)


@pytest.fixture
def mcp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "mcp"
    monkeypatch.setenv("CLUTCH_MCP_DIR", str(target))
    return target


def test_probe_bad_command_readable_error() -> None:
    result = _probe_endpoint_sync("clutch-mcp-definitely-missing-bin-xyz")
    assert result["ok"] is False
    assert result["toolsCount"] == 0
    assert result["error"]
    assert "not found" in result["error"].lower() or "failed" in result["error"].lower()


def test_probe_http_endpoint_honest() -> None:
    result = _probe_endpoint_sync("https://example.com/mcp/sse")
    assert result["ok"] is False
    assert "SSE" in (result["error"] or "") or "HTTP" in (result["error"] or "")


@pytest.mark.asyncio
async def test_probe_server_by_id_missing(mcp_data_dir: Path) -> None:
    del mcp_data_dir
    with pytest.raises(ValueError):
        await probe_server_by_id("no-such-server")


def test_api_test_endpoint_bad_command(mcp_data_dir: Path) -> None:
    del mcp_data_dir
    reg = client.post(
        "/api/mcp/servers/register",
        json={
            "name": "Broken",
            "transport": "stdio",
            "endpoint": "clutch-mcp-definitely-missing-bin-xyz",
        },
    )
    assert reg.status_code == 200
    server_id = next(s["id"] for s in reg.json()["servers"] if s.get("name") == "Broken")
    probed = client.post("/api/mcp/servers/test", json={"id": server_id})
    assert probed.status_code == 200
    body = probed.json()
    assert body["ok"] is False
    assert body["error"]
    assert body["toolsCount"] == 0


def test_api_test_legacy_sse_honest(mcp_data_dir: Path) -> None:
    del mcp_data_dir
    from src import mcp_storage

    # Persist a legacy SSE row (pre-D39) without going through register_server.
    mcp_storage.save_servers(
        [
            {
                "id": "mcp_legacy_sse",
                "name": "Remote",
                "type": "remote",
                "transport": "sse",
                "endpoint": "https://example.com/mcp/sse",
                "enabled": True,
            }
        ]
    )
    probed = client.post("/api/mcp/servers/test", json={"id": "mcp_legacy_sse"})
    assert probed.status_code == 200
    body = probed.json()
    assert body["ok"] is False
    assert "stdio" in body["error"].lower() or "sse" in body["error"].lower()
