from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import WebSocket

from src.chat_messages import (
    _chat_message,
    _diff_summary_for_seal,
    _history_for_llm,
    _merge_files_changed_with_tool_steps,
    _sealed_subtasks,
    _sealed_tool_steps,
    _token_patch,
    _token_patch_turn,
    _verification_report_for_seal,
)
from src.chat_mcp_gates import (
    _is_plan_pause,
    _is_question_pause,
    _mcp_pause_gate_line,
    _mcp_pause_human_prompt,
    _messages_for_mcp_pause,
    _patch_plan_card_status,
    _patch_question_card_status,
    _supervisor_gate_messages,
)
from src.chat_run_live import (
    _apply_bg_jobs_update,
    _apply_foreground_shell_update,
    _bg_jobs_live_patch,
    _bind_worktree_from_state,
    _commit_run_state,
    _foreground_shell_live_patch,
    _get_or_create_run,
    _merge_patch,
    _reasoning_live_patch,
    _release_worktree_bindings,
    _run_states,
    _setup_run_log_forwarder,
    _subtask_live_patch,
    _tool_step_live_patch,
    _worktree_isolation_live_patch,
)
from src.chat_ws_events import (
    _is_ws_transport_error,
    _notify_run_state,
    _send_file_changed,
    _send_human_required,
    _send_hybrid_execution_event,
    _send_log_event,
    _send_message_event,
    _send_pty_output,
    _send_pty_session_status,
    _send_state_patch,
    _try_ws_notify,
)
from src.preferences_storage import tr
from src.state import ClutchState
from src.terminal_logs import stamp_log_line, tagged, TAG_HUMAN, TAG_WORKFLOW

logger = logging.getLogger(__name__)

def _touch_session(*args, **kwargs):
    from src.chat_runner import _touch_session as _impl
    return _impl(*args, **kwargs)

async def _publish_verification_report(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    report: dict[str, Any],
    *,
    reply_label: str,
) -> ClutchState:
    """Seal a D5/D50 verification card into the Chat timeline immediately."""
    card = dict(report)
    messages = list(state["messages"])
    last = messages[-1] if messages else None
    prev = last.get("verificationReport") if isinstance(last, dict) else None
    if (
        isinstance(prev, dict)
        and prev.get("title") == card.get("title")
        and prev.get("conclusion") == card.get("conclusion")
    ):
        state = _merge_patch(state, {"verification_report": card})
        _commit_run_state(run_id, state)
        return state

    card_msg = _chat_message(reply_label or "Clutch Agent", "", verification_report=card)
    messages = messages + [card_msg]
    state = _merge_patch(
        state,
        {
            "messages": messages,
            "verification_report": card,
        },
    )
    _commit_run_state(run_id, state)
    await _send_message_event(websocket, run_id, card_msg, "")
    await _notify_run_state(
        websocket,
        run_id,
        state,
        {"messages": messages, "verification_report": card},
    )
    return state


async def _publish_diff_summary(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    report: dict[str, Any],
    *,
    reply_label: str,
) -> ClutchState:
    """Seal a D6/D50 diff card into the Chat timeline immediately (per-edit or review)."""
    card = dict(report)
    if not card.get("files"):
        return state
    messages = list(state["messages"])
    last = messages[-1] if messages else None
    prev = last.get("diffSummary") if isinstance(last, dict) else None
    # Inline cards: skip only exact duplicate of the same single-file patch.
    if isinstance(prev, dict) and prev.get("inline") and card.get("inline"):
        prev_files = prev.get("files") or []
        next_files = card.get("files") or []
        if (
            len(prev_files) == 1
            and len(next_files) == 1
            and isinstance(prev_files[0], dict)
            and isinstance(next_files[0], dict)
            and prev_files[0].get("path") == next_files[0].get("path")
            and prev_files[0].get("patch") == next_files[0].get("patch")
        ):
            state = _merge_patch(state, {"diff_summary": card})
            _commit_run_state(run_id, state)
            return state
    elif (
        isinstance(prev, dict)
        and not card.get("inline")
        and prev.get("title") == card.get("title")
    ):
        prev_paths = [str(f.get("path")) for f in (prev.get("files") or []) if isinstance(f, dict)]
        next_paths = [str(f.get("path")) for f in (card.get("files") or []) if isinstance(f, dict)]
        if prev_paths == next_paths:
            state = _merge_patch(state, {"diff_summary": card})
            _commit_run_state(run_id, state)
            return state

    card_msg = _chat_message(reply_label or "Clutch Agent", "", diff_summary=card)
    messages = messages + [card_msg]
    state = _merge_patch(
        state,
        {
            "messages": messages,
            "diff_summary": card,
        },
    )
    _commit_run_state(run_id, state)
    await _send_message_event(websocket, run_id, card_msg, "")
    # Push Changes panel for inline edits as they land.
    paths = [
        str(f.get("path")).strip()
        for f in (card.get("files") or [])
        if isinstance(f, dict) and str(f.get("path") or "").strip()
    ]
    if paths:
        await _notify_workspace_files_changed(websocket, run_id, paths)
    await _notify_run_state(
        websocket,
        run_id,
        state,
        {"messages": messages, "diff_summary": card},
    )
    return state


def _hybrid_execution_entry(
    *,
    raw_output: str | None,
    output_events: list[dict[str, Any]] | None,
    system_prompt: str | None = None,
) -> dict[str, object]:
    events = list(output_events or [])
    if system_prompt and not any(event.get("type") == "system_prompt" for event in events):
        events.insert(
            0,
            {"type": "system_prompt", "visible": False, "content": system_prompt},
        )
    return {
        "rawOutput": raw_output,
        "outputEvents": events,
    }


def _merge_hybrid_executions(
    state: ClutchState,
    *,
    message_id: str,
    raw_output: str | None,
    output_events: list[dict[str, Any]] | None,
    system_prompt: str | None = None,
) -> dict[str, dict[str, object]]:
    merged = dict(state.get("hybrid_executions") or {})
    merged[message_id] = _hybrid_execution_entry(
        raw_output=raw_output,
        output_events=output_events,
        system_prompt=system_prompt,
    )
    return merged


def _uses_configured_llm(agent: dict[str, Any] | None) -> bool:
    from src.agent_type import is_clutch_agent

    if not agent:
        return True
    return is_clutch_agent(agent)


def _compose_agent_system_prompt(
    agent: dict[str, Any],
    *,
    model_name: str,
    model_api: str,
    mcp_servers_bound: bool = True,
    user_turn_text: str | None = None,
    state: dict[str, Any] | None = None,
) -> str:
    from src.agent_prompt import compose_agent_system_prompt
    from src.preferences_storage import load_permission_mode
    from src.task_state import latest_plan_card

    agent_todos = list((state or {}).get("agent_todos") or [])
    plan_card = latest_plan_card(list((state or {}).get("messages") or []))

    return compose_agent_system_prompt(
        agent,
        model_name=model_name,
        model_api=model_api,
        mcp_servers_bound=mcp_servers_bound,
        permission_mode=load_permission_mode(),
        user_turn_text=user_turn_text,
        agent_todos=agent_todos,
        plan_card=plan_card,
    )


def _append_terminal_logs(
    current_logs: list[str],
    route_logs: list[str],
    tail_line: str,
    *,
    streamed: bool,
) -> list[str]:
    stamped_tail = stamp_log_line(tail_line)
    if streamed:
        merged = list(current_logs)
        if not merged or merged[-1] != stamped_tail:
            merged.append(stamped_tail)
        return merged
    return list(current_logs) + [stamp_log_line(line) for line in route_logs] + [stamped_tail]


