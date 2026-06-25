"""Terminal log prefixes — neutral tags, not sample-flow role names."""

from __future__ import annotations

TAG_WORKFLOW = "WORKFLOW"
TAG_CHECK = "CHECK"
TAG_HUMAN = "HUMAN"


def tagged(tag: str, message: str) -> str:
    return f"[{tag}] {message}"


def resolve_agent_tag(agent_ref: str, *, label: str = "") -> str:
    ref = agent_ref.strip()
    if ref:
        from src.engine_router import find_agent

        record = find_agent(ref)
        if record:
            return str(record.get("name") or ref)
        return ref
    return label.strip() or "Agent"


def agent_line(agent_ref: str, message: str, *, label: str = "") -> str:
    return tagged(resolve_agent_tag(agent_ref, label=label), message)


def with_agent_prefix(agent_ref: str, line: str, *, label: str = "") -> str:
    if line.startswith("["):
        return line
    return agent_line(agent_ref, line, label=label)
