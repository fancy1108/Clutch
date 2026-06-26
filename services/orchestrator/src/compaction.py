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
    digest = await _generate_llm_digest(intermediate_messages, model_id=model_id)

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

async def _generate_llm_digest(intermediate_messages: list[dict[str, Any]], model_id: str | None = None) -> str:
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
    
    system_prompt = (
        "You are a system assistant. Summarize the following AI agent conversation history of a software workflow. "
        "Focus on:\n"
        "1. The user's main goal.\n"
        "2. What changes were made to files/code.\n"
        "3. What tools were executed and what tests passed/failed.\n"
        "4. The current state/status.\n\n"
        "Be extremely concise, clear, and bulleted. Do not include introductory chatter. Just return the summary digest. "
        "Respond in the same language as the conversation (English or Chinese)."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": formatted_history}
    ]
    
    try:
        response = await asyncio.to_thread(router.chat, messages, model_id=model_id)
        if isinstance(response, dict):
            content = response.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
            return str(response).strip()
        return str(response).strip()
    except Exception as exc:
        logger.error(f"Failed to generate compaction digest via LLM: {exc}")
        agents_involved = list(set([str(m.get("agent")) for m in intermediate_messages if m.get("agent")]))
        return tr(
            f"History compacted due to token limit. Original messages: {len(intermediate_messages)}. "
            f"Last actions performed by agents: {', '.join(agents_involved)}.",
            f"由于 Token 消耗达到阈值，历史对话已折叠。已压缩消息数：{len(intermediate_messages)}。 "
            f"参与的 Agent 包括：{', '.join(agents_involved)}。"
        )
