import json
import logging
import os
import uuid
import datetime
from pathlib import Path
from typing import Any
from src.state import ClutchState
from src.preferences_storage import tr

logger = logging.getLogger("clutch.compaction")

_CRITICAL_STATUSES = {"approval_required", "awaiting_human", "error", "failed", "rejected"}
_CRITICAL_EVENT_TYPES = {
    "file_changed", "human_required", "tool", "tool_call", "tool_result", "validation_result"
}
_CRITICAL_TEXT_MARKERS = (
    "checks failed", "execution error", "human approval:", "requires your approval", "tool result",
    "人工审批：", "需要您批准", "检查未通过", "执行错误", "工具结果",
)


def get_archive_dir() -> Path:
    from src.workspace import get_workspace
    workspace = get_workspace()
    if workspace and workspace.get("workspace_path"):
        path = Path(workspace["workspace_path"]) / "runs" / "archive"
    else:
        from src.run_history import sessions_data_dir
        path = sessions_data_dir() / "archive"
    path.mkdir(parents=True, exist_ok=True)
    return path

def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _is_critical_message(message: dict[str, Any]) -> bool:
    """Return whether a message contains trajectory details compaction must retain."""
    status = str(message.get("status") or "").strip().lower()
    event_type = str(
        message.get("event") or message.get("type") or message.get("kind") or ""
    ).strip().lower()
    badge = str(message.get("badgeText") or message.get("badge_text") or "").lower()
    output_events = message.get("outputEvents") or message.get("output_events") or []
    text = str(message.get("text") or "").lower()
    return bool(message.get("approvalKey") or message.get("approval_key")) or any((
        status in _CRITICAL_STATUSES,
        event_type in _CRITICAL_EVENT_TYPES,
        any(marker in badge for marker in ("approval", "error", "fail", "validation", "审批", "失败")),
        isinstance(output_events, list) and any(
            isinstance(event, dict) and str(event.get("type") or "").lower() in {"tool", "stderr"}
            for event in output_events
        ),
        any(marker in text for marker in _CRITICAL_TEXT_MARKERS),
    ))


def _build_critical_context(
    state: ClutchState,
    messages: list[dict[str, Any]],
) -> list[str]:
    """Build deterministic context lines that must survive LLM summarization."""
    lines: list[str] = []
    status = str(state.get("status") or "").strip()
    if status and status != "idle":
        state_parts = [f"status={status}"]
        state_parts.extend(
            f"{label}={value}" for label, value in (
                ("active_node", state.get("active_node_id")),
                ("active_agent", state.get("active_agent")),
            ) if value
        )
        lines.append("[workflow_state] " + "; ".join(state_parts))

    changed_files = list(dict.fromkeys(
        str(path).strip() for path in state.get("changed_files", []) if str(path).strip()
    ))
    if changed_files:
        lines.append("[files_changed] " + ", ".join(changed_files))

    for message in messages:
        if not _is_critical_message(message):
            continue
        details = [f"{key}={message[key]}" for key in ("id", "agent", "status") if message.get(key)]
        badge = str(message.get("badgeText") or message.get("badge_text") or "").strip()
        if badge:
            details.append(f"badge={badge}")
        text = " ".join(str(message.get("text") or "").split())
        if text:
            details.append(f"text={text[:1000]}")
        output_events = message.get("outputEvents") or message.get("output_events") or []
        if isinstance(output_events, list):
            details.extend(
                f"{event['type']}={' '.join(str(event.get('content') or '').split())[:500]}"
                for event in output_events if isinstance(event, dict) and event.get("type") in {"tool", "stderr"}
            )
        if details:
            lines.append("[critical_message] " + "; ".join(details))

    return lines


def should_compact(state: ClutchState, threshold: int = 15000) -> bool:
    messages = state.get("messages", [])
    if len(messages) <= 5:
        return False
    
    # Read threshold from environment variable if present
    env_threshold = os.environ.get("CLUTCH_COMPACT_THRESHOLD")
    if env_threshold:
        try:
            threshold = int(env_threshold)
        except ValueError:
            pass
    return state.get("session_tokens", 0) > threshold



