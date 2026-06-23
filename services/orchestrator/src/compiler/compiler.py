"""Compile validated workflow JSON into an executable LangGraph."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from dataclasses import dataclass
from typing import Any, Callable, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.orchestrator.routing import route_next


class CompilerState(TypedDict):
    """Runtime state passed through compiled LangGraph nodes."""

    run_id: str
    active_node_id: str
    active_agent: str
    status: str
    check_result: str
    human_decision: str


NodeHandler = Callable[[CompilerState, dict[str, Any]], CompilerState]


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


def _handle_start(state: CompilerState, _node: dict[str, Any]) -> CompilerState:
    return {
        **state,
        "active_node_id": "start",
        "active_agent": "Orchestrator",
        "status": "running",
    }


def _handle_agent_task(state: CompilerState, node: dict[str, Any]) -> CompilerState:
    data = node.get("data", {})
    return {
        **state,
        "active_node_id": node["id"],
        "active_agent": str(data.get("agent", "Builder")),
        "status": "running",
    }


def _handle_check(state: CompilerState, node: dict[str, Any]) -> CompilerState:
    preset = state.get("check_result") or ""
    if preset:
        result = preset
    else:
        from src.evaluator import evaluate_node_data
        from src.workspace import get_workspace

        if get_workspace() is None:
            result = "passed"
        else:
            result, _logs = evaluate_node_data(node.get("data", {}))
    return {
        **state,
        "active_node_id": node["id"],
        "active_agent": "Evaluator",
        "status": "running",
        "check_result": result,
    }


def _handle_human_gate(state: CompilerState, node: dict[str, Any]) -> CompilerState:
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


def _handle_end(state: CompilerState, node: dict[str, Any]) -> CompilerState:
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

    @property
    def node_metas(self) -> list[NodeMeta]:
        return list(self._node_metas)

    @property
    def edge_metas(self) -> list[EdgeMeta]:
        return list(self._edge_metas)

    def compile(self, workflow: dict[str, Any]):
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

        def _run(state: CompilerState) -> CompilerState:
            return handler(state, node)

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


def initial_compiler_state(run_id: str) -> CompilerState:
    return CompilerState(
        run_id=run_id,
        active_node_id="start",
        active_agent="Orchestrator",
        status="running",
        check_result="",
        human_decision="",
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
) -> tuple[WorkflowSession, CompilerState]:
    compiled = compile_workflow(workflow)
    config = workflow_run_config(run_id)
    state = initial_state or initial_compiler_state(run_id)
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


def resume_workflow(session: WorkflowSession, run_id: str, decision: str) -> CompilerState:
    """Resume a paused workflow after supervisor human_decision."""
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
