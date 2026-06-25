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


def test_move_file_delete_workaround_message() -> None:
    from src.mcp_risk import move_file_delete_workaround_message

    msg = move_file_delete_workaround_message(
        "move_file",
        {"source": "/ws/.deleted_test.txt", "destination": "/ws/deleted_test.txt"},
    )
    assert msg is not None
    assert "apply_patch" in msg
    assert move_file_delete_workaround_message(
        "move_file",
        {"source": "a.txt", "destination": "b.txt"},
    ) is None


def test_mcp_approval_key_matches_relative_and_absolute_path(tmp_path, monkeypatch) -> None:
    from src import workspace as workspace_mod
    from src.mcp_risk import mcp_approval_key

    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    workspace_mod.add_workspace(str(tmp_path))

    relative = mcp_approval_key(
        "local-fs__write_file",
        {"path": "aa.txt", "content": ""},
    )
    absolute = mcp_approval_key(
        "local-fs__write_file",
        {"path": str(tmp_path / "aa.txt"), "content": ""},
    )
    assert relative == absolute