async def _llm_chat_reply(
    state: ClutchState,
    text: str,
    agent_id: str | None = None,
    *,
    session_model_id: str | None = None,
    cli_session_id: str | None = None,
    emit_log: Callable[[str], Awaitable[None]] | None = None,
    emit_tool_step: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    emit_reasoning: Callable[[str], Awaitable[None]] | None = None,
    emit_todos: Callable[[list[dict[str, Any]]], Awaitable[None]] | None = None,
    emit_goal: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    emit_verification: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    emit_diff_summary: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    emit_subtask: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    tool_steps_sink: list[dict[str, Any]] | None = None,
    subtasks_sink: list[dict[str, Any]] | None = None,
    mcp_approved_tool: dict[str, Any] | None = None,
    mcp_resume: dict[str, Any] | None = None,
    isolate_cli_history: bool = False,
    chat_source: str = "plain_chat",
    system_prompt_suffix: str = "",
) -> tuple[str, str, str, list[str], str | None, dict[str, Any] | None, list[str], str | None, list[dict[str, Any]] | None, bool]:
    from src.agent_storage import BUILTIN_AGENT_ID, get_agent_by_id
    from src.engine_router import route_engine
    from src.models_config import get_router
    from src.workspace import get_workspace

    resolved_id = (agent_id or "").strip() or BUILTIN_AGENT_ID
    agent = get_agent_by_id(resolved_id)
    agent_ref = str(agent.get("id", resolved_id)) if agent else resolved_id
    reply_label = str(agent.get("name", "Clutch Agent")) if agent else (state.get("active_agent") or "Builder")

    router = get_router()
    from src.agent_type import agent_type_from_record, is_clutch_agent, resolve_model_for_agent

    uses_clutch_model = is_clutch_agent(agent)
    model, resolved_model_id = resolve_model_for_agent(
        router,
        agent,
        session_model_id=session_model_id if uses_clutch_model else None,
    )
    if uses_clutch_model:
        runtime_model_name = model.name
        model_api = getattr(model, "api_model", None) or runtime_model_name
    else:
        runtime_model_name = str(agent.get("name", reply_label)) if agent else reply_label
        model_api = agent_type_from_record(agent) if agent else "cli"
    from src.adapters.ollama_adapter import model_supports_vision
    from src.image_router import format_image_reply, generate_image_for_model, is_image_model
    from src.video_router import format_video_reply, generate_video_for_model, is_video_model
    from src.chat_content import extract_image_data_urls

    _plain, attached_images = extract_image_data_urls(text)

    # Try-first: always send attached images multimodally for Clutch chat models.
    # Soft/API vision failures retry with local OCR/palette analysis below.
    # Local CLI agents: deliver workspace file paths first (same idea as Terminal);
    # OCR only after the CLI refuses / cannot read the image.
    cli_path_images = False
    if uses_clutch_model:
        if is_image_model(model) or is_video_model(model):
            vision_enabled = False
        elif attached_images:
            vision_enabled = True
        else:
            vision_enabled = model_supports_vision(model)
    elif agent and agent_type_from_record(agent) == "ollama-cli":
        from src.llm.router import ModelSpec

        tag = str(agent.get("ollamaModel", "")).strip()
        if tag:
            vision_enabled = model_supports_vision(
                ModelSpec(
                    id=tag,
                    name=tag,
                    provider_id="ollama",
                    api_model=tag,
                    base_url="http://localhost:11434/v1",
                )
            )
        else:
            vision_enabled = False
    else:
        vision_enabled = False
        cli_path_images = bool(attached_images)

    if uses_clutch_model and is_video_model(model):
        if attached_images:
            err = (
                "This model only generates videos and cannot read uploaded screenshots. "
                "Switch to a vision chat model (e.g. Qwen 2.5 VL 7B) using the Model menu in the footer."
            )
            return (
                reply_label,
                runtime_model_name,
                err,
                [f"[CHAT] Vision input ignored for video-generation model {runtime_model_name}"],
                None,
                None,
                [],
                None,
                None,
                False,
            )
        spec, api_key = router.resolve_for_model(resolved_model_id)
        loop = asyncio.get_running_loop()
        video_logs: list[str] = []

        def on_video_log(line: str) -> None:
            if emit_log:
                asyncio.run_coroutine_threadsafe(emit_log(line), loop)

        try:
            video_prompt = (_plain or text).strip()
            result = await asyncio.to_thread(
                generate_video_for_model,
                spec,
                video_prompt,
                api_key=router._require_api_key(spec.provider_id, api_key),
                on_log=on_video_log if emit_log else None,
            )
            return reply_label, runtime_model_name, format_video_reply(result), video_logs, None, None, [], None, None, False
        except Exception as exc:
            from src.models_config import format_connection_error

            err = format_connection_error(exc)
            return (
                reply_label,
                runtime_model_name,
                err,
                [f"Error generating video: {err}"],
                None,
                None,
                [],
                None,
                None,
                False,
            )

    if uses_clutch_model and is_image_model(model):
        if attached_images:
            err = (
                "This model only generates images and cannot read uploaded screenshots. "
                "Switch to a vision chat model (e.g. Qwen 2.5 VL 7B) using the Model menu in the footer."
            )
            return (
                reply_label,
                runtime_model_name,
                err,
                [f"[CHAT] Vision input ignored for image-generation model {runtime_model_name}"],
                None,
                None,
                [],
                None,
                None,
                False,
            )
        spec, api_key = router.resolve_for_model(resolved_model_id)
        loop = asyncio.get_running_loop()
        image_logs: list[str] = []

        def on_image_log(line: str) -> None:
            if emit_log:
                asyncio.run_coroutine_threadsafe(emit_log(line), loop)

        try:
            result = await asyncio.to_thread(
                generate_image_for_model,
                spec,
                text,
                api_key=router._require_api_key(spec.provider_id, api_key),
                on_log=on_image_log if emit_log else None,
            )
            return reply_label, runtime_model_name, format_image_reply(result), image_logs, None, None, [], None, None, False
        except Exception as exc:
            err = str(exc)
            return (
                reply_label,
                runtime_model_name,
                err,
                [f"Error generating image: {err}"],
                None,
                None,
                [],
                None,
                None,
                False,
            )

    from src.agent_mcp import resolve_agent_mcp_servers

    mcp_servers_bound = bool(resolve_agent_mcp_servers(agent)) if agent else False
    system_prompt = (
        _compose_agent_system_prompt(
            agent,
            model_name=runtime_model_name,
            model_api=model_api,
            mcp_servers_bound=mcp_servers_bound,
            user_turn_text=text,
            state=state,
        )
        if agent
        else None
    )
    if system_prompt_suffix.strip():
        system_prompt = (system_prompt or "") + system_prompt_suffix

    history = _history_for_llm(
        state["messages"],
        vision_enabled=vision_enabled,
        image_delivery="paths" if cli_path_images else "auto",
        hybrid_executions=state.get("hybrid_executions"),
    )
    if system_prompt:
        history = [{"role": "system", "content": system_prompt}] + [
            item for item in history if item.get("role") != "system"
        ]

    workspace = get_workspace()
    cwd = workspace.get("workspace_path") if workspace else None
    llm_only_logs: list[str] = []

    from src.hybrid_concurrency import HybridPlainChatRejected

    try:
        if mcp_resume or (agent and _uses_configured_llm(agent)):
            from src.mcp_pending import get_approved_mcp_keys
            from src.mcp_react import run_mcp_react_loop

            mcp_servers = (
                list(mcp_resume.get("servers") or [])
                if mcp_resume
                else resolve_agent_mcp_servers(agent)
            )
            if mcp_servers:
                chat_messages: list[dict[str, Any]] = (
                    list(mcp_resume.get("chat_messages") or [])
                    if mcp_resume
                    else list(history)
                )
                loop = asyncio.get_running_loop()
                step_futures: list[Any] = []

                def on_log(line: str) -> None:
                    if emit_log:
                        asyncio.run_coroutine_threadsafe(emit_log(line), loop)

                def on_tool_step(step: dict[str, Any]) -> None:
                    if emit_tool_step:
                        step_futures.append(
                            asyncio.run_coroutine_threadsafe(emit_tool_step(step), loop)
                        )

                def on_reasoning(text: str) -> None:
                    if emit_reasoning:
                        step_futures.append(
                            asyncio.run_coroutine_threadsafe(emit_reasoning(text), loop)
                        )

                def on_todos(todos: list[dict[str, Any]]) -> None:
                    if emit_todos:
                        step_futures.append(
                            asyncio.run_coroutine_threadsafe(emit_todos(todos), loop)
                        )

                def on_goal(goal: dict[str, Any]) -> None:
                    if emit_goal:
                        step_futures.append(
                            asyncio.run_coroutine_threadsafe(emit_goal(goal), loop)
                        )

                def on_verification(report: dict[str, Any]) -> None:
                    if emit_verification:
                        step_futures.append(
                            asyncio.run_coroutine_threadsafe(emit_verification(report), loop)
                        )

                def on_diff_summary(report: dict[str, Any]) -> None:
                    if emit_diff_summary:
                        step_futures.append(
                            asyncio.run_coroutine_threadsafe(emit_diff_summary(report), loop)
                        )

                def on_subtask(card: dict[str, Any]) -> None:
                    if emit_subtask:
                        step_futures.append(
                            asyncio.run_coroutine_threadsafe(emit_subtask(card), loop)
                        )

                from src.bg_jobs import bind_bg_job_context, release_bg_job_context

                bg_token = bind_bg_job_context({"run_id": state["run_id"]})
                wt_root_token, wt_ctx_token = _bind_worktree_from_state(state)
                try:
                    outcome = await asyncio.to_thread(
                        run_mcp_react_loop,
                        messages=chat_messages,
                        servers=mcp_servers,
                        log_prefix="CHAT",
                        on_log=on_log if emit_log else None,
                        on_tool_step=on_tool_step if emit_tool_step else None,
                        on_reasoning=on_reasoning if emit_reasoning else None,
                        on_todos=on_todos if emit_todos else None,
                        on_goal=on_goal if emit_goal else None,
                        existing_goal=(
                            dict(state.get("agent_goal"))
                            if isinstance(state.get("agent_goal"), dict)
                            else None
                        ),
                        on_verification=on_verification if emit_verification else None,
                        on_diff_summary=on_diff_summary if emit_diff_summary else None,
                        on_subtask=on_subtask if emit_subtask else None,
                        existing_todos=list(state.get("agent_todos") or []),
                        pause_on_risky=True,
                        permission_mode=__import__(
                            "src.preferences_storage", fromlist=["load_permission_mode"]
                        ).load_permission_mode(),
                        approved_tool=mcp_approved_tool,
                        approved_keys=get_approved_mcp_keys(state["run_id"]),
                        model_id=resolved_model_id,
                    )
                finally:
                    release_bg_job_context(bg_token)
                    _release_worktree_bindings(wt_root_token, wt_ctx_token)
                # Live emits can fail if the client dropped mid-loop; never overwrite a
                # successful react outcome with an ASGI/transport error string.
                for fut in step_futures:
                    try:
                        await asyncio.wrap_future(fut)
                    except Exception as emit_exc:
                        if _is_ws_transport_error(emit_exc):
                            logger.warning(
                                "Live WS emit failed after react loop run_id=%s: %s",
                                state["run_id"],
                                emit_exc,
                            )
                            continue
                        logger.warning(
                            "Live emit failed after react loop run_id=%s: %s",
                            state["run_id"],
                            emit_exc,
                        )
                if tool_steps_sink is not None:
                    tool_steps_sink.clear()
                    tool_steps_sink.extend(list(outcome.tool_steps or []))
                if subtasks_sink is not None:
                    subtasks_sink.clear()
                    subtasks_sink.extend(list(outcome.subtasks or []))
                if outcome.todos is not None and emit_todos:
                    await emit_todos(list(outcome.todos))
                if outcome.goal is not None and emit_goal:
                    await emit_goal(dict(outcome.goal))
                if outcome.verification_report is not None and emit_verification:
                    await emit_verification(dict(outcome.verification_report))
                if outcome.diff_summary is not None and emit_diff_summary:
                    await emit_diff_summary(dict(outcome.diff_summary))
                if outcome.approval_required:
                    pause_payload = {
                        **outcome.approval_required,
                        "servers": mcp_servers,
                        "agent_id": resolved_id,
                        "reply_label": reply_label,
                        "engine_label": outcome.engine_label,
                        "tool_steps": list(outcome.tool_steps or []),
                    }
                    if outcome.todos is not None:
                        pause_payload["todos"] = list(outcome.todos)
                    if outcome.verification_report is not None:
                        pause_payload["verification_report"] = dict(
                            outcome.verification_report
                        )
                    if outcome.diff_summary is not None:
                        pause_payload["diff_summary"] = dict(outcome.diff_summary)
                    if outcome.subtasks is not None:
                        pause_payload["subtasks"] = list(outcome.subtasks)
                    return (
                        reply_label,
                        outcome.engine_label,
                        "",
                        outcome.logs,
                        None,
                        pause_payload,
                        list(outcome.files_changed or []),
                        None,
                        None,
                        False,
                    )
                return (
                    reply_label,
                    outcome.engine_label,
                    outcome.output,
                    outcome.logs,
                    None,
                    None,
                    list(outcome.files_changed or []),
                    None,
                    None,
                    False,
                )

            llm_only_logs = [
                tr(
                    "[CHAT] No tools available for this agent — using LLM text only. "
                    "Clutch Agent needs an authorized workspace for builtin tools; "
                    "other agents need MCP Hub bindings or a CLI engine.",
                    "[CHAT] 此 Agent 无可用工具，仅使用 LLM 文本回复。"
                    "Clutch Agent 需要已授权工作区以启用内置工具；其他 Agent 需绑定 MCP 或使用 CLI 引擎。",
                )
            ]
            system_prompt = _compose_agent_system_prompt(
                agent,
                model_name=runtime_model_name,
                model_api=model_api,
                mcp_servers_bound=False,
                user_turn_text=text,
                state=state,
            )
            history = _history_for_llm(
                state["messages"],
                vision_enabled=vision_enabled,
                image_delivery="paths" if cli_path_images else "auto",
                hybrid_executions=state.get("hybrid_executions"),
            )
            if system_prompt:
                history = [{"role": "system", "content": system_prompt}] + [
                    item for item in history if item.get("role") != "system"
                ]

        loop = asyncio.get_running_loop()

        def on_log(line: str) -> None:
            if emit_log:
                asyncio.run_coroutine_threadsafe(emit_log(line), loop)

        route_history = history
        tried_vision = bool(attached_images and vision_enabled)
        tried_cli_paths = bool(cli_path_images)
        from src.chat_content import (
            materialize_images_as_file_refs,
            ocr_fallback_prompt_for_engine,
        )

        # Never put raw data:image on CLI argv. Paths first; OCR only on refusal.
        if cli_path_images:
            engine_prompt = materialize_images_as_file_refs(text)
        elif attached_images and not vision_enabled:
            engine_prompt = ocr_fallback_prompt_for_engine(text)
        else:
            engine_prompt = text

        def _route_once(hist: list[dict[str, Any]], *, prompt: str | None = None):
            return route_engine(
                agent_name=agent_ref,
                prompt=prompt if prompt is not None else engine_prompt,
                cwd=cwd,
                history=hist,
                system_prompt=system_prompt,
                cli_session_id=cli_session_id,
                on_log=on_log if emit_log else None,
                run_id=state.get("run_id"),
                source=chat_source,
                session_model_id=session_model_id,
            )

        def _ocr_retry_history() -> list[dict[str, Any]]:
            hist = _history_for_llm(
                state["messages"],
                vision_enabled=False,
                image_delivery="ocr",
                hybrid_executions=state.get("hybrid_executions"),
            )
            if system_prompt:
                return [{"role": "system", "content": system_prompt}] + [
                    item for item in hist if item.get("role") != "system"
                ]
            return hist

        try:
            result = await asyncio.to_thread(_route_once, route_history)
        except HybridPlainChatRejected:
            raise
        except Exception as vision_exc:
            from src.chat_content import looks_like_vision_api_error

            if not (tried_vision and looks_like_vision_api_error(vision_exc)):
                raise
            if emit_log:
                await emit_log(
                    "[CHAT] Vision API rejected image input — retrying with local OCR/palette analysis."
                )
            llm_only_logs.append(
                "[CHAT] Vision API rejected image input — retrying with local OCR/palette analysis."
            )
            ocr_prompt = ocr_fallback_prompt_for_engine(text)
            result = await asyncio.to_thread(
                _route_once, _ocr_retry_history(), prompt=ocr_prompt
            )
        else:
            from src.chat_content import looks_like_vision_error

            if (tried_vision or tried_cli_paths) and looks_like_vision_error(
                result.output or ""
            ):
                if emit_log:
                    await emit_log(
                        "[CHAT] Model refused vision input — retrying with local OCR/palette analysis."
                    )
                llm_only_logs.append(
                    "[CHAT] Model refused vision input — retrying with local OCR/palette analysis."
                )
                ocr_prompt = ocr_fallback_prompt_for_engine(text)
                result = await asyncio.to_thread(
                    _route_once, _ocr_retry_history(), prompt=ocr_prompt
                )

        return (
            reply_label,
            result.engine,
            result.output,
            llm_only_logs + result.logs,
            result.cli_session_id,
            None,
            [],
            result.raw_output,
            result.output_events,
            result.shell_recovered,
        )
    except HybridPlainChatRejected:
        raise
    except Exception as exc:
        from src.agent_type import agent_type_from_record

        err = str(exc)
        if _is_ws_transport_error(exc):
            err = tr(
                "Connection interrupted while finishing the reply. Please resend your message.",
                "回复发送时连接中断，请重新发送消息。",
            )
        agent_type = agent_type_from_record(agent) if agent else "clutch"
        if agent_type == "claude-cli" or "Claude CLI" in err:
            runtime_engine = "Claude CLI"
        else:
            runtime_engine = runtime_model_name
        return reply_label, runtime_engine, err, [f"Error routing plain chat request: {err}"], None, None, [], None, None, False


