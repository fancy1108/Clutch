"""D8 — task_state layer + format helpers."""

from __future__ import annotations

from src.agent_prompt import compose_agent_prompt_assembly
from src.task_state import format_task_state, latest_plan_card


def test_format_task_state_todos_and_plan() -> None:
    text = format_task_state(
        agent_todos=[
            {"content": "Done item", "status": "completed"},
            {"content": "Active item", "status": "in_progress"},
            {"content": "Todo item", "status": "pending"},
        ],
        plan_card={
            "title": "Ship feature",
            "status": "approved",
            "steps": ["A", "B"],
        },
    )
    assert "## Current task state" in text
    assert "Plan: Ship feature (approved)" in text
    assert "[x] Done item" in text
    assert "[~] Active item" in text
    assert "[ ] Todo item" in text
    assert "do NOT call tools" in text


def test_latest_plan_card_skips_cancelled() -> None:
    messages = [
        {"planCard": {"title": "Old", "status": "cancelled", "steps": []}},
        {"planCard": {"title": "Live", "status": "approved", "steps": ["1"]}},
    ]
    card = latest_plan_card(messages)
    assert card is not None
    assert card["title"] == "Live"


def test_assembly_puts_todos_in_trailing_status_not_prefix() -> None:
    assembly = compose_agent_prompt_assembly(
        {
            "id": "clutch-agent",
            "name": "Clutch Agent",
            "agentType": "clutch",
            "markdownDoc": "",
            "skills": [],
        },
        model_name="A",
        model_api="a",
        mcp_servers_bound=False,
        permission_mode="ask",
        include_project_rules=False,
        agent_todos=[{"content": "Finish D8", "status": "in_progress"}],
        plan_card={"title": "D8", "status": "approved", "steps": ["Pin todos"]},
    )
    names = [layer.name for layer in assembly.layers]
    assert "task_state" not in names
    assert "agent_status" in names
    status = assembly.agent_status_text()
    assert "Finish D8" in status
    assert "D8" in status
    assert "Finish D8" not in assembly.as_system_prompt()
