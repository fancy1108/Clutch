"""B-41: filename existence uses list_dir (List), not grep (Search)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.builtin_tools import execute_builtin_tool, list_builtin_tools
from src.tool_steps import make_tool_step, verb_group_header_label
from src.tool_use_policy import (
    apply_filename_grep_rewrite,
    classify_tool_expectation,
    looks_like_filename_grep,
)
from src.workspace import clear_workspace_for_tests, set_workspace


PM_PROMPT = "不要读文件内容。用工具找出工作区里有没有叫 README.md 的文件。"


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    clear_workspace_for_tests()
    root = tmp_path / "proj"
    root.mkdir()
    (root / "README.md").write_text("# hello\n", encoding="utf-8")
    src = root / "src"
    src.mkdir()
    (src / "app.py").write_text("print('see README.md')\n", encoding="utf-8")
    set_workspace(str(root))
    yield root
    clear_workspace_for_tests()


def test_filename_patterns_are_list_not_content_search() -> None:
    assert looks_like_filename_grep("README.md")
    assert looks_like_filename_grep(r"README\.md")
    assert looks_like_filename_grep("^README.md$")
    assert not looks_like_filename_grep("TODO")
    assert not looks_like_filename_grep("print")
    assert not looks_like_filename_grep("def foo")


def test_rewrite_grep_filename_to_list_dir() -> None:
    name, args = apply_filename_grep_rewrite(
        "clutch-tools__grep", {"pattern": r"README\.md", "path": "."}
    )
    assert name == "clutch-tools__list_dir"
    assert args == {"path": "."}
    kept, kept_args = apply_filename_grep_rewrite("grep", {"pattern": "TODO", "path": "src"})
    assert kept == "grep"
    assert kept_args["pattern"] == "TODO"
    inside, _ = apply_filename_grep_rewrite(
        "grep", {"pattern": "README.md", "path": "src/app.py"}
    )
    assert inside == "grep"


def test_grep_filename_lists_dir_without_reading_contents(workspace: Path) -> None:
    out = execute_builtin_tool("grep", {"pattern": "README.md"})
    assert "README.md" in out
    assert "hello" not in out
    assert "see README.md" not in out
    assert "app.py:" not in out


def test_aci_descriptions_say_when_not_to_use() -> None:
    by_name = {item["name"]: item["description"] for item in list_builtin_tools()}
    listed = by_name["list_dir"].lower()
    assert "filename" in listed or "exist" in listed
    assert "filename" in by_name["grep"].lower()
    assert "list_dir" in by_name["grep"]


def test_rewritten_step_bar_is_list_not_search() -> None:
    name, args = apply_filename_grep_rewrite(
        "clutch-tools__grep", {"pattern": "README.md"}
    )
    step = make_tool_step(tool_alias=name, func_args=args, status="completed", step_idx=0)
    assert step["kind"] == "list"
    assert step["title"].startswith("List")
    assert "Search" not in step["title"]
    assert verb_group_header_label([step]).startswith("Listed")
    assert "Searched" not in verb_group_header_label([step])


def test_existence_prompt_nudges_list_dir_only() -> None:
    expect = classify_tool_expectation(
        PM_PROMPT, available_tools={"list_dir", "grep", "read_file"}
    )
    assert expect is not None
    assert expect.kind == "file_exists"
    assert "list_dir" in expect.nudge
    assert "grep" in expect.nudge.lower() or "Do NOT" in expect.nudge
