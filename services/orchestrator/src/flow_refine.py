"""Flow pause → @agent hybrid refine → legacy resume."""

from __future__ import annotations

import re
from typing import Any

from src.compiler.compiler import (
    CompilerState,
    WorkflowSession,
    compile_workflow,
    initial_compiler_state,
    is_awaiting_human_gate,
    workflow_run_config,
)
from src.preferences_storage import tr
from src.terminal_logs import TAG_WORKFLOW, tagged


_AT_MENTION_RE = re.compile(r"^@(\S+)\s*(.*)$", re.DOTALL)
_CONTINUE_RE = re.compile(r"^/(continue|resume)\b", re.I)
_FINAL_IMAGE_PROMPT_RE = re.compile(
    r'"final_image_prompt"\s*:\s*"((?:[^"\\]|\\.)*)"',
    re.DOTALL,
)


def workflow_mention_names(workflow: dict[str, Any] | None) -> list[str]:
    if not workflow:
        return []
    names: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        token = name.strip()
        if token and token not in seen:
            seen.add(token)
            names.append(token)

    for node in ordered_agent_task_nodes(workflow):
        data = node.get("data") or {}
        add(str(data.get("label") or ""))
        agent_ref = str(data.get("agent") or "").strip()
        if agent_ref:
            from src.engine_router import find_agent

            record = find_agent(agent_ref)
            if record:
                add(str(record.get("name") or ""))
    return names


def parse_agent_mention(
    text: str,
    *,
    workflow: dict[str, Any] | None = None,
) -> tuple[str | None, str]:
    stripped = text.strip()
    if not stripped.startswith("@"):
        return None, stripped
    rest = stripped[1:].lstrip()
    for name in sorted(workflow_mention_names(workflow), key=len, reverse=True):
        if rest == name or rest.startswith(f"{name} "):
            return name, rest[len(name) :].strip()
    match = _AT_MENTION_RE.match(stripped)
    if not match:
        return None, stripped
    return match.group(1).strip(), match.group(2).strip()


def extract_final_image_prompt(text: str) -> str:
    body = text.strip()
    if not body:
        return ""
    try:
        import json

        data = json.loads(body)
        if isinstance(data, dict):
            prompt = str(data.get("final_image_prompt") or "").strip()
            if prompt:
                return prompt
    except json.JSONDecodeError:
        pass
    match = _FINAL_IMAGE_PROMPT_RE.search(body)
    if match:
        return match.group(1).replace("\\n", "\n").replace('\\"', '"').strip()
    return ""


def upstream_node_ids(workflow: dict[str, Any], node_id: str) -> list[str]:
    return [
        str(edge.get("source", ""))
        for edge in workflow.get("edges", [])
        if str(edge.get("target", "")) == node_id
    ]


def resolve_image_refine_prompt(
    *,
    session: WorkflowSession,
    refining_node_id: str,
    user_body: str,
    messages: list[dict[str, Any]],
) -> str:
    workflow = session.workflow
    outputs = dict(compiler_snapshot_values(session).get("node_outputs") or {})
    if not outputs:
        outputs = rebuild_node_outputs_from_messages(workflow, messages)

    upstreams = upstream_node_ids(workflow, refining_node_id)
    base_prompt = ""
    if len(upstreams) == 1:
        upstream_text = str(outputs.get(upstreams[0]) or "").strip()
        extracted = extract_final_image_prompt(upstream_text)
        # Match normal flow routing: pass full upstream output when no dedicated image key.
        base_prompt = extracted if extracted else upstream_text

    user_text = user_body.strip()
    if base_prompt and user_text:
        return f"{base_prompt}. {user_text}"
    if base_prompt:
        return base_prompt
    return user_text or "regenerate the image with the same scene"


def is_continue_command(text: str) -> bool:
    stripped = text.strip()
    if _CONTINUE_RE.match(stripped):
        return True
    return stripped in {"继续", "继续执行", "继续工作流"}


