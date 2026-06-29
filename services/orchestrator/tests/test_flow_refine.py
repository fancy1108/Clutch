"""Tests for flow pause → refine → resume."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.flow_refine import (
    build_refine_system_appendix,
    continue_workflow_after_refine,
    infer_refining_node_id,
    is_continue_command,
    is_workflow_refine_eligible,
    parse_agent_mention,
    rebuild_node_outputs_from_messages,
    refine_reply_ready_to_commit,
    refine_triggered_by_message,
    resolve_image_refine_prompt,
    workflow_node_id_for_agent,
)
from src.runtime_config import hybrid_eligible


def test_parse_agent_mention() -> None:
    agent, body = parse_agent_mention("@Scriptwriter make it darker")
    assert agent == "Scriptwriter"
    assert body == "make it darker"


def test_parse_agent_mention_supports_spaces_in_label() -> None:
    workflow = {
        "nodes": [
            {
                "id": "n5",
                "type": "agent_task",
                "data": {"label": "5-Visual Rendering Engine", "agent": "agent-img"},
            },
        ],
        "edges": [{"source": "start", "target": "n5"}],
    }
    agent, body = parse_agent_mention(
        "@5-Visual Rendering Engine 重新生成图片",
        workflow=workflow,
    )
    assert agent == "5-Visual Rendering Engine"
    assert body == "重新生成图片"


def test_resolve_image_refine_prompt_uses_upstream_json() -> None:
    workflow = {
        "nodes": [
            {"id": "n4", "type": "agent_task", "data": {"label": "Prompt", "agent": "a4"}},
            {"id": "n5", "type": "agent_task", "data": {"label": "Image", "agent": "a5"}},
        ],
        "edges": [
            {"source": "start", "target": "n4"},
            {"source": "n4", "target": "n5"},
        ],
    }
    compiled = MagicMock()
    compiled.get_state.return_value = MagicMock(
        values={
            "node_outputs": {
                "n4": '{"final_image_prompt":"green dragon in mist"}',
                "n5": "![Generated image](http://example.com/x.png)",
            }
        }
    )
    session = MagicMock()
    session.compiled = compiled
    session.workflow = workflow
    prompt = resolve_image_refine_prompt(
        session=session,
        refining_node_id="n5",
        user_body="重新生成图片",
        messages=[],
    )
    assert "green dragon in mist" in prompt
    assert "重新生成图片" in prompt


def test_resolve_image_refine_prompt_falls_back_to_full_upstream_json() -> None:
    workflow = {
        "nodes": [
            {"id": "n4", "type": "agent_task", "data": {"label": "Prompt", "agent": "a4"}},
            {"id": "n5", "type": "agent_task", "data": {"label": "Image", "agent": "a5"}},
        ],
        "edges": [
            {"source": "start", "target": "n4"},
            {"source": "n4", "target": "n5"},
        ],
    }
    compiled = MagicMock()
    compiled.get_state.return_value = MagicMock(
        values={
            "node_outputs": {
                "n4": '{"ui_spec":"dark observability dashboard with service map"}',
                "n5": "![Generated image](http://example.com/x.png)",
            }
        }
    )
    session = MagicMock()
    session.compiled = compiled
    session.workflow = workflow
    prompt = resolve_image_refine_prompt(
        session=session,
        refining_node_id="n5",
        user_body="重新生成图片",
        messages=[],
    )
    assert "dark observability dashboard" in prompt
    assert "重新生成图片" in prompt


def test_is_continue_command() -> None:
    assert is_continue_command("/continue")
    assert is_continue_command("继续执行")
    assert not is_continue_command("@Agent hi")


def test_refine_reply_ready_to_commit() -> None:
    assert refine_reply_ready_to_commit("Revised UX spec")
    assert not refine_reply_ready_to_commit("")
    assert not refine_reply_ready_to_commit("   ")
    assert not refine_reply_ready_to_commit("Error: model unavailable")


def test_infer_refining_node_id_prefers_output_node() -> None:
    node_id = infer_refining_node_id(
        clutch_active_node_id="n2",
        compiler_values={"node_outputs": {"n1": "done"}, "active_node_id": "n2"},
    )
    assert node_id == "n2"


def test_hybrid_eligible_flow_refine_without_global_hybrid(monkeypatch) -> None:
    monkeypatch.delenv("CLUTCH_RUNTIME_MODE", raising=False)
    assert hybrid_eligible(source="flow_refine", agent_type="claude-cli")
    assert not hybrid_eligible(source="flow", agent_type="claude-cli")


def test_continue_workflow_after_refine_invokes_graph() -> None:
    graph_result = {
        "run_id": "run_refine",
        "active_node_id": "n3",
        "active_agent": "Artist",
        "status": "running",
        "node_outputs": {"n2": "revised"},
        "task_logs": [],
        "task_messages": [],
        "check_result": "",
        "human_decision": "",
        "current_instruction": "",
    }
    compiled = MagicMock()
    compiled.get_state.return_value = MagicMock(values={"node_outputs": {"n1": "a"}, "status": "running"})
    compiled.invoke.return_value = graph_result
    session = MagicMock()
    session.compiled = compiled
    session.config = {"configurable": {"thread_id": "run_refine"}}
    session.workflow = {"nodes": [], "edges": []}

    result = continue_workflow_after_refine(
        session,
        node_id="n2",
        node_output='{"script":"revised"}',
    )
    compiled.update_state.assert_called_once()
    compiled.invoke.assert_called_once_with(None, session.config)
    assert result["node_outputs"]["n2"] == "revised"


def test_build_refine_system_appendix_includes_output() -> None:
    text = build_refine_system_appendix(
        node_id="n2",
        node_label="Scriptwriter",
        node_output='{"hook":"old"}',
    )
    assert "Scriptwriter" in text
    assert '{"hook":"old"}' in text


def test_rebuild_node_outputs_from_messages() -> None:
    workflow = {
        "nodes": [
            {"id": "n1", "type": "agent_task", "data": {"label": "Writer", "agent": "a1"}},
            {"id": "n2", "type": "agent_task", "data": {"label": "Artist", "agent": "a2"}},
        ],
        "edges": [
            {"source": "start", "target": "n1"},
            {"source": "n1", "target": "n2"},
        ],
    }
    messages = [
        {"agent": "User", "text": "hi"},
        {"agent": "Writer", "text": '{"script":"one"}'},
        {"agent": "Artist", "text": '{"prompt":"two"}'},
    ]
    outputs = rebuild_node_outputs_from_messages(workflow, messages)
    assert outputs["n1"] == '{"script":"one"}'
    assert outputs["n2"] == '{"prompt":"two"}'


def test_refine_eligible_after_passed() -> None:
    state = {"workflow_id": "wf-1", "status": "passed"}
    assert is_workflow_refine_eligible(state)
    assert refine_triggered_by_message("@Artist darker", status="passed")
    assert not refine_triggered_by_message("hello", status="passed")
    workflow = {
        "nodes": [
            {
                "id": "n5",
                "type": "agent_task",
                "data": {"label": "5-Visual Rendering Engine", "agent": "agent-img"},
            },
        ],
        "edges": [{"source": "start", "target": "n5"}],
    }
    assert refine_triggered_by_message(
        "@5-Visual Rendering Engine regen",
        status="passed",
        workflow=workflow,
    )


def test_workflow_node_id_for_agent() -> None:
    workflow = {
        "nodes": [
            {"id": "n1", "type": "agent_task", "data": {"label": "Writer", "agent": "agent-1"}},
        ],
        "edges": [{"source": "start", "target": "n1"}],
    }
    assert workflow_node_id_for_agent(workflow, "agent-1") == "n1"
