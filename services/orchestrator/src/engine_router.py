"""Engine router for deciding between Claude CLI, Cursor workspace, or global LLM provider."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from src.agent_storage import list_agents
from src.tools_status import load_connected_ids, resolve_tool_binary, tool_available_for_routing
from src.adapters.claude_cli_adapter import chat_claude_cli
from src.adapters.cursor_adapter import open_workspace_in_cursor
from src.workspace import get_workspace
from src.preferences_storage import tr


@dataclass(frozen=True)
class EngineResult:
    engine: str
    output: str
    logs: list[str]
    claude_session_id: str | None = None


def _normalize_engine_type(engine_type: str) -> str:
    key = engine_type.strip().lower()
    if key in {
        "claude code (local cli)",
        "claude code cli",
        "claude-cli",
        "claude cli",
    }:
        return "Claude Code (Local CLI)"
    if "cursor" in key and "workspace" in key:
        return "Cursor Workspace Node"
    return engine_type.strip()


def _format_history_for_cli_prompt(history: list[dict[str, str]] | None) -> str:
    if not history:
        return ""
    lines: list[str] = []
    for item in history:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if not content or role == "system":
            continue
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")
    return "\n\n".join(lines)


def find_agent(agent_name: str) -> dict[str, Any] | None:
    agents = list_agents()
    for agent in agents:
        if agent.get("name") == agent_name or agent.get("id") == agent_name:
            return agent
    for agent in agents:
        name = agent.get("name", "")
        aid = agent.get("id", "")
        if name.lower() == agent_name.lower() or aid.lower() == agent_name.lower():
            return agent
    for agent in agents:
        name = agent.get("name", "")
        aid = agent.get("id", "")
        if agent_name.lower() in name.lower() or agent_name.lower() in aid.lower():
            return agent
    return None


def route_engine(
    agent_name: str,
    prompt: str,
    system_prompt: str | None = None,
    cwd: str | None = None,
    history: list[dict[str, str]] | None = None,
    fallback_tool: str | None = None,
    claude_session_id: str | None = None,
) -> EngineResult:
    agent = find_agent(agent_name)
    raw_engine_type = str(agent.get("aiEngine", "")) if agent else ""
    engine_type = _normalize_engine_type(raw_engine_type)

    if not engine_type and fallback_tool:
        if fallback_tool == "claude-cli":
            engine_type = "Claude Code (Local CLI)"
        elif fallback_tool == "cursor":
            engine_type = "Cursor Workspace Node"

    workspace_path = cwd
    if not workspace_path:
        workspace = get_workspace()
        if workspace:
            workspace_path = workspace.get("workspace_path")

    logs: list[str] = [
        (
            f"[ROUTER] agent={agent_name!r} matched={agent is not None} "
            f"aiEngine={raw_engine_type!r}->{engine_type!r} "
            f"claude_path={resolve_tool_binary('claude-cli')!r} "
            f"connected={'claude-cli' in load_connected_ids()}"
        )
    ]

    if engine_type == "Claude Code (Local CLI)" and tool_available_for_routing("claude-cli"):
        cli_binary = resolve_tool_binary("claude-cli")
        logs.append(f"Routing task to Claude Code (Local CLI) for agent {agent_name}.")
        if cli_binary:
            logs.append(f"Using Claude binary: {cli_binary}")
        elif "claude-cli" in load_connected_ids():
            raise RuntimeError(
                tr(
                    "Claude Code CLI is connected but the `claude` binary was not found. "
                    "Restart Clutch after install, or ensure it is on PATH "
                    "(e.g. /opt/homebrew/bin/claude).",
                    "Claude Code CLI 已连接，但未找到 `claude` 可执行文件。"
                    "请安装后重启 Clutch，或确认其在 PATH 中（如 /opt/homebrew/bin/claude）。",
                )
            )

        def _invoke_cli(
            *,
            cli_prompt: str,
            cli_system_prompt: str | None,
            session_id: str | None = None,
            resume_session_id: str | None = None,
        ) -> str:
            return chat_claude_cli(
                prompt=cli_prompt,
                cwd=workspace_path,
                system_prompt=cli_system_prompt,
                session_id=session_id,
                resume_session_id=resume_session_id,
                binary=cli_binary,
            )

        try:
            if claude_session_id:
                logs.append(f"Resuming Claude CLI session {claude_session_id}.")
                output = _invoke_cli(
                    cli_prompt=prompt,
                    cli_system_prompt=None,
                    resume_session_id=claude_session_id,
                )
                logs.append("Claude CLI session resumed successfully.")
                return EngineResult(
                    engine="Claude CLI",
                    output=output,
                    logs=logs,
                    claude_session_id=claude_session_id,
                )

            history_prompt = _format_history_for_cli_prompt(history).strip()
            bootstrap_prompt = history_prompt or prompt
            new_session_id = str(uuid.uuid4())
            logs.append(f"Starting new Claude CLI session {new_session_id}.")
            output = _invoke_cli(
                cli_prompt=bootstrap_prompt,
                cli_system_prompt=system_prompt,
                session_id=new_session_id,
            )
            logs.append("Claude CLI execution completed successfully.")
            return EngineResult(
                engine="Claude CLI",
                output=output,
                logs=logs,
                claude_session_id=new_session_id,
            )
        except Exception as exc:
            if claude_session_id:
                logs.append(f"Claude session resume failed ({exc}); replaying history.")
                try:
                    history_prompt = _format_history_for_cli_prompt(history).strip() or prompt
                    new_session_id = str(uuid.uuid4())
                    output = _invoke_cli(
                        cli_prompt=history_prompt,
                        cli_system_prompt=system_prompt,
                        session_id=new_session_id,
                    )
                    logs.append(f"Claude CLI recovered with new session {new_session_id}.")
                    return EngineResult(
                        engine="Claude CLI",
                        output=output,
                        logs=logs,
                        claude_session_id=new_session_id,
                    )
                except Exception as retry_exc:
                    logs.append(f"Claude CLI recovery failed: {retry_exc}")
                    raise RuntimeError(
                        tr(
                            f"Failed to execute task via Claude CLI: {retry_exc}",
                            f"通过 Claude CLI 执行任务失败：{retry_exc}",
                        )
                    ) from retry_exc
            logs.append(f"Claude CLI execution failed: {exc}")
            raise RuntimeError(
                tr(
                    f"Failed to execute task via Claude CLI: {exc}",
                    f"通过 Claude CLI 执行任务失败：{exc}",
                )
            ) from exc

    if engine_type == "Cursor Workspace Node" and tool_available_for_routing("cursor-app"):
        logs.append(f"Routing task to Cursor Workspace Node for agent {agent_name}.")
        if not workspace_path:
            raise RuntimeError(
                tr(
                    "Cannot open in Cursor: no active workspace path.",
                    "无法在 Cursor 中打开：没有激活的工作区路径。",
                )
            )
        try:
            open_workspace_in_cursor(workspace_path)
            output = tr(
                "Workspace opened in Cursor Desktop.",
                "已在 Cursor 桌面端中打开工作区。",
            )
            logs.append("Workspace opened in Cursor successfully.")
            return EngineResult(engine="Cursor", output=output, logs=logs)
        except Exception as exc:
            logs.append(f"Failed to open workspace in Cursor: {exc}")
            raise RuntimeError(
                tr(
                    f"Failed to open workspace in Cursor: {exc}",
                    f"无法在 Cursor 中打开工作区：{exc}",
                )
            ) from exc

    if engine_type == "Claude Code (Local CLI)":
        logs.append(
            tr(
                f"Agent {agent_name} requests Claude Code CLI but `claude` is not installed/connected — falling back to LLM.",
                f"Agent {agent_name} 需要 Claude Code CLI，但未安装或未连接，已回退到 LLM。",
            )
        )
    elif raw_engine_type and engine_type != "Claude Code (Local CLI)":
        logs.append(
            tr(
                f"Agent {agent_name} aiEngine={raw_engine_type!r} is not a Claude CLI profile — using LLM.",
                f"Agent {agent_name} 的 aiEngine={raw_engine_type!r} 不是 Claude CLI 配置，已使用 LLM。",
            )
        )

    from src.models_config import get_router

    router = get_router()
    model = router.get_active_model()
    engine_name = model.name
    logs.append(f"Routing task to global LLM provider ({engine_name}) for agent {agent_name}.")

    chat_history = history
    if not chat_history:
        chat_history = []
        if system_prompt:
            chat_history.append({"role": "system", "content": system_prompt})
        chat_history.append({"role": "user", "content": prompt})

    try:
        output = router.chat(chat_history)
        logs.append(f"Global LLM execution completed successfully via {engine_name}.")
        return EngineResult(engine=engine_name, output=output, logs=logs)
    except Exception as exc:
        logs.append(f"Global LLM execution failed: {exc}")
        raise RuntimeError(
            tr(
                f"Cannot reach the configured model ({engine_name}). Add an API key in Settings → Models. ({exc})",
                f"无法访问配置的模型 ({engine_name})。请在 设置 → 模型 配置 API Key。({exc})",
            )
        ) from exc
