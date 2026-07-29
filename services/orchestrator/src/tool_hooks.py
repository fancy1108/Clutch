"""D17 — PreToolUse / PostToolUse hook rules (user + project JSON)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.workspace import get_workspace


@dataclass(frozen=True)
class HookVerdict:
    allowed: bool
    reason: str = ""
    phase: str = "PreToolUse"


def _user_hooks_path() -> Path:
    from src.preferences_storage import preferences_dir

    return preferences_dir() / "hooks.json"


def _project_hooks_path() -> Path | None:
    workspace = get_workspace()
    if not workspace:
        return None
    root = Path(str(workspace.get("workspace_path") or ""))
    if not root.is_dir():
        return None
    return root / ".clutch" / "hooks.json"


def _pack_hooks_paths() -> list[Path]:
    try:
        from src.capability_pack import installed_pack_hooks_paths

        return installed_pack_hooks_paths()
    except Exception:
        return []


def _load_hooks_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _merged_rules(phase: str) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for path in [_user_hooks_path(), *_pack_hooks_paths(), _project_hooks_path() or Path()]:
        if not path or not path.is_file():
            continue
        blob = _load_hooks_file(path)
        chunk = blob.get(phase) or blob.get(phase.lower())
        if isinstance(chunk, list):
            rules.extend([item for item in chunk if isinstance(item, dict)])
    return rules


def _tool_matches(rule: dict[str, Any], tool_name: str) -> bool:
    pattern = str(rule.get("tool") or rule.get("name") or "*").strip()
    if not pattern or pattern == "*":
        return True
    if pattern == tool_name:
        return True
    try:
        return bool(re.search(pattern, tool_name, re.I))
    except re.error:
        return pattern.lower() == tool_name.lower()


def _path_matches(rule: dict[str, Any], func_args: dict[str, Any]) -> bool:
    path_pattern = str(rule.get("path_pattern") or rule.get("path") or "").strip()
    if not path_pattern:
        return True
    path = str(func_args.get("path") or func_args.get("file_path") or "").strip()
    if not path:
        return True
    try:
        return bool(re.search(path_pattern, path, re.I))
    except re.error:
        return path_pattern.lower() in path.lower()


def _evaluate(phase: str, tool_name: str, func_args: dict[str, Any]) -> HookVerdict:
    for rule in _merged_rules(phase):
        action = str(rule.get("action") or "deny").strip().lower()
        if action not in {"deny", "block", "reject"}:
            continue
        if not _tool_matches(rule, tool_name):
            continue
        if not _path_matches(rule, func_args):
            continue
        reason = str(rule.get("reason") or rule.get("message") or "Hook denied this tool call.")
        return HookVerdict(allowed=False, reason=reason, phase=phase)
    return HookVerdict(allowed=True, phase=phase)


def evaluate_pretool(tool_name: str, func_args: dict[str, Any]) -> HookVerdict:
    return _evaluate("PreToolUse", tool_name, func_args or {})


def evaluate_posttool(
    tool_name: str,
    func_args: dict[str, Any],
    result_str: str,
) -> HookVerdict:
    verdict = _evaluate("PostToolUse", tool_name, func_args or {})
    if not verdict.allowed:
        return verdict
    for rule in _merged_rules("PostToolUse"):
        action = str(rule.get("action") or "deny").strip().lower()
        if action not in {"deny", "block", "reject"}:
            continue
        if not _tool_matches(rule, tool_name):
            continue
        pattern = str(rule.get("result_pattern") or "").strip()
        if pattern:
            try:
                if not re.search(pattern, result_str, re.I):
                    continue
            except re.error:
                if pattern.lower() not in result_str.lower():
                    continue
        reason = str(rule.get("reason") or rule.get("message") or "Hook rejected tool output.")
        return HookVerdict(allowed=False, reason=reason, phase="PostToolUse")
    return HookVerdict(allowed=True, phase="PostToolUse")


def format_hook_denial_message(verdict: HookVerdict, tool_name: str) -> str:
    return f"Hook {verdict.phase} blocked `{tool_name}`: {verdict.reason}"
