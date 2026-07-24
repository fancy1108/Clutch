"""D2/D49 propose_plan pause and plan card helpers."""

from __future__ import annotations

from src.builtin_tools import (
    execute_builtin_tool,
    is_propose_plan_tool,
    list_builtin_tools,
    normalize_plan_args,
)
from src.chat_runner import _chat_message, _is_plan_pause, _messages_for_mcp_pause, _patch_plan_card_status


def test_propose_plan_is_listed_builtin() -> None:
    names = {t["name"] for t in list_builtin_tools()}
    assert "propose_plan" in names


def test_normalize_and_execute_propose_plan() -> None:
    plan = normalize_plan_args(
        {"title": "Add login", "steps": ["Add route", "Wire auth"], "summary": "MVP"}
    )
    assert plan["title"] == "Add login"
    assert len(plan["steps"]) == 2
    out = execute_builtin_tool("propose_plan", plan)
    assert "Plan approved" in out
    assert "Add route" in out


def test_normalize_plan_strips_leading_step_numbers() -> None:
    plan = normalize_plan_args(
        {
            "title": "Health",
            "steps": [
                "1. Create health.py",
                "2) Update README",
                "3、Run import check",
                "1. 1. Double numbered",
            ],
        }
    )
    assert plan["steps"] == [
        "Create health.py",
        "Update README",
        "Run import check",
        "Double numbered",
    ]


def test_is_propose_plan_tool_alias() -> None:
    assert is_propose_plan_tool("propose_plan")
    assert is_propose_plan_tool("clutch-tools__propose_plan")
    assert not is_propose_plan_tool("search_replace")


def test_plan_pause_message_seals_plan_card() -> None:
    pause = {
        "kind": "plan",
        "func_name": "clutch-tools__propose_plan",
        "func_args": {"title": "Add login", "steps": ["A", "B"]},
        "tool_steps": [],
    }
    assert _is_plan_pause(pause)
    messages, msg, created = _messages_for_mcp_pause([], pause, reply_label="Clutch Agent")
    assert created is True
    assert len(messages) == 1
    assert msg["text"] == ""
    assert msg["planCard"]["title"] == "Add login"
    assert msg["planCard"]["status"] == "pending"
    assert msg["planCard"]["steps"] == ["A", "B"]
    assert "toolSteps" not in msg


def test_supervisor_gate_dedupes_same_approval_key() -> None:
    from src.chat_runner import _supervisor_gate_messages

    args = {"patch": "*** Begin Patch\n*** Add File: a.py\n+x\n*** End Patch"}
    messages, msg, created = _supervisor_gate_messages([], "clutch-tools__apply_patch", args)
    assert created is True
    assert len(messages) == 1
    again, msg2, created2 = _supervisor_gate_messages(messages, "clutch-tools__apply_patch", args)
    assert created2 is False
    assert len(again) == 1
    assert msg2 is msg

    base = _chat_message(
        "Clutch Agent",
        "plan",
        plan_card={"title": "T", "steps": ["1"], "status": "pending"},
    )
    updated = _patch_plan_card_status([base], status="approved")
    assert updated[0]["planCard"]["status"] == "approved"


def test_feature_request_heuristic_and_reminder() -> None:
    from src.agent_prompt import compose_agent_prompt_assembly, looks_like_feature_request

    assert looks_like_feature_request("帮我加一个简单的登录：登录页 + 假校验即可")
    assert looks_like_feature_request("Add a login page with fake auth")
    assert not looks_like_feature_request("README 第一行是什么？")

    agent = {
        "id": "clutch-agent",
        "name": "Clutch Agent",
        "agentType": "clutch",
        "markdownDoc": "## Protocol\n- Prefer tools.\n",
        "skills": [],
    }
    assembly = compose_agent_prompt_assembly(
        agent,
        model_name="Test",
        model_api="test",
        mcp_servers_bound=True,
        permission_mode="ask",
        user_turn_text="帮我加一个简单的登录",
        include_project_rules=False,
    )
    mode = next((layer for layer in assembly.layers if layer.name == "mode"), None)
    assert mode is not None
    assert "propose_plan required" in mode.content
