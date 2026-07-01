"""Execute workflow agent_task nodes via configured LLM (M3 agent leg)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.chat_events import chat_message
from src.terminal_logs import agent_line, resolve_agent_tag, with_agent_prefix


@dataclass(frozen=True)
class AgentTaskResult:
    agent: str
    output: str
    logs: list[str]
    message: dict[str, Any]
    state_patch: dict[str, Any] | None = None
    failed: bool = False


def _agent_display_name(agent_dict: dict[str, Any] | None, fallback: str) -> str:
    if agent_dict and str(agent_dict.get("name", "")).strip():
        return str(agent_dict["name"]).strip()
    return fallback


def _agent_id_for_session(agent_dict: dict[str, Any] | None, agent_ref: str) -> str:
    if agent_dict and str(agent_dict.get("id", "")).strip():
        return str(agent_dict["id"]).strip()
    return agent_ref


def _read_flow_cli_session_id(run_id: str, agent_id: str) -> str | None:
    from src.run_state_store import load_run_state
    from src.state import read_cli_session_agent_id, read_cli_session_id

    state = load_run_state(run_id)
    if state is None:
        return None
    stored_agent = read_cli_session_agent_id(state)
    if stored_agent and stored_agent != agent_id:
        return None
    sid = read_cli_session_id(state)
    return sid if sid else None


def _persist_flow_cli_session(
    run_id: str,
    agent_id: str,
    cli_session_id: str | None,
    *,
    extra_patch: dict[str, Any] | None = None,
) -> None:
    if not run_id or not cli_session_id:
        return
    from src.state import cli_session_patch
    from src.workflow_runtime import emit_workflow_agent_step

    patch = cli_session_patch(cli_session_id, agent_id)
    if extra_patch:
        patch = {**patch, **extra_patch}
    emit_workflow_agent_step(run_id, patch)


def _run_clutch_chat_task(
    *,
    agent_dict: dict[str, Any],
    task_instruction: str,
    agent_ref: str,
    label: str,
    run_id: str,
    node_id: str,
    stream_log,
) -> tuple[str, list[str]]:
    from src.agent_mcp import resolve_agent_mcp_servers
    from src.agent_prompt import compose_agent_system_prompt
    from src.agent_type import resolve_model_for_agent
    from src.image_router import is_image_model
    from src.video_router import is_video_model
    from src.models_config import get_router
    from src.mcp_react import run_mcp_react_loop

    router = get_router()
    spec, model_id = resolve_model_for_agent(router, agent_dict)
    if is_image_model(spec) or is_video_model(spec):
        raise RuntimeError("media model should be handled before clutch chat")

    mcp_servers = resolve_agent_mcp_servers(agent_dict)
    system_prompt = compose_agent_system_prompt(
        agent_dict,
        model_name=spec.name,
        model_api=spec.api_model,
        mcp_servers_bound=bool(mcp_servers),
    )
    chat_messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_instruction},
    ]
    extra_logs: list[str] = []

    if mcp_servers:
        outcome = run_mcp_react_loop(
            messages=chat_messages,
            servers=mcp_servers,
            log_prefix=resolve_agent_tag(agent_ref, label=label),
            on_log=stream_log if run_id else None,
            model_id=model_id,
        )
        extra_logs.extend(outcome.logs)
        return outcome.output, extra_logs

    response = router.chat(chat_messages, model_id=model_id)
    if isinstance(response, dict):
        content = response.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip(), extra_logs
        return str(response), extra_logs
    return str(response), extra_logs


def execute_agent_task(
    node_data: dict[str, Any],
    *,
    instruction: str = "",
    run_id: str = "",
    node_id: str = "",
) -> AgentTaskResult:
    agent_ref = str(node_data.get("agent", "")).strip()
    task_instruction = instruction.strip() or str(node_data.get("instruction", "")).strip()
    tool = str(node_data.get("tool", "llm") or "llm")
    label = str(node_data.get("label", "")).strip()
    agent = agent_ref or label or "Agent"

    def stream_log(line: str) -> None:
        if not run_id:
            return
        from src.run_log_forwarder import get_forwarder

        get_forwarder(run_id).emit(
            with_agent_prefix(agent_ref, line, label=label),
            node_id=node_id,
        )

    logs = [
        agent_line(
            agent_ref,
            f"Starting: {label or task_instruction[:120] or 'agent task'}",
            label=label,
        )
    ]
    if run_id:
        stream_log(logs[0])

    if not task_instruction:
        output = "No task instruction was provided for this agent step."
        logs.append(agent_line(agent_ref, "Skipped — empty instruction", label=label))
        return AgentTaskResult(
            agent=agent,
            output=output,
            logs=logs,
            message=chat_message(agent, output),
        )

    from src.agent_type import is_clutch_agent
    from src.engine_router import find_agent

    agent_dict = find_agent(agent_ref or agent)
    display_name = _agent_display_name(agent_dict, agent)
    output = ""
    state_patch: dict[str, Any] | None = None
    result_message: dict[str, Any] | None = None
    task_failed = False

    if tool in {"claude-cli", "agy-cli", "agy", "antigravity-cli", "codex-cli", "codex", "aider-cli", "opencode-cli", "opencode", "llm", "ollama", "ollama-cli", ""}:
        from src.agent_type import resolve_model_for_agent
        from src.engine_router import route_engine
        from src.image_router import format_image_reply, generate_image_for_model, is_image_model
        from src.video_router import format_video_reply, generate_video_for_model, is_video_model
        from src.models_config import get_router
        from src.workspace import get_workspace

        workspace = get_workspace()
        cwd = workspace.get("workspace_path") if workspace else None

        if agent_dict and is_clutch_agent(agent_dict):
            router = get_router()
            spec, model_id = resolve_model_for_agent(router, agent_dict)
            if is_video_model(spec):
                api_key = router.resolve_for_model(model_id)[1]
                try:
                    result = generate_video_for_model(
                        spec,
                        task_instruction,
                        api_key=router._require_api_key(spec.provider_id, api_key),
                        on_log=stream_log if run_id else None,
                    )
                    output = format_video_reply(result)
                    logs.append(
                        agent_line(agent_ref, f"Video generated via {spec.name}", label=label)
                    )
                    if run_id:
                        stream_log(logs[-1])
                    logs.append(agent_line(agent_ref, f"Output: {len(output)} chars", label=label))
                    if run_id:
                        stream_log(logs[-1])
                    return AgentTaskResult(
                        agent=display_name,
                        output=output,
                        logs=logs,
                        message=chat_message(display_name, output),
                    )
                except Exception as exc:
                    output = f"Video generation failed: {exc}"
                    logs.append(agent_line(agent_ref, f"ERROR: {exc}", label=label))
                    if run_id:
                        stream_log(logs[-1])
                    return AgentTaskResult(
                        agent=display_name,
                        output=output,
                        logs=logs,
                        message=chat_message(display_name, output),
                    )
            if is_image_model(spec):
                api_key = router.resolve_for_model(model_id)[1]
                try:
                    result = generate_image_for_model(
                        spec,
                        task_instruction,
                        api_key=router._require_api_key(spec.provider_id, api_key),
                        on_log=stream_log if run_id else None,
                    )
                    output = format_image_reply(result)
                    logs.append(
                        agent_line(agent_ref, f"Image generated via {spec.name}", label=label)
                    )
                    if run_id:
                        stream_log(logs[-1])
                    logs.append(agent_line(agent_ref, f"Output: {len(output)} chars", label=label))
                    if run_id:
                        stream_log(logs[-1])
                    return AgentTaskResult(
                        agent=display_name,
                        output=output,
                        logs=logs,
                        message=chat_message(display_name, output),
                    )
                except Exception as exc:
                    output = f"Image generation failed: {exc}"
                    logs.append(agent_line(agent_ref, f"ERROR: {exc}", label=label))
                    if run_id:
                        stream_log(logs[-1])
                    return AgentTaskResult(
                        agent=display_name,
                        output=output,
                        logs=logs,
                        message=chat_message(display_name, output),
                    )

            try:
                output, clutch_logs = _run_clutch_chat_task(
                    agent_dict=agent_dict,
                    task_instruction=task_instruction,
                    agent_ref=agent_ref,
                    label=label,
                    run_id=run_id,
                    node_id=node_id,
                    stream_log=stream_log,
                )
                for log_line in clutch_logs:
                    logs.append(with_agent_prefix(agent_ref, log_line, label=label))
            except Exception as exc:
                output = f"Could not run Clutch task with {display_name}. ({exc})"
                logs.append(agent_line(agent_ref, f"ERROR: {exc}", label=label))
                return AgentTaskResult(
                    agent=display_name,
                    output=output,
                    logs=logs,
                    message=chat_message(display_name, output),
                )
            logs.append(agent_line(agent_ref, f"Output: {len(output)} chars", label=label))
            if run_id:
                stream_log(logs[-1])
            return AgentTaskResult(
                agent=display_name,
                output=output,
                logs=logs,
                message=chat_message(display_name, output),
            )

        prompt = task_instruction
        system_prompt: str | None = None
        if agent_dict:
            from src.agent_prompt import compose_agent_system_prompt
            from src.agent_type import resolve_model_for_agent

            router = get_router()
            spec, _model_id = resolve_model_for_agent(router, agent_dict)
            system_prompt = compose_agent_system_prompt(
                agent_dict,
                model_name=spec.name,
                model_api=spec.api_model,
                mcp_servers_bound=False,
                clutch_mcp_path=False,
            )
        agent_id_for_session = _agent_id_for_session(agent_dict, agent_ref or agent)
        from src.agent_type import agent_type_from_record

        resolved_agent_type = agent_type_from_record(agent_dict) if agent_dict else ""
        cli_session_id: str | None = None
        if resolved_agent_type in {"claude-cli", "antigravity-cli", "codex-cli", "aider-cli"} and run_id:
            from src.runtime_config import hybrid_eligible

            if hybrid_eligible(source="flow", agent_type=resolved_agent_type):
                cli_session_id = _read_flow_cli_session_id(run_id, agent_id_for_session)
        try:
            result = route_engine(
                agent_name=agent_ref or agent,
                prompt=prompt,
                system_prompt=system_prompt,
                cwd=cwd,
                fallback_tool=tool,
                cli_session_id=cli_session_id,
                on_log=stream_log if run_id else None,
                run_id=run_id,
                source="flow",
            )
            output = result.output
            if not str(output or "").strip():
                probe = str(result.raw_output or "").strip()
                if probe:
                    from src.claude_hybrid_output_parser import extract_tty_cli_output

                    output = extract_tty_cli_output(probe) or probe
            if resolved_agent_type:
                from src.adapters.cli_adapter import (
                    format_cli_login_retry_message,
                    is_cli_auth_issue,
                    is_formatted_login_retry_message,
                )
                from src.claude_hybrid_output_parser import extract_cli_issue_message

                auth_probe = result.raw_output or output
                if is_cli_auth_issue(auth_probe) and not is_formatted_login_retry_message(
                    output
                ):
                    issue = extract_cli_issue_message(auth_probe) or ""
                    output = format_cli_login_retry_message(
                        resolved_agent_type,
                        raw_message=issue,
                    )
                    auth_log = agent_line(
                        agent_ref,
                        "CLI sign-in required — complete auth in Terminal, then retry",
                        label=label,
                    )
                    logs.append(auth_log)
                    if run_id:
                        stream_log(auth_log)
            for log_line in result.logs:
                logs.append(with_agent_prefix(agent_ref, log_line, label=label))
            message = chat_message(display_name, output)
            state_patch = None
            if result.engine and "Hybrid" in result.engine:
                message["runtimeEngine"] = result.engine
                if result.raw_output:
                    message["rawOutput"] = result.raw_output
                if result.output_events:
                    events = [dict(event) for event in result.output_events]
                    for event in events:
                        if (
                            event.get("type") == "assistant"
                            and event.get("visible", True) is not False
                        ):
                            event["content"] = output
                    message["outputEvents"] = events
                state_patch = {
                    "hybrid_executions": {
                        str(message["id"]): {
                            "rawOutput": result.raw_output,
                            "outputEvents": message.get("outputEvents") or [],
                        }
                    }
                }
            if (
                resolved_agent_type in {"claude-cli", "antigravity-cli", "codex-cli", "aider-cli"}
                and run_id
                and result.cli_session_id
            ):
                _persist_flow_cli_session(
                    run_id,
                    agent_id_for_session,
                    result.cli_session_id,
                    extra_patch=state_patch,
                )
            result_message = message
        except Exception as exc:
            from src.adapters.cli_adapter import (
                format_cli_login_retry_message,
                format_flow_cli_failure,
                is_cli_auth_issue,
            )

            if resolved_agent_type and is_cli_auth_issue(str(exc)):
                output = format_cli_login_retry_message(
                    resolved_agent_type,
                    raw_message=str(exc),
                )
                logs.append(
                    agent_line(
                        agent_ref,
                        "CLI sign-in required — complete auth in Terminal, then retry",
                        label=label,
                    )
                )
                if run_id:
                    stream_log(logs[-1])
            else:
                output = format_flow_cli_failure(display_name, resolved_agent_type, exc)
                logs.append(agent_line(agent_ref, f"ERROR: {exc}", label=label))
            result_message = chat_message(display_name, output, status="FAILED")
            task_failed = True
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
            servers = [
                {
                    "id": tool if tool not in {"local-fs", "Local Filesystem MCP Server"} else "local-fs",
                    "name": mcp_name or "mcp",
                    "endpoint": mcp_endpoint,
                }
            ]
            if mcp_env:
                servers[0]["env"] = mcp_env
            if tool in {"local-fs", "Local Filesystem MCP Server"}:
                from src.builtin_tools import resolve_clutch_tools_server

                clutch_tools = resolve_clutch_tools_server()
                if clutch_tools:
                    servers.append(clutch_tools)

            from src.mcp_react import run_mcp_react_loop

            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are the {display_name} agent in a supervised software workflow.\n"
                        f"You have access to MCP tools from {mcp_name}.\n"
                        "Solve the task by using tools when needed. Reply concisely."
                    ),
                },
                {"role": "user", "content": task_instruction},
            ]
            try:
                outcome = run_mcp_react_loop(
                    messages=messages,
                    servers=servers,
                    log_prefix=resolve_agent_tag(agent_ref, label=label),
                    on_log=stream_log if run_id else None,
                )
                output = outcome.output
                for log_line in outcome.logs:
                    logs.append(with_agent_prefix(agent_ref, log_line, label=label))
            except Exception as exc:
                output = f"Execution error: {exc}"
                logs.append(agent_line(agent_ref, f"ERROR: {exc}", label=label))
        else:
            output = f"Tool {tool!r} is not wired yet for agent tasks."
            logs.append(agent_line(agent_ref, output, label=label))

    logs.append(agent_line(agent_ref, f"Output: {len(output)} chars", label=label))
    if run_id:
        stream_log(logs[-1])

    from src.adapters.cli_adapter import is_agent_task_failure

    failed = task_failed or is_agent_task_failure(output)
    if failed and result_message and not result_message.get("status"):
        result_message = {**result_message, "status": "FAILED"}

    return AgentTaskResult(
        agent=display_name,
        output=output,
        logs=logs,
        message=result_message or chat_message(display_name, output, status="FAILED" if failed else None),
        state_patch=state_patch,
        failed=failed,
    )
