"""Workflow JSON validation against workflows/workflow.schema.json (M1-01)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = _REPO_ROOT / "workflows" / "workflow.schema.json"
_WORKFLOWS_DIR = _REPO_ROOT / "workflows"


def workflows_dir() -> Path:
    """Built-in read-only workflow templates directory (D5)."""
    return _WORKFLOWS_DIR


class WorkflowValidationError(ValueError):
    """Raised when workflow JSON fails schema validation."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or []


@lru_cache(maxsize=1)
def _load_schema() -> dict[str, Any]:
    if not _SCHEMA_PATH.is_file():
        raise WorkflowValidationError(f"未找到 Schema 文件：{_SCHEMA_PATH}", [])
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_workflow(workflow: dict[str, Any]) -> None:
    """Validate workflow dict; raise WorkflowValidationError with readable paths."""
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(workflow), key=lambda item: list(item.absolute_path))
    if errors:
        formatted = [
            f"{'.'.join(str(part) for part in err.absolute_path) or '（根）'}: {err.message}"
            for err in errors[:10]
        ]
        raise WorkflowValidationError("工作流 JSON 不符合 Schema 规范", formatted)

    validate_workflow_graph(workflow)


def validate_workflow_graph(workflow: dict[str, Any]) -> None:
    """Graph-level checks: start/end connectivity and isolated nodes (M1-07)."""
    errors: list[str] = []
    nodes = workflow.get("nodes", [])
    node_ids = {node["id"] for node in nodes}
    has_end = any(node.get("type") == "end" for node in nodes)
    if not has_end:
        errors.append("工作流缺少结束节点")

    edges = workflow.get("edges", [])
    if not any(edge.get("source") == "start" for edge in edges):
        errors.append("工作流缺少开始节点连接")

    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    adjacency["start"] = []
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source in adjacency:
            adjacency[source].append(str(target))

    reachable: set[str] = set()
    queue = ["start"]
    while queue:
        current = queue.pop()
        for target in adjacency.get(current, []):
            if target in node_ids and target not in reachable:
                reachable.add(target)
                queue.append(target)

    for node_id in sorted(node_ids - reachable):
        errors.append(f"孤立节点：{node_id} 未与开始节点连通")

    if errors:
        raise WorkflowValidationError("工作流图结构无效", errors)


def load_workflow_by_id(workflow_id: str) -> dict[str, Any]:
    """Load built-in workflow template from workflows/{workflow_id}.json."""
    path = _WORKFLOWS_DIR / f"{workflow_id}.json"
    if not path.is_file():
        raise WorkflowValidationError(f"未找到工作流模板：{workflow_id}", [])

    try:
        workflow = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkflowValidationError(f"工作流文件 JSON 解析失败：{path.name}", [str(exc)]) from exc

    if not isinstance(workflow, dict):
        raise WorkflowValidationError("工作流文件必须是 JSON 对象", [])

    validate_workflow(workflow)
    return workflow


def load_and_validate_workflow(workflow_id: str) -> dict[str, Any]:
    """Load template and ensure file id matches workflow.id."""
    workflow = load_workflow_by_id(workflow_id)
    if workflow.get("id") != workflow_id:
        raise WorkflowValidationError(
            f"工作流 id 与文件名不一致：文件 {workflow_id}.json，内容 id={workflow.get('id')!r}",
            [],
        )
    return workflow
