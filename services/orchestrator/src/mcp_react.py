"""MCP + LLM ReAct loop shared by workflow nodes and plain chat (P2-15 / P2-16)."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.mcp_client import McpClient
from src.mcp_risk import is_risky_mcp_tool


@dataclass(frozen=True)
class McpRunOutcome:
    output: str
    logs: list[str]
    engine_label: str
    approval_required: dict[str, Any] | None = None


def _tool_alias(server_id: str, tool_name: str) -> str:
    return f"{server_id}::{tool_name}"


def _parse_tool_alias(alias: str) -> tuple[str, str] | None:
    if "::" not in alias:
        return None
    server_id, tool_name = alias.split("::", 1)
    if not server_id or not tool_name:
        return None
    return server_id, tool_name


def _emit(logs: list[str], on_log: Callable[[str], None] | None, line: str) -> None:
    logs.append(line)
    if on_log:
        on_log(line)


def _execute_tool_call(
    *,
    func_name: str,
    func_args: dict[str, Any],
    tool_routes: dict[str, tuple[str, str]],
    clients: dict[str, McpClient],
    log_prefix: str,
    logs: list[str],
    on_log: Callable[[str], None] | None,
    step_idx: int,
) -> str:
    route = _parse_tool_alias(func_name)
    _emit(
        logs,
        on_log,
        f"[{log_prefix}] Step {step_idx + 1}: {func_name} "
        f"args={json.dumps(func_args, ensure_ascii=False)[:240]}",
    )
    if route is None:
        return f"Unknown tool alias: {func_name}"
    server_id, tool_name = route
    client = clients.get(server_id)
    if client is None:
        return f"MCP server not connected: {server_id}"
    try:
        tool_res = client.call_tool(tool_name, func_args)
        content_parts = [
            item.get("text", "")
            for item in tool_res.get("content", [])
            if item.get("type") == "text"
        ]
        result_str = "\n".join(content_parts) or json.dumps(tool_res)
        _emit(logs, on_log, f"[{log_prefix}] Tool response length: {len(result_str)} chars")
        return result_str
    except Exception as exc:
        _emit(logs, on_log, f"[{log_prefix}] Tool error: {exc}")
        return f"Error executing tool: {exc}"


def run_mcp_react_loop(
    *,
    messages: list[dict[str, Any]],
    servers: list[dict[str, Any]],
    log_prefix: str = "MCP",
    max_steps: int = 10,
    on_log: Callable[[str], None] | None = None,
    pause_on_risky: bool = False,
    approved_tool: dict[str, Any] | None = None,
) -> McpRunOutcome:
    """Run tool-augmented chat against one or more MCP servers."""
    if not servers:
        raise ValueError("At least one MCP server is required")

    from src.models_config import get_router

    clients: dict[str, McpClient] = {}
    tool_routes: dict[str, tuple[str, str]] = {}
    openai_tools: list[dict[str, Any]] = []
    logs: list[str] = []
    _emit(logs, on_log, f"[{log_prefix}] Starting MCP ReAct with {len(servers)} server(s)")

    for server in servers:
        server_id = str(server.get("id", "mcp"))
        name = str(server.get("name", server_id))
        endpoint = str(server.get("endpoint", ""))
        env = server.get("env") if isinstance(server.get("env"), dict) else None
        client = McpClient(name, endpoint, env=env)
        if not client.start():
            _emit(logs, on_log, f"[{log_prefix}] Failed to start MCP server: {name}")
            for started in clients.values():
                started.close()
            raise RuntimeError(f"Failed to start MCP server: {name}")
        clients[server_id] = client
        _emit(logs, on_log, f"[{log_prefix}] Connected MCP server: {name}")

        for tool in client.list_tools():
            tool_name = str(tool.get("name", "")).strip()
            if not tool_name:
                continue
            alias = _tool_alias(server_id, tool_name)
            tool_routes[alias] = (server_id, tool_name)
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": alias,
                        "description": tool.get("description", "") or f"{name}: {tool_name}",
                        "parameters": tool.get(
                            "inputSchema",
                            {"type": "object", "properties": {}},
                        ),
                    },
                }
            )

    _emit(logs, on_log, f"[{log_prefix}] Discovered {len(openai_tools)} tool(s)")
    router = get_router()
    model = router.get_active_model()
    engine_label = f"{model.name} · MCP ({len(openai_tools)} tools)"
    output = ""

    try:
        chat_messages = list(messages)
        start_step = 0

        if approved_tool:
            tc_id = str(approved_tool["tool_call_id"])
            func_name = str(approved_tool["func_name"])
            func_args = approved_tool.get("func_args") or {}
            if not isinstance(func_args, dict):
                func_args = {}
            start_step = int(approved_tool.get("step_idx", 0))
            result_str = _execute_tool_call(
                func_name=func_name,
                func_args=func_args,
                tool_routes=tool_routes,
                clients=clients,
                log_prefix=log_prefix,
                logs=logs,
                on_log=on_log,
                step_idx=start_step,
            )
            chat_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result_str,
                }
            )
            start_step += 1

        for step_idx in range(start_step, max_steps):
            response = router.chat(chat_messages, tools=openai_tools or None)
            if isinstance(response, dict) and response.get("tool_calls"):
                chat_messages.append(response)
                for tool_call in response["tool_calls"]:
                    tc_id = tool_call["id"]
                    func_name = tool_call["function"]["name"]
                    func_args = tool_call["function"]["arguments"]
                    if isinstance(func_args, str):
                        try:
                            func_args = json.loads(func_args)
                        except json.JSONDecodeError:
                            pass
                    if not isinstance(func_args, dict):
                        func_args = {}

                    _, raw_tool_name = _parse_tool_alias(func_name) or ("", func_name)
                    if pause_on_risky and is_risky_mcp_tool(raw_tool_name):
                        _emit(
                            logs,
                            on_log,
                            f"[{log_prefix}] Approval required for risky tool: {func_name}",
                        )
                        return McpRunOutcome(
                            output="",
                            logs=logs,
                            engine_label=engine_label,
                            approval_required={
                                "chat_messages": chat_messages,
                                "tool_call_id": tc_id,
                                "func_name": func_name,
                                "func_args": func_args,
                                "step_idx": step_idx,
                            },
                        )

                    result_str = _execute_tool_call(
                        func_name=func_name,
                        func_args=func_args,
                        tool_routes=tool_routes,
                        clients=clients,
                        log_prefix=log_prefix,
                        logs=logs,
                        on_log=on_log,
                        step_idx=step_idx,
                    )
                    chat_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": result_str,
                        }
                    )
            else:
                output = str(response)
                _emit(logs, on_log, f"[{log_prefix}] Completed via {model.name}")
                break
        else:
            output = (
                f"Agent task hit maximum tool call iteration limit ({max_steps}) "
                f"in {model.name}."
            )
            _emit(logs, on_log, f"[{log_prefix}] ERROR: max iterations limit reached")
    finally:
        for server_id, client in clients.items():
            name = str(next(
                (s.get("name", server_id) for s in servers if str(s.get("id")) == server_id),
                server_id,
            ))
            client.close()
            _emit(logs, on_log, f"[{log_prefix}] Stopped MCP server: {name}")

    return McpRunOutcome(
        output=output,
        logs=logs,
        engine_label=engine_label,
        approval_required=None,
    )
