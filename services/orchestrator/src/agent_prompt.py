"""Shared agent system prompt composition for chat and Flow (D53 layered assembly)."""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

_RULE_FILENAMES = ("AGENTS.md", "CLAUDE.md")
_RULES_MAX_CHARS = 8_000

_PLAN_MODE_REMINDER = (
    "## Mode: Plan (read-only)\n"
    "Plan mode is active for this turn. Do not create, edit, delete, or run "
    "mutating shell commands. Propose a concrete plan and wait; file/shell "
    "writes are blocked until Plan mode is exited."
)

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
        parts = [layer.content.strip() for layer in self.layers if layer.content.strip()]
        return "\n\n".join(parts)

    def summary(self) -> dict[str, Any]:
        return {
            "layer_count": len(self.layers),
            "total_chars": sum(layer.chars for layer in self.layers),
            "layers": [
                {"name": layer.name, "chars": layer.chars, "injected": bool(layer.content.strip())}
                for layer in self.layers
            ],
        }


def _load_workspace_rules(workspace_path: str | None) -> str:
    if not workspace_path:
        return ""
    root = Path(workspace_path)
    if not root.is_dir():
        return ""
    chunks: list[str] = []
    remaining = _RULES_MAX_CHARS
    for name in _RULE_FILENAMES:
        if remaining <= 0:
            break
        path = root / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if not text:
            continue
        body = text if len(text) <= remaining else text[: remaining - 1] + "…"
        chunks.append(f"### {name}\n{body}")
        remaining -= len(body)
    if not chunks:
        return ""
    return "## Project rules\n\n" + "\n\n".join(chunks)


def _env_layer(workspace_path: str | None) -> str:
    import os

    shell = (os.environ.get("SHELL") or os.environ.get("ComSpec") or "").strip() or "unknown"
    lines = [
        "## Environment",
        f"Date: {date.today().isoformat()}",
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
) -> PromptAssembly:
    """Build layered prompt (D53). markdownDoc is protocol only — not the whole system."""
    from src.agent_skills import compose_skills_section
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
    elif (
        clutch_mcp_path
        and is_clutch
        and mcp_servers_bound
        and looks_like_feature_request(user_turn_text or "")
    ):
        layers.append(PromptLayer("mode", _FEATURE_PLAN_REMINDER))

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
            layers.append(
                PromptLayer(
                    "tools",
                    "## Tools\n"
                    "For multi-step / feature work (add login, new page, scaffold app), "
                    "call clutch-tools `propose_plan` early — do not interview the user about "
                    "stack first; put defaults in the plan. Wait for Chat Approve / Revise / "
                    "Cancel before any write or mutating shell. "
                    "After a plan is approved (or for clear multi-step work), call `todo_write` "
                    "with ≥3 items and keep statuses updated (one in_progress). "
                    "Call `todo_write` only when the list or a status changes — do not spam it. "
                    "When work is done, mark todos completed, call `submit_verification` "
                    "with concrete passed/failed steps (never claim passed while todos remain "
                    "open), then reply in plain text; do not keep calling tools after the goal "
                    "is met. On a failed check, still submit a failed report with next_actions — "
                    "do not silently end. "
                    "When the user leaves a real fork unspecified (e.g. Redis vs Memcached "
                    "for cache), call `ask_user_question` with 2–5 short options — do not "
                    "interview in free prose. Skip asking when the request is already clear. "
                    "Skip propose_plan only for trivial Q&A or single-line edits.",
                )
            )
        skills_block = compose_skills_section(
            list(agent.get("skills") or []),
            include_bodies=include_skill_bodies,
        )
        if skills_block:
            layers.append(PromptLayer("skills", skills_block))

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
) -> str:
    """Backward-compatible flat system string from layered assembly (D53)."""
    if permission_mode is None:
        try:
            from src.preferences_storage import load_permission_mode

            permission_mode = load_permission_mode()
        except Exception:
            permission_mode = "ask"
    return compose_agent_prompt_assembly(
        agent,
        model_name=model_name,
        model_api=model_api,
        mcp_servers_bound=mcp_servers_bound,
        clutch_mcp_path=clutch_mcp_path,
        permission_mode=permission_mode,
        include_skill_bodies=include_skill_bodies,
        user_turn_text=user_turn_text,
    ).as_system_prompt()
