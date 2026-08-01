"""Built-in Clutch tools (virtual MCP server, no external MCP subprocess)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import difflib
from pathlib import Path
from typing import Any

_MAX_DIFF_PATCH_LINES = 160
import logging

logger = logging.getLogger(__name__)

def _bg_job_run_id():
    from src.builtin_tools_workspace import _bg_job_run_id as _impl
    return _impl()



def is_propose_plan_tool(name: str) -> bool:
    short = name.split("__")[-1].lower().replace("-", "_")
    return short == "propose_plan"


def is_todo_write_tool(name: str) -> bool:
    short = name.split("__")[-1].lower().replace("-", "_")
    return short in {"todo_write", "write_todos", "update_todos"}


def is_goal_write_tool(name: str) -> bool:
    short = name.split("__")[-1].lower().replace("-", "_")
    return short in {"goal_write", "set_goal", "update_goal"}


def is_ask_user_question_tool(name: str) -> bool:
    short = name.split("__")[-1].lower().replace("-", "_")
    return short in {"ask_user_question", "ask_question", "user_question"}


def is_submit_verification_tool(name: str) -> bool:
    short = name.split("__")[-1].lower().replace("-", "_")
    return short in {
        "submit_verification",
        "verification_report",
        "submit_verification_report",
    }


def is_submit_diff_summary_tool(name: str) -> bool:
    short = name.split("__")[-1].lower().replace("-", "_")
    return short in {
        "submit_diff_summary",
        "diff_summary",
        "propose_diff_review",
    }


def is_read_skill_tool(name: str) -> bool:
    short = name.split("__")[-1].lower().replace("-", "_")
    return short in {"read_skill", "load_skill"}


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
        items_in = _coerce_todos_list(raw.get("todos"))
    elif isinstance(raw, list):
        items_in = raw
    elif isinstance(raw, str):
        items_in = _coerce_todos_list(raw)
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


def normalize_goal_args(func_args: dict[str, Any] | None) -> dict[str, Any]:
    payload = func_args if isinstance(func_args, dict) else {}
    title = str(payload.get("title") or payload.get("goal") or "").strip()
    if not title:
        title = "Goal"
    try:
        progress = int(payload.get("progress") if payload.get("progress") is not None else 0)
    except (TypeError, ValueError):
        progress = 0
    progress = max(0, min(100, progress))
    done = bool(payload.get("done"))
    if progress >= 100:
        done = True
        progress = 100
    return {"title": title, "progress": progress, "done": done}


def normalize_question_args(func_args: dict[str, Any] | None) -> dict[str, Any]:
    payload = func_args if isinstance(func_args, dict) else {}
    question = str(payload.get("question") or payload.get("prompt") or "").strip()
    raw_opts = payload.get("options")
    options: list[dict[str, str]] = []
    if isinstance(raw_opts, list):
        for idx, item in enumerate(raw_opts):
            if isinstance(item, str):
                label = item.strip()
                if not label:
                    continue
                options.append({"id": f"opt_{idx + 1}", "label": label})
            elif isinstance(item, dict):
                label = str(item.get("label") or item.get("text") or item.get("title") or "").strip()
                if not label:
                    continue
                oid = str(item.get("id") or f"opt_{idx + 1}").strip() or f"opt_{idx + 1}"
                options.append({"id": oid, "label": label})
    allow_custom = payload.get("allow_custom")
    if allow_custom is None:
        allow_custom = True
    return {
        "question": question or "Please choose an option",
        "options": options,
        "allow_custom": bool(allow_custom),
    }


def parse_question_selection(
    instructions: str,
    func_args: dict[str, Any] | None,
) -> dict[str, str]:
    """Map human_decision instructions to {id, label}."""
    normalized = normalize_question_args(func_args)
    options = normalized["options"]
    raw = (instructions or "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                label = str(parsed.get("label") or parsed.get("text") or "").strip()
                oid = str(parsed.get("id") or "").strip()
                if label or oid:
                    if not label and oid:
                        for opt in options:
                            if opt["id"] == oid:
                                label = opt["label"]
                                break
                        label = label or oid
                    if not oid:
                        oid = next((o["id"] for o in options if o["label"] == label), f"custom_{label[:24]}")
                    return {"id": oid, "label": label}
        except json.JSONDecodeError:
            pass
        for opt in options:
            if opt["id"] == raw or opt["label"] == raw:
                return dict(opt)
        return {"id": "custom", "label": raw}
    if options:
        return dict(options[0])
    return {"id": "custom", "label": "(no answer)"}


def enrich_diff_file_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Fill status/patch/diffs for one file entry when missing."""
    path = str(entry.get("path") or "").strip()
    if not path:
        return entry
    status = str(entry.get("status") or "").strip().upper()[:1]
    if status not in _DIFF_FILE_STATUSES:
        status = ""
    patch = str(entry.get("patch") or "").strip()
    if not patch or not status:
        git_status, git_patch = _git_diff_for_path(path)
        if not status:
            status = git_status
        if not patch:
            patch = git_patch
    patch = _truncate_patch(patch) if patch else ""
    diffs = entry.get("diffs")
    if not isinstance(diffs, list) or not diffs:
        diffs = _parse_unified_diff_lines(patch) if patch else []
    summary = str(entry.get("summary") or "").strip()
    return {
        "path": path,
        "status": status or "M",
        "summary": summary,
        "patch": patch,
        "diffs": diffs,
    }