async def compact_run_messages(
    run_id: str,
    state: ClutchState,
    model_id: str | None = None,
) -> ClutchState:
    messages = list(state.get("messages", []))
    if len(messages) <= 5:
        return state

    # Step 1: Archive original messages to runs/archive/{run_id}.jsonl
    archive_dir = get_archive_dir()
    archive_file = archive_dir / f"{run_id}.jsonl"
    try:
        with open(archive_file, "a", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        logger.info(f"Archived {len(messages)} messages to {archive_file}")
    except Exception as e:
        logger.error(f"Failed to archive messages for compaction: {e}")

    # Step 2: Slice the message array
    first_message = messages[0]
    last_messages = messages[-4:]
    intermediate_messages = messages[1:-4]

    # Step 3: Call LLM to summarize intermediate history
    critical_context = _build_critical_context(state, intermediate_messages)
    digest = await _generate_llm_digest(
        intermediate_messages,
        model_id=model_id,
        critical_context=critical_context,
    )

    # Step 4: Create a compaction digest message
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    relative_archive_path = f"runs/archive/{run_id}.jsonl"
    
    text_en = (
        f"⚠️ [Context Compacted] The intermediate conversation history has been archived to `{relative_archive_path}` to save context tokens.\n\n"
        f"**Summary of progress so far:**\n{digest}"
    )
    text_zh = (
        f"⚠️ [上下文已压缩] 中间轮次的历史对话已被归档至 `{relative_archive_path}` 以节省上下文 Token。\n\n"
        f"**历史变更与进度摘要：**\n{digest}"
    )
    
    digest_msg = {
        "id": f"system_digest_{uuid.uuid4().hex[:8]}",
        "agent": "System",
        "text": tr(text_en, text_zh),
        "time": now_str,
        "status": "COMPLETED",
        "badgeText": tr("COMPACTION DIGEST", "上下文压缩摘要"),
        "badge_text": tr("COMPACTION DIGEST", "上下文压缩摘要"),
    }


    # Step 5: Merge into compacted message list
    compacted_messages = [first_message, digest_msg] + last_messages
    state["messages"] = compacted_messages

    # Step 6: Recalculate tokens
    input_tokens = 0
    output_tokens = 0
    for msg in compacted_messages:
        agent = str(msg.get("agent", ""))
        text_content = str(msg.get("text", ""))
        toks = _estimate_tokens(text_content)
        if agent == "User":
            input_tokens += toks
        else:
            output_tokens += toks
    
    total = input_tokens + output_tokens
    state["token_input"] = input_tokens
    state["token_output"] = output_tokens
    state["session_tokens"] = total
    state["session_cost_usd"] = round(total * 0.00000015, 6)

    # Save to disk
    from src.run_state_store import save_run_state
    save_run_state(state)

    logger.info(f"Compaction completed. New session tokens: {total}")
    return state

async def _generate_llm_digest(
    intermediate_messages: list[dict[str, Any]],
    model_id: str | None = None,
    critical_context: list[str] | None = None,
) -> str:
    import asyncio
    from src.models_config import get_router
    router = get_router()
    
    lines: list[str] = []
    for msg in intermediate_messages:
        agent = str(msg.get("agent", ""))
        text = str(msg.get("text", "")).strip()
        if text:
            lines.append(f"{agent}: {text}")
    formatted_history = "\n\n".join(lines)
    protected_context = "\n".join(f"- {line}" for line in critical_context or [])
    
    system_prompt = (
        "You are a system assistant. Summarize the following AI agent conversation history of a software workflow. "
        "Focus on:\n"
        "1. The user's main goal.\n"
        "2. What changes were made to files/code.\n"
        "3. What tools were executed and what tests passed/failed.\n"
        "4. The current state/status.\n"
        "5. Human approvals, rejections, and retry instructions.\n\n"
        "Be extremely concise, clear, and bulleted. Do not include introductory chatter. Just return the summary digest. "
        "Respond in the same language as the conversation (English or Chinese)."
    )

    user_content = formatted_history if not protected_context else (
        f"Critical trajectory records that must remain recoverable:\n{protected_context}\n\n"
        f"Conversation history:\n{formatted_history}"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]

    try:
        response = await asyncio.to_thread(router.chat, messages, model_id=model_id)
        if isinstance(response, dict):
            response = response.get("content") or response
        summary = str(response).strip()
    except Exception as exc:
        logger.error(f"Failed to generate compaction digest via LLM: {exc}")
        agents_involved = list(set([str(m.get("agent")) for m in intermediate_messages if m.get("agent")]))
        summary = tr(
            f"History compacted due to token limit. Original messages: {len(intermediate_messages)}. "
            f"Last actions performed by agents: {', '.join(agents_involved)}.",
            f"由于 Token 消耗达到阈值，历史对话已折叠。已压缩消息数：{len(intermediate_messages)}。 "
            f"参与的 Agent 包括：{', '.join(agents_involved)}。"
        )
    if protected_context:
        summary += f"\n\nCritical trajectory records:\n{protected_context}"
    return summary
