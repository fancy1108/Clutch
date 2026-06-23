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
    if not errors:
        return

    formatted = [
        f"{'.'.join(str(part) for part in err.absolute_path) or '（根）'}: {err.message}"
        for err in errors[:10]
    ]
    raise WorkflowValidationError("工作流 JSON 不符合 Schema 规范", formatted)


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
