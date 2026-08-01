from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import threading
import uuid
from collections.abc import Awaitable, Callable
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect, HTTPException

from src.release_hardening import api_docs_enabled, debug_api_enabled
from src.sidecar_auth import auth_required, public_http_paths, validate_bearer, validate_token

from src.compiler import WorkflowSession, begin_workflow, resume_workflow
from src.run_history import append_run_record, list_runs, update_run_record, upsert_session
from src.state import ClutchState, initial_state
from src.workflow_storage import resolve_workflow
from src.workflow_validator import WorkflowValidationError, load_and_validate_workflow, validate_workflow
from src.preferences_storage import tr
from src.terminal_logs import TAG_HUMAN, TAG_WORKFLOW, stamp_log_line, tagged

logger = logging.getLogger(__name__)

# D38 Stable Context Boundary — implementation modules (re-exported for main/tests)
from src.chat_messages import (
    _AGENT_AVATARS,
    _chat_message,
    _chat_time,
    _diff_summary_for_seal,
    _estimate_tokens,
    _history_for_llm,
    _merge_files_changed_with_tool_steps,
    _sealed_subtasks,
    _sealed_tool_steps,
    _token_patch,
    _token_patch_turn,
    _verification_report_for_seal,
)
from src.chat_ws_events import (
    _is_terminal_status,
    _is_ws_transport_error,
    _notify_run_state,
    _send_file_changed,
    _send_human_required,
    _send_hybrid_execution_event,
    _send_log_event,
    _send_message_event,
    _send_pty_output,
    _send_pty_session_status,
    _send_run_completed,
    _send_state_patch,
    _send_validation_result,
    _serialize_clutch_state,
    _try_ws_notify,
)
from src.chat_mcp_gates import (
    _is_plan_pause,
    _is_question_pause,
    _mcp_pause_gate_line,
    _mcp_pause_human_prompt,
    _mcp_supervisor_approval_text,
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
    _human_decision_inflight,
    _human_decision_locks,
    _merge_patch,
    _persist_run_log,
    _reasoning_live_patch,
    _release_worktree_bindings,
    _run_sessions,
    _run_states,
    _setup_run_log_forwarder,
    _subtask_live_patch,
    _tool_step_live_patch,
    _worktree_isolation_live_patch,
)
from src.chat_plain import (
    _NullWebSocket,
    _append_terminal_logs,
    _apply_hybrid_plain_chat_rejection,
    _apply_plain_chat_stop,
    _apply_pool_full_queue,
    _async_handoff_summarization_task,
    _compose_agent_system_prompt,
    _extract_llm_text,
    _finish_plain_chat_after_llm,
    _handle_plain_chat,
    _handle_plain_chat_mcp_decision,
    _hybrid_execution_entry,
    _interrupt_plain_chat_shell,
    _llm_chat_reply,
    _maybe_notify_step_file_diff,
    _merge_hybrid_executions,
    _notify_workspace_files_changed,
    _path_diffs_from_tool_steps,
    _persist_plain_chat_user_message,
    _publish_diff_summary,
    _publish_verification_report,
    _recover_stuck_plain_chat,
    _refresh_pool_queued_run_states,
    _resume_pool_queued_turn,
    _uses_configured_llm,
)
from src.chat_workflow import (
    _apply_human_decision,
    _apply_human_decision_locked,
    _apply_workflow_refining_pause,
    _apply_workflow_step_patch,
    _commit_flow_refine_and_continue,
    _emit_workflow_graph_tail,
    _handle_flow_refine_message,
    _handle_workflow_chat_message,
    _interrupt_workflow_run,
    _merge_graph_resume,
    _prepare_workflow_refine_state,
    _run_workflow,
    _validation_http_error,
)



async def _lifespan(app: FastAPI):
    from src.plain_chat_pool_queue import set_event_loop, set_refresh_handler, set_resume_handler
    from src.shell_session import get_shell_session_manager

    loop = asyncio.get_running_loop()
    set_event_loop(loop)
    set_resume_handler(_resume_pool_queued_turn)
    set_refresh_handler(_refresh_pool_queued_run_states)

    from src.interactive_pty_runtime import interactive_pty_manager
    from src.plain_chat_pool_queue import get_plain_chat_ws

    async def _forward_interactive_pty_output(session_key: str, chunk: str) -> None:
        from src.terminal_orchestra import parse_pty_session_key

        parent_run_id, lane_id = parse_pty_session_key(session_key)
        websocket = get_plain_chat_ws(parent_run_id)
        if websocket is not None:
            await _send_pty_output(websocket, parent_run_id, chunk, lane_id=lane_id)

    interactive_pty_manager.set_event_loop(loop)
    interactive_pty_manager.set_output_handler(_forward_interactive_pty_output)

    async def _sweep_shell_sessions() -> None:
        manager = get_shell_session_manager()
        while True:
            await asyncio.sleep(60)
            try:
                terminated = await asyncio.to_thread(manager.sweep_idle)
                for run_id in terminated:
                    logger.info("shell_session idle sweep terminated run_id=%s", run_id)
                from src.session_snapshot import prune_stale_snapshots

                pruned = await asyncio.to_thread(prune_stale_snapshots)
                for run_id in pruned:
                    logger.info("shell_snapshot pruned run_id=%s", run_id)
            except Exception:
                logger.exception("shell_session sweep failed")

    task = asyncio.create_task(_sweep_shell_sessions())

    async def _prefetch_cc_switch_bundle() -> None:
        try:
            from src.cli_agent_config import prefetch_cc_switch_cli_bundle, resolve_cc_switch_cli_path

            if resolve_cc_switch_cli_path():
                return
            await asyncio.to_thread(prefetch_cc_switch_cli_bundle)
        except Exception:
            logger.debug("cc-switch bundle prefetch skipped", exc_info=True)

    asyncio.create_task(_prefetch_cc_switch_bundle())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

