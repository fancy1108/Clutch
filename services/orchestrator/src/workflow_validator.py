"""Workflow JSON validation against workflows/workflow.schema.json (M1-01)."""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from src.preferences_storage import tr


def _bundle_root() -> Path:
    """Repo root in dev; PyInstaller extraction dir when frozen (M4-06)."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)))
    candidates.append(Path(__file__).resolve().parents[3])
    for parent in Path(__file__).resolve().parents:
        candidates.append(parent)

    for root in candidates:
        if (root / "workflows" / "workflow.schema.json").is_file():
            return root

    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return Path(__file__).resolve().parents[3]


def workflows_dir() -> Path:
    """Built-in read-only workflow templates directory (D5)."""
    candidates = [
        Path(__file__).resolve().parent / "workflow_assets",
        _bundle_root() / "workflows",
        Path(__file__).resolve().parents[3] / "workflows",
    ]
    for path in candidates:
        if (path / "workflow.schema.json").is_file():
            return path
    return candidates[-1]


def _schema_path() -> Path:
    return workflows_dir() / "workflow.schema.json"


class WorkflowValidationError(ValueError):
    """Raised when workflow JSON fails schema validation."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or []


@lru_cache(maxsize=1)
def _load_schema() -> dict[str, Any]:
    schema_path = _schema_path()
    if not schema_path.is_file():
        raise WorkflowValidationError(
            tr(
                f"Schema file not found: {schema_path}",
                f"未找到 Schema 文件：{schema_path}",
            ),
            [],
        )
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_workflow(workflow: dict[str, Any]) -> None:
    """Validate workflow dict; raise WorkflowValidationError with readable paths."""
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(workflow), key=lambda item: list(item.absolute_path))
    if errors:
        root_label = tr("(root)", "（根）")
        formatted = [
            f"{'.'.join(str(part) for part in err.absolute_path) or root_label}: {err.message}"
            for err in errors[:10]
        ]
        raise WorkflowValidationError(
            tr("Workflow JSON does not conform to Schema specifications", "工作流 JSON 不符合 Schema 规范"),
            formatted,
        )

    validate_workflow_graph(workflow)


def validate_workflow_graph(workflow: dict[str, Any]) -> None:
    """Graph-level checks: start/end connectivity and isolated nodes (M1-07)."""
    errors: list[str] = []
    nodes = workflow.get("nodes", [])
    node_ids = {node["id"] for node in nodes}
    has_end = any(node.get("type") == "end" for node in nodes)
    if not has_end:
        errors.append(tr("Workflow is missing end node", "工作流缺少结束节点"))

    edges = workflow.get("edges", [])
    if not any(edge.get("source") == "start" for edge in edges):
        errors.append(tr("Workflow is missing start node connection", "工作流缺少开始节点连接"))

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
        errors.append(
            tr(
                f"Isolated node: {node_id} is not connected to start node",
                f"孤立节点：{node_id} 未与开始节点连通",
            )
        )

    if errors:
        raise WorkflowValidationError(
            tr("Workflow graph structure is invalid", "工作流图结构无效"), errors
        )


def load_workflow_by_id(workflow_id: str) -> dict[str, Any]:
    """Load built-in workflow template from workflows/{workflow_id}.json."""
    path = workflows_dir() / f"{workflow_id}.json"
    if not path.is_file():
        raise WorkflowValidationError(
            tr(
                f"Workflow template not found: {workflow_id}",
                f"未找到工作流模板：{workflow_id}",
            ),
            [],
        )

    try:
        workflow = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkflowValidationError(
            tr(
                f"Failed to parse workflow JSON file: {path.name}",
                f"工作流文件 JSON 解析失败：{path.name}",
            ),
            [str(exc)],
        ) from exc

    if not isinstance(workflow, dict):
        raise WorkflowValidationError(
            tr("Workflow file must be a JSON object", "工作流文件必须是 JSON 对象"), []
        )

    validate_workflow(workflow)
    return workflow


def load_and_validate_workflow(workflow_id: str) -> dict[str, Any]:
    """Load template and ensure file id matches workflow.id."""
    workflow = load_workflow_by_id(workflow_id)
    if workflow.get("id") != workflow_id:
        raise WorkflowValidationError(
            tr(
                f"Workflow ID does not match filename: file {workflow_id}.json, content id={workflow.get('id')!r}",
                f"工作流 id 与文件名不一致：文件 {workflow_id}.json，内容 id={workflow.get('id')!r}",
            ),
            [],
        )
    return workflow
