"""Tests for MCP tool risk classification."""

from __future__ import annotations

from src.mcp_risk import extract_mcp_file_path, is_risky_mcp_tool


def test_is_risky_mcp_tool_detects_write_and_read() -> None:
    assert is_risky_mcp_tool("write_file")
    assert is_risky_mcp_tool("edit_file")
    assert not is_risky_mcp_tool("read_file")
    assert not is_risky_mcp_tool("list_directory")


def test_extract_mcp_file_path_reads_path_argument() -> None:
    assert extract_mcp_file_path("write_file", {"path": "test.txt"}) == "test.txt"
    assert extract_mcp_file_path("read_file", {"path": "test.txt"}) is None
    patch = "*** Begin Patch\n*** Delete File: gone.txt\n*** End Patch"
    assert extract_mcp_file_path("apply_patch", {"patch": patch}) == "gone.txt"
    assert is_risky_mcp_tool("apply_patch")
