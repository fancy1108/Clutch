"""Execute workflow agent_task nodes via configured LLM (M3 agent leg)."""

from __future__ import annotations

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
            server_entry = {
                "id": tool if tool not in {"local-fs", "Local Filesystem MCP Server"} else "local-fs",
                "name": mcp_name or "mcp",
                "endpoint": mcp_endpoint,
            }
            if mcp_env:
                server_entry["env"] = mcp_env

            from src.mcp_react import run_mcp_react_loop

            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are the {agent} agent in a supervised software workflow.\n"
                        f"You have access to MCP tools from {mcp_name}.\n"
                        "Solve the task by using tools when needed. Reply concisely."
                    ),
                },
                {"role": "user", "content": task_instruction},
            ]
            try:
                outcome = run_mcp_react_loop(
                    messages=messages,
                    servers=[server_entry],
                    log_prefix=agent.upper(),
                )
                output = outcome.output
                for log_line in outcome.logs:
                    logs.append(log_line if log_line.startswith("[") else f"[{agent.upper()}] {log_line}")
            except Exception as exc:
                output = f"Execution error: {exc}"
                logs.append(f"[{agent.upper()}] ERROR: {exc}")
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

