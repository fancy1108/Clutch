"""Engine router for deciding between Claude CLI, Cursor workspace, or global LLM provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agent_storage import list_agents
from src.tools_status import load_connected_ids
from src.adapters.claude_cli_adapter import chat_claude_cli
from src.adapters.cursor_adapter import open_workspace_in_cursor
from src.workspace import get_workspace
from src.preferences_storage import tr


@dataclass(frozen=True)
class EngineResult:
    engine: str
    output: str
    logs: list[str]


def find_agent(agent_name: str) -> dict[str, Any] | None:
    agents = list_agents()
    # 1. Exact match
    for agent in agents:
        if agent.get("name") == agent_name or agent.get("id") == agent_name:
            return agent
    # 2. Case-insensitive exact match
    for agent in agents:
        name = agent.get("name", "")
        aid = agent.get("id", "")
        if name.lower() == agent_name.lower() or aid.lower() == agent_name.lower():
            return agent
    # 3. Substring match
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
) -> EngineResult:
    # 1. Match agent in list_agents()
    agent = find_agent(agent_name)
    engine_type = ""
    if agent:
        engine_type = agent.get("aiEngine", "")

    # If agent configuration isn't found but a fallback tool request is provided
    if not engine_type and fallback_tool:
        if fallback_tool == "claude-cli":
            engine_type = "Claude Code (Local CLI)"
        elif fallback_tool == "cursor":
            engine_type = "Cursor Workspace Node"

    # 2. Get connected tools
    connected_ids = load_connected_ids()

    # Get active workspace path if not provided
    workspace_path = cwd
    if not workspace_path:
        workspace = get_workspace()
        if workspace:
            workspace_path = workspace.get("workspace_path")

    # 3. Routing decision
    if engine_type == "Claude Code (Local CLI)" and "claude-cli" in connected_ids:
        logs = [f"Routing task to Claude Code (Local CLI) for agent {agent_name}."]
        try:
            output = chat_claude_cli(
                prompt=prompt,
                cwd=workspace_path,
                system_prompt=system_prompt,
            )
            logs.append("Claude CLI execution completed successfully.")
            return EngineResult(engine="Claude CLI", output=output, logs=logs)
        except Exception as exc:
            logs.append(f"Claude CLI execution failed: {exc}")
            raise RuntimeError(
                tr(
                    f"Failed to execute task via Claude CLI: {exc}",
                    f"通过 Claude CLI 执行任务失败：{exc}"
                )
            ) from exc

    elif engine_type == "Cursor Workspace Node" and "cursor-app" in connected_ids:
        logs = [f"Routing task to Cursor Workspace Node for agent {agent_name}."]
        if not workspace_path:
            raise RuntimeError(
                tr(
                    "Cannot open in Cursor: no active workspace path.",
                    "无法在 Cursor 中打开：没有激活的工作区路径。"
                )
            )
        try:
            open_workspace_in_cursor(workspace_path)
            output = tr(
                "Workspace opened in Cursor Desktop.",
                "已在 Cursor 桌面端中打开工作区。"
            )
            logs.append("Workspace opened in Cursor successfully.")
            return EngineResult(engine="Cursor", output=output, logs=logs)
        except Exception as exc:
            logs.append(f"Failed to open workspace in Cursor: {exc}")
            raise RuntimeError(
                tr(
                    f"Failed to open workspace in Cursor: {exc}",
                    f"无法在 Cursor 中打开工作区：{exc}"
                )
            ) from exc

    else:
        # Fallback to standard LLM Router
        from src.models_config import get_router
        router = get_router()
        model = router.get_active_model()
        engine_name = model.name
        logs = [f"Routing task to global LLM provider ({engine_name}) for agent {agent_name}."]

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
                    f"无法访问配置的模型 ({engine_name})。请在 设置 → 模型 配置 API Key。({exc})"
                )
            ) from exc