_docs_disabled = not api_docs_enabled()

def _skills_registry_payload(*, rescan: bool = True) -> dict[str, Any]:
    from src.skills_scanner import scan_mounted_directories
    from src.skills_storage import sync_workspace_skill_mounts, load_registry, save_registry
    from src.workspace import get_workspace

    workspace = get_workspace()
    workspace_path = workspace.get("workspace_path") if workspace else None
    sync_workspace_skill_mounts(workspace_path=workspace_path)

    data = load_registry()
    if rescan:
        data["skills"] = scan_mounted_directories(
            data["mounted_directories"],
            existing_skills=data["skills"],
        )
        save_registry(
            mounted_directories=data["mounted_directories"],
            skills=data["skills"],
        )
    return data

def _session_workspace_fields() -> dict[str, str]:
    from src.workspace import get_workspace

    workspace = get_workspace()
    if workspace is None:
        return {}
    return {
        "workspace_id": workspace["id"],
        "workspace_name": workspace["name"],
    }

def _usage_fields_from_state(state: ClutchState) -> dict[str, int]:
    """D22 — persist session usage on history records when a run is touched."""
    stats = state.get("run_stats") or {}
    tool_steps = stats.get("tool_steps")
    if tool_steps is None:
        counted = 0
        for message in state.get("messages") or []:
            steps = message.get("toolSteps") or message.get("tool_steps") or []
            if isinstance(steps, list):
                counted += len(steps)
        tool_steps = counted
    tokens = int(state.get("session_tokens") or stats.get("session_tokens") or 0)
    return {
        "session_tokens": max(0, tokens),
        "tool_steps": max(0, int(tool_steps or 0)),
    }


def _touch_session(
    run_id: str,
    *,
    title: str | None = None,
    workflow_id: str | None = None,
    status: str | None = None,
) -> None:
    from src.run_history import list_runs, upsert_session
    from src.session_content import session_has_persistable_content

    fields = _session_workspace_fields()
    if not fields:
        return
    state = _get_or_create_run(run_id)
    existing = next((record for record in list_runs() if record.get("run_id") == run_id), None)
    if not existing and not session_has_persistable_content(state):
        return
    patch: dict[str, Any] = {**fields, "run_id": run_id, "updated_at": _iso_timestamp()}
    if title is not None:
        patch["title"] = title[:80]
    if workflow_id is not None:
        patch["workflow_id"] = workflow_id
    if status is not None:
        patch["status"] = status
    patch.update(_usage_fields_from_state(state))
    if existing:
        upsert_session({**existing, **patch})
    else:
        upsert_session(
            {
                **patch,
                "title": patch.get("title", "New session"),
                "workflow_id": patch.get("workflow_id", ""),
                "status": patch.get("status", "idle"),
                "started_at": _iso_timestamp(),
            }
        )

def _iso_timestamp() -> str:
    return datetime.now(UTC).isoformat()

def _apply_delete_message(
    state: ClutchState,
    message_id: str,
) -> tuple[ClutchState, dict[str, Any]]:
    trimmed_id = message_id.strip()
    if not trimmed_id:
        return state, {}
    messages = [
        message
        for message in state["messages"]
        if str(message.get("id", "")) != trimmed_id
    ]
    if len(messages) == len(state["messages"]):
        return state, {}
    patch: dict[str, Any] = {"messages": messages}
    hybrid = dict(state.get("hybrid_executions") or {})
    if trimmed_id in hybrid:
        del hybrid[trimmed_id]
        patch["hybrid_executions"] = hybrid
    state = _merge_patch(state, patch)
    return state, patch

