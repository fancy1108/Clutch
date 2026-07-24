"""Unit tests for D46 structured tool steps / verb_group labels."""

from src.tool_steps import (
    complete_running_steps,
    humanize_tool_step,
    kind_for_tool,
    make_tool_step,
    upsert_tool_step,
    verb_group_header_label,
)


def test_kind_for_builtin_tools() -> None:
    assert kind_for_tool("read_file") == "read"
    assert kind_for_tool("clutch-tools__grep") == "search"
    assert kind_for_tool("list_dir") == "list"
    assert kind_for_tool("apply_patch") == "edit"
    assert kind_for_tool("run_terminal_cmd") == "execute"


def test_humanize_and_make_step() -> None:
    title, detail = humanize_tool_step("read_file", {"path": "README.md"})
    assert title == "Read README.md"
    assert "README" in detail
    step = make_tool_step(
        tool_alias="clutch-tools__grep",
        func_args={"pattern": "Clutch"},
        status="running",
        step_idx=0,
        step_id="tool_0",
    )
    assert step["id"] == "tool_0"
    assert step["kind"] == "search"
    assert step["status"] == "running"
    assert "Search" in step["title"]


def test_humanize_search_includes_path() -> None:
    title, detail = humanize_tool_step("grep", {"pattern": "Clutch", "path": "README.md"})
    assert "Clutch" in title
    assert "README.md" in title
    assert "README.md" in detail
    title2, _ = humanize_tool_step("grep", {"pattern": "Clutch"})
    assert title2.startswith("Search")
    assert " in " not in title2


def test_upsert_and_complete() -> None:
    a = make_tool_step(
        tool_alias="read_file",
        func_args={"path": "a.md"},
        status="running",
        step_idx=0,
        step_id="tool_0",
    )
    b = make_tool_step(
        tool_alias="read_file",
        func_args={"path": "a.md"},
        status="completed",
        step_idx=0,
        step_id="tool_0",
    )
    steps = upsert_tool_step([], a)
    steps = upsert_tool_step(steps, b)
    assert len(steps) == 1
    assert steps[0]["status"] == "completed"
    running = make_tool_step(
        tool_alias="grep",
        func_args={"pattern": "x"},
        status="running",
        step_idx=1,
        step_id="tool_1",
    )
    sealed = complete_running_steps(upsert_tool_step(steps, running))
    assert sealed[-1]["status"] == "completed"


def test_verb_group_header_label() -> None:
    steps = [
        make_tool_step(
            tool_alias="read_file",
            func_args={"path": "a.md"},
            status="completed",
            step_idx=0,
            step_id="a",
        ),
        make_tool_step(
            tool_alias="read_file",
            func_args={"path": "b.md"},
            status="completed",
            step_idx=1,
            step_id="b",
        ),
        make_tool_step(
            tool_alias="grep",
            func_args={"pattern": "x"},
            status="completed",
            step_idx=2,
            step_id="c",
        ),
    ]
    assert verb_group_header_label(steps) == "Read 2 files, Searched 1 pattern"
    steps[2]["status"] = "running"
    assert verb_group_header_label(steps) == "Reading 2 files, Searching 1 pattern"
