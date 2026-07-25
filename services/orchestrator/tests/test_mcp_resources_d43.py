"""D43 — MCP resources list / pin / prompt injection."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.mcp_resources import format_pinned_resources_block, load_resource_pins, save_resource_pins

client = TestClient(app)


@pytest.fixture
def mcp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "mcp"
    monkeypatch.setenv("CLUTCH_MCP_DIR", str(target))
    return target


def _write_mock_resource_server(tmp_path: Path) -> str:
    code = (
        "import sys, json\n"
        "for line in sys.stdin:\n"
        "    if not line: break\n"
        "    try:\n"
        "        req = json.loads(line.strip())\n"
        "        req_id = req.get('id')\n"
        "        method = req.get('method')\n"
        "        if method == 'initialize':\n"
        "            res = {'jsonrpc': '2.0', 'id': req_id, 'result': {'protocolVersion': '2024-11-05', 'capabilities': {'resources': {}}, 'serverInfo': {'name': 'mock-res'}}}\n"
        "        elif method == 'tools/list':\n"
        "            res = {'jsonrpc': '2.0', 'id': req_id, 'result': {'tools': [{'name': 'noop', 'description': '', 'inputSchema': {}}]}}\n"
        "        elif method == 'resources/list':\n"
        "            res = {'jsonrpc': '2.0', 'id': req_id, 'result': {'resources': [{'uri': 'memo://notes', 'name': 'Notes', 'mimeType': 'text/plain'}]}}\n"
        "        elif method == 'resources/read':\n"
        "            res = {'jsonrpc': '2.0', 'id': req_id, 'result': {'contents': [{'uri': 'memo://notes', 'mimeType': 'text/plain', 'text': 'RESOURCE_TOKEN_ORANGE'}]}}\n"
        "        elif method == 'shutdown':\n"
        "            res = {'jsonrpc': '2.0', 'id': req_id, 'result': {}}\n"
        "        else:\n"
        "            res = {'jsonrpc': '2.0', 'id': req_id, 'error': {'code': -32601, 'message': 'err'}}\n"
        "        sys.stdout.write(json.dumps(res) + '\\n')\n"
        "        sys.stdout.flush()\n"
        "    except Exception:\n"
        "        pass\n"
    )
    script = tmp_path / "mock_mcp_resources.py"
    script.write_text(code, encoding="utf-8")
    return f"{sys.executable} {script}"


def test_list_and_pin_resource_injects_prompt(mcp_data_dir: Path, tmp_path: Path) -> None:
    del mcp_data_dir
    endpoint = _write_mock_resource_server(tmp_path)
    reg = client.post(
        "/api/mcp/servers/register",
        json={"name": "ResServer", "transport": "stdio", "endpoint": endpoint},
    )
    assert reg.status_code == 200
    server_id = next(s["id"] for s in reg.json()["servers"] if s.get("name") == "ResServer")

    listed = client.get(f"/api/mcp/servers/{server_id}/resources")
    assert listed.status_code == 200
    body = listed.json()
    assert body["count"] == 1
    assert body["resources"][0]["uri"] == "memo://notes"

    pinned = client.post(
        "/api/mcp/resource-pins",
        json={"server_id": server_id, "uri": "memo://notes", "name": "Notes"},
    )
    assert pinned.status_code == 200
    assert pinned.json()["count"] == 1
    pins = load_resource_pins()
    assert pins[0]["text"] and "RESOURCE_TOKEN_ORANGE" in pins[0]["text"]

    block = format_pinned_resources_block()
    assert "RESOURCE_TOKEN_ORANGE" in block
    assert "memo://notes" in block


def test_unpin_clears_prompt_block(mcp_data_dir: Path) -> None:
    del mcp_data_dir
    save_resource_pins(
        [
            {
                "server_id": "s1",
                "uri": "memo://x",
                "name": "X",
                "text": "hello",
            }
        ]
    )
    assert "hello" in format_pinned_resources_block()
    removed = client.post(
        "/api/mcp/resource-pins/remove",
        json={"server_id": "s1", "uri": "memo://x"},
    )
    assert removed.status_code == 200
    assert removed.json()["count"] == 0
    assert format_pinned_resources_block() == ""
