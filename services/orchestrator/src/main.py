"""Clutch orchestration sidecar — M0 skeleton with ClutchState projection."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.release_hardening import api_docs_enabled
from src.sidecar_auth import auth_required, public_http_paths, validate_bearer, validate_token

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from src.plain_chat_pool_queue import set_event_loop, set_refresh_handler, set_resume_handler
    from src.chat_runner import _resume_pool_queued_turn, _refresh_pool_queued_run_states

    loop = asyncio.get_running_loop()
    set_event_loop(loop)
    set_resume_handler(_resume_pool_queued_turn)
    set_refresh_handler(_refresh_pool_queued_run_states)

    from src.interactive_pty_runtime import interactive_pty_manager
    from src.chat_runner import _send_pty_output

    async def _forward_interactive_pty_output(session_key: str, chunk: str) -> None:
        from src.terminal_orchestra import parse_pty_session_key

        parent_run_id, lane_id = parse_pty_session_key(session_key)
        from src.plain_chat_pool_queue import get_plain_chat_ws
        websocket = get_plain_chat_ws(parent_run_id)
        if websocket is not None:
            await _send_pty_output(websocket, parent_run_id, chunk, lane_id=lane_id)

    interactive_pty_manager.set_event_loop(loop)
    interactive_pty_manager.set_output_handler(_forward_interactive_pty_output)

    from src.shell_session import get_shell_session_manager
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
app = FastAPI(
    title="Clutch Orchestrator",
    version="1.0.0",
    lifespan=_lifespan,
    **(
        {"docs_url": None, "redoc_url": None, "openapi_url": None}
        if _docs_disabled
        else {}
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|tauri\.localhost)(:\d+)?|tauri://localhost",
    allow_methods=["*"],
    allow_headers=["*"],
)


class SidecarAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if path in public_http_paths():
            return await call_next(request)
        if not auth_required():
            return await call_next(request)
        if not validate_bearer(request.headers.get("authorization")):
            if path == "/api/workspace/media" and validate_token(request.query_params.get("token")):
                return await call_next(request)
            return JSONResponse(
                status_code=401,
                content={
                    "detail": {
                        "message": "Unauthorized sidecar request",
                        "message_zh": "未授权的 Sidecar 请求",
                    }
                },
            )
        return await call_next(request)


app.add_middleware(SidecarAuthMiddleware)


# Re-export state variables and core helpers so other modules/tests importing from main continue to work perfectly
from src.state import ClutchState, initial_state
from src.workflow_validator import WorkflowValidationError, load_and_validate_workflow, validate_workflow
from src.preferences_storage import tr
from src.terminal_logs import TAG_HUMAN, TAG_WORKFLOW, stamp_log_line, tagged
from src.compiler import WorkflowSession, begin_workflow, resume_workflow
from src.run_history import append_run_record, list_runs, update_run_record, upsert_session

from src.chat_runner import (
    _lifespan,
    _docs_disabled,
    _run_states,
    _run_sessions,
    _human_decision_locks,
    _human_decision_inflight,
    StartRunRequest,
    ValidateWorkflowRequest,
    SaveUserWorkflowRequest,
    WorkspaceRequest,
    RepositoryGroupRequest,
    RepositoryGroupUpdateRequest,
    AgentsSaveRequest,
    AgentPromptGenerateRequest,
    ModelsConfigRequest,
    OpenCodeZenListRequest,
    ModelTestRequest,
    CustomImageModelRequest,
    CustomChatModelRequest,
    CustomVideoModelRequest,
    CustomModelUpdateRequest,
    ToolConnectRequest,
    ReassignRequest,
    HumanDecisionRequest,
    SessionCreateRequest,
    SkillsMountRequest,
    SkillsToggleRequest,
    McpRegisterRequest,
    McpServerIdRequest,
    McpSaveConfigRequest,
    CliActivateProviderRequest,
    CliActivateModelRequest,
    ThemePreferenceRequest,
    LanguagePreferenceRequest,
    PermissionModeRequest,
    FontSizePreferenceRequest,
    AvatarPreferenceRequest,
    UserNamePreferenceRequest,
    _skills_registry_payload,
    _session_workspace_fields,
    _touch_session,
    _apply_workflow_step_patch,
    _apply_workflow_refining_pause,
    _prepare_workflow_refine_state,
    _run_workflow,
    _merge_graph_resume,
    _apply_human_decision,
    _apply_human_decision_locked,
    _validation_http_error,
    _iso_timestamp,
    _get_or_create_run,
    _commit_run_state,
    _apply_delete_message,
    _merge_patch,
    _persist_run_log,
    _setup_run_log_forwarder,
    _emit_workflow_graph_tail,
    _is_terminal_status,
    _serialize_clutch_state,
    _send_state_patch,
    _send_run_completed,
    _notify_run_state,
    _try_ws_notify,
    _AGENT_AVATARS,
    _chat_time,
    _chat_message,
    _hybrid_execution_entry,
    _merge_hybrid_executions,
    _send_message_event,
    _send_hybrid_execution_event,
    _mcp_supervisor_approval_text,
    _supervisor_gate_messages,
    _send_human_required,
    _send_pty_output,
    _send_pty_session_status,
    _estimate_tokens,
    _token_patch,
    _token_patch_turn,
    _history_for_llm,
    _uses_configured_llm,
    _compose_agent_system_prompt,
    _append_terminal_logs,
    _llm_chat_reply,
    _handle_plain_chat_mcp_decision,
    _interrupt_plain_chat_shell,
    _interrupt_workflow_run,
    _apply_plain_chat_stop,
    _recover_stuck_plain_chat,
    _apply_hybrid_plain_chat_rejection,
    _NullWebSocket,
    _refresh_pool_queued_run_states,
    _apply_pool_full_queue,
    _resume_pool_queued_turn,
    _persist_plain_chat_user_message,
    _handle_plain_chat,
    _commit_flow_refine_and_continue,
    _handle_flow_refine_message,
    _handle_workflow_chat_message,
    _send_file_changed,
    _notify_workspace_files_changed,
    _send_validation_result,
    _send_log_event,
    ShellSnapshotUpdateRequest,
    _workspace_http_error,
    _build_agent_prompt_skeleton_fallback,
    _extract_llm_text,
    _async_handoff_summarization_task,
    ws_run,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "api_version": "2"}


from src.routes.workspace import router as workspace_router
from src.routes.models import router as models_router
from src.routes.settings import router as settings_router
from src.routes.pty import router as pty_router
from src.routes.design import router as design_router_facade
from src.routes.chat import router as chat_router
from src.routes.preview import router as preview_router

app.include_router(workspace_router)
app.include_router(models_router)
app.include_router(settings_router)
app.include_router(pty_router)
app.include_router(design_router_facade)
app.include_router(chat_router)
app.include_router(preview_router)