def normalize_diff_summary(
    func_args: dict[str, Any] | None,
    *,
    enrich: bool = True,
) -> dict[str, Any]:
    """Normalize submit_diff_summary args into a DiffSummary card payload."""
    payload = func_args if isinstance(func_args, dict) else {}
    title = str(payload.get("title") or payload.get("name") or "").strip() or "Changes"
    summary = str(payload.get("summary") or "").strip()
    files_in: list[Any] = []
    raw_files = payload.get("files")
    if isinstance(raw_files, list):
        files_in = raw_files
    elif isinstance(payload.get("changed_files") or payload.get("changedFiles"), list):
        files_in = list(payload.get("changed_files") or payload.get("changedFiles") or [])

    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in files_in:
        if isinstance(item, str):
            path = item.strip()
            if not path or path in seen:
                continue
            seen.add(path)
            entry: dict[str, Any] = {"path": path}
        elif isinstance(item, dict):
            path = str(item.get("path") or item.get("file") or item.get("name") or "").strip()
            if not path or path in seen:
                continue
            seen.add(path)
            entry = dict(item)
            entry["path"] = path
        else:
            continue
        if enrich:
            files.append(enrich_diff_file_entry(entry))
        else:
            path = entry["path"]
            status = str(entry.get("status") or "M").strip().upper()[:1]
            if status not in _DIFF_FILE_STATUSES:
                status = "M"
            patch = _truncate_patch(str(entry.get("patch") or ""))
            diffs = entry.get("diffs")
            if not isinstance(diffs, list) or not diffs:
                diffs = _parse_unified_diff_lines(patch) if patch else []
            files.append(
                {
                    "path": path,
                    "status": status,
                    "summary": str(entry.get("summary") or "").strip(),
                    "patch": patch,
                    "diffs": diffs,
                }
            )

    if not summary and files:
        summary = f"{len(files)} file(s) changed"

    out: dict[str, Any] = {"title": title, "summary": summary, "files": files}
    if payload.get("inline") is True:
        out["inline"] = True
    return out


