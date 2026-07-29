"""D28 — discover MCP tools via search when catalog is large."""

from __future__ import annotations

import json
import re
from typing import Any

DISCOVERY_THRESHOLD = 24
ALWAYS_ON_EXTERNAL = 3
DISCOVERY_SERVER_ID = "mcp-discovery"
SEARCH_TOOL_NAME = "search_mcp_tools"
SEARCH_ALIAS = f"{DISCOVERY_SERVER_ID}__{SEARCH_TOOL_NAME}"


def search_tool_openai_def() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": SEARCH_ALIAS,
            "description": (
                "Search the MCP tool catalog by keyword when many tools are registered. "
                "Returns matching tool aliases and enables them for subsequent calls."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords to match tool names/descriptions.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max matches to enable (default 8).",
                    },
                },
                "required": ["query"],
            },
        },
    }


def _tokenize(query: str) -> list[str]:
    return [tok for tok in re.split(r"\W+", query.lower()) if tok]


def search_catalog(
    catalog: dict[str, dict[str, Any]],
    query: str,
    *,
    limit: int = 8,
) -> list[str]:
    """Return catalog aliases ranked by relevance to query."""
    tokens = _tokenize(query)
    if not tokens:
        return []
    scored: list[tuple[int, str]] = []
    for alias, meta in catalog.items():
        hay = f"{meta.get('tool_name', '')} {meta.get('description', '')}".lower()
        score = sum(1 for tok in tokens if tok in hay)
        if score:
            scored.append((score, alias))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [alias for _, alias in scored[: max(1, limit)]]


def execute_search_mcp_tools(
    arguments: dict[str, Any],
    *,
    catalog: dict[str, dict[str, Any]],
    enabled: set[str],
) -> str:
    query = str(arguments.get("query") or "").strip()
    if not query:
        return "Error executing tool: search_mcp_tools requires `query`"
    try:
        limit = int(arguments.get("limit") or 8)
    except (TypeError, ValueError):
        limit = 8
    matches = search_catalog(catalog, query, limit=limit)
    enabled.update(matches)
    payload = {
        "query": query,
        "matched": matches,
        "enabled_count": len(enabled),
        "catalog_size": len(catalog),
        "hint": "Matched tools are now available for tool calls in follow-up turns.",
    }
    return json.dumps(payload, ensure_ascii=False)


def initial_enabled_aliases(catalog: dict[str, dict[str, Any]]) -> set[str]:
    """Few always-on external tools (stable sort by alias)."""
    return set(sorted(catalog.keys())[:ALWAYS_ON_EXTERNAL])


def build_external_openai_tools(
    *,
    catalog: dict[str, dict[str, Any]],
    enabled: set[str],
    discovery_mode: bool,
) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    if discovery_mode:
        tools.append(search_tool_openai_def())
        for alias in sorted(enabled):
            entry = catalog.get(alias)
            if entry and entry.get("openai"):
                tools.append(entry["openai"])
    else:
        for alias in sorted(catalog.keys()):
            entry = catalog[alias]
            if entry.get("openai"):
                tools.append(entry["openai"])
    return tools
