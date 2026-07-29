"""D28 — MCP tool discovery when catalog is large."""

from __future__ import annotations

from src.mcp_tool_discovery import (
    DISCOVERY_THRESHOLD,
    SEARCH_ALIAS,
    build_external_openai_tools,
    execute_search_mcp_tools,
    initial_enabled_aliases,
    search_catalog,
)


def _sample_catalog(count: int) -> dict:
    catalog: dict = {}
    for i in range(count):
        alias = f"srv__tool_{i:02d}"
        catalog[alias] = {
            "openai": {
                "type": "function",
                "function": {
                    "name": alias,
                    "description": f"tool number {i}",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            "tool_name": f"tool_{i:02d}",
            "description": f"tool number {i}",
            "server_id": "srv",
        }
    return catalog


def test_discovery_threshold_constant() -> None:
    assert DISCOVERY_THRESHOLD == 24


def test_search_catalog_matches_keywords() -> None:
    catalog = _sample_catalog(30)
    catalog["srv__tool_00"]["description"] = "Read workspace files"
    matches = search_catalog(catalog, "read file", limit=5)
    assert "srv__tool_00" in matches


def test_execute_search_enables_tools() -> None:
    catalog = _sample_catalog(30)
    enabled: set[str] = set()
    out = execute_search_mcp_tools({"query": "tool 05"}, catalog=catalog, enabled=enabled)
    assert "srv__tool_05" in enabled
    assert "matched" in out


def test_build_external_tools_uses_search_when_discovery_mode() -> None:
    catalog = _sample_catalog(30)
    enabled = initial_enabled_aliases(catalog)
    tools = build_external_openai_tools(
        catalog=catalog,
        enabled=enabled,
        discovery_mode=True,
    )
    names = {t["function"]["name"] for t in tools}
    assert SEARCH_ALIAS in names
    assert len(names) == 1 + len(enabled)


def test_build_external_tools_lists_all_when_small_catalog() -> None:
    catalog = _sample_catalog(5)
    tools = build_external_openai_tools(
        catalog=catalog,
        enabled=set(catalog.keys()),
        discovery_mode=False,
    )
    assert len(tools) == 5
