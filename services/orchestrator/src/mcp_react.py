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

# Tools that are ALWAYS hard-blocked in read-only modes (ask / plan; explore = legacy ask)
_READ_ONLY_PERMISSION_MODES = frozenset({"ask", "plan", "explore"})

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
    goal: dict[str, Any] | None = None
    verification_report: dict[str, Any] | None = None
    diff_summary: dict[str, Any] | None = None
    # D9: loop fuse + chat-visible step accounting
    fuse_triggered: bool = False
    steps_used: int = 0
    consecutive_failures: int = 0
    # D10/D48: nested subtask cards from delegate_subtask
    subtasks: list[dict[str, Any]] | None = None


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
    shell_before: dict[str, tuple[int, int]] | None = None,
) -> None:
    if result_str.startswith("Error executing tool"):
        return
    short = (tool_name or "").split("__")[-1].lower().replace("-", "_")
    # Shell heredocs / mv / rm bypass apply_patch — diff mtimes so Changes still fills.
    if short == "run_terminal_cmd" and shell_before is not None:
        try:
            from src.workspace import diff_workspace_snapshots, snapshot_workspace_mtimes

            after = snapshot_workspace_mtimes()
            for rel in diff_workspace_snapshots(shell_before, after):
                if rel and rel not in files_changed:
                    files_changed.append(rel)
        except Exception:
            pass
        return
    if tool_name in {"generate_image", "generate_video"}:
        try:
            payload = json.loads(result_str)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            rel = str(payload.get("local_media_path") or "").strip()
            if rel and rel not in files_changed:
                files_changed.append(rel)
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
    from src.tool_steps import append_execute_output_detail, make_tool_step

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
            else:
                step = append_execute_output_detail(step, tool_name, result)
        elif status == "failed" and result:
            step = append_execute_output_detail(step, tool_name, result)
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

        pretool = __import__(
            "src.tool_hooks", fromlist=["evaluate_pretool", "format_hook_denial_message"]
        ).evaluate_pretool(tool_name, func_args)
        if not pretool.allowed:
            from src.tool_hooks import format_hook_denial_message

            result_str = f"Error executing tool: {format_hook_denial_message(pretool, tool_name)}"
            _emit(logs, on_log, f"[{log_prefix}] {result_str}")
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
        shell_before: dict[str, tuple[int, int]] | None = None
        if (
            files_changed is not None
            and (tool_name or "").split("__")[-1].lower().replace("-", "_")
            == "run_terminal_cmd"
        ):
            try:
                from src.workspace import snapshot_workspace_mtimes

                shell_before = snapshot_workspace_mtimes()
            except Exception:
                shell_before = None
        try:
            result_str = execute_builtin_tool(tool_name, func_args)
            _emit(logs, on_log, f"[{log_prefix}] Builtin tool response length: {len(result_str)} chars")
            if files_changed is not None:
                _record_file_change(
                    files_changed,
                    tool_name=tool_name,
                    func_args=func_args,
                    result_str=result_str,
                    shell_before=shell_before,
                )
            if result_str.startswith("Error executing tool"):
                _finish_step(status="failed", result=result_str, tool_name=tool_name)
            else:
                post = __import__(
                    "src.tool_hooks", fromlist=["evaluate_posttool", "format_hook_denial_message"]
                ).evaluate_posttool(tool_name, func_args, result_str)
                if not post.allowed:
                    from src.tool_hooks import format_hook_denial_message

                    result_str = f"Error executing tool: {format_hook_denial_message(post, tool_name)}"
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
    tool_choice: str | None = None,
) -> tuple[Any, bool]:
    """Call router.chat; fall back to text-only when the model rejects tools."""
    try:
        from src.context_layers import apply_layered_context

        stats = apply_layered_context(chat_messages)
        if stats.offloaded or stats.noise_dropped or stats.batched:
            _emit(
                logs,
                on_log,
                f"[{log_prefix}] Context layers: offload={stats.offloaded} "
                f"noise={stats.noise_dropped} batch={stats.batched}",
            )
    except Exception:
        pass
    tools_arg = openai_tools if use_tools else None
    try:
        kwargs: dict[str, Any] = {"tools": tools_arg, "model_id": model_id}
        if tools_arg and tool_choice:
            kwargs["tool_choice"] = tool_choice
        return router.chat(chat_messages, **kwargs), use_tools
    except RuntimeError as exc:
        if use_tools and _tools_unsupported_error(exc):
            _emit(
                logs,
                on_log,
                f"[{log_prefix}] Model does not support tool calling — retrying text-only",
            )
            return router.chat(chat_messages, tools=None, model_id=model_id), False
        raise