def build_inline_edit_diff_cards(
    *,
    tool_name: str,
    func_args: dict[str, Any],
    result_str: str,
) -> list[dict[str, Any]]:
    """
    Cursor-style: one DiffSummary card per edited file, right after the edit tool.
    Prefer the edit payload (old/new or patch) so the chat shows the hunk immediately.
    """
    if result_str.startswith("Error executing tool"):
        return []
    short = tool_name.split("__")[-1].lower().replace("-", "_")
    cards: list[dict[str, Any]] = []

    if short == "search_replace":
        path = str(func_args.get("path") or "").strip()
        old_s = func_args.get("old_string")
        new_s = func_args.get("new_string")
        if path and old_s is not None and new_s is not None:
            try:
                payload = json.loads(result_str)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and payload.get("path"):
                path = str(payload["path"]).strip() or path
            patch = _hunk_from_old_new(str(old_s), str(new_s))
            entry = enrich_diff_file_entry(
                {"path": path, "status": "M", "patch": patch}
            )
            cards.append(
                {
                    "title": _basename_path(path),
                    "summary": "",
                    "files": [entry],
                    "inline": True,
                }
            )
            return cards

    if short == "apply_patch":
        patch = str(func_args.get("patch") or "").strip()
        paths: list[str] = []
        try:
            payload = json.loads(result_str)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            for raw in payload.get("changed_paths") or []:
                rel = str(raw).strip()
                if rel and rel not in paths:
                    paths.append(rel)
        if not paths and patch:
            try:
                from src.apply_patch import extract_patch_paths

                paths = list(extract_patch_paths(patch) or [])
            except Exception:
                paths = []
        for path in paths:
            entry = enrich_diff_file_entry({"path": path, "patch": patch if len(paths) == 1 else ""})
            cards.append(
                {
                    "title": _basename_path(path),
                    "summary": "",
                    "files": [entry],
                    "inline": True,
                }
            )
        return cards

    # Generic write/create/edit — show git/content diff for the path.
    from src.mcp_risk import extract_mcp_file_paths

    paths = extract_mcp_file_paths(tool_name, func_args)
    if not paths:
        try:
            payload = json.loads(result_str)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            for raw in payload.get("changed_paths") or []:
                rel = str(raw).strip()
                if rel and rel not in paths:
                    paths.append(rel)
            if payload.get("path"):
                rel = str(payload["path"]).strip()
                if rel and rel not in paths:
                    paths.append(rel)
    editish = any(
        tok in short
        for tok in ("write", "edit", "create", "patch", "replace", "delete")
    )
    if not editish:
        return []
    for path in paths:
        entry = enrich_diff_file_entry({"path": path})
        cards.append(
            {
                "title": _basename_path(path),
                "summary": "",
                "files": [entry],
                "inline": True,
            }
        )
    return cards


def build_diff_summary_from_paths(
    paths: list[str] | None,
    *,
    title: str = "Changes",
) -> dict[str, Any] | None:
    """Auto-build a DiffSummary from workspace-relative paths (D6 seal fallback)."""
    cleaned: list[str] = []
    for path in paths or []:
        rel = str(path).strip()
        if rel and rel not in cleaned:
            cleaned.append(rel)
    if not cleaned:
        return None
    return normalize_diff_summary({"title": title, "files": cleaned}, enrich=True)


def _parse_unified_diff_lines(patch: str) -> list[dict[str, Any]]:
    """Map unified diff text → DiffLine-shaped dicts for Chat/Changes."""
    out: list[dict[str, Any]] = []
    line_num = 0
    for raw in patch.splitlines():
        if raw.startswith("+++") or raw.startswith("---") or raw.startswith("diff ") or raw.startswith("index "):
            continue
        if raw.startswith("@@"):
            # @@ -a,b +c,d @@ → start from new-file line c
            m = re.search(r"\+(\d+)", raw)
            if m:
                line_num = max(0, int(m.group(1)) - 1)
            continue
        if raw.startswith("+"):
            line_num += 1
            out.append({"lineNum": line_num, "type": "addition", "text": raw[1:]})
        elif raw.startswith("-"):
            out.append({"lineNum": line_num, "type": "deletion", "text": raw[1:]})
        elif raw.startswith("\\"):
            continue
        else:
            text = raw[1:] if raw.startswith(" ") else raw
            line_num += 1
            out.append({"lineNum": line_num, "type": "normal", "text": text})
    return out


def _hunk_from_old_new(old_s: str, new_s: str) -> str:
    """Line-level unified hunk so appends don't re-paint unchanged lines as -/+."""
    old_lines = str(old_s).splitlines()
    new_lines = str(new_s).splitlines()
    if old_lines == new_lines:
        return ""
    diff_lines = [
        line
        for line in difflib.unified_diff(old_lines, new_lines, lineterm="", n=2)
        if not line.startswith("---") and not line.startswith("+++")
    ]
    if diff_lines:
        return "\n".join(diff_lines)
    # Fallback: whole block replace (should be rare).
    parts: list[str] = ["@@ -1 +1 @@"]
    parts.extend(f"-{line}" for line in old_lines)
    parts.extend(f"+{line}" for line in new_lines)
    return "\n".join(parts)


def _tool_read_skill(arguments: dict[str, Any]) -> str:
    from src.agent_skills import load_skill_body

    key = str(arguments.get("key") or arguments.get("skill") or "").strip()
    if not key:
        return "Error executing tool: read_skill requires `key` (skill registry key)"
    body = load_skill_body(key)
    if not body:
        return (
            f"Error executing tool: skill `{key}` not found in the Skills Registry. "
            "Check the Skills catalog keys bound to this agent."
        )
    return body


