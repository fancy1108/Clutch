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

CLUTCH_TOOLS_SERVER_ID = "clutch-tools"


# D38 — tool-family modules (re-exported for routes/tests)
from src.builtin_tools_agent import (
    _DIFF_FILE_STATUSES,
    _STEP_INDEX_RE,
    _TODO_STATUSES,
    _VERIFICATION_CONCLUSIONS,
    _VERIFICATION_STEP_STATUSES,
    _basename_path,
    _coerce_todos_list,
    _git_diff_for_path,
    _hunk_from_old_new,
    _parse_unified_diff_lines,
    _tool_ask_user_question,
    _tool_delegate_subtask,
    _tool_diagnostics,
    _tool_goal_write,
    _tool_propose_plan,
    _tool_read_skill,
    _tool_remember_preference,
    _tool_submit_diff_summary,
    _tool_submit_verification,
    _tool_todo_write,
    _truncate_patch,
    build_diff_summary_from_paths,
    build_inline_edit_diff_cards,
    enrich_diff_file_entry,
    is_ask_user_question_tool,
    is_delegate_subtask_tool,
    is_goal_write_tool,
    is_propose_plan_tool,
    is_read_skill_tool,
    is_submit_diff_summary_tool,
    is_submit_verification_tool,
    is_todo_write_tool,
    normalize_diff_summary,
    normalize_goal_args,
    normalize_plan_args,
    normalize_question_args,
    normalize_todo_items,
    normalize_verification_report,
    parse_question_selection,
    strip_plan_step_index,
)
from src.builtin_tools_workspace import (
    _DEFAULT_CMD_TIMEOUT_S,
    _MAX_CMD_OUTPUT_CHARS,
    _MAX_DIFF_PATCH_LINES,
    _MAX_GREP_HITS,
    _MAX_LIST_ENTRIES,
    _MAX_READ_CHARS,
    _bg_job_run_id,
    _tool_apply_patch,
    _tool_grep,
    _tool_kill_background_job,
    _tool_list_background_jobs,
    _tool_list_dir,
    _tool_read_file,
    _tool_run_terminal_cmd,
    _tool_search_replace,
)
from src.builtin_tools_external import (
    _run_git,
    _tool_generate_image,
    _tool_generate_video,
    _tool_git_commit,
    _tool_git_diff,
    _tool_git_status,
    _tool_web_fetch,
    _tool_web_search,
)

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
    from src.preferences_storage import (
        load_allow_network,
        load_cross_session_memory_enabled,
    )

    tools: list[dict[str, Any]] = [
        {
            "name": "read_file",
            "description": (
                "Read a file from the active workspace. "
                "Text files return numbered lines; images use local OCR/analysis; "
                "PDFs use pdftotext when available (D33)."
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
                "Prefer non-interactive commands. Risky — may require human approval. "
                "Set background=true to start a long-running job and return immediately. "
                "Do NOT create/edit source files via shell heredocs (`cat >`, `echo >`); "
                "use apply_patch or search_replace so Chat Diff cards and Changes update."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute."},
                    "timeout_sec": {
                        "type": "integer",
                        "description": f"Timeout seconds (default {_DEFAULT_CMD_TIMEOUT_S}).",
                    },
                    "background": {
                        "type": "boolean",
                        "description": "When true, start in background and return job_id immediately.",
                    },
                },
                "required": ["command"],
            },
        },
        {
            "name": "list_background_jobs",
            "description": "List background shell jobs for the current Chat session.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "kill_background_job",
            "description": "Kill a running background job by job_id.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Background job id from run_terminal_cmd."},
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "git_status",
            "description": (
                "Show git status for the active workspace (D12). "
                "Read-only; prefer before commit."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "git_diff",
            "description": (
                "Show git diff for the workspace or optional paths (D12). Read-only."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional workspace-relative paths to limit the diff.",
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "If true, show staged diff (default false).",
                    },
                },
            },
        },
        {
            "name": "git_commit",
            "description": (
                "Stage paths (or -A when omitted) and create a git commit (D12). "
                "Risky — requires human approval in ask mode."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message.",
                    },
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional paths to stage; omit to stage all tracked changes.",
                    },
                },
                "required": ["message"],
            },
        },
        {
            "name": "web_fetch",
            "description": (
                "Fetch a public http(s) URL and return truncated page text for summarization (D12). "
                "Use for user-provided links and for live facts when you know a concrete page URL "
                "(e.g. weather: https://wttr.in/Shanghai?format=3). "
                "Do NOT fetch search-engine result pages (bing.com/search, google.com/search, …) — "
                "use web_search for open questions, then web_fetch a promising result URL. "
                "Do not refuse real-time questions without calling this or web_search first."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "http(s) URL to fetch."},
                    "timeout_sec": {
                        "type": "integer",
                        "description": "Timeout seconds (default 20).",
                    },
                },
                "required": ["url"],
            },
        },
        {
            "name": "generate_image",
            "description": (
                "REQUIRED when the user wants a picture / poster / illustration / infographic / "
                "可视化图 — call this instead of writing an HTML page. "
                "Uses the user's configured image model (e.g. Agnes Image); saves under "
                "`.clutch/generated/images/`. Never fake images with HTML/CSS."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed image generation prompt (subject, style, layout).",
                    },
                    "filename_stem": {
                        "type": "string",
                        "description": "Optional short filename stem (saved under .clutch/generated/images/).",
                    },
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "generate_video",
            "description": (
                "REQUIRED when the user wants a video / 短视频 / clip — call this instead of "
                "writing an HTML page. Uses the user's configured video model (e.g. Agnes Video); "
                "saves under `.clutch/generated/videos/`."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed video generation prompt.",
                    },
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "apply_patch",
            "description": (
                "Apply a Codex-style patch to the active workspace. "
                "Supports *** Add File, *** Delete File, *** Update File, and *** Move to. "
                "Patch must start with '*** Begin Patch' and end with '*** End Patch' "
                "(a missing End marker is auto-healed when the rest of the patch is valid). "
                "Add File body lines should preferably start with '+' (e.g. `+hello`); "
                "bare content lines are also accepted. "
                "Chat research/visual deliverables (new .md / .html / images) MUST go under "
                "`.clutch/artifacts/` — do not dump them at the project root. "
                "For pictures/infographics call `generate_image` instead of HTML. "
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
            "name": "goal_write",
            "description": (
                "Set or update the current session goal (D29). "
                "Provide title, progress 0-100, and done=true when complete. "
                "Shown as a goal bar above Chat."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Goal title (e.g. Fix login)."},
                    "progress": {
                        "type": "integer",
                        "description": "Progress percent 0-100.",
                    },
                    "done": {
                        "type": "boolean",
                        "description": "Mark goal complete (closes the bar).",
                    },
                },
                "required": ["title"],
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
        {
            "name": "remember_preference",
            "description": (
                "Store a user preference in cross-session memory (D16) when the user asks "
                "you to remember something for future Chat sessions. Requires Memory enabled in Settings."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Short preference to remember (e.g. commit messages in Chinese).",
                    },
                },
                "required": ["text"],
            },
        },
        {
            "name": "ask_user_question",
            "description": (
                "Ask the user a multiple-choice question in Chat when a real fork exists "
                "(e.g. Redis vs Memcached for cache) and the user did not already specify. "
                "Do NOT use for trivia or when the plan already has a clear default. "
                "Pause until the user picks an option (or types a custom answer)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Clear question shown on the Chat card.",
                    },
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "label": {"type": "string"},
                            },
                            "required": ["label"],
                        },
                        "description": "2–5 choices (short labels).",
                    },
                    "allow_custom": {
                        "type": "boolean",
                        "description": "Allow a free-text answer from the dock (default true).",
                    },
                },
                "required": ["question", "options"],
            },
        },
        {
            "name": "submit_verification",
            "description": (
                "Publish a self-check verification report in Chat after implementing work (D5). "
                "Include concrete steps with passed|failed|skipped and an overall conclusion. "
                "Never claim conclusion=passed while session todos are still incomplete — "
                "the tool will force failed. On failure, set next_actions the user can take. "
                "Call this before saying the task is done; do not silently end after a failed check."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short report title shown on the Chat card.",
                    },
                    "conclusion": {
                        "type": "string",
                        "enum": ["passed", "failed"],
                        "description": "Overall pass/fail.",
                    },
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "status": {
                                    "type": "string",
                                    "enum": ["passed", "failed", "skipped"],
                                },
                                "detail": {"type": "string"},
                            },
                            "required": ["name", "status"],
                        },
                        "description": "Ordered verification steps (commands, checks, imports).",
                    },
                    "summary": {
                        "type": "string",
                        "description": "One-paragraph outcome for the user.",
                    },
                    "next_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Actionable follow-ups when failed (or optional tips when passed).",
                    },
                    "changed_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Workspace-relative paths to highlight for View changes.",
                    },
                },
                "required": ["title", "conclusion", "steps"],
            },
        },
        {
            "name": "submit_diff_summary",
            "description": (
                "Publish a Diff review card in Chat after editing files (D6). "
                "Pass the changed workspace-relative paths; include a short per-file "
                "summary and/or unified `patch` when helpful. If patch is omitted, "
                "Clutch fills a git (or content) diff when possible. Call after "
                "meaningful edits so the user can open readable diffs without leaving Chat."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short card title (default: Changes).",
                    },
                    "summary": {
                        "type": "string",
                        "description": "One-paragraph overview of the change set.",
                    },
                    "files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "status": {
                                    "type": "string",
                                    "enum": ["A", "M", "D"],
                                    "description": "A=added M=modified D=deleted",
                                },
                                "summary": {"type": "string"},
                                "patch": {
                                    "type": "string",
                                    "description": "Optional unified diff hunks for this file.",
                                },
                            },
                            "required": ["path"],
                        },
                        "description": "Changed files (≥1).",
                    },
                },
                "required": ["files"],
            },
        },
        {
            "name": "read_skill",
            "description": (
                "Load the full SKILL.md body for a skill listed in the Skills catalog (D7). "
                "Pass the skill key (e.g. my-skills/secure-review). Use when catalog "
                "one-liners are not enough; do not invent skill instructions."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Registry skill key from the Skills catalog.",
                    },
                    "skill": {
                        "type": "string",
                        "description": "Alias for `key`.",
                    },
                },
                "required": ["key"],
            },
        },
        {
            "name": "delegate_subtask",
            "description": (
                "Spawn an isolated subagent for a scoped subtask (D10). "
                "`explore` runs read-only (list/read/search); `implement` may edit files. "
                "Use for「先调研再改」— explore first, then call again with type=implement "
                "for writes (do not skip the implement card when the user asked for both). "
                "Returns JSON with status, summary, and brief tool_steps."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["explore", "implement"],
                        "description": "explore = read-only; implement = may edit.",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Clear task for the subagent.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Short card title shown in parent Chat (optional).",
                    },
                },
                "required": ["type", "prompt"],
            },
        },
        {
            "name": "diagnostics",
            "description": (
                "Run lightweight code diagnostics (tsc, ruff, py_compile when available). "
                "Results are injected into the next Agent turn and shown in Chat issues strip (D24)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional workspace-relative files/dirs to scope checks.",
                    }
                },
            },
        },
    ]
    # Catalog honesty: never advertise tools that cannot run under current prefs.
    if not load_cross_session_memory_enabled():
        tools = [t for t in tools if str(t.get("name")) != "remember_preference"]
    if load_allow_network():
        tools.append(
            {
                "name": "web_search",
                "description": (
                    "Search the public web for recent information (D15) — weather, news, "
                    "events, docs, etc. Returns titles, URLs, and snippets. "
                    "For open questions call this ONCE (or twice only if results are empty), "
                    "then web_fetch at most 1–2 concrete result URLs, then answer. "
                    "Requires Settings → Allow network."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query."},
                        "max_results": {
                            "type": "integer",
                            "description": "Max results to return (default 5).",
                        },
                    },
                    "required": ["query"],
                },
            }
        )
    return tools