def _accumulate_model_reasoning(
    response: Any,
    chunks: list[str],
    on_reasoning: Callable[[str], None] | None,
) -> None:
    from src.llm.router import LLMProviderRouter

    chunk = LLMProviderRouter.extract_reasoning(response)
    if not chunk:
        return
    chunks.append(chunk)
    if on_reasoning:
        on_reasoning("\n\n".join(chunks))


def run_mcp_react_loop(
    *,
    messages: list[dict[str, Any]],
    servers: list[dict[str, Any]],
    log_prefix: str = "MCP",
    max_steps: int = 24,
    on_log: Callable[[str], None] | None = None,
    on_tool_step: Callable[[dict[str, Any]], None] | None = None,
    on_reasoning: Callable[[str], None] | None = None,
    on_todos: Callable[[list[dict[str, Any]]], None] | None = None,
    existing_todos: list[dict[str, Any]] | None = None,
    on_goal: Callable[[dict[str, Any]], None] | None = None,
    existing_goal: dict[str, Any] | None = None,
    on_verification: Callable[[dict[str, Any]], None] | None = None,
    on_diff_summary: Callable[[dict[str, Any]], None] | None = None,
    on_subtask: Callable[[dict[str, Any]], None] | None = None,
    pause_on_risky: bool = False,
    permission_mode: str = "auto_edit",
    approved_tool: dict[str, Any] | None = None,
    approved_keys: set[str] | None = None,
    model_id: str | None = None,
    exclude_builtin_tools: frozenset[str] | None = None,
) -> McpRunOutcome:
    """Run tool-augmented chat against one or more MCP servers."""
    if not servers:
        raise ValueError("At least one MCP server is required")

    from src.adapters.ollama_adapter import model_supports_tool_calling
    from src.builtin_tools import (
        is_goal_write_tool,
        is_submit_diff_summary_tool,
        is_submit_verification_tool,
        is_todo_write_tool,
        is_virtual_server,
        list_builtin_tools,
        normalize_diff_summary,
        normalize_goal_args,
        normalize_todo_items,
        normalize_verification_report,
    )
    from src.models_config import get_router

    router = get_router()
    spec, _resolved_id = router.resolve_for_model(model_id)
    logs: list[str] = []
    latest_todos: list[dict[str, Any]] | None = None
    todo_baseline = list(existing_todos or [])
    latest_goal: dict[str, Any] | None = dict(existing_goal) if isinstance(existing_goal, dict) else None
    latest_verification: dict[str, Any] | None = None
    latest_diff_summary: dict[str, Any] | None = None
    latest_subtasks: list[dict[str, Any]] = []

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

        response = router.chat(list(messages), tools=None, model_id=model_id)
        _accumulate_model_reasoning(response, [], on_reasoning)
        output = LLMProviderRouter.extract_content(response)
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
        next_consecutive_failures,
        short_tool_name as fuse_short_tool_name,
    )

    clients: dict[str, McpClient] = {}
    builtin_servers: set[str] = set()
    tool_routes: dict[str, tuple[str, str]] = {}
    openai_tools: list[dict[str, Any]] = []
    builtin_openai_tools: list[dict[str, Any]] = []
    external_catalog: dict[str, dict[str, Any]] = {}
    consecutive_failures = 0
    fuse_triggered = False
    fuse_limit = max_consecutive_failures()
    reasoning_chunks: list[str] = []
    tool_skip_nudged = False
    pending_tool_choice: str | None = None
    network_calls = 0
    network_stop_nudged = False
    html_wrapup_nudged = False
    same_tool_failures: dict[str, int] = {}
    same_tool_soft_nudged: set[str] = set()
    _emit(logs, on_log, f"[{log_prefix}] Starting MCP ReAct with {len(servers)} server(s)")

    for server in servers:
        server_id = str(server.get("id", "mcp"))
        name = str(server.get("name", server_id))
        if is_virtual_server(server):
            builtin_servers.add(server_id)
            _emit(logs, on_log, f"[{log_prefix}] Registered builtin server: {name}")
            tools = list_builtin_tools()
            if exclude_builtin_tools:
                tools = [
                    tool
                    for tool in tools
                    if str(tool.get("name", "")).strip() not in exclude_builtin_tools
                ]
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
            openai_def = {
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
            if server_id in builtin_servers:
                builtin_openai_tools.append(openai_def)
            else:
                external_catalog[alias] = {
                    "openai": openai_def,
                    "tool_name": tool_name,
                    "description": str(tool.get("description", "") or ""),
                    "server_id": server_id,
                }

    from src.mcp_tool_discovery import (
        DISCOVERY_SERVER_ID,
        DISCOVERY_THRESHOLD,
        SEARCH_ALIAS,
        SEARCH_TOOL_NAME,
        build_external_openai_tools,
        execute_search_mcp_tools,
        initial_enabled_aliases,
    )

    discovery_mode = len(external_catalog) > DISCOVERY_THRESHOLD
    enabled_external = (
        initial_enabled_aliases(external_catalog)
        if discovery_mode
        else set(external_catalog.keys())
    )
    if external_catalog:
        tool_routes[SEARCH_ALIAS] = (DISCOVERY_SERVER_ID, SEARCH_TOOL_NAME)
        openai_tools = list(builtin_openai_tools) + build_external_openai_tools(
            catalog=external_catalog,
            enabled=enabled_external,
            discovery_mode=discovery_mode,
        )
        if discovery_mode:
            _emit(
                logs,
                on_log,
                f"[{log_prefix}] D28 discovery mode: {len(external_catalog)} external tool(s); "
                f"exposing search_mcp_tools + {len(enabled_external)} always-on",
            )
    else:
        openai_tools = list(builtin_openai_tools)

    def _rebuild_openai_tools() -> None:
        nonlocal openai_tools
        openai_tools = list(builtin_openai_tools) + build_external_openai_tools(
            catalog=external_catalog,
            enabled=enabled_external,
            discovery_mode=discovery_mode,
        )

    visible_count = len(openai_tools)
    _emit(logs, on_log, f"[{log_prefix}] Discovered {visible_count} visible tool(s)")
    engine_label = f"{spec.name} · MCP ({visible_count} tools)"
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

    def capture_goal_if_needed(func_name: str, func_args: dict[str, Any], result_str: str) -> None:
        nonlocal latest_goal
        route = tool_routes.get(func_name)
        raw_name = route[1] if route else func_name
        if not (is_goal_write_tool(raw_name) or is_goal_write_tool(func_name)):
            return
        if result_str.startswith("Error executing tool"):
            return
        latest_goal = normalize_goal_args(func_args)
        if on_goal:
            on_goal(dict(latest_goal))

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

    write_recovery_nudged = False

    def note_tool_result(result_str: str, tool_name: str = "") -> bool:
        """Track consecutive + same-tool failures; return True when D9 loop fuse trips."""
        nonlocal consecutive_failures, fuse_triggered
        from src.tool_use_policy import (
            same_tool_soft_budget,
            same_tool_stop_nudge,
        )

        short = fuse_short_tool_name(tool_name)
        failed = is_tool_failure_result(result_str)
        consecutive_failures = next_consecutive_failures(
            consecutive_failures,
            result=result_str,
            tool_name=tool_name,
        )
        if failed and short:
            same_tool_failures[short] = same_tool_failures.get(short, 0) + 1
            used = same_tool_failures[short]
            soft = same_tool_soft_budget()
            if used >= soft and short not in same_tool_soft_nudged:
                same_tool_soft_nudged.add(short)
                chat_messages.append(
                    {
                        "role": "user",
                        "content": same_tool_stop_nudge(short, used=used, soft=soft),
                    }
                )
                _emit(
                    logs,
                    on_log,
                    f"[{log_prefix}] Same-tool soft-cap ({short} {used}/{soft}): stop-retry nudge",
                )
        elif not failed and short:
            same_tool_failures[short] = 0
        if consecutive_failures >= fuse_limit:
            fuse_triggered = True
            return True
        return False

    def maybe_nudge_html_wrapup() -> None:
        """After HTML write: wrap up if page intent, else correct wrong substitute."""
        nonlocal html_wrapup_nudged
        if html_wrapup_nudged:
            return
        from src.deliverable_intent import (
            forbids_html_substitute,
            html_deliverable_wrapup_nudge,
            html_substitute_correction_nudge,
            is_html_deliverable_path,
            wants_browser_preview,
        )
        from src.tool_use_policy import last_user_text

        user_text = last_user_text(chat_messages)
        html_paths = [p for p in files_changed if is_html_deliverable_path(p)]
        if not html_paths:
            return
        html_wrapup_nudged = True
        if wants_browser_preview(user_text):
            content = html_deliverable_wrapup_nudge(paths=html_paths)
            label = "HTML deliverable wrap-up nudge"
        elif forbids_html_substitute(user_text):
            content = html_substitute_correction_nudge(paths=html_paths, user_text=user_text)
            label = "Wrong-deliverable HTML correction nudge"
        else:
            return
        chat_messages.append({"role": "user", "content": content})
        _emit(logs, on_log, f"[{log_prefix}] {label} ({html_paths[0]})")

    def maybe_nudge_write_recovery(tool_name: str, result_str: str) -> None:
        """Before the fuse trips, steer Flash models off truncated apply_patch loops."""
        nonlocal write_recovery_nudged
        if write_recovery_nudged or consecutive_failures < 2:
            return
        short = (tool_name or "").split("__")[-1].lower().replace("-", "_")
        if short != "apply_patch" and "end patch" not in (result_str or "").lower():
            return
        write_recovery_nudged = True
        chat_messages.append(
            {
                "role": "user",
                "content": (
                    "[System reminder — write recovery] apply_patch failed twice. "
                    "Do NOT retry the same truncated patch. Create/overwrite the file "
                    "with search_replace (full file contents) or a short complete "
                    "apply_patch that ends with *** End Patch. Then finish remaining todos "
                    "(e.g. generate the HTML page)."
                ),
            }
        )
        _emit(
            logs,
            on_log,
            f"[{log_prefix}] Write-recovery nudge after apply_patch failures",
        )

    def record_subtask(card: dict[str, Any]) -> None:
        from src.subagent_runner import upsert_subtask

        latest_subtasks[:] = upsert_subtask(latest_subtasks, card)
        if on_subtask:
            on_subtask(dict(card))

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
            goal=latest_goal,
            verification_report=latest_verification,
            diff_summary=latest_diff_summary,
            fuse_triggered=fuse_triggered,
            steps_used=len(collected_steps),
            consecutive_failures=consecutive_failures,
            subtasks=list(latest_subtasks) or None,
        )

    from src.artifact_layout import bind_user_turn_text, release_user_turn_text
    from src.media_deliverable import finalize_media_deliverables
    from src.tool_use_policy import (
        last_user_text as _last_user_text_for_artifacts,
        looks_like_plan_approval,
    )

    user_text_for_media = _last_user_text_for_artifacts(list(messages))
    user_turn_token = bind_user_turn_text(user_text_for_media)
    chat_messages: list[dict[str, Any]] = list(messages)
    if looks_like_plan_approval(user_text_for_media) and use_tools:
        chat_messages.append(
            {
                "role": "user",
                "content": (
                    "[System reminder — execute approved plan] The user approved. "
                    "Call `todo_write` (≥3 items, one `in_progress`) NOW, then "
                    "`apply_patch`/`search_replace` to implement. Do not ask for "
                    "confirmation again. Do not claim completion without tool results."
                ),
            }
        )
        _emit(logs, on_log, f"[{log_prefix}] Plan-approval execute reminder injected")

    def finish(out: str) -> McpRunOutcome:
        finalized = finalize_media_deliverables(
            output=out,
            user_text=user_text_for_media,
            chat_messages=chat_messages,
            files_changed=files_changed,
            logs=logs,
            log_prefix=log_prefix,
            on_log=on_log,
        )
        return _outcome(output=finalized)

    try:
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
            capture_goal_if_needed(func_name, func_args, result_str)
            capture_verification_if_needed(func_name, func_args, result_str)
            capture_diff_summary_if_needed(func_name, func_args, result_str)
            chat_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result_str,
                }
            )
            if note_tool_result(result_str, func_name):
                output = fuse_message(
                    failures=consecutive_failures, max_failures=fuse_limit
                )
                _emit(
                    logs,
                    on_log,
                    f"[{log_prefix}] LOOP FUSE: {consecutive_failures} consecutive tool failures",
                )
                return finish(output)
            maybe_nudge_html_wrapup()
            start_step += 1

        for step_idx in range(start_step, max_steps):
            step_tool_choice = pending_tool_choice
            pending_tool_choice = None
            response, use_tools = _router_chat(
                router,
                chat_messages,
                openai_tools=openai_tools,
                use_tools=use_tools,
                model_id=model_id,
                logs=logs,
                log_prefix=log_prefix,
                on_log=on_log,
                tool_choice=step_tool_choice,
            )
            _accumulate_model_reasoning(response, reasoning_chunks, on_reasoning)
            if not use_tools and "no tools" not in engine_label:
                engine_label = f"{spec.name} · no tools"
            if isinstance(response, dict) and response.get("tool_calls"):
                from src.tool_use_policy import (
                    NETWORK_HARD_BUDGET,
                    NETWORK_SOFT_BUDGET,
                    is_network_tool,
                    network_budget_exhausted_result,
                    network_budget_stop_nudge,
                )

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
                    from src.builtin_tools import (
                        is_ask_user_question_tool,
                        is_delegate_subtask_tool,
                        is_propose_plan_tool,
                    )

                    # D28: search_mcp_tools enables matched external tools for later turns.
                    if (
                        route
                        and route[0] == DISCOVERY_SERVER_ID
                        and raw_tool_name == SEARCH_TOOL_NAME
                    ):
                        from src.tool_steps import make_tool_step

                        step_id = f"tool_{step_idx}"
                        record_tool_step(
                            make_tool_step(
                                tool_alias=func_name,
                                func_args=func_args,
                                status="running",
                                step_idx=step_idx,
                                step_id=step_id,
                            )
                        )
                        result_str = execute_search_mcp_tools(
                            func_args,
                            catalog=external_catalog,
                            enabled=enabled_external,
                        )
                        _rebuild_openai_tools()
                        _emit(
                            logs,
                            on_log,
                            f"[{log_prefix}] Step {step_idx + 1}: search_mcp_tools "
                            f"enabled={len(enabled_external)} visible={len(openai_tools)}",
                        )
                        record_tool_step(
                            make_tool_step(
                                tool_alias=func_name,
                                func_args=func_args,
                                status="completed" if not result_str.startswith("Error") else "failed",
                                step_idx=step_idx,
                                step_id=step_id,
                            )
                        )
                        chat_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc_id,
                                "content": result_str,
                            }
                        )
                        continue

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
                            goal=latest_goal,
                            verification_report=latest_verification,
                            diff_summary=latest_diff_summary,
                            subtasks=list(latest_subtasks) or None,
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
                            goal=latest_goal,
                            verification_report=latest_verification,
                            diff_summary=latest_diff_summary,
                            subtasks=list(latest_subtasks) or None,
                        )

                    from src.permission_rules import resolve_tool_gate

                    gate = resolve_tool_gate(
                        tool_name=raw_tool_name,
                        func_args=func_args,
                        permission_mode=permission_mode,
                    )
                    if gate == "deny":
                        deny_msg = (
                            f"[Permission] Denied by rule for `{raw_tool_name}`. "
                            "Adjust Settings permission rules or choose a safer command."
                        )
                        _emit(logs, on_log, f"[{log_prefix}] Permission deny: {func_name}")
                        chat_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc_id,
                                "content": deny_msg,
                            }
                        )
                        if note_tool_result(deny_msg, raw_tool_name or func_name):
                            output = fuse_message(
                                failures=consecutive_failures, max_failures=fuse_limit
                            )
                            break
                        continue

                    force_ask = gate == "ask"
                    force_allow = gate == "allow"

                    if pause_on_risky and (
                        force_ask or (is_risky_mcp_tool(raw_tool_name) and not force_allow)
                    ):
                        # Plan / Explore: hard-block ALL write/exec tools immediately
                        if permission_mode in _READ_ONLY_PERMISSION_MODES and not force_ask:
                            tool_key = raw_tool_name.lower().replace("-", "_")
                            is_write_exec = any(
                                token in tool_key for token in _PLAN_MODE_BLOCKED_TOKENS
                            )
                            if is_write_exec:
                                if permission_mode == "plan":
                                    mode_label = "Plan"
                                else:
                                    # ask (+ legacy explore)
                                    mode_label = "Ask"
                                _emit(
                                    logs,
                                    on_log,
                                    f"[{log_prefix}] {mode_label} mode: blocked write/exec tool: {func_name}",
                                )
                                chat_messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": tc_id,
                                        "content": (
                                            f"[{mode_label} Mode] This operation is blocked. "
                                            f"You are in read-only conversation mode. "
                                            "Describe what you WOULD do without executing it. "
                                            "The user can switch to Agent or Full to allow changes."
                                        ),
                                    }
                                )
                                continue

                        # auto_edit mode: auto-approve pure file-edit tools
                        if permission_mode == "auto_edit" and not force_ask:
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
                                        goal=latest_goal,
                                        verification_report=latest_verification,
                                        diff_summary=latest_diff_summary,
                                        subtasks=list(latest_subtasks) or None,
                                    )

                        # full mode: skip approval gates entirely — unless D13 force_ask
                        elif force_ask or permission_mode != "full":
                            # ask mode (default) or dangerous/rule force-ask: pause
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
                            goal=latest_goal,
                                    verification_report=latest_verification,
                                    diff_summary=latest_diff_summary,
                                    subtasks=list(latest_subtasks) or None,
                                )

                    if is_delegate_subtask_tool(raw_tool_name) or is_delegate_subtask_tool(func_name):
                        import uuid as _uuid

                        from src.subagent_runner import (
                            bind_delegate_context,
                            default_subtask_max_steps,
                            initial_subtask_card,
                            normalize_delegate_args,
                            release_delegate_context,
                        )

                        try:
                            args = normalize_delegate_args(func_args)
                        except ValueError as exc:
                            result_str = f"Error executing tool: {exc}"
                            chat_messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tc_id,
                                    "content": result_str,
                                }
                            )
                            if note_tool_result(result_str, raw_tool_name or func_name):
                                output = fuse_message(
                                    failures=consecutive_failures, max_failures=fuse_limit
                                )
                                break
                            continue

                        sub_id = f"sub_{_uuid.uuid4().hex[:8]}"
                        running = initial_subtask_card(args, subtask_id=sub_id)
                        record_subtask(running)
                        ctx_token = bind_delegate_context(
                            {
                                "servers": servers,
                                "model_id": model_id,
                                "on_log": on_log,
                                "on_subtask_update": record_subtask,
                                "max_steps": default_subtask_max_steps(args["type"]),
                                "permission_mode": permission_mode,
                                "pause_on_risky": pause_on_risky,
                                "subtask_id": sub_id,
                            }
                        )
                        try:
                            func_args_exec = enrich_verification_args(func_name, func_args)
                            result_str = _execute_tool_call(
                                func_name=func_name,
                                func_args=func_args_exec,
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
                        finally:
                            release_delegate_context(ctx_token)
                        chat_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc_id,
                                "content": result_str,
                            }
                        )
                        if note_tool_result(result_str, raw_tool_name or func_name):
                            output = fuse_message(
                                failures=consecutive_failures, max_failures=fuse_limit
                            )
                            _emit(
                                logs,
                                on_log,
                                f"[{log_prefix}] LOOP FUSE: {consecutive_failures} consecutive tool failures",
                            )
                            break
                        continue

                    from src.tool_use_policy import (
                        same_tool_exhausted_result,
                        same_tool_hard_budget,
                    )

                    same_short = fuse_short_tool_name(raw_tool_name) or fuse_short_tool_name(
                        func_name
                    )
                    same_hard = same_tool_hard_budget()
                    if same_short and same_tool_failures.get(same_short, 0) >= same_hard:
                        from src.tool_steps import make_tool_step

                        used = same_tool_failures[same_short]
                        result_str = same_tool_exhausted_result(
                            same_short, used=used, hard=same_hard
                        )
                        step_id = f"tool_{step_idx}"
                        record_tool_step(
                            make_tool_step(
                                tool_alias=func_name,
                                func_args=func_args,
                                status="failed",
                                step_idx=step_idx,
                                step_id=step_id,
                            )
                        )
                        _emit(
                            logs,
                            on_log,
                            f"[{log_prefix}] Same-tool hard-cap "
                            f"({same_short} {used}/{same_hard}): blocked {func_name}",
                        )
                        chat_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc_id,
                                "content": result_str,
                            }
                        )
                        continue

                    if is_network_tool(raw_tool_name) or is_network_tool(func_name):
                        if network_calls >= NETWORK_HARD_BUDGET:
                            from src.tool_steps import make_tool_step

                            result_str = network_budget_exhausted_result(used=network_calls)
                            step_id = f"tool_{step_idx}"
                            record_tool_step(
                                make_tool_step(
                                    tool_alias=func_name,
                                    func_args=func_args,
                                    status="failed",
                                    step_idx=step_idx,
                                    step_id=step_id,
                                )
                            )
                            _emit(
                                logs,
                                on_log,
                                f"[{log_prefix}] Network budget hard-cap "
                                f"({network_calls}/{NETWORK_HARD_BUDGET}): blocked {func_name}",
                            )
                            chat_messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tc_id,
                                    "content": result_str,
                                }
                            )
                            continue

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
                    capture_goal_if_needed(func_name, func_args, result_str)
                    capture_verification_if_needed(func_name, func_args, result_str)
                    capture_diff_summary_if_needed(func_name, func_args, result_str)
                    if is_network_tool(raw_tool_name) or is_network_tool(func_name):
                        network_calls += 1
                    chat_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": result_str,
                        }
                    )
                    if note_tool_result(result_str, raw_tool_name or func_name):
                        output = fuse_message(
                            failures=consecutive_failures, max_failures=fuse_limit
                        )
                        _emit(
                            logs,
                            on_log,
                            f"[{log_prefix}] LOOP FUSE: {consecutive_failures} consecutive tool failures",
                        )
                        break
                    maybe_nudge_write_recovery(func_name, result_str)
                    maybe_nudge_html_wrapup()
                if fuse_triggered:
                    break
                if (
                    network_calls >= NETWORK_SOFT_BUDGET
                    and not network_stop_nudged
                ):
                    network_stop_nudged = True
                    chat_messages.append(
                        {
                            "role": "user",
                            "content": network_budget_stop_nudge(used=network_calls),
                        }
                    )
                    _emit(
                        logs,
                        on_log,
                        f"[{log_prefix}] Network budget soft-cap "
                        f"({network_calls}/{NETWORK_SOFT_BUDGET}): stop-search nudge",
                    )
            else:
                from src.llm.router import LLMProviderRouter
                from src.tool_use_policy import last_user_text, should_nudge_for_skipped_tools

                output = LLMProviderRouter.extract_content(response)
                short_names = {route[1] for route in tool_routes.values()}
                # Only nudge when the model skipped tools entirely — never after a
                # successful tool round (would loop: answer → nudge → required).
                tools_already_used = any(
                    message.get("role") == "tool" for message in chat_messages
                )
                nudge = (
                    should_nudge_for_skipped_tools(
                        user_text=last_user_text(chat_messages),
                        assistant_text=output,
                        available_tools=short_names,
                        already_nudged=tool_skip_nudged,
                    )
                    if use_tools and openai_tools and not tools_already_used
                    else None
                )
                if nudge is not None:
                    tool_skip_nudged = True
                    pending_tool_choice = "required"
                    chat_messages.append({"role": "assistant", "content": output or ""})
                    chat_messages.append({"role": "user", "content": nudge.nudge})
                    _emit(
                        logs,
                        on_log,
                        f"[{log_prefix}] Tool-skip nudge ({nudge.kind}): no tool_calls — "
                        "retrying with tool_choice=required",
                    )
                    continue
                _emit(logs, on_log, f"[{log_prefix}] Completed via {spec.name}")
                break
        else:
            limit_msg = (
                f"Agent task hit maximum tool call iteration limit ({max_steps}) "
                f"in {spec.name}."
            )
            output = limit_msg
            _emit(logs, on_log, f"[{log_prefix}] ERROR: max iterations limit reached")
            # One tool-free synthesis turn so the user gets an answer from gathered evidence
            # instead of only seeing the budget error (common on open web questions).
            try:
                from src.llm.router import LLMProviderRouter

                synth_messages = list(chat_messages) + [
                    {
                        "role": "user",
                        "content": (
                            "[System] Tool-call step budget exhausted. "
                            "Answer the user's latest question NOW using only the tool "
                            "results already in this conversation. Do not call tools. "
                            "Be concise; cite URLs you used. If evidence is thin, say what "
                            "you found and what is still unknown."
                        ),
                    }
                ]
                response, _ = _router_chat(
                    router,
                    synth_messages,
                    openai_tools=openai_tools,
                    use_tools=False,
                    model_id=model_id,
                    logs=logs,
                    log_prefix=log_prefix,
                    on_log=on_log,
                )
                _accumulate_model_reasoning(response, reasoning_chunks, on_reasoning)
                synthesized = LLMProviderRouter.extract_content(response)
                if isinstance(synthesized, str) and synthesized.strip():
                    output = synthesized.strip()
                    _emit(
                        logs,
                        on_log,
                        f"[{log_prefix}] Synthesized answer after max iterations",
                    )
                else:
                    output = limit_msg
            except Exception as synth_exc:
                _emit(
                    logs,
                    on_log,
                    f"[{log_prefix}] Max-iter synthesis failed: {synth_exc}",
                )
                output = limit_msg
    finally:
        release_user_turn_text(user_turn_token)
        for server_id, client in clients.items():
            name = str(next(
                (s.get("name", server_id) for s in servers if str(s.get("id")) == server_id),
                server_id,
            ))
            client.close()
            _emit(logs, on_log, f"[{log_prefix}] Stopped MCP server: {name}")

    return finish(output)
