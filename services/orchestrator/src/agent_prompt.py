"""Shared agent system prompt composition for chat and Flow (D53 layered assembly)."""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Grok-compatible named instruction files (all matches in a directory load).
_RULE_FILENAMES = (
    "AGENTS.md",
    "Agents.md",
    "AGENT.md",
    "AGENTS.override.md",
    "CLAUDE.md",
    "Claude.md",
    "CLAUDE.local.md",
)
_RULES_SUBDIRS = (".grok/rules", ".claude/rules", ".cursor/rules")
_RULES_MAX_CHARS = 8_000
_RULE_FILE_MAX_CHARS = 10_000
_RULES_DIR_MAX_FILES = 12


def _append_rule_chunk(
    chunks: list[str],
    *,
    heading: str,
    text: str,
    remaining: int,
) -> int:
    """Append a ### rule block; return chars still available."""
    if remaining <= 0 or not text.strip():
        return remaining
    body = text.strip()
    if len(body) > _RULE_FILE_MAX_CHARS:
        body = body[: _RULE_FILE_MAX_CHARS - 1] + "…"
    if len(body) > remaining:
        body = body[: remaining - 1] + "…"
    chunks.append(f"### {heading}\n{body}")
    return remaining - len(body)


_PLAN_MODE_REMINDER = (
    "## Mode: Plan (read-only)\n"
    "Plan mode is active for this turn. Do not create, edit, delete, or run "
    "mutating shell commands. Propose a concrete plan and wait; file/shell "
    "writes are blocked until Plan mode is exited."
)

_ASK_MODE_REMINDER = (
    "## Mode: Ask (conversation only, read-only)\n"
    "Ask mode is active. Answer with read/search tools only "
    "(including web_fetch / web_search for live facts). "
    "Do not create, edit, delete, or run mutating shell commands. "
    "To make changes, the user must switch the composer mode to Agent or Full."
)
# Legacy alias — same semantics as Ask (D27 merge 2026-07-25).
_EXPLORE_MODE_REMINDER = _ASK_MODE_REMINDER

_FEATURE_PLAN_REMINDER = (
    "## Reminder: propose_plan required (D2)\n"
    "The latest user message is a multi-step implementation request.\n"
    "You MUST call clutch-tools `propose_plan` in this turn BEFORE any "
    "search_replace / apply_patch / run_terminal_cmd and BEFORE asking the user "
    "which framework or stack to use.\n"
    "Put a default stack and assumptions in the plan title/steps/summary "
    "(e.g. plain HTML+CSS+JS with fake credentials). The user will Approve / "
    "Revise / Cancel in Chat. At most one quick list_dir/read_file for orientation, "
    "then propose_plan immediately."
)

_FEATURE_REQUEST_RE = (
    r"(加|添加|实现|做一[个個]?|新建|创建|搭建|开发|寫|写一|"
    r"build|add\b|implement|create\b|scaffold|login|登录|註冊|注册|"
    r"auth|認證|认证|页面|頁面|feature|功能|模块|模組)"
)


def looks_like_feature_request(text: str) -> bool:
    """Heuristic for D2: multi-step coding asks should force propose_plan."""
    import re

    cleaned = (text or "").strip()
    if len(cleaned) < 4:
        return False
    # Trivial Q&A / read-only probes
    if re.search(r"^(什么|什麼|谁|誰|why|what|who|哪|怎么读|怎麼讀|看看|读一下|讀一下)\b", cleaned, re.I):
        return False
    if "?" in cleaned or "？" in cleaned:
        # Questions about existing code are usually not "build a feature"
        if not re.search(r"(加|添加|实现|做|新建|创建|build|add|implement|login|登录)", cleaned, re.I):
            return False
    return bool(re.search(_FEATURE_REQUEST_RE, cleaned, re.I))


@dataclass(frozen=True)
class PromptLayer:
    name: str
    content: str

    @property
    def chars(self) -> int:
        return len(self.content)