def _tool_delegate_subtask(arguments: dict[str, Any]) -> str:
    from src.subagent_runner import (
        default_subtask_max_steps,
        delegate_result_json,
        get_delegate_context,
        run_subagent,
    )

    try:
        ctx = get_delegate_context()
        if not ctx:
            return (
                "Error executing tool: delegate_subtask requires an active Chat agent context"
            )
        task_type = str(arguments.get("type") or "explore")
        raw_max = ctx.get("max_steps")
        steps = (
            int(raw_max)
            if raw_max is not None
            else default_subtask_max_steps(task_type)
        )
        card = run_subagent(
            task_type=task_type,
            prompt=str(arguments.get("prompt") or ""),
            title=str(arguments.get("title") or "") or None,
            servers=list(ctx.get("servers") or []),
            model_id=ctx.get("model_id"),
            on_log=ctx.get("on_log"),
            on_subtask_update=ctx.get("on_subtask_update"),
            max_steps=steps,
            permission_mode=str(ctx.get("permission_mode") or "auto_edit"),
            pause_on_risky=bool(ctx.get("pause_on_risky", True)),
            subtask_id=ctx.get("subtask_id"),
        )
        return delegate_result_json(card)
    except ValueError as exc:
        return f"Error executing tool: {exc}"
    except Exception as exc:
        return f"Error executing tool: {exc}"


def _tool_goal_write(arguments: dict[str, Any]) -> str:
    goal = normalize_goal_args(arguments)
    status = "completed" if goal["done"] else f"{goal['progress']}%"
    return f"Updated goal: {goal['title']} ({status})"


def _tool_todo_write(arguments: dict[str, Any]) -> str:
    todos = normalize_todo_items(arguments)
    if not todos:
        return "Error executing tool: todo_write requires a non-empty `todos` array"
    lines = [
        f"- [{t['status']}] {t['id']}: {t['content']}" for t in todos
    ]
    completed_n = sum(1 for t in todos if t.get("status") == "completed")
    in_progress_n = sum(1 for t in todos if t.get("status") == "in_progress")
    tip = ""
    # Coach models that batch-complete everything after sitting on step 1.
    if completed_n >= 3 and in_progress_n <= 1 and completed_n + in_progress_n >= len(todos) - 1:
        tip = (
            "\nNote for next turns: update statuses step-by-step "
            "(complete current + set next in_progress) so Chat progress is visible — "
            "avoid marking many items completed in a single todo_write."
        )
    return f"Updated {len(todos)} todo(s):\n" + "\n".join(lines) + tip


def _tool_remember_preference(arguments: dict[str, Any]) -> str:
    from src.cross_session_memory import add_entry
    from src.preferences_storage import load_cross_session_memory_enabled

    if not load_cross_session_memory_enabled():
        return (
            "Error executing tool: cross-session memory is disabled in Settings. "
            "Ask the user to enable Memory first."
        )
    text = str(arguments.get("text") or "").strip()
    if not text:
        return "Error executing tool: remember_preference requires `text`"
    run_id = _bg_job_run_id() or ""
    try:
        entry = add_entry(text, source_run_id=run_id or None)
    except ValueError as exc:
        return f"Error executing tool: {exc}"
    return json.dumps({"ok": True, "id": entry["id"], "text": entry["text"]}, ensure_ascii=False)


def _tool_submit_diff_summary(arguments: dict[str, Any]) -> str:
    card = normalize_diff_summary(arguments, enrich=True)
    if not card["files"]:
        return "Error executing tool: submit_diff_summary requires a non-empty `files` array"
    lines = [
        f"- [{f.get('status') or 'M'}] {f['path']}"
        + (f": {f['summary']}" if f.get("summary") else "")
        for f in card["files"]
    ]
    summary = card.get("summary") or ""
    summary_line = f"\nSummary: {summary}" if summary else ""
    return (
        f"Diff summary published: {card['title']}\n"
        + "\n".join(lines)
        + summary_line
        + "\nUser can review readable diffs in Chat; continue or call submit_verification."
    )