def refine_reply_ready_to_commit(reply_text: str) -> bool:
    """True when refine output is worth committing and auto-continuing downstream."""
    text = reply_text.strip()
    if not text:
        return False
    return not text.lower().startswith("error")


def compiler_snapshot_values(session: WorkflowSession) -> dict[str, Any]:
    snapshot = session.compiled.get_state(session.config)
    values = snapshot.values
    return dict(values) if values else {}


def infer_refining_node_id(
    *,
    clutch_active_node_id: str,
    compiler_values: dict[str, Any],
) -> str:
    explicit = str(compiler_values.get("active_node_id") or "").strip()
    outputs = dict(compiler_values.get("node_outputs") or {})
    if explicit and explicit in outputs:
        return explicit
    if explicit and explicit not in {"start", "end", ""}:
        return explicit
    if clutch_active_node_id.strip():
        return clutch_active_node_id.strip()
    if outputs:
        return list(outputs.keys())[-1]
    return explicit or clutch_active_node_id


def node_output_for_refine(
    *,
    session: WorkflowSession,
    node_id: str,
    messages: list[dict[str, Any]],
) -> str:
    values = compiler_snapshot_values(session)
    outputs = dict(values.get("node_outputs") or {})
    if node_id and outputs.get(node_id):
        return str(outputs[node_id])
    for message in reversed(messages):
        if message.get("agent") == "User":
            continue
        text = str(message.get("text", "")).strip()
        if text:
            return text
    return ""


def build_refine_system_appendix(
    *,
    node_id: str,
    node_label: str,
    node_output: str,
) -> str:
    label = node_label or node_id or "step"
    body = node_output.strip() or "(no prior output captured)"
    return tr(
        (
            f"\n\n[Flow refine] You are revising workflow step «{label}» (node `{node_id}`).\n"
            f"Current committed output:\n{body}\n\n"
            "Apply the supervisor's feedback and return the revised output for this step only."
        ),
        (
            f"\n\n[Flow 精修] 你正在修订工作流步骤「{label}」（节点 `{node_id}`）。\n"
            f"当前已提交输出：\n{body}\n\n"
            "请根据监督者的修改意见，仅返回该步骤的修订结果。"
        ),
    )


def workflow_node_label(session: WorkflowSession, node_id: str) -> str:
    for node in session.workflow.get("nodes", []):
        if str(node.get("id", "")) == node_id:
            data = node.get("data") or {}
            return str(data.get("label") or data.get("agent") or node_id)
    return node_id


def continue_workflow_after_refine(
    session: WorkflowSession,
    *,
    node_id: str,
    node_output: str,
) -> CompilerState:
    """Commit refined output for `node_id` and resume downstream steps (legacy flow routing)."""
    snapshot = session.compiled.get_state(session.config)
    values = dict(snapshot.values or {})
    node_outputs = dict(values.get("node_outputs") or {})
    node_outputs[node_id] = node_output.strip()
    values["node_outputs"] = node_outputs
    values["status"] = "running"
    values["active_node_id"] = node_id
    session.compiled.update_state(session.config, values, as_node=node_id)
    result = session.compiled.invoke(None, session.config)
    if is_awaiting_human_gate(session.compiled, session.config, session.workflow):
        gate_id = next(iter(session.compiled.get_state(session.config).next))
        return {
            **result,
            "active_node_id": gate_id,
            "active_agent": "Supervisor",
            "status": "awaiting_human",
        }
    return result


def pause_log_line() -> str:
    return tagged(
        TAG_WORKFLOW,
        tr(
            "Workflow paused for refine — @ an agent with feedback; downstream runs automatically after refine. Use Stop to pause first.",
            "工作流已暂停精修 — @ Agent 并输入修改意见，精修完成后自动继续下游。不满意可先点停止再重新 @。",
        ),
    )


def is_workflow_refine_eligible(state: dict[str, Any]) -> bool:
    if not str(state.get("workflow_id") or "").strip():
        return False
    return str(state.get("status") or "") in {"refining", "passed", "failed"}


