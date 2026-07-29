"""Unit tests for D46 structured tool steps / verb_group labels."""

from src.tool_steps import (
    append_tool_result_detail,
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
    assert kind_for_tool("web_fetch") == "fetch"
    assert kind_for_tool("web_search") == "search"
    assert kind_for_tool("list_dir") == "list"
    assert kind_for_tool("apply_patch") == "edit"
    assert kind_for_tool("run_terminal_cmd") == "execute"


def test_humanize_todo_write_uses_target_content() -> None:
    title, detail = humanize_tool_step(
        "todo_write",
        {
            "todos": [
                {"id": "1", "content": "整理中国古代著名皇帝及事件", "status": "completed"},
                {"id": "2", "content": "生成包含皇帝和事件的HTML页面", "status": "in_progress"},
            ]
        },
    )
    assert "生成包含皇帝和事件的HTML页面" in title
    assert title.startswith("Todos")
    assert "[in_progress]" in detail
    assert "Update 2 todos" not in title


def test_humanize_web_fetch_and_search() -> None:
    title, detail = humanize_tool_step(
        "web_fetch",
        {"url": "https://www.shanghai.disney.com/events"},
    )
    assert title.startswith("Fetched")
    assert "shanghai.disney.com" in title.lower() or "disney" in title.lower()
    assert detail.startswith("https://")
    st, sd = humanize_tool_step("web_search", {"query": "上海迪士尼 活动"})
    assert "上海迪士尼" in st
    assert sd == "上海迪士尼 活动"


def test_append_fetch_result_keeps_url() -> None:
    step = make_tool_step(
        tool_alias="web_fetch",
        func_args={"url": "https://example.com/a"},
        status="completed",
        step_idx=0,
    )
    merged = append_tool_result_detail(
        step,
        "web_fetch",
        "<html><body>Hello Disney events page</body></html>" * 20,
    )
    detail = merged["detail"]
    assert "https://example.com/a" in detail
    assert "── result" in detail
    assert "Hello Disney" in detail


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
    assert verb_group_header_label(steps) == "Read 2 files, Searched 1 query"
    steps[2]["status"] = "running"
    assert verb_group_header_label(steps) == "Reading 2 files, Searching 1 query"


def test_verb_group_header_fetch_pages() -> None:
    steps = [
        make_tool_step(
            tool_alias="web_fetch",
            func_args={"url": "https://a.example/x"},
            status="completed",
            step_idx=0,
            step_id="a",
        ),
        make_tool_step(
            tool_alias="web_fetch",
            func_args={"url": "https://b.example/y"},
            status="completed",
            step_idx=1,
            step_id="b",
        ),
    ]
    assert verb_group_header_label(steps) == "Fetched 2 pages"