async def _handle_plain_chat_mcp_decision(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    decision: str,
    instructions: str = "",
) -> ClutchState:
    from src.builtin_tools import (
        is_ask_user_question_tool,
        is_propose_plan_tool,
        parse_question_selection,
    )
    from src.mcp_pending import get_pending, pop_pending, record_mcp_approval

    pending = get_pending(run_id)
    if pending is None:
        return state

    is_plan = is_propose_plan_tool(pending.func_name)
    is_question = is_ask_user_question_tool(pending.func_name)
    normalized = (decision or "").strip().lower()
    if normalized == "retry":
        normalized = "revise"

    # Free-text on a question card = the user's custom answer (continue).
    if is_question and normalized == "revise":
        normalized = "approve"

    if is_plan and normalized == "revise":
        from src.plan_revise import (
            align_step_comments,
            format_plan_feedback,
            parse_plan_revise_instructions,
        )

        pop_pending(run_id)
        note, annotations = parse_plan_revise_instructions(instructions or "")
        pending_card = None
        for msg in reversed(state["messages"]):
            card = msg.get("planCard")
            if isinstance(card, dict) and card.get("status") == "pending":
                pending_card = card
                break
        steps = list((pending_card or {}).get("steps") or [])
        step_comments = align_step_comments(steps, annotations)
        feedback = format_plan_feedback(note, annotations) or tr("(no comments)", "（无附加说明）")
        messages = _patch_plan_card_status(
            list(state["messages"]),
            status="revised",
            note=feedback,
            step_comments=step_comments,
        )
        revise_line = tagged(TAG_HUMAN, f"Plan revise requested: {feedback}")
        chat_messages = list(pending.chat_messages)
        chat_messages.append(
            {
                "role": "tool",
                "tool_call_id": pending.tool_call_id,
                "content": (
                    "User requested changes to the plan before approval.\n"
                    f"Feedback:\n{feedback}\n"
                    "Call propose_plan again with a revised title and steps. "
                    "Do not edit files until the new plan is approved."
                ),
            }
        )
        state = _merge_patch(
            state,
            {
                "messages": messages,
                "terminal_logs": list(state["terminal_logs"]) + [stamp_log_line(revise_line)],
                "status": "running",
                "active_agent": pending.reply_label,
                "pending_tool_steps": [], "live_reasoning": "",
            },
        )
        _commit_run_state(run_id, state)
        _touch_session(run_id, status=state["status"])
        await _send_log_event(websocket, run_id, revise_line, node_id="")
        await _notify_run_state(
            websocket,
            run_id,
            state,
            {"messages": messages, "status": "running", "pending_tool_steps": []},
        )

        streamed_logs = False
        tool_steps_sink: list[dict[str, Any]] = []
        subtasks_sink: list[dict[str, Any]] = []

        async def emit_log(line: str) -> None:
            nonlocal streamed_logs, state
            streamed_logs = True
            stamped = stamp_log_line(line)
            await _send_log_event(websocket, run_id, stamped, node_id="")
            logs = list(state["terminal_logs"]) + [stamped]
            state = _merge_patch(state, {"terminal_logs": logs})
            _commit_run_state(run_id, state)
            await _notify_run_state(websocket, run_id, state, {"terminal_logs": logs})

        async def emit_tool_step(step: dict[str, Any]) -> None:
            nonlocal state
            patch = _tool_step_live_patch(state, step)
            state = _merge_patch(state, patch)
            _commit_run_state(run_id, state)
            await _notify_run_state(websocket, run_id, state, patch)
            await _maybe_notify_step_file_diff(websocket, run_id, step)

        async def emit_reasoning(text: str) -> None:
            nonlocal state
            patch = _reasoning_live_patch(text)
            state = _merge_patch(state, patch)
            _commit_run_state(run_id, state)
            await _notify_run_state(websocket, run_id, state, patch)

        async def emit_todos(todos: list[dict[str, Any]]) -> None:
            nonlocal state
            state = _merge_patch(state, {"agent_todos": list(todos)})
            _commit_run_state(run_id, state)
            await _notify_run_state(websocket, run_id, state, {"agent_todos": list(todos)})

        async def emit_goal(goal: dict[str, Any]) -> None:
            nonlocal state
            state = _merge_patch(state, {"agent_goal": dict(goal)})
            _commit_run_state(run_id, state)
            await _notify_run_state(websocket, run_id, state, {"agent_goal": dict(goal)})

        async def emit_verification(report: dict[str, Any]) -> None:
            nonlocal state
            label = str(state.get("active_agent") or pending.reply_label or "Clutch Agent")
            state = await _publish_verification_report(
                websocket, run_id, state, dict(report), reply_label=label
            )

        async def emit_diff_summary(report: dict[str, Any]) -> None:
            nonlocal state
            label = str(state.get("active_agent") or pending.reply_label or "Clutch Agent")
            state = await _publish_diff_summary(
                websocket, run_id, state, dict(report), reply_label=label
            )

        async def emit_subtask(card: dict[str, Any]) -> None:
            nonlocal state
            patch = _subtask_live_patch(state, card)
            state = _merge_patch(state, patch)
            _commit_run_state(run_id, state)
            await _notify_run_state(websocket, run_id, state, patch)

        (
            model_name,
            runtime_engine,
            reply_text,
            route_logs,
            _cli_session_id,
            mcp_pause,
            files_changed,
            raw_output,
            output_events,
            shell_recovered,
        ) = await _llm_chat_reply(
            state,
            "",
            agent_id=pending.agent_id,
            emit_log=emit_log,
            emit_tool_step=emit_tool_step,
            emit_reasoning=emit_reasoning,
            emit_todos=emit_todos,
            emit_goal=emit_goal,
            emit_verification=emit_verification,
            emit_diff_summary=emit_diff_summary,
            emit_subtask=emit_subtask,
            tool_steps_sink=tool_steps_sink,
            subtasks_sink=subtasks_sink,
            mcp_resume={
                "chat_messages": chat_messages,
                "servers": pending.servers,
            },
        )
        # Fall through into shared pause/complete handling below via recursive-style continue:
        return await _finish_plain_chat_after_llm(
            websocket,
            run_id,
            state,
            model_name=model_name,
            runtime_engine=runtime_engine,
            reply_text=reply_text,
            route_logs=route_logs,
            mcp_pause=mcp_pause,
            files_changed=files_changed,
            raw_output=raw_output,
            output_events=output_events,
            shell_recovered=shell_recovered,
            tool_steps_sink=tool_steps_sink,
            subtasks_sink=subtasks_sink,
            streamed_logs=streamed_logs,
            active_agent=pending.reply_label,
            pending_agent_id=pending.agent_id,
            user_text_for_tokens="",
        )

    if normalized != "approve":
        pop_pending(run_id)
        if is_plan:
            messages = _patch_plan_card_status(list(state["messages"]), status="cancelled")
            supervisor = _chat_message(
                "Supervisor",
                tr("Plan cancelled by supervisor.", "监督者已取消计划。"),
            )
            log_line = tagged(TAG_HUMAN, f"Plan {pending.func_name} cancelled")
        elif is_question:
            messages = _patch_question_card_status(
                list(state["messages"]), status="cancelled"
            )
            supervisor = _chat_message(
                "Supervisor",
                tr("Question cancelled by supervisor.", "监督者已取消提问。"),
            )
            log_line = tagged(TAG_HUMAN, f"Question {pending.func_name} cancelled")
        else:
            messages = list(state["messages"])
            supervisor = _chat_message(
                "Supervisor",
                tr("MCP tool call rejected by supervisor.", "监督者已拒绝 MCP 工具调用。"),
            )
            log_line = tagged(TAG_HUMAN, f"MCP tool {pending.func_name} rejected")
        final_messages = messages + [supervisor]
        final_patch: dict[str, Any] = {
            "messages": final_messages,
            "terminal_logs": list(state["terminal_logs"]) + [stamp_log_line(log_line)],
            "status": "idle",
            "active_agent": pending.reply_label,
            "pending_tool_steps": [], "live_reasoning": "",
        }
        state = _merge_patch(state, final_patch)
        _commit_run_state(run_id, state)
        _touch_session(run_id, status=state["status"])
        await _send_message_event(websocket, run_id, supervisor, "")
        await _send_log_event(websocket, run_id, log_line, node_id="")
        await _notify_run_state(websocket, run_id, state, final_patch)
        return state

    pop_pending(run_id)
    if not is_plan and not is_question:
        record_mcp_approval(run_id, pending.func_name, pending.func_args)
    question_selection: dict[str, str] | None = None
    if is_question:
        question_selection = parse_question_selection(
            instructions, dict(pending.func_args or {})
        )
        messages = _patch_question_card_status(
            list(state["messages"]),
            status="answered",
            selected=question_selection,
        )
    elif is_plan:
        messages = _patch_plan_card_status(list(state["messages"]), status="approved")
    else:
        messages = list(state["messages"])
    state = _merge_patch(
        state,
        {
            "messages": messages,
            "status": "running",
            "active_agent": pending.reply_label,
        },
    )
    await _notify_run_state(
        websocket, run_id, state, {"status": "running", "messages": messages}
    )

    streamed_logs = False
    tool_steps_sink: list[dict[str, Any]] = []
    subtasks_sink: list[dict[str, Any]] = []

    async def emit_log(line: str) -> None:
        nonlocal streamed_logs, state
        streamed_logs = True
        stamped = stamp_log_line(line)
        await _send_log_event(websocket, run_id, stamped, node_id="")
        logs = list(state["terminal_logs"]) + [stamped]
        state = _merge_patch(state, {"terminal_logs": logs})
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, {"terminal_logs": logs})

    async def emit_tool_step(step: dict[str, Any]) -> None:
        nonlocal state
        patch = _tool_step_live_patch(state, step)
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, patch)
        await _maybe_notify_step_file_diff(websocket, run_id, step)

    async def emit_reasoning(text: str) -> None:
        nonlocal state
        patch = _reasoning_live_patch(text)
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, patch)

    async def emit_todos(todos: list[dict[str, Any]]) -> None:
        nonlocal state
        state = _merge_patch(state, {"agent_todos": list(todos)})
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, {"agent_todos": list(todos)})

    async def emit_goal(goal: dict[str, Any]) -> None:
        nonlocal state
        state = _merge_patch(state, {"agent_goal": dict(goal)})
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, {"agent_goal": dict(goal)})

    async def emit_verification(report: dict[str, Any]) -> None:
        nonlocal state
        label = str(state.get("active_agent") or "Clutch Agent")
        state = await _publish_verification_report(
            websocket, run_id, state, dict(report), reply_label=label
        )

    async def emit_diff_summary(report: dict[str, Any]) -> None:
        nonlocal state
        label = str(state.get("active_agent") or "Clutch Agent")
        state = await _publish_diff_summary(
            websocket, run_id, state, dict(report), reply_label=label
        )

    async def emit_subtask(card: dict[str, Any]) -> None:
        nonlocal state
        patch = _subtask_live_patch(state, card)
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, patch)

    resume_args = dict(pending.func_args or {})
    if question_selection is not None:
        resume_args["selected"] = question_selection
    approved_tool = {
        "tool_call_id": pending.tool_call_id,
        "func_name": pending.func_name,
        "func_args": resume_args,
        "step_idx": pending.step_idx,
        "step_id": pending.step_id or f"tool_{pending.step_idx}",
    }
    mcp_resume = {
        "chat_messages": pending.chat_messages,
        "servers": pending.servers,
    }

    (
        model_name,
        runtime_engine,
        reply_text,
        route_logs,
        _cli_session_id,
        mcp_pause,
        files_changed,
        raw_output,
        output_events,
        shell_recovered,
    ) = await _llm_chat_reply(
        state,
        "",
        agent_id=pending.agent_id,
        emit_log=emit_log,
        emit_tool_step=emit_tool_step,
        emit_reasoning=emit_reasoning,
        emit_todos=emit_todos,
        emit_goal=emit_goal,
        emit_verification=emit_verification,
        emit_diff_summary=emit_diff_summary,
        emit_subtask=emit_subtask,
        tool_steps_sink=tool_steps_sink,
        subtasks_sink=subtasks_sink,
        mcp_approved_tool=approved_tool,
        mcp_resume=mcp_resume,
    )

    return await _finish_plain_chat_after_llm(
        websocket,
        run_id,
        state,
        model_name=model_name,
        runtime_engine=runtime_engine,
        reply_text=reply_text,
        route_logs=route_logs,
        mcp_pause=mcp_pause,
        files_changed=files_changed,
        raw_output=raw_output,
        output_events=output_events,
        shell_recovered=shell_recovered,
        tool_steps_sink=tool_steps_sink,
        subtasks_sink=subtasks_sink,
        streamed_logs=streamed_logs,
        active_agent=pending.reply_label,
        pending_agent_id=pending.agent_id,
        user_text_for_tokens="",
    )