def refine_triggered_by_message(
    text: str,
    *,
    status: str,
    workflow: dict[str, Any] | None = None,
) -> bool:
    if status == "refining":
        return True
    if is_continue_command(text):
        return True
    mention, _body = parse_agent_mention(text, workflow=workflow)
    return bool(mention)


def ordered_agent_task_nodes(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    agent_nodes = [node for node in workflow.get("nodes", []) if node.get("type") == "agent_task"]
    if not agent_nodes:
        return []
    node_by_id = {str(node.get("id", "")): node for node in agent_nodes}
    edges_by_source: dict[str, list[str]] = {}
    for edge in workflow.get("edges", []):
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        edges_by_source.setdefault(source, []).append(target)

    ordered: list[dict[str, Any]] = []
    visited: set[str] = set()
    queue = ["start"]
    while queue:
        current = queue.pop(0)
        for target in edges_by_source.get(current, []):
            if target in visited or target == "end":
                continue
            visited.add(target)
            node = node_by_id.get(target)
            if node:
                ordered.append(node)
            queue.append(target)
    return ordered or agent_nodes


def rebuild_node_outputs_from_messages(
    workflow: dict[str, Any],
    messages: list[dict[str, Any]],
) -> dict[str, str]:
    outputs: dict[str, str] = {}
    for node in ordered_agent_task_nodes(workflow):
        node_id = str(node.get("id", ""))
        data = node.get("data") or {}
        label = str(data.get("label") or node_id).strip()
        if not label:
            continue
        labels_to_match = {label}
        agent_ref = str(data.get("agent") or "").strip()
        if agent_ref:
            from src.engine_router import find_agent

            record = find_agent(agent_ref)
            if record:
                name = str(record.get("name") or "").strip()
                if name:
                    labels_to_match.add(name)
        for message in reversed(messages):
            if message.get("agent") == "User":
                continue
            agent_name = str(message.get("agent") or "").strip()
            if agent_name in labels_to_match:
                text = str(message.get("text") or "").strip()
                if text:
                    outputs[node_id] = text
                    break
    return outputs


def workflow_node_id_for_agent(workflow: dict[str, Any], agent_id: str) -> str:
    token = agent_id.strip()
    if not token:
        return ""
    for node in ordered_agent_task_nodes(workflow):
        data = node.get("data") or {}
        if str(data.get("agent", "")).strip() == token:
            return str(node.get("id", ""))
    return ""


def ensure_workflow_session_for_refine(
    run_id: str,
    state: dict[str, Any],
    *,
    sessions: dict[str, WorkflowSession],
) -> WorkflowSession | None:
    existing = sessions.get(run_id)
    if existing is not None:
        return existing

    workflow_id = str(state.get("workflow_id") or "").strip()
    if not workflow_id:
        return None

    from src.workflow_storage import resolve_workflow

    workflow, _source = resolve_workflow(workflow_id)
    compiled = compile_workflow(workflow)
    config = workflow_run_config(run_id)
    session = WorkflowSession(compiled=compiled, config=config, workflow=workflow)
    node_outputs = rebuild_node_outputs_from_messages(workflow, list(state.get("messages") or []))
    if not node_outputs:
        return None

    refining_node_id = infer_refining_node_id(
        clutch_active_node_id=str(state.get("active_node_id") or ""),
        compiler_values={
            "node_outputs": node_outputs,
            "active_node_id": str(state.get("active_node_id") or ""),
        },
    )
    compiler_state = initial_compiler_state(
        run_id,
        instruction=str(state.get("current_instruction") or ""),
    )
    compiler_state = {
        **compiler_state,
        "node_outputs": node_outputs,
        "active_node_id": refining_node_id,
        "status": "passed",
    }
    session.compiled.update_state(session.config, compiler_state, as_node=refining_node_id)
    sessions[run_id] = session
    return session
