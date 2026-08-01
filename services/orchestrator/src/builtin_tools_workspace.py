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


_MAX_READ_CHARS = 120_000

_MAX_GREP_HITS = 50

_MAX_LIST_ENTRIES = 200

_DEFAULT_CMD_TIMEOUT_S = 60

_MAX_CMD_OUTPUT_CHARS = 80_000

_MAX_DIFF_PATCH_LINES = 160


def _tool_apply_patch(arguments: dict[str, Any]) -> str:
    from src.apply_patch import ApplyPatchError, apply_patch_in_workspace, extract_patch_paths, format_apply_patch_result
    from src.artifact_layout import (
        block_html_for_non_page_intent,
        current_user_turn_text,
        rewrite_apply_patch_paths,
    )

    patch = str(arguments.get("patch", "")).strip()
    if not patch:
        return "Error executing tool: apply_patch requires non-empty `patch`"
    user_text = current_user_turn_text()
    for path in extract_patch_paths(patch):
        blocked = block_html_for_non_page_intent(path, user_text=user_text)
        if blocked:
            return f"Error executing tool: {blocked}"
    patch, relocate_notes = rewrite_apply_patch_paths(patch, user_text=user_text)
    run_id = _bg_job_run_id()
    if run_id:
        from src.file_rewind import snapshot_paths_before_write

        snapshot_paths_before_write(run_id, extract_patch_paths(patch))
    try:
        result = format_apply_patch_result(apply_patch_in_workspace(patch))
    except ApplyPatchError as exc:
        return f"Error executing tool: {exc}"
    if relocate_notes:
        note = "; ".join(relocate_notes)
        return f"{result}\n[Clutch] Relocated chat deliverable(s) under .clutch/artifacts/: {note}"
    return result


def _tool_read_file(arguments: dict[str, Any]) -> str:
    from src.ignore_rules import ignored_path_message, is_ignored_path
    from src.rich_read_util import (
        is_rich_read_path,
        read_image_workspace_file,
        read_pdf_workspace_file,
    )
    from src.workspace import WorkspaceError, require_workspace, resolve_allowed_path

    rel = str(arguments.get("path", "")).strip()
    if not rel:
        return "Error executing tool: read_file requires `path`"
    try:
        root = require_workspace()
        if is_ignored_path(root, rel):
            return f"Error executing tool: {ignored_path_message(rel)}"
        target = resolve_allowed_path(rel)
    except WorkspaceError as exc:
        return f"Error executing tool: {exc}"
    if not target.is_file():
        return f"Error executing tool: not a file: {rel}"
    if is_rich_read_path(target):
        if target.suffix.lower() == ".pdf":
            return read_pdf_workspace_file(target)
        return read_image_workspace_file(target)
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
    from src.ignore_rules import is_ignored_path
    from src.workspace import WorkspaceError, require_workspace, resolve_allowed_path, to_workspace_relative

    rel = str(arguments.get("path") or ".").strip() or "."
    try:
        root = require_workspace()
        if is_ignored_path(root, rel, is_dir=True):
            from src.ignore_rules import ignored_path_message

            return f"Error executing tool: {ignored_path_message(rel)}"
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
        child_rel = to_workspace_relative(str(child)) or child.name
        if is_ignored_path(root, child_rel, is_dir=child.is_dir()):
            continue
        suffix = "/" if child.is_dir() else ""
        entries.append(f"{child.name}{suffix}")
    extra = len(children) - _MAX_LIST_ENTRIES
    if extra > 0:
        entries.append(f"…and {extra} more")
    return "\n".join(entries) if entries else "(empty directory)"