async def _finish_plain_chat_after_llm(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    *,
    model_name: str,
    runtime_engine: str,
    reply_text: str,
    route_logs: list[str],
    mcp_pause: dict[str, Any] | None,
    files_changed: list[str] | None,
    raw_output: str | None,
    output_events: list[dict[str, Any]] | None,
    shell_recovered: bool,
    tool_steps_sink: list[dict[str, Any]],
    streamed_logs: bool,
    active_agent: str,
    pending_agent_id: str,
    user_text_for_tokens: str,
    cli_session_id: str | None = None,
    subtasks_sink: list[dict[str, Any]] | None = None,
) -> ClutchState:
    """Shared pause/complete path after plain-chat LLM (+ MCP) returns."""
    if mcp_pause:
        from src.mcp_pending import McpPendingApproval, store_pending

        store_pending(
            run_id,
            McpPendingApproval(
                agent_id=pending_agent_id,
                reply_label=model_name,
                chat_messages=list(mcp_pause["chat_messages"]),
                servers=list(mcp_pause["servers"]),
                tool_call_id=str(mcp_pause["tool_call_id"]),
                func_name=str(mcp_pause["func_name"]),
                func_args=dict(mcp_pause.get("func_args") or {}),
                step_idx=int(mcp_pause.get("step_idx", 0)),
                logs=list(route_logs),
                step_id=str(mcp_pause.get("step_id") or ""),
            ),
        )
        is_plan = _is_plan_pause(mcp_pause)
        gate_line = _mcp_pause_gate_line(mcp_pause)
        pause_messages, pause_msg, pause_created = _messages_for_mcp_pause(
            list(state["messages"]),
            mcp_pause,
            reply_label=model_name or active_agent,
        )
        pause_patch: dict[str, Any] = {
            "messages": pause_messages,
            "terminal_logs": _append_terminal_logs(
                list(state["terminal_logs"]), route_logs, gate_line, streamed=streamed_logs
            ),
            "status": "awaiting_human",
            "active_agent": active_agent,
            "pending_tool_steps": list(mcp_pause.get("tool_steps") or tool_steps_sink),
            "pending_subtasks": list(
                mcp_pause.get("subtasks") or subtasks_sink or []
            ),
        }
        if mcp_pause.get("todos") is not None:
            pause_patch["agent_todos"] = list(mcp_pause.get("todos") or [])
        if mcp_pause.get("verification_report") is not None:
            pause_patch["verification_report"] = dict(mcp_pause["verification_report"])
        if mcp_pause.get("diff_summary") is not None:
            pause_patch["diff_summary"] = dict(mcp_pause["diff_summary"])
        state = _merge_patch(state, pause_patch)
        _commit_run_state(run_id, state)
        _touch_session(run_id, status=state["status"])
        if pause_created:
            await _send_message_event(websocket, run_id, pause_msg, "")
        if not streamed_logs:
            for log in route_logs:
                await _send_log_event(websocket, run_id, log, node_id="")
        await _send_log_event(websocket, run_id, gate_line, node_id="")
        await _notify_run_state(websocket, run_id, state, pause_patch)
        await _send_human_required(
            websocket, run_id, node_id="", prompt=_mcp_pause_human_prompt(mcp_pause)
        )
        return state

    from src.run_control import build_run_stats, should_offer_continue

    sealed_steps = _sealed_tool_steps(state, sink=tool_steps_sink)
    sealed_subtasks = _sealed_subtasks(state, sink=subtasks_sink)
    merged_changed = _merge_files_changed_with_tool_steps(files_changed, sealed_steps)
    files_changed = merged_changed
    reply = _chat_message(
        model_name,
        reply_text,
        runtime_engine=runtime_engine,
        raw_output=raw_output,
        output_events=output_events,
        tool_steps=sealed_steps,
        files_changed=merged_changed or None,
        todo_list=list(state.get("agent_todos") or []) or None,
        verification_report=_verification_report_for_seal(
            state, files_changed=merged_changed or None
        ),
        diff_summary=_diff_summary_for_seal(
            state, files_changed=merged_changed or None
        ),
        subtask_cards=sealed_subtasks,
    )
    log_line = f"[CHAT] {model_name} via {runtime_engine}: {len(reply_text)} chars"
    if not streamed_logs:
        for log in route_logs:
            await _send_log_event(websocket, run_id, log, node_id="")
    await _send_log_event(websocket, run_id, log_line, node_id="")

    final_messages = list(state["messages"]) + [reply]
    final_logs = _append_terminal_logs(
        list(state["terminal_logs"]), route_logs, log_line, streamed=streamed_logs
    )
    token_patch = _token_patch_turn(
        state, user_text=user_text_for_tokens, assistant_text=reply_text
    )
    offer_continue = should_offer_continue(reply_text)
    fuse_hit = "Loop fuse" in (reply_text or "") or "死循环熔断" in (reply_text or "")
    final_patch = {
        "messages": final_messages,
        "terminal_logs": final_logs,
        "status": "idle",
        "active_agent": active_agent,
        "pending_tool_steps": [], "live_reasoning": "",
        "pending_subtasks": [],
        "awaiting_continue": offer_continue,
        "run_stats": build_run_stats(
            tool_steps=len(sealed_steps or []),
            session_tokens=int(token_patch.get("session_tokens") or 0),
            fuse_triggered=fuse_hit,
        ),
        **token_patch,
    }
    if shell_recovered:
        final_patch["shell_session_status"] = "recovering"
    elif runtime_engine and "Hybrid" in runtime_engine:
        final_patch["shell_session_status"] = "ready"
    if cli_session_id:
        from src.state import cli_session_patch

        final_patch.update(cli_session_patch(cli_session_id, pending_agent_id))
    if merged_changed:
        # Persist shell + edit paths so Changes works without a git repo.
        prev = [str(p) for p in (state.get("changed_files") or []) if str(p).strip()]
        final_patch["changed_files"] = list(dict.fromkeys([*prev, *merged_changed]))
    state = _merge_patch(state, final_patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, status=state["status"])
    await _send_message_event(websocket, run_id, reply, "")
    if runtime_engine and "Hybrid" in runtime_engine:
        await _send_hybrid_execution_event(
            websocket,
            run_id,
            message_id=str(reply["id"]),
            raw_output=raw_output,
            output_events=output_events,
        )
    if files_changed:
        await _notify_workspace_files_changed(
            websocket,
            run_id,
            files_changed,
            path_diffs=_path_diffs_from_tool_steps(sealed_steps),
        )
    await _notify_run_state(websocket, run_id, state, final_patch)
    return state