def _tool_submit_verification(arguments: dict[str, Any]) -> str:
    report = normalize_verification_report(arguments)
    if not report["steps"]:
        return "Error executing tool: submit_verification requires a non-empty `steps` array"
    lines = [
        f"- [{s['status']}] {s['name']}"
        + (f": {s['detail']}" if s.get("detail") else "")
        for s in report["steps"]
    ]
    actions = report.get("nextActions") or []
    action_block = ""
    if actions:
        action_block = "\nNext actions:\n" + "\n".join(f"- {a}" for a in actions)
    summary = report.get("summary") or ""
    summary_line = f"\nSummary: {summary}" if summary else ""
    return (
        f"Verification {report['conclusion'].upper()}: {report['title']}\n"
        + "\n".join(lines)
        + summary_line
        + action_block
        + (
            "\nDo not claim the task succeeded; address failed steps or next actions."
            if report["conclusion"] == "failed"
            else "\nChecks passed; you may summarize completion for the user."
        )
    )


def _tool_ask_user_question(arguments: dict[str, Any]) -> str:
    q = normalize_question_args(arguments)
    selected = arguments.get("selected")
    if isinstance(selected, dict):
        label = str(selected.get("label") or "").strip()
        oid = str(selected.get("id") or "").strip()
        if label:
            extra = f" (id={oid})" if oid else ""
            return (
                f"User selected: {label}{extra}. "
                "Proceed with this choice; do not ask the same question again."
            )
    if isinstance(selected, str) and selected.strip():
        return (
            f"User selected: {selected.strip()}. "
            "Proceed with this choice; do not ask the same question again."
        )
    opts = ", ".join(o["label"] for o in q["options"]) or "(none)"
    return (
        f"Question presented to user: {q['question']}\n"
        f"Options: {opts}\n"
        "Awaiting selection."
    )


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


def _tool_diagnostics(arguments: dict[str, Any]) -> str:
    import json

    from src.code_diagnostics import run_code_diagnostics, store_pending_diagnostics
    from src.workspace import WorkspaceError, require_workspace

    try:
        root = require_workspace()
    except WorkspaceError as exc:
        return f"Error executing tool: {exc}"
    paths_arg = arguments.get("paths")
    paths: list[str] | None = None
    if isinstance(paths_arg, list):
        paths = [str(item) for item in paths_arg if str(item).strip()]
    issues = run_code_diagnostics(root, paths)
    run_id = _bg_job_run_id()
    if run_id:
        store_pending_diagnostics(run_id, issues)
    return json.dumps({"count": len(issues), "issues": issues}, ensure_ascii=False)


