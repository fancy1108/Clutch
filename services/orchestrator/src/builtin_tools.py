"""Built-in Clutch tools (virtual MCP server, no external MCP subprocess)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

CLUTCH_TOOLS_SERVER_ID = "clutch-tools"

_MAX_READ_CHARS = 120_000
_MAX_GREP_HITS = 50
_MAX_LIST_ENTRIES = 200
_DEFAULT_CMD_TIMEOUT_S = 60
_MAX_CMD_OUTPUT_CHARS = 80_000


def resolve_clutch_tools_server() -> dict[str, Any] | None:
    from src.workspace import get_workspace

    if not get_workspace():
        return None
    return {
        "id": CLUTCH_TOOLS_SERVER_ID,
        "name": "Clutch Builtin Tools",
        "type": "builtin",
        "transport": "virtual",
        "enabled": True,
        "builtin": True,
        "virtual": True,
    }


def is_virtual_server(server: dict[str, Any]) -> bool:
    return bool(server.get("virtual")) or server.get("transport") == "virtual"


def list_builtin_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "read_file",
            "description": (
                "Read a text file from the active workspace. "
                "Paths are workspace-relative. Prefer for inspecting code before edits."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Workspace-relative file path."},
                    "offset": {
                        "type": "integer",
                        "description": "1-based start line (optional).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of lines to return (optional).",
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "list_dir",
            "description": "List files and directories under a workspace-relative path.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to workspace (default '.').",
                    }
                },
            },
        },
        {
            "name": "grep",
            "description": (
                "Search file contents in the workspace (ripgrep if available). "
                "Returns matching lines with paths."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex or fixed string to search."},
                    "path": {
                        "type": "string",
                        "description": "Optional subdirectory or file to scope the search.",
                    },
                    "case_insensitive": {"type": "boolean", "description": "Ignore case."},
                },
                "required": ["pattern"],
            },
        },
        {
            "name": "search_replace",
            "description": (
                "Replace an exact string occurrence in a workspace file. "
                "Fails if old_string is missing or not unique unless replace_all is true."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                    "replace_all": {"type": "boolean", "description": "Replace every match."},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
        {
            "name": "run_terminal_cmd",
            "description": (
                "Run a shell command in the workspace root. "
                "Prefer non-interactive commands. Risky — may require human approval."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute."},
                    "timeout_sec": {
                        "type": "integer",
                        "description": f"Timeout seconds (default {_DEFAULT_CMD_TIMEOUT_S}).",
                    },
                },
                "required": ["command"],
            },
        },
        {
            "name": "apply_patch",
            "description": (
                "Apply a Codex-style patch to the active workspace. "
                "Supports *** Add File, *** Delete File, *** Update File, and *** Move to. "
                "Patch must start with '*** Begin Patch' and end with '*** End Patch'. "
                "Add File body lines should preferably start with '+' (e.g. `+hello`); "
                "bare content lines are also accepted. "
                "For deletion (including dotfiles like `.deleted_test.txt`), use "
                "`*** Delete File: .deleted_test.txt` — never use local-fs move_file."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "patch": {
                        "type": "string",
                        "description": "Full patch body including Begin/End markers.",
                    }
                },
                "required": ["patch"],
            },
        },
        {
            "name": "propose_plan",
            "description": (
                "REQUIRED for multi-step feature work (add login, new page, scaffold). "
                "Call this ASAP with title + ordered steps — before writing files and before "
                "asking which framework to use; put stack defaults in the plan. "
                "User must Approve / Revise / Cancel in Chat. "
                "Skip only for trivial Q&A or single-line edits."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short plan title (e.g. Add login).",
                    },
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Ordered implementation steps (3–8 typical). "
                            "Plain text only — do NOT prefix with '1.' / '2.'; the UI numbers them."
                        ),
                    },
                    "summary": {
                        "type": "string",
                        "description": "Optional one-paragraph rationale.",
                    },
                },
                "required": ["title", "steps"],
            },
        },
        {
            "name": "todo_write",
            "description": (
                "Create or replace the session todo list for multi-step work (D3). "
                "Use ≥3 items with statuses pending | in_progress | completed. "
                "Keep exactly one in_progress when working. Call again as status changes. "
                "Todos appear in the Chat timeline."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "content": {"type": "string"},
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "completed"],
                                },
                            },
                            "required": ["content", "status"],
                        },
                        "description": "Full replacement todo list.",
                    },
                    "merge": {
                        "type": "boolean",
                        "description": "If true, merge by id into the existing list (default false = replace).",
                    },
                },
                "required": ["todos"],
            },
        },
    ]


def is_propose_plan_tool(name: str) -> bool:
    short = name.split("__")[-1].lower().replace("-", "_")
    return short == "propose_plan"


def is_todo_write_tool(name: str) -> bool:
    short = name.split("__")[-1].lower().replace("-", "_")
    return short in {"todo_write", "write_todos", "update_todos"}


_TODO_STATUSES = frozenset({"pending", "in_progress", "completed"})


def normalize_todo_items(
    raw: Any,
    *,
    existing: list[dict[str, Any]] | None = None,
    merge: bool = False,
) -> list[dict[str, Any]]:
    """Normalize todo_write args into [{id, content, status}, ...]."""
    items_in: list[Any]
    if isinstance(raw, dict) and "todos" in raw:
        merge = bool(raw.get("merge")) or merge
        items_in = list(raw.get("todos") or [])
    elif isinstance(raw, list):
        items_in = raw
    else:
        items_in = []

    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(items_in):
        if isinstance(item, str):
            content = item.strip()
            status = "pending"
            todo_id = f"todo_{idx + 1}"
        elif isinstance(item, dict):
            content = str(item.get("content") or item.get("text") or item.get("title") or "").strip()
            status = str(item.get("status") or "pending").strip().lower().replace("-", "_")
            if status == "done":
                status = "completed"
            if status == "doing" or status == "active":
                status = "in_progress"
            if status not in _TODO_STATUSES:
                status = "pending"
            todo_id = str(item.get("id") or f"todo_{idx + 1}").strip() or f"todo_{idx + 1}"
        else:
            continue
        if not content:
            continue
        normalized.append({"id": todo_id, "content": content, "status": status})

    if not merge or not existing:
        return normalized

    by_id = {str(t.get("id")): dict(t) for t in existing if isinstance(t, dict)}
    order = [str(t.get("id")) for t in existing if isinstance(t, dict)]
    for item in normalized:
        tid = str(item["id"])
        if tid in by_id:
            by_id[tid] = item
        else:
            by_id[tid] = item
            order.append(tid)
    return [by_id[tid] for tid in order if tid in by_id]


_STEP_INDEX_RE = re.compile(r"^\s*(?:\d+[\.\)\:．、]\s*|\d+\s+)")


def strip_plan_step_index(text: str) -> str:
    """Remove leading '1.' / '1)' (repeat) so PlanCard does not show '1. 1. …'."""
    cleaned = (text or "").strip()
    for _ in range(4):
        next_text = _STEP_INDEX_RE.sub("", cleaned).strip()
        if next_text == cleaned:
            break
        cleaned = next_text
    return cleaned or (text or "").strip()


def normalize_plan_args(func_args: dict[str, Any] | None) -> dict[str, Any]:
    payload = func_args if isinstance(func_args, dict) else {}
    title = str(payload.get("title") or "Plan").strip() or "Plan"
    raw_steps = payload.get("steps")
    steps: list[str] = []
    if isinstance(raw_steps, list):
        for item in raw_steps:
            text = strip_plan_step_index(str(item))
            if text:
                steps.append(text)
    elif isinstance(raw_steps, str) and raw_steps.strip():
        steps = [
            strip_plan_step_index(line.strip(" -*\t"))
            for line in raw_steps.splitlines()
            if line.strip()
        ]
        steps = [s for s in steps if s]
    summary = str(payload.get("summary") or "").strip()
    return {"title": title, "steps": steps, "summary": summary}


def execute_builtin_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    handlers = {
        "read_file": _tool_read_file,
        "list_dir": _tool_list_dir,
        "grep": _tool_grep,
        "search_replace": _tool_search_replace,
        "run_terminal_cmd": _tool_run_terminal_cmd,
        "apply_patch": _tool_apply_patch,
        "propose_plan": _tool_propose_plan,
        "todo_write": _tool_todo_write,
    }
    handler = handlers.get(tool_name)
    if handler is None:
        return f"Error executing tool: unknown builtin tool {tool_name}"
    try:
        return handler(arguments)
    except Exception as exc:
        return f"Error executing tool: {exc}"


def _tool_todo_write(arguments: dict[str, Any]) -> str:
    todos = normalize_todo_items(arguments)
    if not todos:
        return "Error executing tool: todo_write requires a non-empty `todos` array"
    lines = [
        f"- [{t['status']}] {t['id']}: {t['content']}" for t in todos
    ]
    return f"Updated {len(todos)} todo(s):\n" + "\n".join(lines)


def _tool_propose_plan(arguments: dict[str, Any]) -> str:
    plan = normalize_plan_args(arguments)
    steps = plan["steps"]
    numbered = "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1)) or "(no steps)"
    summary = plan["summary"]
    extra = f"\nRationale: {summary}" if summary else ""
    return (
        f"Plan approved by the user: {plan['title']}\n"
        f"Steps:\n{numbered}{extra}\n"
        "Proceed to implement these steps with clutch-tools. "
        "Do not call propose_plan again unless the user asks to revise."
    )


def _tool_apply_patch(arguments: dict[str, Any]) -> str:
    from src.apply_patch import ApplyPatchError, apply_patch_in_workspace, format_apply_patch_result

    patch = str(arguments.get("patch", "")).strip()
    if not patch:
        return "Error executing tool: apply_patch requires non-empty `patch`"
    try:
        return format_apply_patch_result(apply_patch_in_workspace(patch))
    except ApplyPatchError as exc:
        return f"Error executing tool: {exc}"


def _tool_read_file(arguments: dict[str, Any]) -> str:
    from src.workspace import WorkspaceError, resolve_allowed_path

    rel = str(arguments.get("path", "")).strip()
    if not rel:
        return "Error executing tool: read_file requires `path`"
    try:
        target = resolve_allowed_path(rel)
    except WorkspaceError as exc:
        return f"Error executing tool: {exc}"
    if not target.is_file():
        return f"Error executing tool: not a file: {rel}"
    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    offset = arguments.get("offset")
    limit = arguments.get("limit")
    start = 0
    if offset is not None:
        try:
            start = max(0, int(offset) - 1)
        except (TypeError, ValueError):
            start = 0
    end = len(lines)
    if limit is not None:
        try:
            end = min(len(lines), start + max(0, int(limit)))
        except (TypeError, ValueError):
            pass
    sliced = lines[start:end]
    numbered = [f"{start + i + 1}|{line}" for i, line in enumerate(sliced)]
    body = "\n".join(numbered)
    if len(body) > _MAX_READ_CHARS:
        body = body[:_MAX_READ_CHARS] + "\n…[truncated]"
    return body or "(empty file)"


def _tool_list_dir(arguments: dict[str, Any]) -> str:
    from src.workspace import WorkspaceError, resolve_allowed_path

    rel = str(arguments.get("path") or ".").strip() or "."
    try:
        target = resolve_allowed_path(rel)
    except WorkspaceError as exc:
        return f"Error executing tool: {exc}"
    if not target.is_dir():
        return f"Error executing tool: not a directory: {rel}"
    entries: list[str] = []
    try:
        children = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError as exc:
        return f"Error executing tool: {exc}"
    for child in children[:_MAX_LIST_ENTRIES]:
        suffix = "/" if child.is_dir() else ""
        entries.append(f"{child.name}{suffix}")
    extra = len(children) - _MAX_LIST_ENTRIES
    if extra > 0:
        entries.append(f"…and {extra} more")
    return "\n".join(entries) if entries else "(empty directory)"


def _tool_grep(arguments: dict[str, Any]) -> str:
    from src.workspace import WorkspaceError, require_workspace, resolve_allowed_path

    pattern = str(arguments.get("pattern", ""))
    if not pattern:
        return "Error executing tool: grep requires `pattern`"
    scope = str(arguments.get("path") or ".").strip() or "."
    case_insensitive = bool(arguments.get("case_insensitive"))
    try:
        root = require_workspace()
        scope_path = resolve_allowed_path(scope)
    except WorkspaceError as exc:
        return f"Error executing tool: {exc}"

    rg = shutil.which("rg")
    if rg:
        cmd = [rg, "--line-number", "--no-heading", "--color", "never", "-m", str(_MAX_GREP_HITS)]
        if case_insensitive:
            cmd.append("-i")
        cmd.extend(["--", pattern, str(scope_path)])
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return "Error executing tool: grep timed out"
        if proc.returncode not in (0, 1):
            err = (proc.stderr or proc.stdout or "rg failed").strip()
            return f"Error executing tool: {err[:500]}"
        out = (proc.stdout or "").strip()
        return out or "(no matches)"

    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as exc:
        return f"Error executing tool: invalid pattern: {exc}"
    hits: list[str] = []
    paths = [scope_path] if scope_path.is_file() else scope_path.rglob("*")
    for path in paths:
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        for idx, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                hits.append(f"{rel}:{idx}:{line}")
                if len(hits) >= _MAX_GREP_HITS:
                    return "\n".join(hits)
    return "\n".join(hits) if hits else "(no matches)"


def _tool_search_replace(arguments: dict[str, Any]) -> str:
    from src.workspace import WorkspaceError, resolve_allowed_path, to_workspace_relative

    rel = str(arguments.get("path", "")).strip()
    old = arguments.get("old_string")
    new = arguments.get("new_string")
    replace_all = bool(arguments.get("replace_all"))
    if not rel:
        return "Error executing tool: search_replace requires `path`"
    if old is None or new is None:
        return "Error executing tool: search_replace requires `old_string` and `new_string`"
    old_s = str(old)
    new_s = str(new)
    if old_s == new_s:
        return "Error executing tool: old_string and new_string are identical"
    if not old_s:
        return "Error executing tool: old_string must be non-empty"
    try:
        target = resolve_allowed_path(rel)
    except WorkspaceError as exc:
        return f"Error executing tool: {exc}"
    if not target.is_file():
        return f"Error executing tool: not a file: {rel}"
    text = target.read_text(encoding="utf-8", errors="replace")
    count = text.count(old_s)
    if count == 0:
        return "Error executing tool: old_string not found in file"
    if count > 1 and not replace_all:
        return (
            f"Error executing tool: old_string found {count} times; "
            "pass replace_all=true or provide a more unique old_string"
        )
    updated = text.replace(old_s, new_s) if replace_all else text.replace(old_s, new_s, 1)
    target.write_text(updated, encoding="utf-8")
    rel_out = to_workspace_relative(str(target)) or rel
    replaced = count if replace_all else 1
    return json.dumps(
        {"ok": True, "path": rel_out, "replacements": replaced, "changed_paths": [rel_out]},
        ensure_ascii=False,
    )


def _tool_run_terminal_cmd(arguments: dict[str, Any]) -> str:
    from src.workspace import WorkspaceError, require_workspace

    command = str(arguments.get("command", "")).strip()
    if not command:
        return "Error executing tool: run_terminal_cmd requires `command`"
    try:
        timeout = int(arguments.get("timeout_sec") or _DEFAULT_CMD_TIMEOUT_S)
    except (TypeError, ValueError):
        timeout = _DEFAULT_CMD_TIMEOUT_S
    timeout = max(1, min(timeout, 300))
    try:
        root = require_workspace()
    except WorkspaceError as exc:
        return f"Error executing tool: {exc}"

    shell = os.environ.get("SHELL") or ("cmd.exe" if os.name == "nt" else "/bin/bash")
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "PWD": str(root)},
            executable=shell if os.name != "nt" and Path(shell).is_file() else None,
        )
    except subprocess.TimeoutExpired:
        return f"Error executing tool: command timed out after {timeout}s"
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    combined = stdout
    if stderr.strip():
        combined = f"{stdout}\n[stderr]\n{stderr}" if stdout else f"[stderr]\n{stderr}"
    if len(combined) > _MAX_CMD_OUTPUT_CHARS:
        combined = combined[:_MAX_CMD_OUTPUT_CHARS] + "\n…[truncated]"
    header = f"exit_code={proc.returncode}\n"
    return header + (combined if combined.strip() else "(no output)")
