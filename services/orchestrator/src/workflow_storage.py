"""User workflow persistence — D5 builtin templates vs app data dir (M1-09)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Literal

from src.workflow_validator import WorkflowValidationError, validate_workflow, workflows_dir

WorkflowSource = Literal["template", "user"]
USER_WORKFLOWS_ENV = "CLUTCH_USER_WORKFLOWS_DIR"


def user_workflows_dir() -> Path:
    override = os.environ.get(USER_WORKFLOWS_ENV)
    if override:
        return Path(override)
    from src.storage_helper import get_storage_dir
    return get_storage_dir() / "workflows"


def _ensure_user_dir() -> Path:
    path = user_workflows_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _workflow_path(directory: Path, workflow_id: str) -> Path:
    return directory / f"{workflow_id}.json"


def list_templates() -> list[str]:
    return sorted(
        path.stem
        for path in workflows_dir().glob("*.json")
        if path.name != "workflow.schema.json"
    )


def get_template(workflow_id: str) -> dict[str, Any]:
    from src.workflow_validator import load_workflow_by_id

    return load_workflow_by_id(workflow_id)


def list_user_workflows() -> list[str]:
    directory = user_workflows_dir()
    if not directory.is_dir():
        return []
    return sorted(path.stem for path in directory.glob("*.json"))


def get_user_workflow(workflow_id: str) -> dict[str, Any]:
    path = _workflow_path(user_workflows_dir(), workflow_id)
    if not path.is_file():
        raise WorkflowValidationError(f"未找到用户工作流：{workflow_id}", [])
    return _load_json_workflow(path, workflow_id)


def save_user_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    validate_workflow(workflow)
    workflow_id = workflow.get("id")
    if not workflow_id or not isinstance(workflow_id, str):
        raise WorkflowValidationError("工作流 id 不能为空", [])

    path = _workflow_path(_ensure_user_dir(), workflow_id)
    path.write_text(
        json.dumps(workflow, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return workflow


def delete_user_workflow(workflow_id: str) -> None:
    path = _workflow_path(user_workflows_dir(), workflow_id)
    if not path.is_file():
        raise WorkflowValidationError(f"未找到用户工作流：{workflow_id}", [])
    path.unlink()


def resolve_workflow(workflow_id: str) -> tuple[dict[str, Any], WorkflowSource]:
    """User workflows override built-in templates with the same id."""
    user_path = _workflow_path(user_workflows_dir(), workflow_id)
    if user_path.is_file():
        return _load_json_workflow(user_path, workflow_id), "user"

    from src.workflow_validator import load_and_validate_workflow

    return load_and_validate_workflow(workflow_id), "template"


def _load_json_workflow(path: Path, expected_id: str) -> dict[str, Any]:
    try:
        workflow = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkflowValidationError(f"工作流文件 JSON 解析失败：{path.name}", [str(exc)]) from exc

    if not isinstance(workflow, dict):
        raise WorkflowValidationError("工作流文件必须是 JSON 对象", [])

    validate_workflow(workflow)
    if workflow.get("id") != expected_id:
        raise WorkflowValidationError(
            f"工作流 id 与文件名不一致：文件 {expected_id}.json，内容 id={workflow.get('id')!r}",
            [],
        )
    return workflow
