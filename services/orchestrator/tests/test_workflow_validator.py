import json
from pathlib import Path

import pytest

from src.workflow_validator import (
    WorkflowValidationError,
    load_and_validate_workflow,
    validate_workflow,
    validate_workflow_graph,
)

_AGENT_NODE = {
    "id": "n1",
    "type": "agent_task",
    "data": {"label": "步骤", "agent": "Builder", "instruction": "执行"},
}
_END_NODE = {"id": "end", "type": "end", "data": {"label": "完成"}}

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VIDEO_PRODUCTION = _REPO_ROOT / "workflows" / "video-production.json"


def test_builtin_video_production_passes_schema() -> None:
    workflow = load_and_validate_workflow("video-production")
    assert workflow["id"] == "video-production"
    assert len(workflow["nodes"]) >= 1


def test_validate_workflow_rejects_missing_required_fields() -> None:
    with pytest.raises(WorkflowValidationError) as exc_info:
        validate_workflow({"id": "incomplete"})

    assert "Schema" in exc_info.value.message
    assert exc_info.value.errors


def test_validate_workflow_rejects_invalid_node_type() -> None:
    workflow = json.loads(_VIDEO_PRODUCTION.read_text(encoding="utf-8"))
    workflow["nodes"][0]["type"] = "unknown_type"

    with pytest.raises(WorkflowValidationError) as exc_info:
        validate_workflow(workflow)

    assert any("unknown_type" in err or "enum" in err for err in exc_info.value.errors)


def test_load_unknown_workflow_template() -> None:
    with pytest.raises(WorkflowValidationError) as exc_info:
        load_and_validate_workflow("does-not-exist")

    assert "未找到工作流模板" in exc_info.value.message


def test_invalid_graph_missing_end_node() -> None:
    workflow = {
        "id": "no-end",
        "name": "No End",
        "version": 1,
        "nodes": [_AGENT_NODE],
        "edges": [{"id": "e1", "source": "start", "target": "n1"}],
    }
    with pytest.raises(WorkflowValidationError) as exc_info:
        validate_workflow(workflow)
    assert any("缺少结束节点" in err for err in exc_info.value.errors)


def test_invalid_graph_missing_start_edge() -> None:
    workflow = {
        "id": "no-start",
        "name": "No Start",
        "version": 1,
        "nodes": [_AGENT_NODE, _END_NODE],
        "edges": [{"id": "e1", "source": "n1", "target": "end"}],
    }
    with pytest.raises(WorkflowValidationError) as exc_info:
        validate_workflow(workflow)
    assert any("缺少开始节点连接" in err for err in exc_info.value.errors)


def test_invalid_graph_isolated_node() -> None:
    workflow = {
        "id": "isolated",
        "name": "Isolated",
        "version": 1,
        "nodes": [
            _AGENT_NODE,
            {
                "id": "n2",
                "type": "agent_task",
                "data": {"label": "孤立", "agent": "Builder", "instruction": "未连接"},
            },
            _END_NODE,
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "n1"},
            {"id": "e2", "source": "n1", "target": "end"},
        ],
    }
    with pytest.raises(WorkflowValidationError) as exc_info:
        validate_workflow_graph(workflow)
    assert any("孤立节点" in err for err in exc_info.value.errors)
