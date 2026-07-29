"""Structured Chat/MCP tool steps for D46 (Grok/Cursor-style verb_group transcript)."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Literal
from urllib.parse import urlparse

ToolStepKind = Literal["read", "fetch", "search", "list", "edit", "execute", "other"]
ToolStepStatus = Literal["running", "completed", "failed", "awaiting"]

_KIND_BY_TOOL: dict[str, ToolStepKind] = {
    "read_file": "read",
    "list_dir": "list",
    "grep": "search",
    "web_search": "search",
    "web_fetch": "fetch",
    "search_replace": "edit",
    "apply_patch": "edit",
    "run_terminal_cmd": "execute",
    "propose_plan": "other",
    "todo_write": "other",
    "ask_user_question": "other",
    "submit_verification": "other",
    "submit_diff_summary": "other",
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
    "git_status": "other",
    "git_diff": "other",
    "git_commit": "other",
    "remember_preference": "other",
    "read_skill": "read",
}


def short_tool_name(alias: str) -> str:
    if "__" in alias:
        return alias.split("__", 1)[1] or alias
    return alias


def kind_for_tool(tool: str) -> ToolStepKind:
    key = short_tool_name(tool).lower().replace("-", "_")
    if key in _KIND_BY_TOOL:
        return _KIND_BY_TOOL[key]
    if key.startswith("web_fetch") or "fetch" in key and "web" in key:
        return "fetch"
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


def _host_label(url: str) -> str:
    """Cursor-style short host/path for fetch titles."""
    raw = (url or "").strip()
    if not raw:
        return "page"
    try:
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        host = (parsed.netloc or parsed.path.split("/")[0] or "").removeprefix("www.")
        path = (parsed.path or "").rstrip("/")
        if path and path != "/":
            leaf = path.rsplit("/", 1)[-1]
            if leaf and len(leaf) < 28:
                return _compact(f"{host}/{leaf}" if host else leaf, 44)
        return _compact(host or raw, 44)
    except Exception:
        return _compact(raw, 44)


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
    """Return (title, detail) — title is Cursor one-liner; detail is target (+ later preview)."""
    short = short_tool_name(tool)
    payload = args if isinstance(args, dict) else {}
    path = _pick(payload, ("path", "file_path", "file", "target"))
    pattern = _pick(payload, ("pattern", "query", "regex", "q", "search"))
    command = _pick(payload, ("command", "cmd"))
    url = _pick(payload, ("url", "uri", "href"))
    patch = _pick(payload, ("patch",))
    detail = json.dumps(payload, ensure_ascii=False)[:240] if payload else short

    if short in {"web_fetch", "fetch_url", "browse_page"}:
        target = url or path
        label = _host_label(target) if target else "page"
        return f"Fetched {label}", target or detail

    if short in {"web_search", "internet_search", "search_web"}:
        q = pattern or _pick(payload, ("q", "text", "keywords"))
        if q:
            return f"Searched “{_compact(q, 36)}”", q
        return "Searched the web", detail

    if short in {"git_status", "git_diff", "git_commit"}:
        labels = {
            "git_status": ("Git status", "git status"),
            "git_diff": ("Git diff", _pick(payload, ("path", "ref")) or "git diff"),
            "git_commit": (
                f"Git commit {_compact(_pick(payload, ('message', 'msg')), 28)}".rstrip(),
                _pick(payload, ("message", "msg")) or "git commit",
            ),
        }
        return labels[short]

    if short in {"todo_write", "write_todos", "update_todos"}:
        todos = payload.get("todos")
        lines: list[str] = []
        focus = ""
        in_progress = ""
        completed: list[str] = []
        if isinstance(todos, list):
            for item in todos[:8]:
                if not isinstance(item, dict):
                    continue
                content = str(item.get("content") or item.get("text") or "").strip()
                status = str(item.get("status") or "pending").strip().lower()
                if not content:
                    continue
                lines.append(f"[{status}] {content}")
                if status == "in_progress" and not in_progress:
                    in_progress = content
                elif status == "completed":
                    completed.append(content)
                elif not focus:
                    focus = content
        detail_lines = "\n".join(lines) if lines else _compact(detail, 160)
        if in_progress:
            return f"Todos · {_compact(in_progress, 40)}", detail_lines
        if completed and len(completed) == len(lines):
            return f"Todos done · {_compact(completed[-1], 36)}", detail_lines
        if completed:
            return f"Todos · {_compact(completed[-1], 40)}", detail_lines
        if focus:
            return f"Todos · {_compact(focus, 40)}", detail_lines
        return "Updated todos", detail_lines
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
    if short in {
        "submit_diff_summary",
        "diff_summary",
        "propose_diff_review",
    }:
        title = _pick(payload, ("title", "name")) or "Changes"
        files = payload.get("files")
        n = len(files) if isinstance(files, list) else 0
        return (
            f"Diff: {_compact(title, 32)}",
            f"{n} file(s)" if n else detail,
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
    if kind == "fetch":
        target = url or path
        return f"Fetched {_host_label(target) if target else 'page'}", target or detail
    focus = _compact(path or pattern or command or url or short, 40)
    return f"{short.replace('_', ' ')} {focus}".strip(), detail


def _progressive_title(title: str, status: ToolStepStatus) -> str:
    """Cursor-style: Running → progressive verb; sealed → past tense."""
    if status not in {"running", "awaiting"}:
        return title
    swaps = (
        ("Fetched ", "Fetching "),
        ("Searched ", "Searching "),
        ("Read ", "Reading "),
        ("List ", "Listing "),
        ("Edit ", "Editing "),
        ("Run ", "Running "),
        ("Delete ", "Deleting "),
        ("Create ", "Creating "),
    )
    for past, prog in swaps:
        if title.startswith(past):
            return prog + title[len(past) :]
    return title


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
        "title": _progressive_title(title, status),
        "detail": detail,
    }


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")


def _strip_to_text(raw: str, *, max_len: int) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    if text.lstrip().startswith("<") or "<html" in text[:200].lower():
        text = _HTML_TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text.replace("\r", ""))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > max_len:
        text = f"{text[: max_len - 1]}…"
    return text


def _preview_web_search(result: str, *, max_len: int) -> str:
    text = (result or "").strip()
    if not text:
        return ""
    try:
        data = json.loads(text)
    except Exception:
        return _strip_to_text(text, max_len=max_len)
    hits: list[Any]
    if isinstance(data, list):
        hits = data
    elif isinstance(data, dict):
        for key in ("results", "items", "organic", "hits"):
            if isinstance(data.get(key), list):
                hits = data[key]
                break
        else:
            return _strip_to_text(text, max_len=max_len)
    else:
        return _strip_to_text(text, max_len=max_len)
    lines: list[str] = []
    for item in hits[:5]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or "").strip()
        link = str(item.get("url") or item.get("href") or item.get("link") or "").strip()
        snippet = str(item.get("snippet") or item.get("body") or item.get("description") or "").strip()
        if title and link:
            lines.append(f"• {title}\n  {link}")
        elif title:
            lines.append(f"• {title}")
        elif link:
            lines.append(f"• {link}")
        if snippet and len("\n".join(lines)) < max_len - 40:
            lines.append(f"  {_compact(snippet, 80)}")
    if not lines:
        return _strip_to_text(text, max_len=max_len)
    return _strip_to_text("\n".join(lines), max_len=max_len)


def _result_preview(tool_name: str, result: str, *, max_len: int) -> str:
    short = short_tool_name(tool_name).lower().replace("-", "_")
    if short in {"web_search", "internet_search", "search_web"}:
        return _preview_web_search(result, max_len=max_len)
    return _strip_to_text(result, max_len=max_len)


def append_tool_result_detail(
    step: dict[str, Any],
    tool_name: str,
    result: str,
    *,
    max_len: int = 480,
    failed: bool = False,
) -> dict[str, Any]:
    """Attach result/error preview under the target line (Cursor expand body)."""
    snippet = _result_preview(tool_name, result, max_len=max_len)
    if not snippet:
        return step
    merged = dict(step)
    kind = kind_for_tool(short_tool_name(tool_name))
    # Shell: keep prior D19 behavior — detail becomes the output.
    if kind == "execute" and not failed:
        merged["detail"] = snippet
        return merged

    existing = str(step.get("detail") or "").strip()
    if "── result" in existing.lower() or "── error" in existing.lower():
        return step

    chars = len((result or "").strip())
    label = "error" if failed or str(step.get("status")) == "failed" else "result"
    meta = f"{chars:,} chars" if chars and label == "result" else ""
    header = f"── {label}" + (f" ({meta})" if meta else "") + " ──"
    if existing and kind != "execute":
        merged["detail"] = f"{existing}\n\n{header}\n{snippet}"
    else:
        merged["detail"] = f"{header}\n{snippet}" if kind != "execute" else snippet
    return merged


def append_execute_output_detail(
    step: dict[str, Any],
    tool_name: str,
    result: str,
    *,
    max_len: int = 480,
) -> dict[str, Any]:
    """Back-compat alias — now enriches all supervise-worthy tool kinds."""
    failed = str(step.get("status")) == "failed" or (result or "").startswith(
        "Error executing tool"
    )
    return append_tool_result_detail(
        step, tool_name, result, max_len=max_len, failed=failed
    )


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
    "fetch": ("page", "pages"),
    "search": ("query", "queries"),
    "list": ("dir", "dirs"),
    "edit": ("edit", "edits"),
    "execute": ("command", "commands"),
    "other": ("tool", "tools"),
}

_HEADER_VERB_RUNNING: dict[ToolStepKind, str] = {
    "read": "Reading",
    "fetch": "Fetching",
    "search": "Searching",
    "list": "Listing",
    "edit": "Editing",
    "execute": "Running",
    "other": "Using",
}

_HEADER_VERB_DONE: dict[ToolStepKind, str] = {
    "read": "Read",
    "fetch": "Fetched",
    "search": "Searched",
    "list": "Listed",
    "edit": "Edited",
    "execute": "Ran",
    "other": "Used",
}


def verb_group_header_label(steps: list[dict[str, Any]]) -> str:
    """Grok/Cursor fold header: 'Fetched 4 pages, Searched 1 query'."""
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
    order: list[ToolStepKind] = [
        "read",
        "fetch",
        "search",
        "list",
        "edit",
        "execute",
        "other",
    ]
    parts: list[str] = []
    for kind in order:
        n = counts.get(kind, 0)
        if not n:
            continue
        singular, plural = _HEADER_NOUN[kind]
        noun = singular if n == 1 else plural
        parts.append(f"{verbs[kind]} {n} {noun}")
    return ", ".join(parts) if parts else ("Working…" if any_running else "Tools")