def _interrupt_plain_chat_shell(run_id: str) -> None:
    from src.shell_session import get_shell_session_manager

    get_shell_session_manager().release(run_id)


async def _apply_plain_chat_stop(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
) -> ClutchState:
    from src.run_control import build_run_stats, stop_supervisor_message
    from src.runtime_config import runtime_mode

    # Idempotent: avoid stacking duplicate "Run stopped" Supervisor bubbles.
    if state.get("status") == "idle" and state.get("awaiting_continue"):
        await asyncio.to_thread(_interrupt_plain_chat_shell, run_id)
        return state

    await asyncio.to_thread(_interrupt_plain_chat_shell, run_id)
    if runtime_mode() == "hybrid":
        log_line = stamp_log_line(tagged(TAG_WORKFLOW, "[HYBRID] Plain chat stopped by user."))
    else:
        log_line = stamp_log_line(tagged(TAG_WORKFLOW, "Run stopped by supervisor."))
    stop_text = tr(stop_supervisor_message(lang="en"), stop_supervisor_message(lang="zh"))
    supervisor = _chat_message("Supervisor", stop_text)
    logs = list(state["terminal_logs"]) + [log_line]
    steps = list(state.get("pending_tool_steps") or [])
    stats = build_run_stats(
        tool_steps=len(steps),
        session_tokens=int(state.get("session_tokens") or 0),
    )
    patch: dict[str, Any] = {
        "status": "idle",
        "terminal_logs": logs,
        "messages": list(state["messages"]) + [supervisor],
        "pending_tool_steps": [], "live_reasoning": "",
        "awaiting_continue": True,
        "run_stats": stats,
    }
    if runtime_mode() == "hybrid":
        patch["shell_session_status"] = "ready"
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, status=state["status"])
    await _send_log_event(websocket, run_id, log_line, node_id="")
    await _send_message_event(websocket, run_id, supervisor, "")
    await _notify_run_state(websocket, run_id, state, patch)
    return state


async def _recover_stuck_plain_chat(run_id: str) -> None:
    from src.runtime_config import runtime_mode

    state = _get_or_create_run(run_id)
    if state.get("workflow_id"):
        return
    if state["status"] != "running":
        return
    log_line = stamp_log_line(
        tagged(
            TAG_WORKFLOW,
            "[HYBRID] Recovered plain chat after WebSocket disconnect.",
        )
    )
    logs = list(state["terminal_logs"]) + [log_line]
    patch: dict[str, Any] = {"status": "idle", "terminal_logs": logs}
    if runtime_mode() == "hybrid":
        patch["shell_session_status"] = "ready"
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, status=state["status"])


async def _apply_hybrid_plain_chat_rejection(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    *,
    code: str,
    keep_running: bool = False,
) -> ClutchState:
    from src.hybrid_audit_log import append_hybrid_rejection_audit
    from src.hybrid_concurrency import hybrid_rejection_message, shell_session_status_for_rejection
    from src.runtime_config import runtime_mode

    user_text = hybrid_rejection_message(code)
    log_line = f"[HYBRID] rejected ({code}): {user_text}"
    append_hybrid_rejection_audit(run_id=run_id, reason=code, message=user_text)

    supervisor = _chat_message("Supervisor", user_text)
    logs = list(state["terminal_logs"]) + [stamp_log_line(log_line)]
    patch: dict[str, Any] = {
        "messages": list(state["messages"]) + [supervisor],
        "terminal_logs": logs,
    }
    if runtime_mode() == "hybrid":
        patch["shell_session_status"] = shell_session_status_for_rejection(code)
    if not keep_running:
        patch["status"] = "idle"
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, status=state["status"])
    await _send_message_event(websocket, run_id, supervisor, "")
    await _send_log_event(websocket, run_id, log_line, node_id="")
    await _notify_run_state(websocket, run_id, state, patch)
    return state