async def ws_run(websocket: WebSocket, run_id: str) -> None:
    if auth_required():
        ws_token = websocket.query_params.get("token")
        if not validate_token(ws_token):
            await websocket.close(code=4401, reason="Unauthorized")
            return
    await websocket.accept()
    from src.plain_chat_pool_queue import register_plain_chat_ws, unregister_plain_chat_ws
    from src.run_state_store import sync_run_state_from_disk

    register_plain_chat_ws(run_id, websocket)
    from src.bg_jobs import register_bg_jobs_notifier, unregister_bg_jobs_notifier

    state = sync_run_state_from_disk(run_id, _get_or_create_run(run_id))
    _run_states[run_id] = state
    _setup_run_log_forwarder(run_id)
    from src.run_log_forwarder import get_forwarder

    forwarder = get_forwarder(run_id)
    loop = asyncio.get_running_loop()

    def _bg_jobs_sync_notifier(
        rid: str,
        jobs: list[dict[str, Any]],
        finished: dict[str, Any] | None,
    ) -> None:
        if rid != run_id:
            return
        asyncio.run_coroutine_threadsafe(
            _apply_bg_jobs_update(websocket, run_id, jobs, finished),
            loop,
        )

    register_bg_jobs_notifier(run_id, _bg_jobs_sync_notifier)

    def _foreground_shell_sync_notifier(
        rid: str,
        payload: dict[str, Any] | None,
    ) -> None:
        if rid != run_id:
            return
        asyncio.run_coroutine_threadsafe(
            _apply_foreground_shell_update(websocket, run_id, payload),
            loop,
        )

    from src.foreground_shell import register_foreground_notifier, unregister_foreground_notifier

    register_foreground_notifier(run_id, _foreground_shell_sync_notifier)

    async def ws_log_emit(line: str, node_id: str) -> None:
        await _send_log_event(websocket, run_id, line, node_id=node_id)
        current = _get_or_create_run(run_id)
        await _notify_run_state(
            websocket,
            run_id,
            current,
            {"terminal_logs": list(current["terminal_logs"])},
        )

    async def ws_state_patch_emit(patch: dict[str, Any], status: str) -> None:
        current = _get_or_create_run(run_id)
        await _notify_run_state(websocket, run_id, current, patch)

    async def ws_message_emit(message: dict[str, Any], node_id: str) -> None:
        await _send_message_event(websocket, run_id, message, node_id)

    async def ws_hybrid_execution_emit(
        message_id: str,
        raw_output: str | None,
        output_events: list[dict[str, Any]] | None,
    ) -> None:
        await _send_hybrid_execution_event(
            websocket,
            run_id,
            message_id=message_id,
            raw_output=raw_output,
            output_events=output_events,
        )

    forwarder.attach_ws(
        loop,
        ws_log_emit,
        ws_state_patch_emit,
        ws_message_emit,
        ws_hybrid_execution_emit,
    )

    logger.info(
        "WebSocket connected",
        extra={
            "run_id": run_id,
            "node_id": state["active_node_id"],
            "source": "orchestrator",
            "level": "info",
            "message": "client connected",
            "timestamp": _iso_timestamp(),
        },
    )

    await _send_state_patch(websocket, run_id, dict(state))
    if state["status"] == "awaiting_human":
        await _send_validation_result(
            websocket,
            run_id,
            node_id=state["active_node_id"],
            passed=False,
            message=tr("Evaluator checks failed, waiting for human approval.", "Evaluator 检查未通过，等待人工审批。"),
        )
        await _send_human_required(
            websocket,
            run_id,
            node_id=state["active_node_id"],
            prompt=tr("Checks failed, waiting for human confirmation.", "检查未通过，等待人工确认。"),
        )
    if _is_terminal_status(state["status"]):
        await _send_run_completed(websocket, run_id, state)

    ws_loop = asyncio.get_running_loop()
    from src.hybrid_concurrency import plain_chat_turn_in_progress
    from src.runtime_config import runtime_mode

    plain_chat_task: asyncio.Task[ClutchState] | None = None
    plain_chat_queue: list[dict[str, str | None]] = []

    async def _start_plain_chat_turn(
        text: str,
        agent_id: str | None,
        session_model_id: str | None,
        client_message_id: str | None = None,
    ) -> None:
        nonlocal plain_chat_task, state
        if plain_chat_task is not None and not plain_chat_task.done():
            return
        state = await _persist_plain_chat_user_message(
            websocket,
            run_id,
            state,
            text,
            agent_id=agent_id,
            client_message_id=client_message_id,
        )
        plain_chat_task = asyncio.create_task(
            _handle_plain_chat(
                websocket,
                run_id,
                state,
                text,
                agent_id=agent_id,
                session_model_id=session_model_id,
                client_message_id=client_message_id,
                user_persisted=True,
            )
        )
        plain_chat_task.add_done_callback(_plain_chat_done)

    async def _enqueue_plain_chat(
        text: str,
        agent_id: str | None,
        session_model_id: str | None,
        client_message_id: str | None = None,
    ) -> None:
        nonlocal state
        plain_chat_queue.append(
            {
                "text": text,
                "agent_id": agent_id,
                "session_model_id": session_model_id,
                "client_message_id": client_message_id,
            }
        )
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
        log_line = stamp_log_line(
            tagged(
                TAG_WORKFLOW,
                f"[HYBRID] queued plain chat ({len(plain_chat_queue)} pending)",
            )
        )
        logs = list(state["terminal_logs"]) + [log_line]
        patch: dict[str, Any] = {
            "messages": messages,
            "terminal_logs": logs,
            "shell_session_status": "ready",
            "status": "running",
            "awaiting_continue": False,
        }
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        if user_message_added:
            _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])
        if user_message_added:
            await _send_message_event(websocket, run_id, user_message, "")
        await _send_log_event(websocket, run_id, log_line, node_id="")
        await _notify_run_state(websocket, run_id, state, patch)

    async def _drain_plain_chat_queue() -> None:
        if not plain_chat_queue or (plain_chat_task is not None and not plain_chat_task.done()):
            return
        if plain_chat_turn_in_progress(
            plain_chat_task_done=True,
            state=state,
            hybrid_runtime=runtime_mode() == "hybrid",
        ):
            ws_loop.call_later(0.5, lambda: ws_loop.create_task(_drain_plain_chat_queue()))
            return
        item = plain_chat_queue.pop(0)
        await _start_plain_chat_turn(
            str(item["text"]),
            item.get("agent_id"),
            item.get("session_model_id"),
            item.get("client_message_id"),
        )

    def _plain_chat_done(task: asyncio.Task[ClutchState]) -> None:
        nonlocal plain_chat_task, state
        if plain_chat_task is not task:
            return
        plain_chat_task = None
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.exception("plain chat task failed run_id=%s", run_id, exc_info=exc)
            loop = ws_loop
            loop.create_task(_recover_stuck_plain_chat(run_id))
            return
        try:
            state = task.result()
        except Exception:
            logger.exception("plain chat task result failed run_id=%s", run_id)
        loop = ws_loop
        loop.create_task(_drain_plain_chat_queue())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"raw": raw}

            logger.info(
                "WebSocket message received",
                extra={
                    "run_id": run_id,
                    "node_id": state["active_node_id"],
                    "source": "orchestrator",
                    "level": "info",
                    "message": raw,
                    "timestamp": _iso_timestamp(),
                },
            )

            patch: dict[str, Any] = {}
            if isinstance(payload, dict) and payload.get("text") and not payload.get("action"):
                text = str(payload["text"])
                agent_id = str(payload.get("agent_id", "")).strip() or None
                session_model_id = str(payload.get("model_id", "")).strip() or None
                client_message_id = str(payload.get("client_message_id", "")).strip() or None
                if state.get("workflow_id"):
                    from src.flow_refine import is_workflow_refine_eligible, refine_triggered_by_message

                    status = str(state.get("status") or "")
                    session = _run_sessions.get(run_id)
                    workflow = session.workflow if session else None
                    if not workflow:
                        try:
                            workflow, _ = resolve_workflow(str(state["workflow_id"]))
                        except Exception:
                            workflow = None
                    if is_workflow_refine_eligible(state) and refine_triggered_by_message(
                        text,
                        status=status,
                        workflow=workflow,
                    ):
                        state = await _handle_flow_refine_message(
                            websocket, run_id, state, text, agent_id
                        )
                    elif status == "refining":
                        state = await _handle_flow_refine_message(
                            websocket, run_id, state, text, agent_id
                        )
                    else:
                        state = await _handle_workflow_chat_message(
                            websocket, run_id, state, text, agent_id
                        )
                elif plain_chat_turn_in_progress(
                    plain_chat_task_done=plain_chat_task is None or plain_chat_task.done(),
                    state=state,
                    hybrid_runtime=runtime_mode() == "hybrid",
                ):
                    await _enqueue_plain_chat(text, agent_id, session_model_id, client_message_id)
                else:
                    await _start_plain_chat_turn(text, agent_id, session_model_id, client_message_id)
            elif isinstance(payload, dict) and payload.get("action") == "human_decision":
                decision = str(payload.get("decision", "approve"))
                from src.mcp_pending import get_pending

                if get_pending(run_id) and not state.get("workflow_id"):
                    instructions = str(payload.get("instructions", ""))
                    state = await _handle_plain_chat_mcp_decision(
                        websocket, run_id, state, decision, instructions
                    )
                else:
                    instructions = str(payload.get("instructions", ""))
                    node_id = state["active_node_id"]

                    state, patch, supervisor_message, log_line = await asyncio.to_thread(
                        _apply_human_decision,
                        run_id,
                        decision,
                        instructions,
                    )

                    await _send_message_event(websocket, run_id, supervisor_message, node_id)
                    await _notify_run_state(websocket, run_id, state, patch)
                    if state["status"] == "awaiting_human":
                        await _send_validation_result(
                            websocket,
                            run_id,
                            node_id=state["active_node_id"],
                            passed=False,
                            message=tr("Evaluator checks failed, waiting for human approval.", "Evaluator 检查未通过，等待人工审批。"),
                        )
                        await _send_human_required(
                            websocket,
                            run_id,
                            node_id=state["active_node_id"],
                            prompt=tr("Checks failed, waiting for human confirmation.", "检查未通过，等待人工确认。"),
                        )
            elif isinstance(payload, dict) and payload.get("action") == "kill_bg_job":
                job_id = str(payload.get("job_id") or "").strip()
                if job_id:
                    from src.bg_jobs import kill_job

                    await asyncio.to_thread(kill_job, run_id, job_id)
            elif isinstance(payload, dict) and payload.get("action") == "move_fg_to_background":
                from src.foreground_shell import transfer_to_background

                job = await asyncio.to_thread(transfer_to_background, run_id)
                if job:
                    notice = _chat_message(
                        "Supervisor",
                        tr(
                            f"Moved foreground command to background (job {job.get('id', '')}).",
                            f"前台命令已转入后台（任务 {job.get('id', '')}）。",
                        ),
                    )
                    patch = {"messages": list(state["messages"]) + [notice]}
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    await _send_message_event(websocket, run_id, notice, "")
                    await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "enable_worktree":
                from src.worktree_isolation import create_worktree, describe_worktree
                from src.workspace import require_workspace

                try:
                    root = await asyncio.to_thread(require_workspace)
                    info = await asyncio.to_thread(create_worktree, root)
                    wt_payload = describe_worktree(info, root)
                    patch = {"worktree_isolation": wt_payload}
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    notice = _chat_message(
                        "Supervisor",
                        tr(
                            f"Worktree isolation enabled at {wt_payload.get('path', '')}.",
                            f"已启用 worktree 隔离：{wt_payload.get('path', '')}。",
                        ),
                    )
                    patch = {**patch, "messages": list(state["messages"]) + [notice]}
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    await _send_message_event(websocket, run_id, notice, "")
                    await _notify_run_state(websocket, run_id, state, patch)
                except Exception as exc:
                    notice = _chat_message(
                        "Supervisor",
                        tr(f"Worktree enable failed: {exc}", f"启用 worktree 失败：{exc}"),
                    )
                    patch = {"messages": list(state["messages"]) + [notice]}
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    await _send_message_event(websocket, run_id, notice, "")
                    await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "merge_worktree":
                from src.worktree_isolation import merge_worktree
                from src.workspace import require_workspace

                wt_info = state.get("worktree_isolation")
                wt_id = str((wt_info or {}).get("id") or payload.get("wt_id") or "").strip()
                if wt_id:
                    try:
                        root = await asyncio.to_thread(require_workspace)
                        summary = await asyncio.to_thread(merge_worktree, root, wt_id)
                        notice = _chat_message(
                            "Supervisor",
                            tr(f"Merged worktree {wt_id}: {summary}", f"已合并 worktree {wt_id}：{summary}"),
                        )
                        patch = {
                            "worktree_isolation": None,
                            "messages": list(state["messages"]) + [notice],
                        }
                        state = _merge_patch(state, patch)
                        _commit_run_state(run_id, state)
                        await _send_message_event(websocket, run_id, notice, "")
                        await _notify_run_state(websocket, run_id, state, patch)
                    except Exception as exc:
                        notice = _chat_message(
                            "Supervisor",
                            tr(f"Worktree merge failed: {exc}", f"合并 worktree 失败：{exc}"),
                        )
                        patch = {"messages": list(state["messages"]) + [notice]}
                        state = _merge_patch(state, patch)
                        _commit_run_state(run_id, state)
                        await _send_message_event(websocket, run_id, notice, "")
                        await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "discard_worktree":
                from src.worktree_isolation import discard_worktree
                from src.workspace import require_workspace

                wt_info = state.get("worktree_isolation")
                wt_id = str((wt_info or {}).get("id") or payload.get("wt_id") or "").strip()
                if wt_id:
                    try:
                        root = await asyncio.to_thread(require_workspace)
                        await asyncio.to_thread(discard_worktree, root, wt_id)
                        notice = _chat_message(
                            "Supervisor",
                            tr(
                                f"Discarded worktree {wt_id}; main workspace unchanged.",
                                f"已丢弃 worktree {wt_id}；主工作区保持干净。",
                            ),
                        )
                        patch = {
                            "worktree_isolation": None,
                            "messages": list(state["messages"]) + [notice],
                        }
                        state = _merge_patch(state, patch)
                        _commit_run_state(run_id, state)
                        await _send_message_event(websocket, run_id, notice, "")
                        await _notify_run_state(websocket, run_id, state, patch)
                    except Exception as exc:
                        notice = _chat_message(
                            "Supervisor",
                            tr(f"Worktree discard failed: {exc}", f"丢弃 worktree 失败：{exc}"),
                        )
                        patch = {"messages": list(state["messages"]) + [notice]}
                        state = _merge_patch(state, patch)
                        _commit_run_state(run_id, state)
                        await _send_message_event(websocket, run_id, notice, "")
                        await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "clear_approvals":
                # D13: clear session-remembered MCP tool approvals.
                from src.mcp_pending import clear_mcp_approval_state

                clear_mcp_approval_state(run_id)
                notice = _chat_message(
                    "Supervisor",
                    tr(
                        "Cleared remembered tool approvals for this chat.",
                        "已清除本会话记住的工具批准。",
                    ),
                )
                patch = {"messages": list(state["messages"]) + [notice]}
                state = _merge_patch(state, patch)
                _commit_run_state(run_id, state)
                await _send_message_event(websocket, run_id, notice, "")
                await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "continue_run":
                # D9: resume after Stop / loop fuse — enqueue a continue prompt.
                if state.get("workflow_id"):
                    pass
                elif state.get("status") == "running":
                    pass
                else:
                    from src.run_control import continue_user_prompt

                    resume_text = tr(
                        continue_user_prompt(lang="en"),
                        continue_user_prompt(lang="zh"),
                    )
                    clear_patch = {"awaiting_continue": False}
                    state = _merge_patch(state, clear_patch)
                    _commit_run_state(run_id, state)
                    await _notify_run_state(websocket, run_id, state, clear_patch)
                    if plain_chat_task is not None and not plain_chat_task.done():
                        await _enqueue_plain_chat(resume_text, None, None, None)
                    else:
                        await _start_plain_chat_turn(resume_text, None, None, None)
            elif isinstance(payload, dict) and payload.get("action") == "stop_run":
                if not state.get("workflow_id"):
                    plain_chat_queue.clear()
                    await asyncio.to_thread(_interrupt_plain_chat_shell, run_id)
                    if plain_chat_task is not None and not plain_chat_task.done():
                        plain_chat_task.cancel()
                    plain_chat_task = None
                    state = await _apply_plain_chat_stop(websocket, run_id, state)
                else:
                    await asyncio.to_thread(_interrupt_workflow_run, run_id)
                    session = _run_sessions.get(run_id)
                    if session:
                        state = _apply_workflow_refining_pause(run_id, session, prepend_log=False)
                        await _send_log_event(
                            websocket,
                            run_id,
                            state["terminal_logs"][-1],
                            node_id=state.get("active_node_id", ""),
                        )
                        await _notify_run_state(
                            websocket,
                            run_id,
                            state,
                            {
                                "status": "refining",
                                "refining_node_id": state.get("refining_node_id", ""),
                                "terminal_logs": state["terminal_logs"],
                            },
                        )
                    else:
                        logs = list(state["terminal_logs"])
                        log_line = stamp_log_line(
                            tagged(TAG_WORKFLOW, "Run stopped by supervisor — entering refine mode.")
                        )
                        logs.append(log_line)
                        patch = {
                            "status": "refining",
                            "refining_node_id": state.get("active_node_id", ""),
                            "terminal_logs": logs,
                        }
                        state = _merge_patch(state, patch)
                        _commit_run_state(run_id, state)
                        _touch_session(run_id, status="refining")
                        await _send_log_event(
                            websocket, run_id, log_line, node_id=state["active_node_id"]
                        )
                        await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "pty_attach":
                from src.interactive_pty_runtime import InteractivePtyError, interactive_pty_manager
                from src.terminal_orchestra import (
                    _ensure_lane_cli_session_id,
                    ensure_primary_lane,
                    normalize_lane_id,
                    pty_session_key,
                )
                from src.workspace import active_workspace_issue, get_workspace

                cli_tool = str(payload.get("cli_tool", "claude-cli")).strip() or "claude-cli"
                lane_id = normalize_lane_id(str(payload.get("lane_id", "primary")), state)
                workspace_issue = active_workspace_issue()
                workspace = get_workspace()
                workspace_path = str(workspace.get("workspace_path", "")).strip() if workspace else ""
                orch_patch = ensure_primary_lane(state, cli_tool=cli_tool)
                if orch_patch:
                    state = _merge_patch(state, orch_patch)
                    _commit_run_state(run_id, state)
                    await _notify_run_state(websocket, run_id, state, orch_patch)
                    lane_id = normalize_lane_id(lane_id, state)
                lane_cli_session_id: str | None = None
                ollama_model: str | None = None
                configured_agent_id = str(payload.get("configured_agent_id") or "").strip()
                if configured_agent_id:
                    from src.agent_storage import get_agent_by_id

                    agent = get_agent_by_id(configured_agent_id)
                    if agent:
                        tag = str(agent.get("ollamaModel", "")).strip()
                        if tag:
                            ollama_model = tag
                for lane in state.get("pty_lanes") or []:
                    if isinstance(lane, dict) and str(lane.get("lane_id") or "") == lane_id:
                        lane_cli_session_id = _ensure_lane_cli_session_id(lane)
                        _commit_run_state(run_id, state)
                        if cli_tool in {"ollama-cli", "ollama"} and not ollama_model:
                            lane_cfg_id = str(lane.get("configured_agent_id") or "").strip()
                            if lane_cfg_id:
                                from src.agent_storage import get_agent_by_id

                                agent = get_agent_by_id(lane_cfg_id)
                                if agent:
                                    tag = str(agent.get("ollamaModel", "")).strip()
                                    if tag:
                                        ollama_model = tag
                        break
                session_key = pty_session_key(run_id, lane_id)
                if workspace_issue or not workspace_path:
                    await _send_pty_session_status(
                        websocket,
                        run_id,
                        "blocked",
                        detail=workspace_issue or "No workspace authorized for interactive PTY",
                        lane_id=lane_id,
                    )
                else:
                    try:
                        session = await asyncio.to_thread(
                            interactive_pty_manager.attach,
                            session_key,
                            workspace_path=workspace_path,
                            cli_tool=cli_tool,
                            cli_session_id=lane_cli_session_id,
                            ollama_model=ollama_model,
                        )
                        await _send_pty_session_status(
                            websocket,
                            run_id,
                            session.status.value,
                            detail="Interactive PTY attached",
                            lane_id=lane_id,
                        )
                    except (InteractivePtyError, OSError) as exc:
                        await _send_pty_session_status(
                            websocket,
                            run_id,
                            "blocked",
                            detail=str(exc),
                            lane_id=lane_id,
                        )
                    except Exception as exc:
                        await _send_pty_session_status(
                            websocket,
                            run_id,
                            "blocked",
                            detail=str(exc),
                            lane_id=lane_id,
                        )
            elif isinstance(payload, dict) and payload.get("action") == "pty_detach":
                from src.interactive_pty_runtime import interactive_pty_manager
                from src.terminal_orchestra import normalize_lane_id, pty_session_key

                lane_id = normalize_lane_id(str(payload.get("lane_id", "primary")), state)
                await asyncio.to_thread(interactive_pty_manager.detach, pty_session_key(run_id, lane_id))
                await _send_pty_session_status(
                    websocket,
                    run_id,
                    "detached",
                    detail="Interactive PTY detached",
                    lane_id=lane_id,
                )
            elif isinstance(payload, dict) and payload.get("action") == "pty_input":
                from src.interactive_pty_runtime import InteractivePtyError, interactive_pty_manager
                from src.terminal_orchestra import normalize_lane_id, pty_session_key

                data = str(payload.get("data", ""))
                lane_id = normalize_lane_id(str(payload.get("lane_id", "primary")), state)
                if data:
                    try:
                        await asyncio.to_thread(
                            interactive_pty_manager.write_input,
                            pty_session_key(run_id, lane_id),
                            data,
                        )
                    except InteractivePtyError as exc:
                        await _send_pty_session_status(
                            websocket,
                            run_id,
                            "blocked",
                            detail=str(exc),
                            lane_id=lane_id,
                        )
            elif isinstance(payload, dict) and payload.get("action") == "pty_resize":
                from src.interactive_pty_runtime import interactive_pty_manager
                from src.terminal_orchestra import normalize_lane_id, pty_session_key

                cols = int(payload.get("cols", 80))
                rows = int(payload.get("rows", 24))
                lane_id = normalize_lane_id(str(payload.get("lane_id", "primary")), state)
                await asyncio.to_thread(
                    interactive_pty_manager.resize,
                    pty_session_key(run_id, lane_id),
                    cols,
                    rows,
                )
            elif isinstance(payload, dict) and payload.get("action") == "dispatch_preview":
                from src.terminal_orchestra import preview_dispatch, serialize_preview

                text = str(payload.get("text", "")).strip()
                preview = preview_dispatch(state, text)
                if preview is None:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "dispatch_preview",
                                "data": {
                                    "run_id": run_id,
                                    "ok": False,
                                    "error": "输入需包含 @目标 Agent",
                                },
                            }
                        )
                    )
                else:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "dispatch_preview",
                                "data": {
                                    "run_id": run_id,
                                    "ok": True,
                                    "preview": serialize_preview(preview),
                                },
                            }
                        )
                    )
            elif isinstance(payload, dict) and payload.get("action") == "dispatch_confirm":
                from src.terminal_orchestra import confirm_dispatch, preview_dispatch, serialize_preview
                from src.workspace import get_workspace

                text = str(payload.get("text", "")).strip()
                active_chips = payload.get("active_sources")
                chip_list = (
                    [str(x) for x in active_chips]
                    if isinstance(active_chips, list)
                    else None
                )
                preview = preview_dispatch(state, text)
                if preview is None:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "dispatch_error",
                                "data": {"run_id": run_id, "error": "无法解析派发"},
                            }
                        )
                    )
                else:
                    workspace = get_workspace()
                    workspace_path = (
                        str(workspace.get("workspace_path", "")).strip() if workspace else ""
                    )
                    is_handoff = preview.dispatch_mode == "handoff"
                    patch = confirm_dispatch(
                        state,
                        preview=preview,
                        prompt=text,
                        workspace_path=workspace_path or ".",
                        active_chips=chip_list,
                        target_configured_agent_id=str(
                            payload.get("target_configured_agent_id") or ""
                        ),
                        target_configured_agent_name=str(
                            payload.get("target_configured_agent_name") or ""
                        ),
                        lane_transcripts=(
                            payload.get("lane_transcripts")
                            if isinstance(payload.get("lane_transcripts"), list)
                            else None
                        ),
                        skip_llm_summary=is_handoff,
                    )
                    sessions_to_close = patch.pop("pty_sessions_to_close", [])
                    for session_key in sessions_to_close:
                        await asyncio.to_thread(interactive_pty_manager.close, session_key)
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])
                    await _notify_run_state(websocket, run_id, state, patch)

                    if is_handoff:
                        dispatch_log = patch.get("dispatch_log", [])
                        added_entry = dispatch_log[-1] if dispatch_log else None
                        if added_entry:
                            entry_id = added_entry["id"]
                            custom_file_name = added_entry["handoff_file"]
                            asyncio.create_task(
                                _async_handoff_summarization_task(
                                    run_id=run_id,
                                    websocket=websocket,
                                    workspace_path=workspace_path or ".",
                                    sources=list(chip_list if chip_list is not None else preview.sources),
                                    target=preview.target,
                                    task=preview.task,
                                    prompt=text,
                                    file_refs=preview.file_refs,
                                    dispatch_history=list(state.get("dispatch_log") or [])[:-1],
                                    lane_transcripts=payload.get("lane_transcripts"),
                                    custom_file_name=custom_file_name,
                                    entry_id=entry_id,
                                    chat_messages=list(state.get("messages") or []),
                                )
                            )
                    if sessions_to_close:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "event": "pty_sessions_closed",
                                    "data": {"run_id": run_id, "mode": "dispatch"},
                                }
                            )
                        )
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "dispatch_confirmed",
                                "data": {
                                    "run_id": run_id,
                                    "preview": serialize_preview(preview),
                                },
                            }
                        )
                    )
            elif isinstance(payload, dict) and payload.get("action") == "lane_focus":
                from src.terminal_orchestra import patch_lane_focus

                lane_id = str(payload.get("lane_id", "")).strip()
                if lane_id:
                    patch = patch_lane_focus(state, lane_id)
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "lane_collapse":
                from src.terminal_orchestra import patch_lane_collapse

                lane_id = str(payload.get("lane_id", "")).strip()
                collapsed = bool(payload.get("collapsed", True))
                if lane_id:
                    patch = patch_lane_collapse(state, lane_id, collapsed=collapsed)
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "lane_complete":
                from src.terminal_orchestra import patch_lane_complete

                lane_id = str(payload.get("lane_id", "")).strip()
                if lane_id:
                    patch = patch_lane_complete(state, lane_id)
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "pty_session_stats":
                from src.interactive_pty_runtime import interactive_pty_manager

                sessions = interactive_pty_manager.list_alive_for_run(run_id, include_system=True)
                await websocket.send_text(
                    json.dumps(
                        {
                            "event": "pty_session_stats",
                            "data": {
                                "run_id": run_id,
                                "total": len(sessions),
                                "sessions": sessions,
                            },
                        }
                    )
                )
            elif isinstance(payload, dict) and payload.get("action") == "pty_close_all":
                from src.interactive_pty_runtime import interactive_pty_manager
                from src.terminal_orchestra import patch_close_terminal_lanes

                patch = patch_close_terminal_lanes(state, keep_lane_id=None)
                for session_key in patch.pop("pty_sessions_to_close", []):
                    await asyncio.to_thread(interactive_pty_manager.close, session_key)
                interactive_pty_manager.close_for_run(run_id)
                state = _merge_patch(state, patch)
                _commit_run_state(run_id, state)
                await _notify_run_state(websocket, run_id, state, patch)
                await websocket.send_text(
                    json.dumps(
                        {
                            "event": "pty_sessions_closed",
                            "data": {"run_id": run_id, "mode": "all"},
                        }
                    )
                )
            elif isinstance(payload, dict) and payload.get("action") == "pty_close_others":
                from src.interactive_pty_runtime import interactive_pty_manager

                keep_raw = payload.get("keep_lane_ids")
                keep_lane_ids: list[str] = []
                if isinstance(keep_raw, list):
                    keep_lane_ids = [str(item).strip() for item in keep_raw if str(item).strip()]
                else:
                    lane_id = str(payload.get("lane_id", "")).strip()
                    if lane_id:
                        keep_lane_ids = [lane_id]
                interactive_pty_manager.close_for_run(run_id, keep_lane_ids=keep_lane_ids)
                await websocket.send_text(
                    json.dumps(
                        {
                            "event": "pty_sessions_closed",
                            "data": {
                                "run_id": run_id,
                                "mode": "others",
                                "keep_lane_ids": keep_lane_ids,
                            },
                        }
                    )
                )
            elif isinstance(payload, dict) and payload.get("action") == "pty_inject_ack":
                patch = {"pending_pty_inject": None}
                log = list(state.get("dispatch_log") or [])
                if log:
                    last_entry = log[-1]
                    if last_entry.get("step_status") and last_entry["step_status"] != "done":
                        last_entry["step_status"] = "done"
                        patch["dispatch_log"] = log
                state = _merge_patch(state, patch)
                _commit_run_state(run_id, state)
                await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "delete_message":
                message_id = str(payload.get("message_id", "")).strip()
                if message_id:
                    state, patch = _apply_delete_message(state, message_id)
                    if patch:
                        _commit_run_state(run_id, state)
                        await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "clear_workflow":
                state = _merge_patch(state, {"workflow_id": ""})
                _commit_run_state(run_id, state)
                _touch_session(run_id, workflow_id="")
                if run_id in _run_sessions:
                    del _run_sessions[run_id]
                await _notify_run_state(websocket, run_id, state, {"workflow_id": ""})
            else:
                unknown = _chat_message(
                    "Orchestrator",
                    tr(f"Unrecognized WebSocket payload: {payload!r}", f"未识别的 WebSocket 载荷：{payload!r}"),
                )
                await _send_message_event(
                    websocket, run_id, unknown, state["active_node_id"]
                )

    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected",
            extra={
                "run_id": run_id,
                "node_id": state["active_node_id"],
                "source": "orchestrator",
                "level": "info",
                "message": "client disconnected",
                "timestamp": _iso_timestamp(),
            },
        )
    finally:
        unregister_plain_chat_ws(run_id)
        unregister_bg_jobs_notifier(run_id)
        unregister_foreground_notifier(run_id)
        forwarder.detach_ws()

