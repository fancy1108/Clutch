"""Unit tests for lightweight synchronous MCP Client."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from src.mcp_client import McpClient, extract_login_url, oauth_proxy_eligible


def test_extract_login_url_skips_docs_keeps_oauth() -> None:
    assert extract_login_url("Please authorize this client by visiting:") is None
    assert extract_login_url("https://developers.figma.com/docs/figma-mcp-server/") is None
    figma = extract_login_url("https://www.figma.com/oauth?client_id=abc")
    assert figma is not None and "figma.com" in figma
    followed = extract_login_url(
        "https://www.figma.com/oauth?client_id=abc",
        previous="Please authorize this client by visiting:",
    )
    assert followed is not None
    assert extract_login_url("https://registry.npmjs.org/mcp-remote") is None
    assert extract_login_url("https://mcp.figma.com/mcp") is None


def test_oauth_proxy_eligible_https_without_key() -> None:
    assert oauth_proxy_eligible("https://mcp.figma.com/mcp") is True
    assert oauth_proxy_eligible("https://mcp.example.com/mcp") is True
    assert oauth_proxy_eligible("http://127.0.0.1:3845/mcp") is False
    assert oauth_proxy_eligible("https://mcp.example.com/mcp", {"Authorization": "Bearer x"}) is False


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


def test_mcp_client_http_streamable() -> None:
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            return

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            method = body.get("method")
            req_id = body.get("id")
            if method == "notifications/initialized":
                self.send_response(202)
                self.end_headers()
                return
            if method == "initialize":
                result: dict = {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "serverInfo": {"name": "mock"},
                }
            elif method == "tools/list":
                result = {"tools": [{"name": "ping", "description": "p", "inputSchema": {}}]}
            else:
                result = {}
            payload = json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Mcp-Session-Id", "sess-1")
            self.end_headers()
            self.wfile.write(payload)

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    client = McpClient("http-mock", f"http://127.0.0.1:{httpd.server_address[1]}/mcp")
    try:
        assert client.start() is True
        tools = client.list_tools()
        assert tools[0]["name"] == "ping"
    finally:
        client.close()
        httpd.shutdown()