class _NullWebSocket:
    """Placeholder when resuming a pool-queued turn after the client disconnected."""

    async def send_text(self, _data: str) -> None:
        return


async def _refresh_pool_queued_run_states() -> None:
    from src.plain_chat_pool_queue import iter_queued_run_ids, pool_queue_state_patch

    for run_id in iter_queued_run_ids():
        state = _get_or_create_run(run_id)
        if state.get("shell_session_status") != "queued_pool":
            continue
        patch = pool_queue_state_patch(run_id)
        state = _merge_patch(state, patch)
        _run_states[run_id] = state
        _commit_run_state(run_id, state)
        from src.plain_chat_pool_queue import get_plain_chat_ws

        websocket = get_plain_chat_ws(run_id)
        if websocket is not None:
            await _notify_run_state(websocket, run_id, state, patch)


async def _apply_pool_full_queue(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    *,
    text: str,
    agent_id: str,
    session_model_id: str | None,
    client_message_id: str | None,
) -> ClutchState:
    from src.hybrid_concurrency import shell_session_status_for_pool_queue
    from src.plain_chat_pool_queue import (
        PoolQueuedTurn,
        clear_pool_queue_state_patch,
        enqueue_turn,
        pool_queue_state_patch,
        register_plain_chat_ws,
        schedule_pool_drain,
    )
    from src.runtime_config import runtime_mode

    register_plain_chat_ws(run_id, websocket)
    pending = enqueue_turn(
        PoolQueuedTurn(
            run_id=run_id,
            text=text,
            agent_id=agent_id,
            session_model_id=session_model_id,
            client_message_id=client_message_id,
        )
    )
    log_line = stamp_log_line(
        tagged(
            TAG_WORKFLOW,
            f"[HYBRID] queued waiting for shell pool ({pending} pending globally)",
        )
    )
    logs = list(state["terminal_logs"]) + [log_line]
    patch: dict[str, Any] = {
        "terminal_logs": logs,
        "status": "running",
    }
    if runtime_mode() == "hybrid":
        patch["shell_session_status"] = shell_session_status_for_pool_queue()
        patch.update(pool_queue_state_patch(run_id))
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    await _send_log_event(websocket, run_id, log_line, node_id="")
    await _notify_run_state(websocket, run_id, state, patch)
    await schedule_pool_drain()
    return state


async def _resume_pool_queued_turn(
    item: "PoolQueuedTurn",
    websocket: WebSocket | None,
) -> None:
    from src.plain_chat_pool_queue import PoolQueuedTurn, register_plain_chat_ws
    from src.run_state_store import sync_run_state_from_disk

    assert isinstance(item, PoolQueuedTurn)
    run_id = item.run_id
    ws: WebSocket = websocket if websocket is not None else _NullWebSocket()  # type: ignore[assignment]
    if websocket is not None:
        register_plain_chat_ws(run_id, websocket)
    state = sync_run_state_from_disk(run_id, _get_or_create_run(run_id))
    _run_states[run_id] = state
    await _handle_plain_chat(
        ws,
        run_id,
        state,
        item.text,
        agent_id=item.agent_id,
        session_model_id=item.session_model_id,
        client_message_id=item.client_message_id,
        resume_after_pool_queue=True,
    )


async def _persist_plain_chat_user_message(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    text: str,
    agent_id: str | None = None,
    client_message_id: str | None = None,
) -> ClutchState:
    """Commit user turn + session list entry before LLM work starts."""
    from src.agent_storage import BUILTIN_AGENT_ID, get_agent_by_id
    from src.runtime_config import runtime_mode

    resolved_id = (agent_id or "").strip() or BUILTIN_AGENT_ID
    agent = get_agent_by_id(resolved_id)
    active_agent = str(agent.get("name", "Clutch Agent")) if agent else "Clutch Agent"

    stripped = text.strip()
    client_id = (client_message_id or "").strip()
    user_message = _chat_message(
        "User",
        text,
        msg_id=client_id or f"user_{uuid.uuid4().hex[:8]}",
    )
    messages = list(state["messages"])
    already_has_client_id = bool(
        client_id and any(str(item.get("id", "")) == client_id for item in messages)
    )
    user_message_added = not already_has_client_id and not (
        messages
        and messages[-1].get("agent") == "User"
        and str(messages[-1].get("text", "")).strip() == stripped
    )
    if user_message_added:
        messages = messages + [user_message]
    user_patch: dict[str, Any] = {
        "messages": messages,
        "status": "running",
        "active_agent": active_agent,
        "awaiting_continue": False,
    }
    if runtime_mode() == "hybrid":
        user_patch["shell_session_status"] = "ready"
    state = _merge_patch(state, user_patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])
    if user_message_added:
        await _send_message_event(websocket, run_id, user_message, "")
    await _notify_run_state(websocket, run_id, state, user_patch)
    return state


