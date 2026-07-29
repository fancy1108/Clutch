"""D15 — builtin web_search + allow_network preference."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.builtin_tools import execute_builtin_tool, list_builtin_tools
from src.preferences_storage import save_allow_network


def test_web_search_hidden_when_network_disabled() -> None:
    save_allow_network(False)
    names = {t["name"] for t in list_builtin_tools()}
    assert "web_search" not in names
    out = execute_builtin_tool("web_search", {"query": "clutch agent"})
    assert "disabled" in out.lower()


def test_web_search_listed_when_network_enabled() -> None:
    save_allow_network(True)
    names = {t["name"] for t in list_builtin_tools()}
    assert "web_search" in names


def test_web_search_requires_query() -> None:
    save_allow_network(True)
    out = execute_builtin_tool("web_search", {})
    assert "requires `query`" in out


def test_search_web_parses_html(monkeypatch: pytest.MonkeyPatch) -> None:
    from src import web_search_util

    sample_html = """
    <a class="result__a" href="https://example.com/a">Alpha</a>
    <a class="result__snippet">Snippet A</a>
    <a class="result__a" href="https://example.com/b">Beta</a>
    <a class="result__snippet">Snippet B</a>
    """

    class _Resp:
        text = sample_html

        def raise_for_status(self) -> None:
            return None

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def get(self, *args: object, **kwargs: object) -> _Resp:
            return _Resp()

    monkeypatch.setattr(web_search_util.httpx, "Client", lambda **kwargs: _Client())
    payload = web_search_util.search_web("alpha", max_results=2)
    assert payload["result_count"] == 2
    assert payload["results"][0]["url"] == "https://example.com/a"