@dataclass
class PromptAssembly:
    layers: list[PromptLayer] = field(default_factory=list)

    def as_system_prompt(self) -> str:
        # B-35: agent_status is trailing (replaced each turn), never the cached prefix.
        parts = [
            layer.content.strip()
            for layer in self.layers
            if layer.content.strip() and layer.name != "agent_status"
        ]
        return "\n\n".join(parts)

    def agent_status_text(self) -> str:
        for layer in self.layers:
            if layer.name == "agent_status" and layer.content.strip():
                return layer.content.strip()
        return ""

    def summary(self) -> dict[str, Any]:
        return {
            "layer_count": len(self.layers),
            "total_chars": sum(layer.chars for layer in self.layers),
            "layers": [
                {"name": layer.name, "chars": layer.chars, "injected": bool(layer.content.strip())}
                for layer in self.layers
            ],
        }


def _find_git_root(start: Path) -> Path | None:
    cur = start.resolve()
    for _ in range(64):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None


def _dirs_git_root_to_workspace(workspace: Path) -> list[Path]:
    """Grok-style chain: git root → … → workspace (inclusive). Deeper dirs load last."""
    ws = workspace.resolve()
    git_root = _find_git_root(ws)
    if git_root is None:
        return [ws]
    try:
        ws.relative_to(git_root)
    except ValueError:
        return [ws]
    chain: list[Path] = []
    cur = ws
    while True:
        chain.append(cur)
        if cur == git_root:
            break
        if cur.parent == cur:
            break
        cur = cur.parent
    chain.reverse()
    return chain


def _collect_rules_in_dir(
    directory: Path,
    *,
    display_root: Path,
    chunks: list[str],
    remaining: int,
) -> int:
    for name in _RULE_FILENAMES:
        if remaining <= 0:
            return remaining
        path = directory / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = path.relative_to(display_root).as_posix()
        except ValueError:
            rel = name
        remaining = _append_rule_chunk(
            chunks, heading=rel, text=text, remaining=remaining
        )

    for sub in _RULES_SUBDIRS:
        if remaining <= 0:
            return remaining
        rules_dir = directory / Path(sub)
        if not rules_dir.is_dir():
            continue
        rule_files: list[Path] = []
        for pattern in ("**/*.mdc", "**/*.md"):
            rule_files.extend(rules_dir.glob(pattern))
        unique = sorted(
            {p.resolve() for p in rule_files if p.is_file()},
            key=lambda p: str(p),
        )
        for path in unique[:_RULES_DIR_MAX_FILES]:
            if remaining <= 0:
                break
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            try:
                rel = path.relative_to(display_root).as_posix()
            except ValueError:
                rel = path.name
            remaining = _append_rule_chunk(
                chunks, heading=rel, text=text, remaining=remaining
            )
    return remaining


def _load_workspace_rules(workspace_path: str | None) -> str:
    """Grok-aligned project rules: git root → workspace chain (D7). No user-home rules."""
    if not workspace_path:
        return ""
    root = Path(workspace_path)
    if not root.is_dir():
        return ""
    chunks: list[str] = []
    remaining = _RULES_MAX_CHARS
    display_root = _find_git_root(root) or root.resolve()
    for directory in _dirs_git_root_to_workspace(root):
        if remaining <= 0:
            break
        remaining = _collect_rules_in_dir(
            directory,
            display_root=display_root,
            chunks=chunks,
            remaining=remaining,
        )
    if not chunks:
        return ""
    return "## Project rules\n\n" + "\n\n".join(chunks)


def _format_local_time(now: datetime | None = None) -> str:
    """Human-readable local clock for the Environment prompt layer."""
    stamp = (now or datetime.now().astimezone()).astimezone()
    tz_name = stamp.tzname() or ""
    raw_offset = stamp.strftime("%z")  # e.g. +0800
    if len(raw_offset) == 5:
        offset_fmt = f"UTC{raw_offset[:3]}:{raw_offset[3:]}"
    else:
        offset_fmt = raw_offset or "local"
    clock = stamp.strftime("%Y-%m-%d %H:%M:%S")
    if tz_name:
        return f"{clock} {tz_name} ({offset_fmt})"
    return f"{clock} ({offset_fmt})"


