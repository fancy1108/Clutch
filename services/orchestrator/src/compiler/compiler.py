"""Compile validated workflow JSON into an executable LangGraph."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph


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
    # M1 stub: real check execution arrives in M3; default to passed for compile smoke.
    result = state.get("check_result") or "passed"
    return {
        **state,
        "active_node_id": node["id"],
        "active_agent": "Evaluator",
        "status": "running",
        "check_result": result,
    }


def _handle_human_gate(state: CompilerState, node: dict[str, Any]) -> CompilerState:
    decision = state.get("human_decision") or "approve"
    return {
        **state,
        "active_node_id": node["id"],
        "active_agent": "Supervisor",
        "status": "awaiting_human",
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

                source_type = (
                    "start"
                    if source == "start"
                    else nodes_by_id.get(source, {}).get("type", "")
                )

                def _route(
                    state: CompilerState,
                    _path_map: dict[str, str] = path_map,
                    _source_type: str = source_type,
                ) -> str:
                    if _source_type == "check":
                        return state.get("check_result") or "passed"
                    if _source_type == "human_gate":
                        return state.get("human_decision") or "approve"
                    return next(iter(_path_map))

                graph.add_conditional_edges(source, _route, path_map)
            elif len(unconditional) == 1:
                graph.add_edge(source, unconditional[0]["target"])
            elif len(unconditional) > 1:
                raise ValueError(f"Node {source} has multiple unconditional edges")

        if "end" in nodes_by_id:
            graph.add_edge("end", END)

        return graph.compile()

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
    """Compile and invoke workflow; return final graph state."""
    compiled = compile_workflow(workflow)
    return compiled.invoke(initial_compiler_state(run_id))
