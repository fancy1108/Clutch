"""Tests for clutch-tools builtins and default Clutch Agent binding (D44 / D1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent_mcp import resolve_agent_mcp_servers
from src.builtin_tools import execute_builtin_tool, list_builtin_tools
from src.mcp_risk import is_risky_mcp_tool
from src.workspace import clear_workspace_for_tests, set_workspace


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    clear_workspace_for_tests()
    root = tmp_path / "proj"
    root.mkdir()
    (root / "README.md").write_text("hello world\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('x')\n", encoding="utf-8")
    set_workspace(str(root))
    yield root
    clear_workspace_for_tests()


def test_list_builtin_tools_includes_core_set() -> None:
    names = {item["name"] for item in list_builtin_tools()}
    assert names >= {
        "read_file",
        "list_dir",
        "grep",
        "search_replace",
        "run_terminal_cmd",
        "apply_patch",
        "propose_plan",
        "todo_write",
    }


def test_read_list_grep_search_replace_and_shell(workspace: Path) -> None:
    listed = execute_builtin_tool("list_dir", {"path": "."})
    assert "README.md" in listed
    assert "src/" in listed

    read = execute_builtin_tool("read_file", {"path": "README.md"})
    assert "hello world" in read

    grepped = execute_builtin_tool("grep", {"pattern": "print", "path": "src"})
    assert "app.py" in grepped

    replaced = execute_builtin_tool(
        "search_replace",
        {
            "path": "README.md",
            "old_string": "hello world",
            "new_string": "hello clutch",
        },
    )
    payload = json.loads(replaced)
    assert payload["ok"] is True
    assert (workspace / "README.md").read_text(encoding="utf-8") == "hello clutch\n"

    shell = execute_builtin_tool("run_terminal_cmd", {"command": "pwd"})
    assert "exit_code=0" in shell
    assert str(workspace) in shell or workspace.name in shell


def test_clutch_agent_gets_clutch_tools_without_mcp_ids(workspace: Path) -> None:
    resolved = resolve_agent_mcp_servers(
        {"id": "clutch-agent", "agentType": "clutch", "builtin": True, "mcpServerIds": []}
    )
    assert any(item["id"] == "clutch-tools" for item in resolved)


def test_search_replace_and_shell_are_risky() -> None:
    assert is_risky_mcp_tool("search_replace")
    assert is_risky_mcp_tool("run_terminal_cmd")
    assert not is_risky_mcp_tool("read_file")
    assert not is_risky_mcp_tool("list_dir")
    assert not is_risky_mcp_tool("grep")