async def _handle_plain_chat(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    text: str,
    agent_id: str | None = None,
    session_model_id: str | None = None,
    client_message_id: str | None = None,
    *,
    resume_after_pool_queue: bool = False,
    user_persisted: bool = False,
) -> ClutchState:
    from src.agent_storage import BUILTIN_AGENT_ID, get_agent_by_id
    from src.runtime_config import runtime_mode

    resolved_id = (agent_id or "").strip() or BUILTIN_AGENT_ID
    agent = get_agent_by_id(resolved_id)
    active_agent = str(agent.get("name", "Clutch Agent")) if agent else "Clutch Agent"

    if (
        state["status"] == "running"
        and runtime_mode() == "hybrid"
        and not resume_after_pool_queue
        and not user_persisted
    ):
        return state

    stripped = text.strip()
    client_id = (client_message_id or "").strip()
    if not resume_after_pool_queue and not user_persisted:
        user_message = _chat_message(
            "User",
            text,
            msg_id=client_id or f"user_{uuid.uuid4().hex[:8]}",
        )
        messages = list(state["messages"])
        already_has_client_id = bool(
            client_id and any(str(item.get("id", "")) == client_id for item in messages)
        )
        user_message_added = not already_has_client_id and not (
            messages
            and messages[-1].get("agent") == "User"
            and str(messages[-1].get("text", "")).strip() == stripped
        )
        if user_message_added:
            messages = messages + [user_message]
        user_patch: dict[str, Any] = {
            "messages": messages,
            "status": "running",
            "active_agent": active_agent,
            "pending_tool_steps": [], "live_reasoning": "",
        }
        if runtime_mode() == "hybrid":
            user_patch["shell_session_status"] = "ready"
        state = _merge_patch(state, user_patch)
        _commit_run_state(run_id, state)
        _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])

        if user_message_added:
            await _send_message_event(websocket, run_id, user_message, "")
        await _notify_run_state(websocket, run_id, state, user_patch)
    elif runtime_mode() == "hybrid":
        from src.plain_chat_pool_queue import clear_pool_queue_state_patch

        ready_patch = {
            "shell_session_status": "ready",
            "status": "running",
            **clear_pool_queue_state_patch(),
        }
        state = _merge_patch(state, ready_patch)
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, ready_patch)

    from src.state import cli_session_patch, read_cli_session_agent_id, read_cli_session_id

    stored_session_id = read_cli_session_id(state) or None
    stored_session_agent = read_cli_session_agent_id(state)
    agent_switched = bool(stored_session_agent and stored_session_agent != resolved_id)
    if agent_switched:
        stored_session_id = None

    streamed_logs = False
    tool_steps_sink: list[dict[str, Any]] = []
    subtasks_sink: list[dict[str, Any]] = []

    async def emit_log(line: str) -> None:
        nonlocal streamed_logs, state
        streamed_logs = True
        stamped = stamp_log_line(line)
        logs = list(state["terminal_logs"]) + [stamped]
        state = _merge_patch(state, {"terminal_logs": logs})
        _commit_run_state(run_id, state)
        await _try_ws_notify(
            _send_log_event(websocket, run_id, stamped, node_id=""),
            run_id=run_id,
            what="log",
        )
        await _try_ws_notify(
            _notify_run_state(websocket, run_id, state, {"terminal_logs": logs}),
            run_id=run_id,
            what="state_patch",
        )

    async def emit_tool_step(step: dict[str, Any]) -> None:
        nonlocal state
        patch = _tool_step_live_patch(state, step)
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        await _try_ws_notify(
            _notify_run_state(websocket, run_id, state, patch),
            run_id=run_id,
            what="state_patch",
        )
        await _maybe_notify_step_file_diff(websocket, run_id, step)

    async def emit_reasoning(text: str) -> None:
        nonlocal state
        patch = _reasoning_live_patch(text)
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        await _try_ws_notify(
            _notify_run_state(websocket, run_id, state, patch),
            run_id=run_id,
            what="state_patch",
        )

    async def emit_todos(todos: list[dict[str, Any]]) -> None:
        nonlocal state
        state = _merge_patch(state, {"agent_todos": list(todos)})
        _commit_run_state(run_id, state)
        await _try_ws_notify(
            _notify_run_state(websocket, run_id, state, {"agent_todos": list(todos)}),
            run_id=run_id,
            what="state_patch",
        )

    async def emit_goal(goal: dict[str, Any]) -> None:
        nonlocal state
        state = _merge_patch(state, {"agent_goal": dict(goal)})
        _commit_run_state(run_id, state)
        await _try_ws_notify(
            _notify_run_state(websocket, run_id, state, {"agent_goal": dict(goal)}),
            run_id=run_id,
            what="state_patch",
        )

    async def emit_verification(report: dict[str, Any]) -> None:
        nonlocal state
        label = str(state.get("active_agent") or active_agent or "Clutch Agent")
        state = await _publish_verification_report(
            websocket, run_id, state, dict(report), reply_label=label
        )

    async def emit_diff_summary(report: dict[str, Any]) -> None:
        nonlocal state
        label = str(state.get("active_agent") or active_agent or "Clutch Agent")
        state = await _publish_diff_summary(
            websocket, run_id, state, dict(report), reply_label=label
        )

    async def emit_subtask(card: dict[str, Any]) -> None:
        nonlocal state
        patch = _subtask_live_patch(state, card)
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        await _try_ws_notify(
            _notify_run_state(websocket, run_id, state, patch),
            run_id=run_id,
            what="state_patch",
        )

    from src.hybrid_concurrency import HybridPlainChatRejected

    chat_text = text
    from src.code_diagnostics import format_diagnostics_for_prompt, pop_pending_diagnostics

    pending_diag = pop_pending_diagnostics(run_id)
    if pending_diag:
        diag_prefix = format_diagnostics_for_prompt(pending_diag)
        if diag_prefix:
            chat_text = f"{diag_prefix}\n\n{text}"
        state = _merge_patch(state, {"chat_diagnostics": pending_diag})
        _commit_run_state(run_id, state)
        await _notify_run_state(
            websocket,
            run_id,
            state,
            {"chat_diagnostics": pending_diag},
        )

    try:
        (
            model_name,
            runtime_engine,
            reply_text,
            route_logs,
            cli_session_id,
            mcp_pause,
            files_changed,
            raw_output,
            output_events,
            shell_recovered,
        ) = await _llm_chat_reply(
            state,
            chat_text,
            agent_id=resolved_id,
            session_model_id=session_model_id,
            cli_session_id=stored_session_id,
            emit_log=emit_log,
            emit_tool_step=emit_tool_step,
            emit_reasoning=emit_reasoning,
            emit_todos=emit_todos,
            emit_goal=emit_goal,
            emit_verification=emit_verification,
            emit_diff_summary=emit_diff_summary,
            emit_subtask=emit_subtask,
            tool_steps_sink=tool_steps_sink,
            subtasks_sink=subtasks_sink,
        )
    except HybridPlainChatRejected as exc:
        if exc.code == "pool_full":
            return await _apply_pool_full_queue(
                websocket,
                run_id,
                state,
                text=text,
                agent_id=resolved_id,
                session_model_id=session_model_id,
                client_message_id=client_id or None,
            )
        keep_running = exc.code == "session_busy" and state["status"] == "running"
        return await _apply_hybrid_plain_chat_rejection(
            websocket,
            run_id,
            state,
            code=exc.code,
            keep_running=keep_running,
        )
    except Exception as exc:
        err_line = f"Error in plain chat: {exc}"
        logs = list(state["terminal_logs"]) + [stamp_log_line(err_line)]
        err_patch: dict[str, Any] = {"status": "idle", "terminal_logs": logs}
        if runtime_mode() == "hybrid":
            err_patch["shell_session_status"] = "ready"
        state = _merge_patch(state, err_patch)
        _commit_run_state(run_id, state)
        _touch_session(run_id, status=state["status"])
        await _try_ws_notify(
            _send_log_event(websocket, run_id, err_line, node_id=""),
            run_id=run_id,
            what="log",
        )
        await _try_ws_notify(
            _notify_run_state(websocket, run_id, state, err_patch),
            run_id=run_id,
            what="state_patch",
        )
        return state

    if mcp_pause:
        from src.mcp_pending import McpPendingApproval, store_pending

        store_pending(
            run_id,
            McpPendingApproval(
                agent_id=resolved_id,
                reply_label=model_name,
                chat_messages=list(mcp_pause["chat_messages"]),
                servers=list(mcp_pause["servers"]),
                tool_call_id=str(mcp_pause["tool_call_id"]),
                func_name=str(mcp_pause["func_name"]),
                func_args=dict(mcp_pause.get("func_args") or {}),
                step_idx=int(mcp_pause.get("step_idx", 0)),
                logs=list(route_logs),
                step_id=str(mcp_pause.get("step_id") or ""),
            ),
        )
        gate_line = _mcp_pause_gate_line(mcp_pause)
        pause_messages, pause_msg, pause_created = _messages_for_mcp_pause(
            list(state["messages"]),
            mcp_pause,
            reply_label=model_name or active_agent,
        )
        pause_logs = _append_terminal_logs(
            list(state["terminal_logs"]), route_logs, gate_line, streamed=streamed_logs
        )
        pause_patch: dict[str, Any] = {
            "messages": pause_messages,
            "terminal_logs": pause_logs,
            "status": "awaiting_human",
            "active_agent": active_agent,
            "pending_tool_steps": list(mcp_pause.get("tool_steps") or tool_steps_sink),
            "pending_subtasks": list(
                mcp_pause.get("subtasks") or subtasks_sink or []
            ),
        }
        state = _merge_patch(state, pause_patch)
        _commit_run_state(run_id, state)
        _touch_session(run_id, status=state["status"])
        if pause_created:
            await _send_message_event(websocket, run_id, pause_msg, "")
        if not streamed_logs:
            for log in route_logs:
                await _send_log_event(websocket, run_id, log, node_id="")
        await _send_log_event(websocket, run_id, gate_line, node_id="")
        await _notify_run_state(websocket, run_id, state, pause_patch)
        await _send_human_required(
            websocket,
            run_id,
            node_id="",
            prompt=_mcp_pause_human_prompt(mcp_pause),
        )
        return state

    sealed_steps = _sealed_tool_steps(state, sink=tool_steps_sink)
    sealed_subtasks = _sealed_subtasks(state, sink=subtasks_sink)
    merged_changed = _merge_files_changed_with_tool_steps(files_changed, sealed_steps)
    files_changed = merged_changed
    reply = _chat_message(
        model_name,
        reply_text,
        runtime_engine=runtime_engine,
        raw_output=raw_output,
        output_events=output_events,
        tool_steps=sealed_steps,
        files_changed=merged_changed or None,
        todo_list=list(state.get("agent_todos") or []) or None,
        verification_report=_verification_report_for_seal(
            state, files_changed=merged_changed or None
        ),
        diff_summary=_diff_summary_for_seal(
            state, files_changed=merged_changed or None
        ),
        subtask_cards=sealed_subtasks,
    )

    hybrid_system_prompt: str | None = None
    hybrid_executions_patch: dict[str, dict[str, object]] | None = None
    hybrid_detail_log: str | None = None
    if runtime_engine and "Hybrid" in runtime_engine:
        if agent:
            from src.agent_mcp import resolve_agent_mcp_servers
            from src.agent_type import resolve_model_for_agent
            from src.models_config import get_router

            router = get_router()
            model, _resolved_model_id = resolve_model_for_agent(
                router, agent, session_model_id=session_model_id
            )
            hybrid_system_prompt = _compose_agent_system_prompt(
                agent,
                model_name=model.name,
                model_api=getattr(model, "api_model", None) or model.name,
                mcp_servers_bound=bool(resolve_agent_mcp_servers(agent)),
                state=state,
            )
        hybrid_executions_patch = _merge_hybrid_executions(
            state,
            message_id=str(reply["id"]),
            raw_output=raw_output,
            output_events=output_events,
            system_prompt=hybrid_system_prompt,
        )
        entry = hybrid_executions_patch[str(reply["id"])]
        reply["rawOutput"] = entry.get("rawOutput")
        reply["outputEvents"] = entry.get("outputEvents")
        hybrid_detail_log = (
            f"[HYBRID] execution_details message={reply['id']} "
            f"events={len(entry.get('outputEvents') or [])} "
            f"raw_bytes={len(str(entry.get('rawOutput') or ''))}"
        )

    log_line = f"[CHAT] {model_name} via {runtime_engine}: {len(reply_text)} chars"

    final_messages = list(state["messages"]) + [reply]
    final_logs = _append_terminal_logs(
        list(state["terminal_logs"]), route_logs, log_line, streamed=streamed_logs
    )
    if hybrid_detail_log:
        final_logs.append(stamp_log_line(hybrid_detail_log))
    final_patch: dict[str, Any] = {
        "messages": final_messages,
        "terminal_logs": final_logs,
        "status": "idle",
        "active_agent": active_agent,
        "pending_tool_steps": [], "live_reasoning": "",
        "pending_subtasks": [],
        **_token_patch_turn(state, user_text=text, assistant_text=reply_text),
    }
    if hybrid_executions_patch is not None:
        final_patch["hybrid_executions"] = hybrid_executions_patch
    if shell_recovered:
        final_patch["shell_session_status"] = "recovering"
    elif runtime_engine and "Hybrid" in runtime_engine:
        from src.plain_chat_pool_queue import clear_pool_queue_state_patch

        final_patch["shell_session_status"] = "ready"
        final_patch.update(clear_pool_queue_state_patch())
    if cli_session_id:
        final_patch.update(cli_session_patch(cli_session_id, resolved_id))
    elif stored_session_agent and stored_session_agent != resolved_id:
        final_patch.update(cli_session_patch(None, ""))
    if merged_changed:
        prev = [str(p) for p in (state.get("changed_files") or []) if str(p).strip()]
        final_patch["changed_files"] = list(dict.fromkeys([*prev, *merged_changed]))
    state = _merge_patch(state, final_patch)

    from src.compaction import should_compact, compact_run_messages
    if should_compact(state):
        state = await compact_run_messages(run_id, state, model_id=resolved_id)
        final_patch.update({
            "messages": list(state["messages"]),
            "token_input": state["token_input"],
            "token_output": state["token_output"],
            "session_tokens": state["session_tokens"],
            "session_cost_usd": state["session_cost_usd"],
        })

    _commit_run_state(run_id, state)
    _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])

    if not streamed_logs:
        for log in route_logs:
            await _try_ws_notify(
                _send_log_event(websocket, run_id, log, node_id=""),
                run_id=run_id,
                what="log",
            )
    await _try_ws_notify(
        _send_log_event(websocket, run_id, log_line, node_id=""),
        run_id=run_id,
        what="log",
    )
    await _try_ws_notify(
        _send_message_event(websocket, run_id, reply, ""),
        run_id=run_id,
        what="message",
    )
    if runtime_engine and "Hybrid" in runtime_engine and hybrid_executions_patch:
        entry = hybrid_executions_patch[str(reply["id"])]
        await _try_ws_notify(
            _send_hybrid_execution_event(
                websocket,
                run_id,
                message_id=str(reply["id"]),
                raw_output=entry.get("rawOutput"),  # type: ignore[arg-type]
                output_events=entry.get("outputEvents"),  # type: ignore[arg-type]
            ),
            run_id=run_id,
            what="hybrid_execution",
        )
    if files_changed:
        await _try_ws_notify(
            _notify_workspace_files_changed(
                websocket,
                run_id,
                files_changed,
                path_diffs=_path_diffs_from_tool_steps(sealed_steps),
            ),
            run_id=run_id,
            what="file_changed",
        )
    await _try_ws_notify(
        _notify_run_state(websocket, run_id, state, final_patch),
        run_id=run_id,
        what="state_patch",
    )

    return state


