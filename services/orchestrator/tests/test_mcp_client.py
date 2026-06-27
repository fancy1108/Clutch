"""Unit tests for lightweight synchronous MCP Client."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from src.mcp_client import McpClient


def test_mcp_client_lifecycle(tmp_path: Path) -> None:
    mock_server_code = (
        "import sys, json\n"
        "for line in sys.stdin:\n"
        "    if not line: break\n"
        "    try:\n"
        "        req = json.loads(line.strip())\n"
        "        req_id = req.get('id')\n"
        "        method = req.get('method')\n"
        "        if method == 'initialize':\n"
        "            res = {'jsonrpc': '2.0', 'id': req_id, 'result': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'serverInfo': {'name': 'mock'}}}\n"
        "        elif method == 'tools/list':\n"
        "            res = {'jsonrpc': '2.0', 'id': req_id, 'result': {'tools': [{'name': 'test_tool', 'description': 'desc', 'inputSchema': {}}]}}\n"
        "        elif method == 'tools/call':\n"
        "            res = {'jsonrpc': '2.0', 'id': req_id, 'result': {'content': [{'type': 'text', 'text': 'success'}]}}\n"
        "        elif method == 'shutdown':\n"
        "            res = {'jsonrpc': '2.0', 'id': req_id, 'result': {}}\n"
        "        else:\n"
        "            res = {'jsonrpc': '2.0', 'id': req_id, 'error': {'code': -32601, 'message': 'err'}}\n"
        "        sys.stdout.write(json.dumps(res) + '\\n')\n"
        "        sys.stdout.flush()\n"
        "    except Exception:\n"
        "        pass\n"
    )
    script_path = tmp_path / "mock_mcp_server.py"
    script_path.write_text(mock_server_code, encoding="utf-8")
    
    endpoint = f"{sys.executable} {script_path}"
    client = McpClient("mock-mcp", endpoint)
    assert client.start() is True
    tools: list[dict] = []
    for _ in range(5):
        tools = client.list_tools()
        if tools:
            break
        time.sleep(0.05)
    assert len(tools) == 1
    assert tools[0]["name"] == "test_tool"
    call_res = client.call_tool("test_tool", {"arg1": "val1"})
    assert call_res.get("content", [{}])[0].get("text") == "success"
    client.close()
    assert client.proc is None