def _tool_grep(arguments: dict[str, Any]) -> str:
    from src.ignore_rules import is_ignored_path
    from src.workspace import WorkspaceError, require_workspace, resolve_allowed_path, to_workspace_relative

    pattern = str(arguments.get("pattern", ""))
    if not pattern:
        return "Error executing tool: grep requires `pattern`"
    scope = str(arguments.get("path") or ".").strip() or "."
    case_insensitive = bool(arguments.get("case_insensitive"))
    try:
        root = require_workspace()
        scope_path = resolve_allowed_path(scope)
        if is_ignored_path(root, scope, is_dir=scope_path.is_dir()):
            from src.ignore_rules import ignored_path_message

            return f"Error executing tool: {ignored_path_message(scope)}"
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
        if out:
            filtered: list[str] = []
            for line in out.splitlines():
                rel = line.split(":", 1)[0] if ":" in line else ""
                if rel and is_ignored_path(root, rel):
                    continue
                filtered.append(line)
            out = "\n".join(filtered)
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
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        if is_ignored_path(root, rel):
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
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
    run_id = _bg_job_run_id()
    if run_id:
        from src.file_rewind import snapshot_before_write

        snapshot_before_write(run_id, rel)
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
    from src.workspace import WorkspaceError, assert_strict_sandbox_command, require_workspace

    command = str(arguments.get("command", "")).strip()
    if not command:
        return "Error executing tool: run_terminal_cmd requires `command`"
    try:
        root = require_workspace()
        assert_strict_sandbox_command(command, root)
    except WorkspaceError as exc:
        return f"Error executing tool: {exc}"

    if bool(arguments.get("background")):
        run_id = _bg_job_run_id()
        if not run_id:
            return (
                "Error executing tool: background commands require an active Chat run context"
            )
        from src.bg_jobs import start_job

        try:
            job = start_job(run_id, command, str(root))
        except ValueError as exc:
            return f"Error executing tool: {exc}"
        return json.dumps(
            {
                "ok": True,
                "job_id": job["id"],
                "status": job["status"],
                "title": job.get("title") or command[:60],
            },
            ensure_ascii=False,
        )

    try:
        timeout = int(arguments.get("timeout_sec") or _DEFAULT_CMD_TIMEOUT_S)
    except (TypeError, ValueError):
        timeout = _DEFAULT_CMD_TIMEOUT_S
    timeout = max(1, min(timeout, 300))

    run_id = _bg_job_run_id()
    if run_id:
        from src.foreground_shell import start_foreground, wait_foreground

        try:
            start_foreground(run_id, command, str(root))
        except Exception as exc:
            return f"Error executing tool: {exc}"
        output, transferred, exit_code = wait_foreground(run_id, timeout_sec=float(timeout))
        if transferred:
            from src.bg_jobs import list_jobs

            jobs = list_jobs(run_id)
            job_id = jobs[-1]["id"] if jobs else ""
            return json.dumps(
                {
                    "ok": True,
                    "transferred_to_background": True,
                    "job_id": job_id,
                    "status": "running",
                    "title": command[:60],
                    "output_prefix": output[:2000] if output else "",
                },
                ensure_ascii=False,
            )
        if exit_code is None:
            return f"Error executing tool: command timed out after {timeout}s"
        header = f"exit_code={exit_code}\n"
        combined = output
        if len(combined) > _MAX_CMD_OUTPUT_CHARS:
            combined = combined[:_MAX_CMD_OUTPUT_CHARS] + "\n…[truncated]"
        return header + (combined if combined.strip() else "(no output)")

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


def _tool_list_background_jobs(arguments: dict[str, Any]) -> str:
    del arguments
    run_id = _bg_job_run_id()
    if not run_id:
        return "Error executing tool: list_background_jobs requires an active Chat run context"
    from src.bg_jobs import list_jobs

    return json.dumps(list_jobs(run_id), ensure_ascii=False)


def _tool_kill_background_job(arguments: dict[str, Any]) -> str:
    run_id = _bg_job_run_id()
    if not run_id:
        return "Error executing tool: kill_background_job requires an active Chat run context"
    job_id = str(arguments.get("job_id") or "").strip()
    if not job_id:
        return "Error executing tool: kill_background_job requires `job_id`"
    from src.bg_jobs import kill_job

    killed = kill_job(run_id, job_id)
    if killed is None:
        return f"Error executing tool: background job `{job_id}` not found"
    return json.dumps(killed, ensure_ascii=False)


def _bg_job_run_id() -> str | None:
    from src.bg_jobs import get_bg_job_context

    ctx = get_bg_job_context()
    if not ctx:
        return None
    run_id = str(ctx.get("run_id") or "").strip()
    return run_id or None

