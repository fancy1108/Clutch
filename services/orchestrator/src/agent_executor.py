"""Execute workflow agent_task nodes via configured LLM (M3 agent leg)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.chat_events import chat_message



@dataclass(frozen=True)
class AgentTaskResult:
    agent: str
    output: str
    logs: list[str]
    message: dict[str, Any]


def execute_agent_task(node_data: dict[str, Any], *, instruction: str = "") -> AgentTaskResult:
    agent = str(node_data.get("agent", "Builder"))
    task_instruction = instruction.strip() or str(node_data.get("instruction", "")).strip()
    tool = str(node_data.get("tool", "llm") or "llm")
    label = str(node_data.get("label", "")).strip()

    logs = [f"[{agent.upper()}] Starting: {label or task_instruction[:120] or 'agent task'}"]

    if not task_instruction:
        output = "No task instruction was provided for this agent step."
        logs.append(f"[{agent.upper()}] Skipped — empty instruction")
        return AgentTaskResult(
            agent=agent,
            output=output,
            logs=logs,
            message=chat_message(agent, output),
        )

    if tool in {"claude-cli", "llm", "cursor", ""}:
        from src.engine_router import route_engine
        from src.workspace import get_workspace

        workspace = get_workspace()
        cwd = workspace.get("workspace_path") if workspace else None

        prompt = (
            f"You are the {agent} agent in a supervised software workflow.\n\n"
            f"Task:\n{task_instruction}\n\n"
            "Respond concisely with what you would do, files touched, and next steps."
        )
        try:
            result = route_engine(
                agent_name=agent,
                prompt=prompt,
                cwd=cwd,
                fallback_tool=tool,
            )
            output = result.output
            for log_line in result.logs:
                logs.append(f"[{agent.upper()}] {log_line}")
        except Exception as exc:
            output = (
                f"Could not run task with {agent}. ({exc})"
            )
            logs.append(f"[{agent.upper()}] ERROR: {exc}")
    else:
        from src.mcp_storage import load_servers
        from src.workspace import get_workspace

        mcp_endpoint = None
        mcp_name = None
        mcp_env = None

        if tool in {"local-fs", "Local Filesystem MCP Server"}:
            mcp_name = "Local Filesystem"
            workspace = get_workspace()
            if workspace:
                mcp_endpoint = f"npx -y @modelcontextprotocol/server-filesystem {workspace['workspace_path']}"
            else:
                mcp_endpoint = "npx -y @modelcontextprotocol/server-filesystem"
        else:
            for s in load_servers():
                if s.get("enabled", True) and (s.get("id") == tool or s.get("name") == tool):
                    mcp_name = s.get("name")
                    mcp_endpoint = s.get("endpoint")
                    mcp_env = s.get("env")
                    break

        if mcp_endpoint:
            from src.mcp_client import McpClient
            from src.models_config import get_router

            client = McpClient(mcp_name or "mcp", mcp_endpoint, env=mcp_env)
            logs.append(f"[{agent.upper()}] Starting MCP Server: {mcp_name} ({mcp_endpoint})")

            if not client.start():
                output = f"Failed to start MCP server: {mcp_name} ({mcp_endpoint})"
                logs.append(f"[{agent.upper()}] ERROR: {output}")
                return AgentTaskResult(
                    agent=agent,
                    output=output,
                    logs=logs,
                    message=chat_message(agent, output),
                )

            try:
                mcp_tools = client.list_tools()
                logs.append(f"[{agent.upper()}] Discovered {len(mcp_tools)} tools")

                openai_tools = []
                for t in mcp_tools:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t["name"],
                            "description": t.get("description", ""),
                            "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
                        },
                    })

                router = get_router()
                model = router.get_active_model()
                messages = [
                    {
                        "role": "system",
                        "content": (
                            f"You are the {agent} agent in a supervised software workflow.\n"
                            f"You have access to the following MCP tools from {mcp_name}.\n"
                            f"Please solve the task instruction by using the tools. Reply with a concise message describing the outcome."
                        ),
                    },
                    {"role": "user", "content": task_instruction},
                ]

                # ReAct Loop
                for step_idx in range(10):
                    response = router.chat(messages, tools=openai_tools)
                    if isinstance(response, dict) and response.get("tool_calls"):
                        messages.append(response)
                        for tc in response["tool_calls"]:
                            tc_id = tc["id"]
                            func_name = tc["function"]["name"]
                            func_args = tc["function"]["arguments"]
                            if isinstance(func_args, str):
                                try:
                                    func_args = json.loads(func_args)
                                except Exception:
                                    pass

                            logs.append(f"[{agent.upper()}] Step {step_idx + 1}: Calling tool {func_name} with {json.dumps(func_args)}")
                            try:
                                tool_res = client.call_tool(func_name, func_args)
                                content_parts = []
                                for item in tool_res.get("content", []):
                                    if item.get("type") == "text":
                                        content_parts.append(item.get("text", ""))
                                result_str = "\n".join(content_parts) or json.dumps(tool_res)
                                logs.append(f"[{agent.upper()}] Tool response length: {len(result_str)} chars")
                            except Exception as exc:
                                result_str = f"Error executing tool: {exc}"
                                logs.append(f"[{agent.upper()}] Tool execution error: {exc}")

                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc_id,
                                "content": result_str,
                            })
                    else:
                        output = str(response)
                        logs.append(f"[{agent.upper()}] Task completed via {model.name}")
                        break
                else:
                    output = f"Agent task hit maximum tool call iteration limit (10) in {model.name}."
                    logs.append(f"[{agent.upper()}] ERROR: max iterations limit reached")
            except Exception as exc:
                output = f"Execution error: {exc}"
                logs.append(f"[{agent.upper()}] ERROR: {exc}")
            finally:
                client.close()
                logs.append(f"[{agent.upper()}] MCP Server {mcp_name} stopped")
        else:
            output = f"Tool {tool!r} is not wired yet for agent tasks."
            logs.append(f"[{agent.upper()}] {output}")

    logs.append(f"[{agent.upper()}] Output: {len(output)} chars")
    return AgentTaskResult(
        agent=agent,
        output=output,
        logs=logs,
        message=chat_message(agent, output),
    )

