"""Structured Chat/MCP tool steps for D46 (Grok-style verb_group transcript)."""

from __future__ import annotations

import json
import uuid
from typing import Any, Literal

ToolStepKind = Literal["read", "search", "list", "edit", "execute", "other"]
ToolStepStatus = Literal["running", "completed", "failed", "awaiting"]

_KIND_BY_TOOL: dict[str, ToolStepKind] = {
    "read_file": "read",
    "list_dir": "list",
    "grep": "search",
    "search_replace": "edit",
    "apply_patch": "edit",
    "run_terminal_cmd": "execute",
    "propose_plan": "other",
    "todo_write": "other",
    "ask_user_question": "other",
    "submit_verification": "other",
    "write_file": "edit",
    "edit_file": "edit",
    "create_file": "edit",
    "delete_file": "edit",
    "directory_tree": "list",
    "list_directory": "list",
    "list_directory_with_sizes": "list",
    "search_files": "search",
    "get_file_info": "read",
    "move_file": "edit",
}


def short_tool_name(alias: str) -> str:
    if "__" in alias:
        return alias.split("__", 1)[1] or alias
    return alias


def kind_for_tool(tool: str) -> ToolStepKind:
    key = short_tool_name(tool).lower().replace("-", "_")
    if key in _KIND_BY_TOOL:
        return _KIND_BY_TOOL[key]
    if any(tok in key for tok in ("grep", "search")):
        return "search"
    if any(tok in key for tok in ("list", "dir", "tree")):
        return "list"
    if any(tok in key for tok in ("read", "get_file", "cat")):
        return "read"
    if any(tok in key for tok in ("write", "edit", "patch", "delete", "create", "replace")):
        return "edit"
    if any(tok in key for tok in ("run", "shell", "exec", "command", "bash")):
        return "execute"
    return "other"


def _basename(path: str) -> str:
    normalized = path.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p]
    return parts[-1] if parts else path


def _compact(text: str, max_len: int = 48) -> str:
    trimmed = text.strip()
    if len(trimmed) <= max_len:
        return trimmed
    return f"{trimmed[: max_len - 1]}…"