async def _notify_workspace_files_changed(
    websocket: WebSocket,
    run_id: str,
    paths: list[str],
    *,
    node_id: str = "",
    path_diffs: dict[str, list[dict[str, Any]]] | None = None,
) -> None:
    """Push Changes-panel updates. Prefer edit-hunk diffs when provided (D6)."""
    from src.builtin_tools import enrich_diff_file_entry

    for path in paths:
        rel = str(path).strip()
        if not rel:
            continue
        diffs: list[dict[str, Any]] = []
        if path_diffs and rel in path_diffs:
            diffs = list(path_diffs[rel] or [])
        if not diffs:
            entry = enrich_diff_file_entry({"path": rel})
            diffs = list(entry.get("diffs") or [])
        if not diffs:
            diffs = [{"lineNum": 1, "type": "addition", "text": "(updated via MCP)"}]
        await _send_file_changed(
            websocket,
            run_id,
            node_id=node_id,
            path=rel,
            diff_lines=diffs,
        )


def _path_diffs_from_tool_steps(
    sealed_steps: list[dict[str, Any]] | None,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for step in sealed_steps or []:
        if not isinstance(step, dict):
            continue
        file_diff = step.get("fileDiff")
        if not isinstance(file_diff, dict):
            continue
        rel = str(file_diff.get("path") or "").strip()
        if not rel:
            continue
        diffs = file_diff.get("diffs")
        if isinstance(diffs, list) and diffs:
            out[rel] = [dict(d) for d in diffs if isinstance(d, dict)]
    return out


async def _maybe_notify_step_file_diff(
    websocket: WebSocket,
    run_id: str,
    step: dict[str, Any],
    *,
    node_id: str = "",
) -> None:
    """Live-push Changes panel using the same hunk as the Chat Diff card."""
    file_diff = step.get("fileDiff") if isinstance(step, dict) else None
    if not isinstance(file_diff, dict):
        return
    path = str(file_diff.get("path") or "").strip()
    if not path:
        return
    raw_diffs = file_diff.get("diffs")
    diffs = [dict(d) for d in raw_diffs if isinstance(d, dict)] if isinstance(raw_diffs, list) else []
    await _notify_workspace_files_changed(
        websocket,
        run_id,
        [path],
        node_id=node_id,
        path_diffs={path: diffs},
    )


def _extract_llm_text(result: object) -> str:
    if isinstance(result, dict):
        content = result.get("content")
        return str(content).strip() if content else ""
    return str(result).strip()


async def _async_handoff_summarization_task(
    run_id: str,
    websocket: WebSocket,
    workspace_path: str,
    sources: list[str],
    target: str,
    task: str,
    prompt: str,
    file_refs: list[str] | None,
    dispatch_history: list[dict[str, object]] | None,
    lane_transcripts: list[dict[str, object]] | None,
    custom_file_name: str,
    entry_id: str,
    chat_messages: list[dict[str, object]] | None = None,
):
    try:
        from src.interactive_pty_runtime import interactive_pty_manager, configured_cli_binaries
        from src.handoff_summarizer import find_recent_temp_handoff_file, strip_yaml_frontmatter

        HANDOFF_INJECTION_PROMPT = (
            "[System: Please generate a handoff summary file of our current conversation. "
            "Save it to the OS temporary directory as a markdown file starting with 'handoff-'. "
            "You can use your handoff skill or write it directly. "
            "Print the exact path once saved.]"
        )

        agent_handoff_summary = None
        state = _run_states.get(run_id)
        if state:
            lanes = state.get("pty_lanes") or []
            cli_binaries = configured_cli_binaries()
            injected_any = False
            for source_name in sources:
                target_lane = None
                for lane in lanes:
                    if str(lane.get("configured_agent_name") or "").lower() == source_name.lower():
                        target_lane = lane
                        break
                if not target_lane:
                    for lane in lanes:
                        agent_type = str(lane.get("agent_type") or "").lower()
                        clean_type = agent_type.replace("-cli", "")
                        if clean_type == source_name.lower() or source_name.lower() in clean_type:
                            target_lane = lane
                            break
                if target_lane:
                    agent_type = target_lane.get("agent_type")
                    is_cli_agent = (
                        agent_type in ["claude-cli", "opencode-cli", "mimo-cli", "codex-cli"]
                        or source_name.lower() in cli_binaries
                    )
                    if is_cli_agent:
                        lane_id = target_lane.get("lane_id")
                        session_key = f"{run_id}::{lane_id}"
                        session = interactive_pty_manager.get(session_key)
                        if session and session.alive():
                            try:
                                # Ensure we clear any half-typed commands, write prompt, and execute with \r
                                session.write_input("\r")
                                await asyncio.sleep(0.15)
                                session.write_input(HANDOFF_INJECTION_PROMPT)
                                await asyncio.sleep(0.15)
                                session.write_input("\r")
                                injected_any = True
                            except Exception as e:
                                logger.warning("Failed to inject handoff prompt into session %s: %s", session_key, e)

            if injected_any:
                # Poll for the newly generated handoff file (up to 30.0s to accommodate slower LLM thought/write cycles)
                recent_file_path = None
                for _ in range(30):
                    recent_file_path = find_recent_temp_handoff_file(max_age_seconds=45.0)
                    if recent_file_path:
                        break
                    await asyncio.sleep(1.0)

                if recent_file_path:
                    try:
                        from pathlib import Path
                        p = Path(recent_file_path)
                        raw_content = p.read_text(encoding="utf-8", errors="replace")
                        agent_handoff_summary = strip_yaml_frontmatter(raw_content)
                        p.unlink(missing_ok=True)
                    except Exception as exc:
                        logger.warning("Failed to process temp handoff file %s: %s", recent_file_path, exc)

        from src.handoff_writer import write_handoff_markdown
        def do_write():
            return write_handoff_markdown(
                workspace_path,
                sources=sources,
                target=target,
                task=task,
                prompt=prompt,
                file_refs=file_refs,
                dispatch_history=dispatch_history,
                lane_transcripts=lane_transcripts,
                chat_messages=chat_messages,
                agent_handoff_summary=agent_handoff_summary,
                skip_llm_summary=False,
                custom_file_name=custom_file_name,
            )
        
        await asyncio.to_thread(do_write)
        
        state = _run_states.get(run_id)
        if state:
            log = [dict(e) for e in (state.get("dispatch_log") or [])]
            updated = False
            for entry in log:
                if entry.get("id") == entry_id:
                    if entry.get("step_status") == "generating_handoff":
                        entry["step_status"] = "opening_terminal"
                        updated = True
                    break
            if updated:
                from src.terminal_orchestra import transition_handoff_layout
                new_lanes = transition_handoff_layout(state, sources, target)
                patch = {"dispatch_log": log, "pty_lanes": new_lanes}
                state = _merge_patch(state, patch)
                _run_states[run_id] = state
                _commit_run_state(run_id, state)
                try:
                    await _notify_run_state(websocket, run_id, state, patch)
                except Exception as ws_exc:
                    logger.warning("Failed to notify ws in async handoff: %s", ws_exc)
    except Exception as exc:
        logger.exception("Async handoff summarization failed: %s", exc)
        state = _run_states.get(run_id)
        if state:
            log = [dict(e) for e in (state.get("dispatch_log") or [])]
            updated = False
            for entry in log:
                if entry.get("id") == entry_id:
                    if entry.get("step_status") == "generating_handoff":
                        entry["step_status"] = "opening_terminal"
                        updated = True
                    break
            if updated:
                from src.terminal_orchestra import transition_handoff_layout
                new_lanes = transition_handoff_layout(state, sources, target)
                patch = {"dispatch_log": log, "pty_lanes": new_lanes}
                state = _merge_patch(state, patch)
                _run_states[run_id] = state
                _commit_run_state(run_id, state)
                try:
                    await _notify_run_state(websocket, run_id, state, patch)
                except Exception as ws_exc:
                    logger.warning("Failed to notify ws in async handoff error: %s", ws_exc)

