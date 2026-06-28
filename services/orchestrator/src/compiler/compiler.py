"""Compile validated workflow JSON into an executable LangGraph."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.agent_executor import execute_agent_task
from src.compiler.node_input import resolve_agent_task_input
from src.orchestrator.routing import route_next
from src.terminal_logs import TAG_CHECK, TAG_WORKFLOW, tagged
from src.workflow_runtime import emit_workflow_agent_step


def _stream_compiler_log(state: CompilerState, line: str, *, node_id: str | None = None) -> None:
    run_id = str(state.get("run_id", "")).strip()
    if not run_id:
        return
    from src.run_log_forwarder import get_forwarder

    get_forwarder(run_id).emit(line, node_id=node_id or str(state.get("active_node_id", "")))


class CompilerState(TypedDict):
    """Runtime state passed through compiled LangGraph nodes."""

    run_id: str
    active_node_id: str
    active_agent: str
    status: str
    check_result: str
    human_decision: str
    current_instruction: str
    node_outputs: dict[str, str]
    task_logs: list[str]
    task_messages: list[dict[str, Any]]


NodeHandler = Callable[[CompilerState, dict[str, Any], dict[str, Any]], CompilerState]


@dataclass(frozen=True)
class NodeMeta:
    id: str
    type: str


@dataclass(frozen=True)
class EdgeMeta:
    id: str
    source: str
    target: str
    when: str | None = None


def _handle_start(state: CompilerState, _node: dict[str, Any], _workflow: dict[str, Any]) -> CompilerState:
    task_logs = list(state.get("task_logs", []))
    line = tagged(TAG_WORKFLOW, "Workflow graph entered")
    task_logs.append(line)
    _stream_compiler_log(state, line, node_id="start")
    return {
        **state,
        "active_node_id": "start",
        "active_agent": "Orchestrator",
        "status": "running",
        "task_logs": task_logs,
    }


def _handle_agent_task(
    state: CompilerState,
    node: dict[str, Any],
    workflow: dict[str, Any],
) -> CompilerState:
    from src.workflow_cancel import WorkflowCancelled, is_workflow_cancelled

    run_id = str(state.get("run_id", ""))
    if is_workflow_cancelled(run_id):
        raise WorkflowCancelled(f"Workflow {run_id} stopped by supervisor")
    node_id = str(node.get("id", ""))
    node_data = node.get("data", {}) or {}
    agent_ref = str(node_data.get("agent", "")).strip()
    label = str(node_data.get("label", "")).strip()
    from src.engine_router import find_agent

    agent_dict = find_agent(agent_ref) if agent_ref else None
    if agent_dict and str(agent_dict.get("name", "")).strip():
        pending_agent = str(agent_dict["name"]).strip()
    else:
        pending_agent = label or agent_ref or "Agent"
    emit_workflow_agent_step(
        run_id,
        {
            "active_node_id": node_id,
            "active_agent": pending_agent,
            "status": "running",
        },
    )
    task_input = resolve_agent_task_input(state, node, workflow)
    result = execute_agent_task(
        node_data,
        instruction=task_input,
        run_id=run_id,
        node_id=node_id,
    )
    task_logs = list(state.get("task_logs", []))
    task_messages = list(state.get("task_messages", []))
    task_logs.extend(result.logs)
    task_messages.append(result.message)
    node_outputs = dict(state.get("node_outputs") or {})
    node_outputs[node_id] = result.output
    if result.failed:
        from src.preferences_storage import tr
        from src.workflow_cancel import WorkflowStepFailed

        stop_line = tagged(
            TAG_WORKFLOW,
            tr(
                f"Workflow stopped: step «{label or pending_agent}» failed — downstream steps skipped.",
                f"工作流已停止：步骤「{label or pending_agent}」失败，后续步骤已跳过。",
            ),
        )
        task_logs.append(stop_line)
        _stream_compiler_log(state, stop_line, node_id=node_id)
        emit_workflow_agent_step(
            run_id,
            {
                "new_messages": [result.message],
                "active_node_id": node_id,
                "active_agent": result.agent,
                "status": "failed",
            },
        )
        raise WorkflowStepFailed(
            run_id=run_id,
            node_id=node_id,
            agent=result.agent,
            message=result.output,
        )
    emit_workflow_agent_step(
        run_id,
        {
            "new_messages": [result.message],
            "active_node_id": node_id,
            "active_agent": result.agent,
            "status": "running",
            **(result.state_patch or {}),
        },
    )
    if is_workflow_cancelled(run_id):
        raise WorkflowCancelled(f"Workflow {run_id} stopped by supervisor")
    return {
        **state,
        "active_node_id": node_id,
        "active_agent": result.agent,
        "status": "running",
        "node_outputs": node_outputs,
        "task_logs": task_logs,
        "task_messages": task_messages,
    }


def _handle_check(state: CompilerState, node: dict[str, Any], _workflow: dict[str, Any]) -> CompilerState:
    preset = state.get("check_result") or ""
    if preset:
        result = preset
        eval_logs: list[str] = [tagged(TAG_CHECK, f"Using preset result: {result}")]
    else:
        from src.evaluator import evaluate_node_data
        from src.workspace import get_workspace

        if get_workspace() is None:
            result = "passed"
            eval_logs = [tagged(TAG_CHECK, "No workspace — checks skipped (passed)")]
        else:
            result, eval_logs = evaluate_node_data(node.get("data", {}))

    task_logs = list(state.get("task_logs", []))
    task_logs.extend(eval_logs)
    for line in eval_logs:
        _stream_compiler_log(state, line, node_id=node["id"])
    task_messages = list(state.get("task_messages", []))
    if result == "failed":
        summary = "\n".join(eval_logs[-3:]) if eval_logs else "Checks failed."
        from src.chat_events import chat_message

        task_messages.append(
            chat_message(
                "Evaluator",
                f"Checks failed.\n\n{summary}",
                status="FAILED",
                badge_text="VALIDATION FAILED",
            )
        )

    return {
        **state,
        "active_node_id": node["id"],
        "active_agent": "Evaluator",
        "status": "running",
        "check_result": result,
        "task_logs": task_logs,
        "task_messages": task_messages,
    }


def _handle_human_gate(state: CompilerState, node: dict[str, Any], _workflow: dict[str, Any]) -> CompilerState:
    decision = state.get("human_decision") or ""
    if not decision:
        return {
            **state,
            "active_node_id": node["id"],
            "active_agent": "Supervisor",
            "status": "awaiting_human",
        }
    return {
        **state,
        "active_node_id": node["id"],
        "active_agent": "Supervisor",
        "status": "running",
        "human_decision": decision,
    }


def _handle_end(state: CompilerState, node: dict[str, Any], _workflow: dict[str, Any]) -> CompilerState:
    return {
        **state,
        "active_node_id": node["id"],
        "active_agent": "Orchestrator",
        "status": "passed",
    }


NODE_HANDLERS: dict[str, NodeHandler] = {
    "start": _handle_start,
    "agent_task": _handle_agent_task,
    "check": _handle_check,
    "human_gate": _handle_human_gate,
    "end": _handle_end,
}


class WorkflowCompiler:
    """Compile workflow JSON (post schema validation) into LangGraph."""

    NODE_HANDLERS = NODE_HANDLERS

    def __init__(self) -> None:
        self._node_metas: list[NodeMeta] = []
        self._edge_metas: list[EdgeMeta] = []
        self._workflow: dict[str, Any] = {}

    @property
    def node_metas(self) -> list[NodeMeta]:
        return list(self._node_metas)

    @property
    def edge_metas(self) -> list[EdgeMeta]:
        return list(self._edge_metas)

    def compile(self, workflow: dict[str, Any]):
        self._workflow = workflow
        self._node_metas = []
        self._edge_metas = []

        nodes_by_id = {node["id"]: node for node in workflow["nodes"]}
        edges = workflow["edges"]

        graph: StateGraph = StateGraph(CompilerState)

        graph.add_node("start", self._wrap_handler({"id": "start", "type": "start", "data": {}}))
        self._node_metas.append(NodeMeta(id="start", type="start"))

        for node in workflow["nodes"]:
            graph.add_node(node["id"], self._wrap_handler(node))
            self._node_metas.append(NodeMeta(id=node["id"], type=node["type"]))

        for edge in edges:
            when = edge.get("data", {}).get("when")
            self._edge_metas.append(
                EdgeMeta(id=edge["id"], source=edge["source"], target=edge["target"], when=when)
            )

        edges_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in edges:
            edges_by_source[edge["source"]].append(edge)

        graph.add_edge(START, "start")

        for source, outgoing in edges_by_source.items():
            if source not in {"start", *nodes_by_id.keys()}:
                raise ValueError(f"Unknown edge source: {source}")

            conditional = [edge for edge in outgoing if edge.get("data", {}).get("when")]
            unconditional = [edge for edge in outgoing if not edge.get("data", {}).get("when")]

            if conditional and unconditional:
                raise ValueError(f"Node {source} mixes conditional and unconditional edges")

            if conditional:
                path_map = {edge["data"]["when"]: edge["target"] for edge in conditional}

                def _route(
                    state: CompilerState,
                    _workflow: dict[str, Any] = workflow,
                    _source: str = source,
                    _path_map: dict[str, str] = path_map,
                ) -> str:
                    branch, _method = route_next(_workflow, _source, state)
                    if branch not in _path_map:
                        raise ValueError(f"Branch {branch!r} not in path map for {_source!r}")
                    return branch

                graph.add_conditional_edges(source, _route, path_map)
            elif len(unconditional) == 1:
                graph.add_edge(source, unconditional[0]["target"])
            elif len(unconditional) > 1:
                raise ValueError(f"Node {source} has multiple unconditional edges")

        if "end" in nodes_by_id:
            graph.add_edge("end", END)

        human_gate_ids = [node["id"] for node in workflow["nodes"] if node["type"] == "human_gate"]
        checkpointer = MemorySaver()
        return graph.compile(checkpointer=checkpointer, interrupt_before=human_gate_ids)

    def _wrap_handler(self, node: dict[str, Any]) -> Callable[[CompilerState], CompilerState]:
        node_type = node["type"]
        handler = self.NODE_HANDLERS.get(node_type)
        if handler is None:
            raise ValueError(f"No handler registered for node type: {node_type}")
        workflow = self._workflow

        def _run(state: CompilerState) -> CompilerState:
            return handler(state, node, workflow)

        return _run


def compile_workflow(workflow: dict[str, Any]):
    """Convenience helper: compile workflow dict to runnable LangGraph."""
    return WorkflowCompiler().compile(workflow)


def human_gate_node_ids(workflow: dict[str, Any]) -> list[str]:
    return [node["id"] for node in workflow["nodes"] if node["type"] == "human_gate"]


def workflow_run_config(run_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": run_id}}


def is_awaiting_human_gate(compiled: Any, config: dict[str, Any], workflow: dict[str, Any]) -> bool:
    snapshot = compiled.get_state(config)
    if not snapshot.next:
        return False
    gate_ids = set(human_gate_node_ids(workflow))
    return any(node in gate_ids for node in snapshot.next)


def initial_compiler_state(run_id: str, *, instruction: str = "") -> CompilerState:
    return CompilerState(
        run_id=run_id,
        active_node_id="start",
        active_agent="Orchestrator",
        status="running",
        check_result="",
        human_decision="",
        current_instruction=instruction,
        node_outputs={},
        task_logs=[],
        task_messages=[],
    )


def run_workflow(workflow: dict[str, Any], run_id: str) -> CompilerState:
    """Compile and invoke workflow; pause at human_gate interrupts when needed."""
    _session, result = begin_workflow(workflow, run_id)
    return result


@dataclass(frozen=True)
class WorkflowSession:
    compiled: Any
    config: dict[str, Any]
    workflow: dict[str, Any]


def begin_workflow(
    workflow: dict[str, Any],
    run_id: str,
    *,
    initial_state: CompilerState | None = None,
    instruction: str = "",
) -> tuple[WorkflowSession, CompilerState]:
    compiled = compile_workflow(workflow)
    config = workflow_run_config(run_id)
    state = initial_state or initial_compiler_state(run_id, instruction=instruction)
    if instruction and not state.get("current_instruction"):
        state = {**state, "current_instruction": instruction}
    result = compiled.invoke(state, config)
    session = WorkflowSession(compiled=compiled, config=config, workflow=workflow)
    if is_awaiting_human_gate(compiled, config, workflow):
        gate_id = next(iter(compiled.get_state(config).next))
        return session, {
            **result,
            "active_node_id": gate_id,
            "active_agent": "Supervisor",
            "status": "awaiting_human",
        }
    return session, result


def resume_workflow(
    session: WorkflowSession,
    run_id: str,
    decision: str,
    *,
    instruction: str = "",
) -> CompilerState:
    """Resume a paused workflow after supervisor human_decision."""
    update: dict[str, str] = {"human_decision": decision}
    if instruction.strip():
        update["current_instruction"] = instruction.strip()
    if decision == "retry":
        update["check_result"] = ""
    session.compiled.update_state(session.config, update)
    result = session.compiled.invoke(Command(resume=decision), session.config)
    if not result.get("human_decision"):
        result = {**result, "human_decision": decision}
    if is_awaiting_human_gate(session.compiled, session.config, session.workflow):
        gate_id = next(iter(session.compiled.get_state(session.config).next))
        return {
            **result,
            "active_node_id": gate_id,
            "active_agent": "Supervisor",
            "status": "awaiting_human",
        }
    return result