def format_agent_status(
    *,
    agent_todos: list[dict[str, Any]] | None = None,
    plan_card: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> str:
    """Trailing replaceable block: clock + Todo/plan (Q-AGENT-2 = A)."""
    from src.task_state import format_task_state

    lines = [
        f"Local time: {_format_local_time(now)}",
        "Use Local time above for clock/date questions; do not invent a different time.",
    ]
    task = format_task_state(agent_todos=agent_todos, plan_card=plan_card)
    if task:
        lines.append(task)
    return "<agent_status>\n" + "\n".join(lines) + "\n</agent_status>"


def attach_trailing_status(
    messages: list[dict[str, Any]], status: str
) -> list[dict[str, Any]]:
    """Drop any prior <agent_status> user turn and append one fresh block."""
    cleaned = [
        item
        for item in messages
        if not (
            isinstance(item, dict)
            and item.get("role") == "user"
            and "<agent_status>" in str(item.get("content") or "")
        )
    ]
    text = (status or "").strip()
    if not text:
        return cleaned
    block = {"role": "user", "content": text}
    # Keep the latest human turn last so adapters that echo history[-1] stay correct.
    if cleaned and cleaned[-1].get("role") == "user":
        return cleaned[:-1] + [block, cleaned[-1]]
    return cleaned + [block]


def _env_layer(workspace_path: str | None) -> str:
    import os

    shell = (os.environ.get("SHELL") or os.environ.get("ComSpec") or "").strip() or "unknown"
    lines = [
        "## Environment",
        f"OS: {platform.system()} {platform.release()}",
        f"Shell: {shell}",
    ]
    if workspace_path:
        lines.append(f"Workspace root: {workspace_path}")
    else:
        lines.append("Workspace root: (none authorized)")
    return "\n".join(lines)


def _system_base(
    *,
    agent_name: str,
    model_name: str,
    model_api: str,
    is_clutch: bool,
) -> str:
    model_info = f"Runtime model: {model_name} ({model_api}).\n" if is_clutch else ""
    lines = [
        f"You are {agent_name}, the active agent in the user's Clutch workspace.",
        f"When asked who you are, identify yourself as {agent_name}. "
        "Do not claim to be a different product, vendor, or base model.",
        model_info.strip(),
        "Follow the protocol and project-rule layers below. Prefer tools for workspace I/O.",
    ]
    if not is_clutch:
        lines.append(
            "For conversational questions (identity, recall, small talk), answer directly "
            "from the conversation and your role above. Do not scan or modify the workspace "
            "unless the user asks about code, files, or a task."
        )
    return "\n".join(line for line in lines if line)


def compose_agent_prompt_assembly(
    agent: dict[str, Any],
    *,
    model_name: str,
    model_api: str,
    mcp_servers_bound: bool = True,
    clutch_mcp_path: bool = True,
    permission_mode: str | None = None,
    include_skill_bodies: bool = False,
    include_project_rules: bool = True,
    user_turn_text: str | None = None,
    agent_todos: list[dict[str, Any]] | None = None,
    plan_card: dict[str, Any] | None = None,
) -> PromptAssembly:
    """Build layered prompt (D53). markdownDoc is protocol only — not the whole system."""
    from src.agent_skills import compose_skills_section, resolve_effective_skill_keys
    from src.agent_type import is_clutch_agent
    from src.workspace import get_workspace

    is_clutch = is_clutch_agent(agent)
    agent_name = str(agent.get("name", "Clutch Agent"))
    protocol = str(agent.get("markdownDoc", "")).strip()
    workspace = get_workspace()
    workspace_path = workspace.get("workspace_path") if workspace else None

    layers: list[PromptLayer] = [
        PromptLayer(
            "system",
            _system_base(
                agent_name=agent_name,
                model_name=model_name,
                model_api=model_api,
                is_clutch=is_clutch,
            ),
        ),
        PromptLayer("env", _env_layer(str(workspace_path) if workspace_path else None)),
    ]

    if protocol:
        layers.append(
            PromptLayer(
                "protocol",
                "## Agent protocol (editable)\n" + protocol,
            )
        )

    if include_project_rules:
        rules = _load_workspace_rules(str(workspace_path) if workspace_path else None)
        if rules:
            layers.append(PromptLayer("rules", rules))

    mode = (permission_mode or "").strip().lower()
    if mode == "plan":
        layers.append(PromptLayer("mode", _PLAN_MODE_REMINDER))
    elif mode in {"ask", "explore"}:
        layers.append(PromptLayer("mode", _ASK_MODE_REMINDER))
    elif (
        clutch_mcp_path
        and is_clutch
        and mcp_servers_bound
        and looks_like_feature_request(user_turn_text or "")
    ):
        from src.deliverable_intent import allows_html_feature_plan

        # Only push the default HTML+CSS+JS plan stack when a page was inferred.
        if allows_html_feature_plan(user_turn_text):
            layers.append(PromptLayer("mode", _FEATURE_PLAN_REMINDER))

    if clutch_mcp_path and is_clutch and (user_turn_text or "").strip():
        from src.deliverable_intent import deliverable_system_reminder

        reminder = deliverable_system_reminder(user_turn_text, current_model_kind="chat")
        if reminder:
            layers.append(PromptLayer("deliverable", reminder))

    if clutch_mcp_path and is_clutch:
        if not mcp_servers_bound:
            layers.append(
                PromptLayer(
                    "tools",
                    "No MCP tools are bound for this agent in this run. "
                    "You cannot create, modify, or delete files on disk. "
                    "Never claim a file operation succeeded without MCP tool evidence.",
                )
            )
        else:
            from src.preferences_storage import load_allow_network
            from src.workspace import get_git_info

            network_on = load_allow_network()
            git_hint = (
                "Git questions → `git_status` / `git_diff` / `git_commit`. "
                if get_git_info().get("is_git_repo")
                else ""
            )
            network_block = (
                "Tool discipline (harness-enforced): never claim you lack access to the "
                "workspace, files, git, shell, or internet while the matching tools are listed. "
                "Workspace questions → `list_dir` / `read_file` / `grep` first. "
                "Edits → `read_file` then `search_replace` / `apply_patch`. "
                f"{git_hint}"
                "Commands/tests → `run_terminal_cmd`. "
                "Live / external facts (weather, news, events, prices, unfamiliar docs): "
                + (
                    "usually 1× `web_search`, then ≤2× `web_fetch` on promising result "
                    "URLs, then answer — do not re-query synonyms or fetch search-engine "
                    "result pages until the step budget is empty. "
                    if network_on
                    else (
                        "`web_search` is off (Settings → Allow network); use `web_fetch` "
                        "(e.g. `https://wttr.in/Shanghai?format=3`). "
                    )
                )
                + "Do not refuse before a tool call. "
            )
            layers.append(
                PromptLayer(
                    "tools",
                    "## Tools\n"
                    f"{network_block}"
                    "For multi-step / feature work (add login, new page, scaffold app), "
                    "call clutch-tools `propose_plan` early — do not interview the user about "
                    "stack first; put defaults in the plan. Wait for Chat Approve / Revise / "
                    "Cancel before any write or mutating shell. "
                    "After a plan is approved (or the user says 确认/批准/go ahead/按计划/"
                    "按照你说的), IMMEDIATELY call `todo_write` with ≥3 items and start the "
                    "first `in_progress` step — never ask for confirmation again, never only "
                    "restate the plan. Prefer `apply_patch`/`search_replace` over shell "
                    "heredocs (`cat >`); shell file writes skip Diff cards. "
                    "Progress rules (visible in Chat): keep exactly one `in_progress`; when "
                    "that step finishes, call `todo_write` immediately to mark it `completed` "
                    "and set the next to `in_progress` — never leave the card stuck on step 1 "
                    "then jump to all-completed in one write. "
                    "Call `todo_write` only when the list or a status changes — do not spam it. "
                    "Status-only questions (还剩什么 / 还剩哪些 todo / what's left): reply with "
                    "the open items from the trailing <agent_status> list — do not keep editing or calling "
                    "tools unless the user asks to continue. "
                    "When work is done, mark todos completed, call `submit_verification` "
                    "with concrete passed/failed steps (never claim passed while todos remain "
                    "open), then reply in plain text; do not keep calling tools after the goal "
                    "is met. On a failed check, still submit a failed report with next_actions — "
                    "do not silently end. "
                    "Each file edit already streams a Diff card in Chat (Cursor-style); "
                    "optional `submit_diff_summary` only for an explicit multi-file review. "
                    "After edits, do NOT restate each file change in a numbered list — "
                    "the Diff cards are the source of truth; one short sentence is enough. "
                    "When the user leaves a real fork unspecified (e.g. Redis vs Memcached "
                    "for cache), call `ask_user_question` with 2–5 short options — do not "
                    "interview in free prose. Skip asking when the request is already clear. "
                    "When a Skills catalog entry is relevant, call `read_skill` with its key "
                    "to load the full SKILL.md — do not invent skill instructions. "
                    "Skip propose_plan only for trivial Q&A or single-line edits.",
                )
            )
        skill_keys = resolve_effective_skill_keys(agent)
        skills_block = compose_skills_section(
            skill_keys,
            include_bodies=include_skill_bodies,
        )
        if skills_block:
            layers.append(PromptLayer("skills", skills_block))

        # D43 — user-pinned MCP resource snapshots (Hub → Pin for Chat).
        try:
            from src.mcp_resources import format_pinned_resources_block

            resources_block = format_pinned_resources_block()
        except Exception:
            resources_block = ""
        if resources_block:
            layers.append(PromptLayer("mcp_resources", resources_block))

        # D16 — app-level prefs JSON; B-39 — workspace MEMORY.md overview.
        try:
            from src.cross_session_memory import format_memory_prompt_block
            from src.workspace_memory import format_workspace_memory_block

            memory_block = "\n\n".join(
                part
                for part in (
                    format_memory_prompt_block(),
                    format_workspace_memory_block(),
                )
                if part
            )
        except Exception:
            memory_block = ""
        if memory_block:
            layers.append(PromptLayer("memory", memory_block))

    layers.append(
        PromptLayer(
            "agent_status",
            format_agent_status(agent_todos=agent_todos, plan_card=plan_card),
        )
    )
    return PromptAssembly(layers=layers)


def compose_agent_system_prompt(
    agent: dict[str, Any],
    *,
    model_name: str,
    model_api: str,
    mcp_servers_bound: bool = True,
    clutch_mcp_path: bool = True,
    permission_mode: str | None = None,
    include_skill_bodies: bool = False,
    user_turn_text: str | None = None,
    agent_todos: list[dict[str, Any]] | None = None,
    plan_card: dict[str, Any] | None = None,
) -> str:
    """Backward-compatible flat system string from layered assembly (D53)."""
    if permission_mode is None:
        try:
            from src.preferences_storage import load_permission_mode

            permission_mode = load_permission_mode()
        except Exception:
            permission_mode = "auto_edit"
    return compose_agent_prompt_assembly(
        agent,
        model_name=model_name,
        model_api=model_api,
        mcp_servers_bound=mcp_servers_bound,
        clutch_mcp_path=clutch_mcp_path,
        permission_mode=permission_mode,
        include_skill_bodies=include_skill_bodies,
        user_turn_text=user_turn_text,
        agent_todos=agent_todos,
        plan_card=plan_card,
    ).as_system_prompt()