def _pick(args: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _patch_title(patch: str) -> tuple[str, str]:
    if "Delete File:" in patch:
        name = patch.split("Delete File:", 1)[1].split("\n", 1)[0].strip() or "file"
        return f"Delete {_compact(_basename(name), 40)}", patch
    if "Create File:" in patch:
        name = patch.split("Create File:", 1)[1].split("\n", 1)[0].strip() or "file"
        return f"Create {_compact(_basename(name), 40)}", patch
    if "Update File:" in patch:
        name = patch.split("Update File:", 1)[1].split("\n", 1)[0].strip() or "file"
        return f"Edit {_compact(_basename(name), 40)}", patch
    return "Patch workspace", patch


def humanize_tool_step(tool: str, args: dict[str, Any] | None) -> tuple[str, str]:
    """Return (title, detail) one-liners for a tool call."""
    short = short_tool_name(tool)
    payload = args if isinstance(args, dict) else {}
    path = _pick(payload, ("path", "file_path", "file", "target"))
    pattern = _pick(payload, ("pattern", "query", "regex"))
    command = _pick(payload, ("command", "cmd"))
    patch = _pick(payload, ("patch",))
    detail = json.dumps(payload, ensure_ascii=False)[:240] if payload else short

    if short in {"todo_write", "write_todos", "update_todos"}:
        todos = payload.get("todos")
        n = len(todos) if isinstance(todos, list) else 0
        lines: list[str] = []
        if isinstance(todos, list):
            for item in todos[:6]:
                if not isinstance(item, dict):
                    continue
                content = str(item.get("content") or item.get("text") or "").strip()
                status = str(item.get("status") or "pending").strip()
                if content:
                    lines.append(f"[{status}] {content}")
        return (
            f"Update {n} todos" if n else "Update todos",
            "\n".join(lines) if lines else _compact(detail, 160),
        )
    if short in {"propose_plan", "create_plan"}:
        title = _pick(payload, ("title",)) or "Plan"
        steps = payload.get("steps")
        n = len(steps) if isinstance(steps, list) else 0
        return f"Propose plan: {_compact(title, 36)}", (
            f"{n} steps" if n else _compact(str(payload.get("summary") or detail), 160)
        )
    if short in {"ask_user_question", "ask_question", "user_question"}:
        question = _pick(payload, ("question", "prompt")) or "Question"
        opts = payload.get("options")
        n = len(opts) if isinstance(opts, list) else 0
        return f"Ask: {_compact(question, 40)}", f"{n} options" if n else detail
    if short in {
        "submit_verification",
        "verification_report",
        "submit_verification_report",
    }:
        title = _pick(payload, ("title", "name")) or "Verification"
        conclusion = str(payload.get("conclusion") or "").strip().lower() or "?"
        steps = payload.get("steps")
        n = len(steps) if isinstance(steps, list) else 0
        return (
            f"Verify ({conclusion}): {_compact(title, 32)}",
            f"{n} checks" if n else detail,
        )
    kind = kind_for_tool(short)
    if short == "apply_patch" or (kind == "edit" and patch):
        title, raw = _patch_title(patch or "")
        return title, _compact(raw or detail, 160)
    if kind == "list":
        focus = _compact(path or ".", 40)
        return f"List {focus}", path or "."
    if kind == "read":
        focus = _compact(_basename(path) if path else "file", 40)
        return f"Read {focus}", path or detail
    if kind == "search":
        pat = _compact(f"“{pattern}”", 36) if pattern else "workspace"
        if path:
            where = _compact(_basename(path), 28)
            return f"Search {pat} in {where}", (
                f"{pattern} · {path}" if pattern else path
            )
        return f"Search {pat}", pattern or detail
    if kind == "edit":
        focus = _compact(_basename(path) if path else "file", 40)
        return f"Edit {focus}", path or detail
    if kind == "execute":
        focus = _compact(command, 44) if command else "shell"
        return f"Run {focus}", command or detail
    focus = _compact(path or pattern or command or short, 40)
    return f"{short.replace('_', ' ')} {focus}".strip(), detail


def make_tool_step(
    *,
    tool_alias: str,
    func_args: dict[str, Any] | None,
    status: ToolStepStatus,
    step_idx: int,
    step_id: str | None = None,
) -> dict[str, Any]:
    title, detail = humanize_tool_step(tool_alias, func_args or {})
    short = short_tool_name(tool_alias)
    return {
        "id": step_id or f"tool_{step_idx}_{uuid.uuid4().hex[:8]}",
        "kind": kind_for_tool(short),
        "tool": short,
        "status": status,
        "title": title,
        "detail": detail,
    }


def upsert_tool_step(steps: list[dict[str, Any]], step: dict[str, Any]) -> list[dict[str, Any]]:
    """Replace by id or append; returns a new list."""
    out = list(steps)
    for i, existing in enumerate(out):
        if str(existing.get("id")) == str(step.get("id")):
            out[i] = {**existing, **step}
            return out
    out.append(step)
    return out


def mark_last_awaiting(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not steps:
        return steps
    out = [dict(s) for s in steps]
    out[-1]["status"] = "awaiting"
    return out


def complete_running_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for step in steps:
        next_step = dict(step)
        if next_step.get("status") in {"running", "awaiting"}:
            next_step["status"] = "completed"
        out.append(next_step)
    return out


_HEADER_NOUN: dict[ToolStepKind, tuple[str, str]] = {
    "read": ("file", "files"),
    "search": ("pattern", "patterns"),
    "list": ("dir", "dirs"),
    "edit": ("edit", "edits"),
    "execute": ("command", "commands"),
    "other": ("tool", "tools"),
}

_HEADER_VERB_RUNNING: dict[ToolStepKind, str] = {
    "read": "Reading",
    "search": "Searching",
    "list": "Listing",
    "edit": "Editing",
    "execute": "Running",
    "other": "Using",
}

_HEADER_VERB_DONE: dict[ToolStepKind, str] = {
    "read": "Read",
    "search": "Searched",
    "list": "Listed",
    "edit": "Edited",
    "execute": "Ran",
    "other": "Used",
}


def verb_group_header_label(steps: list[dict[str, Any]]) -> str:
    """Grok-style fold header: 'Read 2 files, Searched 1 pattern'."""
    if not steps:
        return ""
    any_running = any(str(s.get("status")) in {"running", "awaiting"} for s in steps)
    verbs = _HEADER_VERB_RUNNING if any_running else _HEADER_VERB_DONE
    counts: dict[str, int] = {}
    for step in steps:
        kind = str(step.get("kind") or "other")
        if kind not in _HEADER_NOUN:
            kind = "other"
        counts[kind] = counts.get(kind, 0) + 1
    order: list[ToolStepKind] = ["read", "search", "list", "edit", "execute", "other"]
    parts: list[str] = []
    for kind in order:
        n = counts.get(kind, 0)
        if not n:
            continue
        singular, plural = _HEADER_NOUN[kind]
        noun = singular if n == 1 else plural
        parts.append(f"{verbs[kind]} {n} {noun}")
    return ", ".join(parts) if parts else ("Working…" if any_running else "Tools")
