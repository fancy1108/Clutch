"""Parse Orchestrator Bar dispatch mentions (D34)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

KNOWN_AGENTS = ("Claude Code", "OpenCode")
WORKSPACE_SOURCE = "工作区"
InputMode = Literal["natural", "graph"]


@dataclass
class DispatchChip:
    id: str
    label: str
    on: bool
    source_name: str


@dataclass
class DispatchPreview:
    sources: list[str]
    target: str
    task: str
    handoff_path: str
    handoff_file: str
    chips: list[DispatchChip]
    file_refs: list[str] = field(default_factory=list)
    input_mode: InputMode = "natural"


def _normalize_agent(value: str) -> str:
    return value.strip()


def extract_at_tokens(text: str) -> list[tuple[str, str]]:
    """Return list of (type, value) where type is 'agent' | 'file'."""
    tokens: list[tuple[str, str]] = []
    i = 0
    sorted_agents = sorted(KNOWN_AGENTS, key=len, reverse=True)
    while i < len(text):
        if text[i] != "@":
            i += 1
            continue
        rest = text[i + 1 :]
        matched: str | None = None
        kind: str | None = None
        for agent in sorted_agents:
            if not rest.lower().startswith(agent.lower()):
                continue
            nxt = rest[len(agent) :] if len(agent) < len(rest) else ""
            if nxt and not re.match(r"[\s，,：:、]", nxt[0]):
                continue
            matched = agent
            kind = "agent"
            break
        if not matched:
            file_match = re.match(r"^([^\s@]+?\.md)", rest)
            if file_match:
                matched = file_match.group(1)
                kind = "file"
        if matched and kind:
            tokens.append((kind, matched))
            i += 1 + len(matched)
        else:
            i += 1
    return tokens


def sources_from_file_refs(
    file_refs: list[str],
    *,
    file_meta_resolver,
) -> list[str]:
    sources: list[str] = []
    for file_name in file_refs:
        meta = file_meta_resolver(file_name)
        for src in meta.get("sources", []):
            if src not in sources:
                sources.append(src)
    return sources


def parse_dispatch_mentions(
    text: str,
    *,
    focused_agent: str | None = None,
    file_meta_resolver=None,
) -> DispatchPreview | None:
    trimmed = text.strip()
    if not trimmed or "@" not in trimmed:
        return None

    if file_meta_resolver is None:
        file_meta_resolver = lambda _f: {"sources": []}  # noqa: E731

    tokens = extract_at_tokens(trimmed)
    file_refs = [v for kind, v in tokens if kind == "file"]
    sources: list[str] = []
    target: str | None = None
    task = ""
    input_mode: InputMode = "natural"

    from_match = re.search(
        r"\bfrom\s+((?:@[^\s@:，,]+(?:\s+|，|,)?)+)",
        trimmed,
        flags=re.IGNORECASE,
    )
    if from_match:
        input_mode = "graph"
        from_clause = from_match.group(1)
        sources = []
        cursor = 0
        sorted_agents = sorted(KNOWN_AGENTS, key=len, reverse=True)
        while cursor < len(from_clause):
            if from_clause[cursor] != "@":
                cursor += 1
                continue
            rest = from_clause[cursor + 1 :]
            matched: str | None = None
            for agent in sorted_agents:
                if rest.lower().startswith(agent.lower()):
                    nxt = rest[len(agent) :] if len(agent) < len(rest) else ""
                    if nxt and not re.match(r"[\s，,]", nxt[0]):
                        continue
                    matched = agent
                    break
            if not matched:
                word = re.match(r"^([^\s@:，,]+)", rest)
                matched = word.group(1) if word else None
            if not matched:
                cursor += 1
                continue
            sources.append(_normalize_agent(matched))
            cursor += 1 + len(matched)
        before_from = trimmed[: from_match.start()]
        after_from = trimmed[from_match.end() :].lstrip(" :：")
        target_before_tokens = extract_at_tokens(before_from)
        agent_before = [v for kind, v in target_before_tokens if kind == "agent"]
        if agent_before:
            target = _normalize_agent(agent_before[-1])
            task = after_from.strip()
        else:
            after_tokens = extract_at_tokens(after_from)
            agent_after = [v for kind, v in after_tokens if kind == "agent"]
            if not agent_after:
                return None
            target = _normalize_agent(agent_after[0])
            rest_after = after_from
            for agent in sorted(KNOWN_AGENTS, key=len, reverse=True):
                if rest_after.lower().startswith(f"@{agent.lower()}"):
                    rest_after = rest_after[len(agent) + 1 :].lstrip(" :：")
                    break
            else:
                rest_after = re.sub(r"^@[^\s@:，,]+\s*", "", rest_after, count=1)
            task = rest_after.strip()
    else:
        agent_tokens = [v for kind, v in tokens if kind == "agent"]
        if not agent_tokens:
            return None
        target = _normalize_agent(agent_tokens[0])
        pattern = re.compile(rf"^@{re.escape(target)}\s*", re.IGNORECASE)
        task = pattern.sub("", trimmed, count=1).strip()
        if file_refs:
            sources = sources_from_file_refs(file_refs, file_meta_resolver=file_meta_resolver)
        if not sources:
            sources = [_normalize_agent(focused_agent)] if focused_agent else [WORKSPACE_SOURCE]

    if file_refs and input_mode == "graph":
        for src in sources_from_file_refs(file_refs, file_meta_resolver=file_meta_resolver):
            if src not in sources:
                sources.append(src)

    if not target:
        return None

    sources_key = ",".join(s.replace(" ", "") for s in sources) or "workspace"
    handoff_file = f"handoff-{sources_key}→{target.replace(' ', '')}.md"
    handoff_path = f".clutch/handoffs/{handoff_file}"

    chips = [
        DispatchChip(
            id=f"src_{i}",
            label=f"Lane · {name}" if name != WORKSPACE_SOURCE else "工作区摘要",
            on=True,
            source_name=name,
        )
        for i, name in enumerate(sources)
    ]

    return DispatchPreview(
        sources=sources,
        target=target,
        task=task,
        handoff_path=handoff_path,
        handoff_file=handoff_file,
        chips=chips,
        file_refs=file_refs,
        input_mode=input_mode,
    )
