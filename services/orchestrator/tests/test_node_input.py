"""Node input resolution for Flow agent_task (D23)."""

from __future__ import annotations

from src.compiler.node_input import resolve_agent_task_input


def test_start_upstream_uses_user_instruction() -> None:
    workflow = {
        "edges": [{"id": "e1", "source": "start", "target": "n1"}],
    }
    node = {"id": "n1", "data": {"instruction": "Research step"}}
    state = {
        "current_instruction": "上海天气怎么样",
        "node_outputs": {},
    }
    resolved = resolve_agent_task_input(state, node, workflow)
    assert "上海天气怎么样" in resolved
    assert resolved.startswith("Research step")


def test_downstream_uses_upstream_output() -> None:
    workflow = {
        "edges": [
            {"id": "e1", "source": "start", "target": "n1"},
            {"id": "e2", "source": "n1", "target": "n2"},
        ],
    }
    node = {"id": "n2", "data": {"instruction": "Paint this scene"}}
    state = {
        "current_instruction": "用户原始问题",
        "node_outputs": {"n1": "黄昏时分的上海外滩，江面雾气，霓虹初上。"},
    }
    resolved = resolve_agent_task_input(state, node, workflow)
    assert "黄昏时分的上海外滩" in resolved
    assert "用户原始问题" not in resolved
    assert resolved.startswith("Paint this scene")
