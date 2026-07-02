"""Tests for dispatch_parse (D34)."""

from src.dispatch_parse import parse_dispatch_mentions


def _meta(file_name: str) -> dict:
    if "claude" in file_name.lower() and "opencode" in file_name.lower():
        return {"sources": ["Claude Code", "OpenCode"]}
    if "claude" in file_name.lower():
        return {"sources": ["Claude Code"]}
    return {"sources": []}


def test_natural_language_focused_source():
    preview = parse_dispatch_mentions(
        "@OpenCode 实现 API",
        focused_agent="Claude Code",
        file_meta_resolver=_meta,
    )
    assert preview is not None
    assert preview.target == "OpenCode"
    assert preview.sources == ["Claude Code"]


def test_file_ref_infers_sources():
    preview = parse_dispatch_mentions(
        "@OpenCode 接上 REST @20260702-claude→opencode-api.md",
        focused_agent="Claude Code",
        file_meta_resolver=_meta,
    )
    assert preview is not None
    assert preview.target == "OpenCode"
    assert "Claude Code" in preview.sources
    assert preview.file_refs


def test_graph_syntax():
    preview = parse_dispatch_mentions(
        "@Claude Code from @OpenCode @Claude Code：整合",
        file_meta_resolver=_meta,
    )
    assert preview is not None
    assert preview.target == "Claude Code"
    assert preview.input_mode == "graph"
    assert "OpenCode" in preview.sources


def test_cold_start_no_focus():
    preview = parse_dispatch_mentions("@OpenCode 实现 CRUD", file_meta_resolver=_meta)
    assert preview is not None
    assert preview.sources == ["工作区"]


def test_missing_agent_returns_none():
    assert parse_dispatch_mentions("hello world", file_meta_resolver=_meta) is None
