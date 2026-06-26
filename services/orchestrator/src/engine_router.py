"""Engine router for deciding between Claude CLI, Cursor workspace, or global LLM provider."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.agent_storage import list_agents
from src.tools_status import load_connected_ids, resolve_tool_binary, tool_available_for_routing
from src.adapters.claude_cli_adapter import chat_claude_cli
from src.adapters.agy_cli_adapter import chat_agy_cli
from src.adapters.cursor_adapter import open_workspace_in_cursor
from src.agent_type import agent_type_from_record, resolve_model_for_agent
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
    if key in {
        "antigravity cli",
        "antigravity-cli",
        "antigravity",
        "agenty cli",
        "agy-cli",
        "agy cli",
    }:
        return "Antigravity CLI"
    if key in {
        "ollama",
        "ollama-cli",
        "ollama (cli)",
    }:
        return "Ollama"
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


def _emit_log(logs: list[str], on_log: Callable[[str], None] | None, line: str) -> None:
    logs.append(line)
    if on_log:
        on_log(line)


def _resolve_agent_type(agent: dict[str, Any] | None, fallback_tool: str | None) -> str:
    if agent:
        return agent_type_from_record(agent)
    if fallback_tool == "claude-cli":
        return "claude-cli"
    if fallback_tool in {"agy-cli", "agy"}:
        return "antigravity-cli"
    if fallback_tool == "cursor":
        return "cursor-workspace"
    if fallback_tool in {"ollama", "ollama-cli"}:
        return "ollama-cli"
    return "clutch"


def _route_engine_raw(
    agent_name: str,
    prompt: str,
    system_prompt: str | None = None,
    cwd: str | None = None,
    history: list[dict[str, str]] | None = None,
    fallback_tool: str | None = None,
    claude_session_id: str | None = None,
    on_log: Callable[[str], None] | None = None,
) -> EngineResult:
    agent = find_agent(agent_name)
    agent_type = _resolve_agent_type(agent, fallback_tool)

    workspace_path = cwd
    if not workspace_path:
        workspace = get_workspace()
        if workspace:
            workspace_path = workspace.get("workspace_path")

    logs: list[str] = []
    _emit_log(
        logs,
        on_log,
        (
            f"[ROUTER] agent={agent_name!r} matched={agent is not None} "
            f"agentType={agent_type!r} "
            f"claude_path={resolve_tool_binary('claude-cli')!r} "
            f"connected={'claude-cli' in load_connected_ids()}"
        ),
    )

    if agent_type == "clutch":
        from src.image_router import format_image_reply, generate_image_for_model, is_image_model
        from src.models_config import get_router

        router = get_router()
        spec, model_id = resolve_model_for_agent(router, agent)
        if is_image_model(spec):
            _emit_log(logs, on_log, f"Routing image generation to {spec.name} for agent {agent_name}.")
            api_key = router.resolve_for_model(model_id)[1]
            try:
                result = generate_image_for_model(
                    spec,
                    prompt,
                    api_key=router._require_api_key(spec.provider_id, api_key),
                    on_log=on_log,
                )
                output = format_image_reply(result)
                _emit_log(logs, on_log, f"Image generation completed via {spec.name}.")
                return EngineResult(engine=spec.name, output=output, logs=logs)
            except Exception as exc:
                _emit_log(logs, on_log, f"Image generation failed: {exc}")
                raise RuntimeError(
                    tr(
                        f"Image generation failed ({spec.name}): {exc}",
                        f"生图失败 ({spec.name})：{exc}",
                    )
                ) from exc

    if agent_type == "claude-cli" and tool_available_for_routing("claude-cli"):
        cli_binary = resolve_tool_binary("claude-cli")
        _emit_log(logs, on_log, f"Routing task to Claude Code (Local CLI) for agent {agent_name}.")
        if cli_binary:
            _emit_log(logs, on_log, f"Using Claude binary: {cli_binary}")
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
                on_log=on_log,
            )

        try:
            if claude_session_id:
                _emit_log(logs, on_log, f"Resuming Claude CLI session {claude_session_id}.")
                output = _invoke_cli(
                    cli_prompt=prompt,
                    cli_system_prompt=None,
                    resume_session_id=claude_session_id,
                )
                _emit_log(logs, on_log, "Claude CLI session resumed successfully.")
                return EngineResult(
                    engine="Claude CLI",
                    output=output,
                    logs=logs,
                    claude_session_id=claude_session_id,
                )

            history_prompt = _format_history_for_cli_prompt(history).strip()
            bootstrap_prompt = history_prompt or prompt
            new_session_id = str(uuid.uuid4())
            _emit_log(logs, on_log, f"Starting new Claude CLI session {new_session_id}.")
            output = _invoke_cli(
                cli_prompt=bootstrap_prompt,
                cli_system_prompt=system_prompt,
                session_id=new_session_id,
            )
            _emit_log(logs, on_log, "Claude CLI execution completed successfully.")
            return EngineResult(
                engine="Claude CLI",
                output=output,
                logs=logs,
                claude_session_id=new_session_id,
            )
        except Exception as exc:
            if claude_session_id:
                _emit_log(logs, on_log, f"Claude session resume failed ({exc}); replaying history.")
                try:
                    history_prompt = _format_history_for_cli_prompt(history).strip() or prompt
                    new_session_id = str(uuid.uuid4())
                    output = _invoke_cli(
                        cli_prompt=history_prompt,
                        cli_system_prompt=system_prompt,
                        session_id=new_session_id,
                    )
                    _emit_log(logs, on_log, f"Claude CLI recovered with new session {new_session_id}.")
                    return EngineResult(
                        engine="Claude CLI",
                        output=output,
                        logs=logs,
                        claude_session_id=new_session_id,
                    )
                except Exception as retry_exc:
                    _emit_log(logs, on_log, f"Claude CLI recovery failed: {retry_exc}")
                    raise RuntimeError(
                        tr(
                            f"Failed to execute task via Claude CLI: {retry_exc}",
                            f"通过 Claude CLI 执行任务失败：{retry_exc}",
                        )
                    ) from retry_exc
            _emit_log(logs, on_log, f"Claude CLI execution failed: {exc}")
            raise RuntimeError(
                tr(
                    f"Failed to execute task via Claude CLI: {exc}",
                    f"通过 Claude CLI 执行任务失败：{exc}",
                )
            ) from exc

    if agent_type == "antigravity-cli" and tool_available_for_routing("agy-cli"):
        cli_binary = resolve_tool_binary("agy-cli")
        _emit_log(logs, on_log, f"Routing task to Antigravity CLI for agent {agent_name}.")
        if cli_binary:
            _emit_log(logs, on_log, f"Using Antigravity binary: {cli_binary}")
        elif "agy-cli" in load_connected_ids():
            raise RuntimeError(
                tr(
                    "Antigravity CLI is connected but the `agy` binary was not found. "
                    "Restart Clutch after install, or ensure it is on PATH "
                    "(e.g. /opt/homebrew/bin/agy).",
                    "Antigravity CLI 已连接，但未找到 `agy` 可执行文件。"
                    "请安装后重启 Clutch，或确认其在 PATH 中（如 /opt/homebrew/bin/agy）。",
                )
            )

        try:
            _emit_log(logs, on_log, f"Executing Antigravity CLI prompt...")
            output = chat_agy_cli(
                prompt=prompt,
                cwd=workspace_path,
                system_prompt=system_prompt,
                resume_session_id=claude_session_id,
                binary=cli_binary,
                on_log=on_log,
            )
            _emit_log(logs, on_log, "Antigravity CLI execution completed successfully.")
            return EngineResult(
                engine="Antigravity CLI",
                output=output,
                logs=logs,
                claude_session_id=claude_session_id or "agy-session",
            )
        except Exception as exc:
            _emit_log(logs, on_log, f"Antigravity CLI execution failed: {exc}")
            raise RuntimeError(
                tr(
                    f"Failed to execute task via Antigravity CLI: {exc}",
                    f"通过 Antigravity CLI 执行任务失败：{exc}",
                )
            ) from exc

    if agent_type == "cursor-workspace" and tool_available_for_routing("cursor-app"):
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

    if agent_type == "ollama-cli" and tool_available_for_routing("ollama-cli"):
        from src.adapters.ollama_adapter import chat_ollama
        _emit_log(logs, on_log, f"Routing task to Ollama for agent {agent_name}.")
        try:
            configured_model = str(agent.get("ollamaModel", "")) if agent else ""
            model_tag, output = chat_ollama(
                prompt=prompt,
                model=configured_model or None,
                system_prompt=system_prompt,
                history=history,
                on_log=on_log,
            )
            _emit_log(logs, on_log, f"Ollama execution completed successfully via {model_tag}.")
            return EngineResult(
                engine=f"Ollama ({model_tag})",
                output=output,
                logs=logs,
            )
        except Exception as exc:
            _emit_log(logs, on_log, f"Ollama execution failed: {exc}")
            raise RuntimeError(
                tr(
                    f"Failed to execute task via Ollama: {exc}",
                    f"通过 Ollama 执行任务失败：{exc}",
                )
            ) from exc

    if agent_type == "claude-cli":
        logs.append(
            tr(
                f"Agent {agent_name} requests Claude CLI but `claude` is not installed/connected — falling back to LLM.",
                f"Agent {agent_name} 需要 Claude CLI，但未安装或未连接，已回退到 LLM。",
            )
        )
    elif agent_type == "antigravity-cli":
        logs.append(
            tr(
                f"Agent {agent_name} requests Antigravity CLI but `agy` is not installed/connected — falling back to LLM.",
                f"Agent {agent_name} 需要 Antigravity CLI，但未安装或未连接，已回退到 LLM。",
            )
        )
    elif agent_type == "ollama-cli":
        logs.append(
            tr(
                f"Agent {agent_name} requests Ollama but Ollama is not installed/connected — falling back to LLM.",
                f"Agent {agent_name} 需要 Ollama，但未安装或未连接，已回退到 LLM。",
            )
        )

    from src.models_config import get_router

    router = get_router()
    spec, model_id = resolve_model_for_agent(router, agent)
    engine_name = spec.name
    logs.append(f"Routing task to Clutch model ({engine_name}) for agent {agent_name}.")

    chat_history = history
    if not chat_history:
        chat_history = []
        if system_prompt:
            chat_history.append({"role": "system", "content": system_prompt})
        chat_history.append({"role": "user", "content": prompt})

    try:
        output = router.chat(chat_history, model_id=model_id)
        logs.append(f"Clutch model execution completed successfully via {engine_name}.")
        return EngineResult(engine=engine_name, output=output, logs=logs)
    except Exception as exc:
        logs.append(f"Clutch model execution failed: {exc}")
        raise RuntimeError(
            tr(
                f"Cannot reach the configured model ({engine_name}). Add an API key in Settings → Models. ({exc})",
                f"无法访问配置的模型 ({engine_name})。请在 设置 → 模型 配置 API Key。({exc})",
            )
        ) from exc


import re

MODEL_BRAND_REPLACEMENTS = [
    (r"\bAgnes\b", "Gemini"),
    (r"\bagnes\b", "gemini"),
]


def sanitize_engine_output(text: str) -> str:
    if not text:
        return text
    for pattern, replacement in MODEL_BRAND_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    return text


def route_engine(
    agent_name: str,
    prompt: str,
    system_prompt: str | None = None,
    cwd: str | None = None,
    history: list[dict[str, str]] | None = None,
    fallback_tool: str | None = None,
    claude_session_id: str | None = None,
    on_log: Callable[[str], None] | None = None,
) -> EngineResult:
    res = _route_engine_raw(
        agent_name=agent_name,
        prompt=prompt,
        system_prompt=system_prompt,
        cwd=cwd,
        history=history,
        fallback_tool=fallback_tool,
        claude_session_id=claude_session_id,
        on_log=on_log,
    )
    return EngineResult(
        engine=res.engine,
        output=sanitize_engine_output(res.output),
        logs=res.logs,
        claude_session_id=res.claude_session_id,
    )
