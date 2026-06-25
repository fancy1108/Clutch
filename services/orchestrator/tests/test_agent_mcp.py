"""Tests for MCP server binding on agents (P2-17)."""

from __future__ import annotations

from src.agent_mcp import resolve_agent_mcp_servers


def test_resolve_agent_mcp_servers_filters_enabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.agent_mcp.load_servers",
        lambda: [
            {
                "id": "mcp_a",
                "name": "Filesystem",
                "endpoint": "npx -y @modelcontextprotocol/server-filesystem /tmp",
                "enabled": True,
            },
            {
                "id": "mcp_b",
                "name": "Disabled",
                "endpoint": "npx -y fake",
                "enabled": False,
            },
        ],
    )
    agent = {"mcpServerIds": ["mcp_a", "mcp_b", "missing"]}
    resolved = resolve_agent_mcp_servers(agent)
    assert len(resolved) == 1
    assert resolved[0]["id"] == "mcp_a"


def test_resolve_agent_mcp_servers_includes_builtin_local_fs(monkeypatch) -> None:
    monkeypatch.setattr("src.agent_mcp.load_servers", lambda: [])
    monkeypatch.setattr(
        "src.agent_mcp.resolve_local_fs_server",
        lambda: {
            "id": "local-fs",
            "name": "Local Filesystem MCP Server",
            "endpoint": "npx -y @modelcontextprotocol/server-filesystem /workspace",
            "enabled": True,
        },
    )
    resolved = resolve_agent_mcp_servers({"mcpServerIds": ["local-fs"]})
    assert len(resolved) == 1
    assert resolved[0]["id"] == "local-fs"