def execute_builtin_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    handlers = {
        "read_file": _tool_read_file,
        "list_dir": _tool_list_dir,
        "grep": _tool_grep,
        "search_replace": _tool_search_replace,
        "run_terminal_cmd": _tool_run_terminal_cmd,
        "list_background_jobs": _tool_list_background_jobs,
        "kill_background_job": _tool_kill_background_job,
        "git_status": _tool_git_status,
        "git_diff": _tool_git_diff,
        "git_commit": _tool_git_commit,
        "web_fetch": _tool_web_fetch,
        "web_search": _tool_web_search,
        "generate_image": _tool_generate_image,
        "generate_video": _tool_generate_video,
        "apply_patch": _tool_apply_patch,
        "propose_plan": _tool_propose_plan,
        "todo_write": _tool_todo_write,
        "remember_preference": _tool_remember_preference,
        "goal_write": _tool_goal_write,
        "set_goal": _tool_goal_write,
        "update_goal": _tool_goal_write,
        "ask_user_question": _tool_ask_user_question,
        "submit_verification": _tool_submit_verification,
        "verification_report": _tool_submit_verification,
        "submit_verification_report": _tool_submit_verification,
        "submit_diff_summary": _tool_submit_diff_summary,
        "diff_summary": _tool_submit_diff_summary,
        "propose_diff_review": _tool_submit_diff_summary,
        "read_skill": _tool_read_skill,
        "load_skill": _tool_read_skill,
        "delegate_subtask": _tool_delegate_subtask,
        "diagnostics": _tool_diagnostics,
    }
    handler = handlers.get(tool_name)
    if handler is None:
        return f"Error executing tool: unknown builtin tool {tool_name}"
    try:
        return handler(arguments)
    except Exception as exc:
        return f"Error executing tool: {exc}"


