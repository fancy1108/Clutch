"""MCP + LLM ReAct loop shared by workflow nodes and plain chat (P2-15 / P2-16)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.mcp_client import McpClient
from src.mcp_risk import (
    extract_mcp_file_path,
    is_risky_mcp_tool,
    mcp_approval_key,
    move_file_delete_workaround_message,
)

# Tools that auto-approve in auto_edit mode (safe file writes within workspace)
_AUTO_EDIT_APPROVED_TOOLS = frozenset({
    "write_file",
    "edit_file",
    "apply_patch",
    "create_file",
    "patch_file",
    "search_replace",
})

# Tools that are ALWAYS hard-blocked in plan mode
_PLAN_MODE_BLOCKED_TOKENS = (
    "write", "edit", "create", "patch", "delete", "remove",
    "move", "rename", "run", "execute", "shell", "command",
)

_INVALID_TOOL_NAME_CHARS = re.compile(r"[^a-zA-Z0-9_-]")


@dataclass(frozen=True)
class McpRunOutcome:
    output: str
    logs: list[str]
    engine_label: str
    approval_required: dict[str, Any] | None = None
    files_changed: list[str] | None = None
    tool_steps: list[dict[str, Any]] | None = None
    todos: list[dict[str, Any]] | None = None
    verification_report: dict[str, Any] | None = None
    diff_summary: dict[str, Any] | None = None
    # D9: loop fuse + chat-visible step accounting
    fuse_triggered: bool = False
    steps_used: int = 0
    consecutive_failures: int = 0


def _sanitize_tool_part(value: str) -> str:
    cleaned = _INVALID_TOOL_NAME_CHARS.sub("_", value.strip())
    return cleaned or "tool"


def _tool_alias(server_id: str, tool_name: str) -> str:
    """OpenAI-compatible tool name (^[a-zA-Z0-9_-]+$)."""
    return f"{_sanitize_tool_part(server_id)}__{_sanitize_tool_part(tool_name)}"


def _emit(logs: list[str], on_log: Callable[[str], None] | None, line: str) -> None:
    logs.append(line)
    if on_log:
        on_log(line)


def _record_file_change(
    files_changed: list[str],
    *,
    tool_name: str,
    func_args: dict[str, Any],
    result_str: str,
) -> None:
    if result_str.startswith("Error executing tool"):
        return
    if tool_name == "apply_patch":
        try:
            payload = json.loads(result_str)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            for raw in payload.get("changed_paths") or []:
                rel = str(raw).strip()
                if rel and rel not in files_changed:
                    files_changed.append(rel)
            return
    if tool_name == "search_replace":
        try:
            payload = json.loads(result_str)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            recorded = False
            for raw in payload.get("changed_paths") or []:
                rel = str(raw).strip()
                if rel and rel not in files_changed:
                    files_changed.append(rel)
                    recorded = True
            path_one = str(payload.get("path") or "").strip()
            if path_one and path_one not in files_changed:
                files_changed.append(path_one)
                recorded = True
            if recorded:
                return
            # Fall through to arg path if JSON lacked paths.
    raw_path = extract_mcp_file_path(tool_name, func_args)
    if not raw_path:
        return
    try:
        from src.workspace import to_workspace_relative

        rel = to_workspace_relative(raw_path)
    except Exception:
        rel = raw_path
    if rel and rel not in files_changed:
        files_changed.append(rel)


def _execute_tool_call(
    *,
    func_name: str,
    func_args: dict[str, Any],
    tool_routes: dict[str, tuple[str, str]],
    clients: dict[str, McpClient],
    builtin_servers: set[str],
    log_prefix: str,
    logs: list[str],
    on_log: Callable[[str], None] | None,
    step_idx: int,
    files_changed: list[str] | None = None,
    on_tool_step: Callable[[dict[str, Any]], None] | None = None,
    on_diff_summary: Callable[[dict[str, Any]], None] | None = None,
    step_id: str | None = None,
) -> str:
    from src.tool_steps import make_tool_step

    def _emit_inline_diffs(tool_name: str, args: dict[str, Any], result: str) -> list[dict[str, Any]]:
        """Build Cursor-style per-edit cards; attach to tool steps (not separate Chat bubbles)."""
        from src.builtin_tools import build_inline_edit_diff_cards

        return build_inline_edit_diff_cards(
            tool_name=tool_name, func_args=args, result_str=result
        )

    def _finish_step(
        *,
        status: str,
        result: str = "",
        tool_name: str = "",
    ) -> None:
        if not on_tool_step:
            return
        step = make_tool_step(
            tool_alias=func_name,
            func_args=func_args,
            status=status,  # type: ignore[arg-type]
            step_idx=step_idx,
            step_id=active_id,
        )
        if status == "completed" and tool_name and not result.startswith("Error executing tool"):
            cards = _emit_inline_diffs(tool_name, func_args, result)
            if cards and cards[0].get("files"):
                step["fileDiff"] = dict(cards[0]["files"][0])
                step["title"] = f"Edit {cards[0].get('title') or tool_name}"
        on_tool_step(step)

    route = tool_routes.get(func_name)
    active_id = step_id or f"tool_{step_idx}"
    if on_tool_step:
        on_tool_step(
            make_tool_step(
                tool_alias=func_name,
                func_args=func_args,
                status="running",
                step_idx=step_idx,
                step_id=active_id,
            )
        )
    _emit(
        logs,
        on_log,
        f"[{log_prefix}] Step {step_idx + 1}: {func_name} "
        f"args={json.dumps(func_args, ensure_ascii=False)[:240]}",
    )
    if route is None:
        if on_tool_step:
            on_tool_step(
                make_tool_step(
                    tool_alias=func_name,
                    func_args=func_args,
                    status="failed",
                    step_idx=step_idx,
                    step_id=active_id,
                )
            )
        return f"Unknown tool alias: {func_name}"
    server_id, tool_name = route
    workaround = move_file_delete_workaround_message(tool_name, func_args)
    if workaround:
        result_str = f"Error executing tool: {workaround}"
        _emit(logs, on_log, f"[{log_prefix}] Blocked move_file delete workaround")
        if on_tool_step:
            on_tool_step(
                make_tool_step(
                    tool_alias=func_name,
                    func_args=func_args,
                    status="failed",
                    step_idx=step_idx,
                    step_id=active_id,
                )
            )
        return result_str
    if server_id in builtin_servers:
        from src.builtin_tools import execute_builtin_tool

        try:
            result_str = execute_builtin_tool(tool_name, func_args)
            _emit(logs, on_log, f"[{log_prefix}] Builtin tool response length: {len(result_str)} chars")
            if files_changed is not None:
                _record_file_change(
                    files_changed,
                    tool_name=tool_name,
                    func_args=func_args,
                    result_str=result_str,
                )
            if result_str.startswith("Error executing tool"):
                _finish_step(status="failed", result=result_str, tool_name=tool_name)
            else:
                _finish_step(status="completed", result=result_str, tool_name=tool_name)
            return result_str
        except Exception as exc:
            _emit(logs, on_log, f"[{log_prefix}] Builtin tool error: {exc}")
            _finish_step(status="failed", result=str(exc), tool_name=tool_name)
            return f"Error executing tool: {exc}"
    client = clients.get(server_id)
    if client is None:
        _finish_step(status="failed", tool_name=tool_name)
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
        if files_changed is not None:
            _record_file_change(
                files_changed,
                tool_name=tool_name,
                func_args=func_args,
                result_str=result_str,
            )
        if result_str.startswith("Error executing tool"):
            _finish_step(status="failed", result=result_str, tool_name=tool_name)
        else:
            _finish_step(status="completed", result=result_str, tool_name=tool_name)
        return result_str
    except Exception as exc:
        _emit(logs, on_log, f"[{log_prefix}] Tool error: {exc}")
        _finish_step(status="failed", result=str(exc), tool_name=tool_name)
        return f"Error executing tool: {exc}"


def _tools_unsupported_error(exc: BaseException) -> bool:
    return "does not support tools" in str(exc).lower()


def _router_chat(
    router: Any,
    chat_messages: list[dict[str, Any]],
    *,
    openai_tools: list[dict[str, Any]],
    use_tools: bool,
    model_id: str | None,
    logs: list[str],
    log_prefix: str,
    on_log: Callable[[str], None] | None,
) -> tuple[Any, bool]:
    """Call router.chat; fall back to text-only when the model rejects tools."""
    tools_arg = openai_tools if use_tools else None
    try:
        return router.chat(chat_messages, tools=tools_arg, model_id=model_id), use_tools
    except RuntimeError as exc:
        if use_tools and _tools_unsupported_error(exc):
            _emit(
                logs,
                on_log,
                f"[{log_prefix}] Model does not support tool calling — retrying text-only",
            )
            return router.chat(chat_messages, tools=None, model_id=model_id), False
        raise


def run_mcp_react_loop(
    *,
    messages: list[dict[str, Any]],
    servers: list[dict[str, Any]],
    log_prefix: str = "MCP",
    max_steps: int = 24,
    on_log: Callable[[str], None] | None = None,
    on_tool_step: Callable[[dict[str, Any]], None] | None = None,
    on_todos: Callable[[list[dict[str, Any]]], None] | None = None,
    existing_todos: list[dict[str, Any]] | None = None,
    on_verification: Callable[[dict[str, Any]], None] | None = None,
    on_diff_summary: Callable[[dict[str, Any]], None] | None = None,
    pause_on_risky: bool = False,
    permission_mode: str = "ask",
    approved_tool: dict[str, Any] | None = None,
    approved_keys: set[str] | None = None,
    model_id: str | None = None,
) -> McpRunOutcome:
    """Run tool-augmented chat against one or more MCP servers."""
    if not servers:
        raise ValueError("At least one MCP server is required")

    from src.adapters.ollama_adapter import model_supports_tool_calling
    from src.builtin_tools import (
        is_submit_diff_summary_tool,
        is_submit_verification_tool,
        is_todo_write_tool,
        is_virtual_server,
        list_builtin_tools,
        normalize_diff_summary,
        normalize_todo_items,
        normalize_verification_report,
    )
    from src.models_config import get_router

    router = get_router()
    spec, _resolved_id = router.resolve_for_model(model_id)
    logs: list[str] = []
    latest_todos: list[dict[str, Any]] | None = None
    todo_baseline = list(existing_todos or [])
    latest_verification: dict[str, Any] | None = None
    latest_diff_summary: dict[str, Any] | None = None

    if approved_tool and not model_supports_tool_calling(spec):
        raise RuntimeError(
            f"Model {spec.name!r} does not support tool calling; cannot resume an MCP tool step."
        )

    if not model_supports_tool_calling(spec) and not approved_tool:
        engine_label = f"{spec.name} · no tools"
        _emit(
            logs,
            on_log,
            f"[{log_prefix}] Model does not support tool calling — chat without MCP tools",
        )
        from src.llm.router import LLMProviderRouter

        output = LLMProviderRouter.extract_content(
            router.chat(list(messages), tools=None, model_id=model_id)
        )
        _emit(logs, on_log, f"[{log_prefix}] Completed via {spec.name}")
        return McpRunOutcome(
            output=output,
            logs=logs,
            engine_label=engine_label,
            approval_required=None,
            files_changed=None,
        )

    from src.run_control import (
        fuse_message,
        is_tool_failure_result,
        max_consecutive_failures,
    )

    clients: dict[str, McpClient] = {}
    builtin_servers: set[str] = set()
    tool_routes: dict[str, tuple[str, str]] = {}
    openai_tools: list[dict[str, Any]] = []
    consecutive_failures = 0
    fuse_triggered = False
    fuse_limit = max_consecutive_failures()
    _emit(logs, on_log, f"[{log_prefix}] Starting MCP ReAct with {len(servers)} server(s)")

    for server in servers:
        server_id = str(server.get("id", "mcp"))
        name = str(server.get("name", server_id))
        if is_virtual_server(server):
            builtin_servers.add(server_id)
            _emit(logs, on_log, f"[{log_prefix}] Registered builtin server: {name}")
            tools = list_builtin_tools()
        else:
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
            tools = client.list_tools()

        for tool in tools:
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
    engine_label = f"{spec.name} · MCP ({len(openai_tools)} tools)"
    output = ""
    files_changed: list[str] = []
    collected_steps: list[dict[str, Any]] = []
    session_approved = set(approved_keys or ())
    use_tools = bool(openai_tools)

    def record_tool_step(step: dict[str, Any]) -> None:
        from src.tool_steps import upsert_tool_step

        collected_steps[:] = upsert_tool_step(collected_steps, step)
        if on_tool_step:
            on_tool_step(step)

    def capture_todos_if_needed(func_name: str, func_args: dict[str, Any], result_str: str) -> None:
        nonlocal latest_todos, todo_baseline
        route = tool_routes.get(func_name)
        raw_name = route[1] if route else func_name
        if not (is_todo_write_tool(raw_name) or is_todo_write_tool(func_name)):
            return
        if result_str.startswith("Error executing tool"):
            return
        latest_todos = normalize_todo_items(
            func_args,
            existing=todo_baseline,
            merge=bool(func_args.get("merge")),
        )
        todo_baseline = list(latest_todos)
        if on_todos:
            on_todos(list(latest_todos))

    def enrich_verification_args(func_name: str, func_args: dict[str, Any]) -> dict[str, Any]:
        route = tool_routes.get(func_name)
        raw_name = route[1] if route else func_name
        if not (
            is_submit_verification_tool(raw_name) or is_submit_verification_tool(func_name)
        ):
            return func_args
        report = normalize_verification_report(
            func_args,
            existing_todos=latest_todos if latest_todos is not None else todo_baseline,
        )
        return {
            "title": report["title"],
            "conclusion": report["conclusion"],
            "steps": report["steps"],
            "summary": report.get("summary") or "",
            "next_actions": list(report.get("nextActions") or []),
            "changed_files": list(report.get("changedFiles") or []),
        }

    def capture_verification_if_needed(
        func_name: str, func_args: dict[str, Any], result_str: str
    ) -> None:
        nonlocal latest_verification
        route = tool_routes.get(func_name)
        raw_name = route[1] if route else func_name
        if not (
            is_submit_verification_tool(raw_name) or is_submit_verification_tool(func_name)
        ):
            return
        if result_str.startswith("Error executing tool"):
            return
        latest_verification = normalize_verification_report(
            func_args,
            existing_todos=latest_todos if latest_todos is not None else todo_baseline,
        )
        if on_verification:
            on_verification(dict(latest_verification))

    def capture_diff_summary_if_needed(
        func_name: str, func_args: dict[str, Any], result_str: str
    ) -> None:
        nonlocal latest_diff_summary
        route = tool_routes.get(func_name)
        raw_name = route[1] if route else func_name
        if not (
            is_submit_diff_summary_tool(raw_name) or is_submit_diff_summary_tool(func_name)
        ):
            return
        if result_str.startswith("Error executing tool"):
            return
        latest_diff_summary = normalize_diff_summary(func_args, enrich=True)
        if on_diff_summary:
            on_diff_summary(dict(latest_diff_summary))

    def note_tool_result(result_str: str) -> bool:
        """Track consecutive failures; return True when D9 loop fuse should trip."""
        nonlocal consecutive_failures, fuse_triggered
        if is_tool_failure_result(result_str):
            consecutive_failures += 1
        else:
            consecutive_failures = 0
        if consecutive_failures >= fuse_limit:
            fuse_triggered = True
            return True
        return False

    def _outcome(
        *,
        output: str,
        approval_required: dict[str, Any] | None = None,
    ) -> McpRunOutcome:
        return McpRunOutcome(
            output=output,
            logs=logs,
            engine_label=engine_label,
            approval_required=approval_required,
            files_changed=files_changed or None,
            tool_steps=list(collected_steps) or None,
            todos=latest_todos,
            verification_report=latest_verification,
            diff_summary=latest_diff_summary,
            fuse_triggered=fuse_triggered,
            steps_used=len(collected_steps),
            consecutive_failures=consecutive_failures,
        )

    try:
        chat_messages = list(messages)
        start_step = 0
        output = ""

        if approved_tool:
            tc_id = str(approved_tool["tool_call_id"])
            func_name = str(approved_tool["func_name"])
            func_args = approved_tool.get("func_args") or {}
            if not isinstance(func_args, dict):
                func_args = {}
            start_step = int(approved_tool.get("step_idx", 0))
            func_args = enrich_verification_args(func_name, func_args)
            result_str = _execute_tool_call(
                func_name=func_name,
                func_args=func_args,
                tool_routes=tool_routes,
                clients=clients,
                builtin_servers=builtin_servers,
                log_prefix=log_prefix,
                logs=logs,
                on_log=on_log,
                step_idx=start_step,
                files_changed=files_changed,
                on_tool_step=record_tool_step,
                on_diff_summary=on_diff_summary,
                step_id=str(approved_tool.get("step_id") or f"tool_{start_step}"),
            )
            capture_todos_if_needed(func_name, func_args, result_str)
            capture_verification_if_needed(func_name, func_args, result_str)
            capture_diff_summary_if_needed(func_name, func_args, result_str)
            chat_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result_str,
                }
            )
            if note_tool_result(result_str):
                output = fuse_message(
                    failures=consecutive_failures, max_failures=fuse_limit
                )
                _emit(
                    logs,
                    on_log,
                    f"[{log_prefix}] LOOP FUSE: {consecutive_failures} consecutive tool failures",
                )
                return _outcome(output=output)
            start_step += 1

        for step_idx in range(start_step, max_steps):
            response, use_tools = _router_chat(
                router,
                chat_messages,
                openai_tools=openai_tools,
                use_tools=use_tools,
                model_id=model_id,
                logs=logs,
                log_prefix=log_prefix,
                on_log=on_log,
            )
            if not use_tools and "no tools" not in engine_label:
                engine_label = f"{spec.name} · no tools"
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

                    route = tool_routes.get(func_name)
                    raw_tool_name = route[1] if route else func_name
                    from src.builtin_tools import is_ask_user_question_tool, is_propose_plan_tool

                    # D2: propose_plan always pauses for in-chat Approve / revise / Cancel (D49).
                    if is_propose_plan_tool(raw_tool_name) or is_propose_plan_tool(func_name):
                        from src.tool_steps import make_tool_step

                        step_id = f"tool_{step_idx}"
                        record_tool_step(
                            make_tool_step(
                                tool_alias=func_name,
                                func_args=func_args,
                                status="awaiting",
                                step_idx=step_idx,
                                step_id=step_id,
                            )
                        )
                        _emit(
                            logs,
                            on_log,
                            f"[{log_prefix}] Step {step_idx + 1}: propose_plan "
                            f"args={json.dumps(func_args, ensure_ascii=False)[:240]}",
                        )
                        _emit(
                            logs,
                            on_log,
                            f"[{log_prefix}] Plan approval required (D2/D49)",
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
                                "step_id": step_id,
                                "kind": "plan",
                            },
                            files_changed=files_changed or None,
                            tool_steps=list(collected_steps) or None,
                            todos=latest_todos,
                            verification_report=latest_verification,
                            diff_summary=latest_diff_summary,
                        )

                    # D4: ask_user_question pauses for in-chat multiple choice (D49).
                    if is_ask_user_question_tool(raw_tool_name) or is_ask_user_question_tool(func_name):
                        from src.tool_steps import make_tool_step

                        step_id = f"tool_{step_idx}"
                        record_tool_step(
                            make_tool_step(
                                tool_alias=func_name,
                                func_args=func_args,
                                status="awaiting",
                                step_idx=step_idx,
                                step_id=step_id,
                            )
                        )
                        _emit(
                            logs,
                            on_log,
                            f"[{log_prefix}] Step {step_idx + 1}: ask_user_question "
                            f"args={json.dumps(func_args, ensure_ascii=False)[:240]}",
                        )
                        _emit(
                            logs,
                            on_log,
                            f"[{log_prefix}] User question required (D4/D49)",
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
                                "step_id": step_id,
                                "kind": "question",
                            },
                            files_changed=files_changed or None,
                            tool_steps=list(collected_steps) or None,
                            todos=latest_todos,
                            verification_report=latest_verification,
                            diff_summary=latest_diff_summary,
                        )

                    if pause_on_risky and is_risky_mcp_tool(raw_tool_name):
                        # Plan mode: hard-block ALL write/exec tools immediately
                        if permission_mode == "plan":
                            tool_key = raw_tool_name.lower().replace("-", "_")
                            is_write_exec = any(
                                token in tool_key for token in _PLAN_MODE_BLOCKED_TOKENS
                            )
                            if is_write_exec:
                                _emit(
                                    logs,
                                    on_log,
                                    f"[{log_prefix}] Plan mode: blocked write/exec tool: {func_name}",
                                )
                                chat_messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": tc_id,
                                        "content": (
                                            "[Plan Mode] This operation is blocked. "
                                            "You are in read-only planning mode. "
                                            "Describe what you WOULD do without executing it."
                                        ),
                                    }
                                )
                                continue

                        # auto_edit mode: auto-approve pure file-edit tools
                        if permission_mode == "auto_edit":
                            tool_key = raw_tool_name.lower().replace("-", "_")
                            if any(approved in tool_key for approved in _AUTO_EDIT_APPROVED_TOOLS):
                                _emit(
                                    logs,
                                    on_log,
                                    f"[{log_prefix}] Auto-edit mode: auto-approved file tool: {func_name}",
                                )
                                # fall through to execute normally
                            else:
                                # shell / delete / network → still pause for approval
                                approval_key = mcp_approval_key(func_name, func_args)
                                if approval_key not in (approved_keys or set()):
                                    from src.tool_steps import make_tool_step

                                    step_id = f"tool_{step_idx}"
                                    record_tool_step(
                                        make_tool_step(
                                            tool_alias=func_name,
                                            func_args=func_args,
                                            status="awaiting",
                                            step_idx=step_idx,
                                            step_id=step_id,
                                        )
                                    )
                                    _emit(
                                        logs,
                                        on_log,
                                        f"[{log_prefix}] Step {step_idx + 1}: {func_name} "
                                        f"args={json.dumps(func_args, ensure_ascii=False)[:240]}",
                                    )
                                    _emit(
                                        logs,
                                        on_log,
                                        f"[{log_prefix}] Auto-edit: approval required for shell/delete: {func_name}",
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
                                            "step_id": step_id,
                                        },
                                        files_changed=files_changed or None,
                                        tool_steps=list(collected_steps) or None,
                                        todos=latest_todos,
                                        verification_report=latest_verification,
                                        diff_summary=latest_diff_summary,
                                    )

                        # full mode: skip approval gates entirely
                        elif permission_mode != "full":
                            # ask mode (default): pause on any risky tool
                            approval_key = mcp_approval_key(func_name, func_args)
                            if approval_key in (approved_keys or set()):
                                _emit(
                                    logs,
                                    on_log,
                                    f"[{log_prefix}] Auto-approved duplicate risky tool: {func_name}",
                                )
                            else:
                                # Emit Step before pause so Chat D46 timeline shows the pending tool
                                from src.tool_steps import make_tool_step

                                step_id = f"tool_{step_idx}"
                                record_tool_step(
                                    make_tool_step(
                                        tool_alias=func_name,
                                        func_args=func_args,
                                        status="awaiting",
                                        step_idx=step_idx,
                                        step_id=step_id,
                                    )
                                )
                                _emit(
                                    logs,
                                    on_log,
                                    f"[{log_prefix}] Step {step_idx + 1}: {func_name} "
                                    f"args={json.dumps(func_args, ensure_ascii=False)[:240]}",
                                )
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
                                        "step_id": step_id,
                                    },
                                    files_changed=files_changed or None,
                                    tool_steps=list(collected_steps) or None,
                                    todos=latest_todos,
                                    verification_report=latest_verification,
                                    diff_summary=latest_diff_summary,
                                )

                    func_args = enrich_verification_args(func_name, func_args)
                    result_str = _execute_tool_call(
                        func_name=func_name,
                        func_args=func_args,
                        tool_routes=tool_routes,
                        clients=clients,
                        builtin_servers=builtin_servers,
                        log_prefix=log_prefix,
                        logs=logs,
                        on_log=on_log,
                        step_idx=step_idx,
                        files_changed=files_changed,
                        on_tool_step=record_tool_step,
                        on_diff_summary=on_diff_summary,
                        step_id=f"tool_{step_idx}",
                    )
                    capture_todos_if_needed(func_name, func_args, result_str)
                    capture_verification_if_needed(func_name, func_args, result_str)
                    capture_diff_summary_if_needed(func_name, func_args, result_str)
                    chat_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": result_str,
                        }
                    )
                    if note_tool_result(result_str):
                        output = fuse_message(
                            failures=consecutive_failures, max_failures=fuse_limit
                        )
                        _emit(
                            logs,
                            on_log,
                            f"[{log_prefix}] LOOP FUSE: {consecutive_failures} consecutive tool failures",
                        )
                        break
                if fuse_triggered:
                    break
            else:
                from src.llm.router import LLMProviderRouter

                output = LLMProviderRouter.extract_content(response)
                _emit(logs, on_log, f"[{log_prefix}] Completed via {spec.name}")
                break
        else:
            output = (
                f"Agent task hit maximum tool call iteration limit ({max_steps}) "
                f"in {spec.name}."
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

    return _outcome(output=output)