def _coerce_todos_list(value: Any) -> list[Any]:
    """Coerce tool `todos` payload to a list (models often JSON-stringify the array)."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        # Single todo object, or nested {"todos": ...}
        if "todos" in value:
            return _coerce_todos_list(value.get("todos"))
        if any(key in value for key in ("content", "text", "title", "status", "id")):
            return [value]
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Do not list(str) — that explodes into one todo per character (D8 PM).
            return []
        return _coerce_todos_list(parsed)
    return []


def _git_diff_for_path(rel: str) -> tuple[str, str]:
    """Return (status A|M|D, unified patch) for a workspace-relative path."""
    from src.workspace import WorkspaceError, require_workspace, resolve_allowed_path

    try:
        root = require_workspace()
        target = resolve_allowed_path(rel)
    except WorkspaceError:
        return "M", ""

    rel_posix = rel.replace("\\", "/")
    try:
        porcelain = subprocess.run(
            ["git", "status", "--porcelain", "--", rel_posix],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        porcelain = None

    status = "M"
    if porcelain and porcelain.returncode == 0 and porcelain.stdout.strip():
        code = porcelain.stdout.strip()[:2]
        if "A" in code or "?" in code:
            status = "A"
        elif "D" in code:
            status = "D"
        else:
            status = "M"

    patch = ""
    try:
        if status == "A" or (porcelain and porcelain.stdout.strip().startswith("??")):
            diff = subprocess.run(
                ["git", "diff", "--no-index", "--", "/dev/null", rel_posix],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            # git --no-index exits 1 when files differ
            patch = diff.stdout or ""
        else:
            diff = subprocess.run(
                ["git", "diff", "HEAD", "--", rel_posix],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            patch = diff.stdout or ""
            if not patch.strip():
                diff = subprocess.run(
                    ["git", "diff", "--", rel_posix],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                )
                patch = diff.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        patch = ""

    if not patch.strip() and target.is_file() and status != "D":
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        preview = text.splitlines()[:80]
        patch = "\n".join(f"+{line}" for line in preview)
        if len(text.splitlines()) > 80:
            patch += f"\n... ({len(text.splitlines()) - 80} more lines truncated)"
        status = status if status in _DIFF_FILE_STATUSES else "A"

    return status, _truncate_patch(patch)

def is_delegate_subtask_tool(name: str) -> bool:
    short = name.split("__")[-1].lower().replace("-", "_")
    return short == "delegate_subtask"


_TODO_STATUSES = frozenset({"pending", "in_progress", "completed"})
_VERIFICATION_STEP_STATUSES = frozenset({"passed", "failed", "skipped"})
_VERIFICATION_CONCLUSIONS = frozenset({"passed", "failed"})
_DIFF_FILE_STATUSES = frozenset({"A", "M", "D"})
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


def normalize_verification_report(
    func_args: dict[str, Any] | None,
    *,
    existing_todos: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Normalize submit_verification args; force failed if todos incomplete."""
    payload = func_args if isinstance(func_args, dict) else {}
    title = str(payload.get("title") or payload.get("name") or "").strip() or "Verification"
    raw_conclusion = str(payload.get("conclusion") or payload.get("status") or "failed").strip().lower()
    conclusion = raw_conclusion if raw_conclusion in _VERIFICATION_CONCLUSIONS else "failed"
    steps: list[dict[str, str]] = []
    raw_steps = payload.get("steps")
    if isinstance(raw_steps, list):
        for idx, item in enumerate(raw_steps):
            if isinstance(item, str):
                name = item.strip()
                if name:
                    steps.append(
                        {
                            "id": f"step_{idx + 1}",
                            "name": name,
                            "status": "passed" if conclusion == "passed" else "failed",
                            "detail": "",
                        }
                    )
                continue
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("title") or item.get("check") or "").strip()
            if not name:
                continue
            status = str(item.get("status") or "failed").strip().lower()
            if status not in _VERIFICATION_STEP_STATUSES:
                status = "failed"
            detail = str(item.get("detail") or item.get("message") or "").strip()
            sid = str(item.get("id") or f"step_{idx + 1}").strip() or f"step_{idx + 1}"
            steps.append({"id": sid, "name": name, "status": status, "detail": detail})
    summary = str(payload.get("summary") or "").strip()
    next_actions: list[str] = []
    raw_next = payload.get("next_actions") or payload.get("nextActions")
    if isinstance(raw_next, list):
        for item in raw_next:
            text = str(item).strip()
            if text:
                next_actions.append(text)
    changed_files: list[str] = []
    raw_files = payload.get("changed_files") or payload.get("changedFiles")
    if isinstance(raw_files, list):
        for item in raw_files:
            path = str(item).strip()
            if path and path not in changed_files:
                changed_files.append(path)

    incomplete = [
        t
        for t in (existing_todos or [])
        if isinstance(t, dict) and str(t.get("status") or "") != "completed"
    ]
    if conclusion == "passed" and incomplete:
        conclusion = "failed"
        names = ", ".join(
            str(t.get("content") or t.get("id") or "todo").strip() for t in incomplete[:5]
        )
        steps.insert(
            0,
            {
                "id": "todos_incomplete",
                "name": "Session todos incomplete",
                "status": "failed",
                "detail": f"Cannot claim passed while todos remain open: {names}",
            },
        )
        tip = "Mark remaining todos completed (or cancel them) before claiming success."
        if tip not in next_actions:
            next_actions.insert(0, tip)
        if not summary:
            summary = "Verification forced to failed because session todos are still incomplete."

    if any(s["status"] == "failed" for s in steps) and conclusion == "passed":
        conclusion = "failed"

    return {
        "title": title,
        "conclusion": conclusion,
        "steps": steps,
        "summary": summary,
        "nextActions": next_actions,
        "changedFiles": changed_files,
    }


def _truncate_patch(patch: str, *, max_lines: int = _MAX_DIFF_PATCH_LINES) -> str:
    lines = patch.splitlines()
    if len(lines) <= max_lines:
        return patch.strip()
    kept = lines[:max_lines]
    kept.append(f"... ({len(lines) - max_lines} more lines truncated)")
    return "\n".join(kept).strip()


def _basename_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p]
    return parts[-1] if parts else path


