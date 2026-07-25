"""D15 — web search for Clutch Agent (DuckDuckGo HTML lite, httpx)."""

from __future__ import annotations

import re
from html import unescape
from typing import Any

import httpx

_MAX_RESULTS = 8
_MAX_SNIPPET_CHARS = 400
_DEFAULT_TIMEOUT_S = 15
_RESULT_LINK_RE = re.compile(
    r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_SNIPPET_RE = re.compile(
    r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(fragment: str) -> str:
    text = unescape(_TAG_RE.sub(" ", fragment))
    return re.sub(r"\s+", " ", text).strip()


def search_web(query: str, *, max_results: int = 5) -> dict[str, Any]:
    cleaned = (query or "").strip()
    if not cleaned:
        raise ValueError("query is required")
    limit = max(1, min(int(max_results or 5), _MAX_RESULTS))
    with httpx.Client(timeout=_DEFAULT_TIMEOUT_S, follow_redirects=True) as client:
        response = client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": cleaned},
            headers={
                "User-Agent": "ClutchAgent/1.0 (+local; D15 web_search)",
                "Accept": "text/html",
            },
        )
        response.raise_for_status()
        html = response.text

    links = _RESULT_LINK_RE.findall(html)
    snippets = _SNIPPET_RE.findall(html)
    results: list[dict[str, str]] = []
    for idx, (url, title_html) in enumerate(links):
        if len(results) >= limit:
            break
        title = _strip_html(title_html)
        snippet = _strip_html(snippets[idx]) if idx < len(snippets) else ""
        if len(snippet) > _MAX_SNIPPET_CHARS:
            snippet = snippet[:_MAX_SNIPPET_CHARS] + "…"
        results.append(
            {
                "title": title or url,
                "url": url,
                "snippet": snippet,
            }
        )
    return {
        "query": cleaned,
        "provider": "duckduckgo_html",
        "results": results,
        "result_count": len(results),
    }
