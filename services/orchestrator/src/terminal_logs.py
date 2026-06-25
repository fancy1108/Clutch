"""Terminal log prefixes — neutral tags, not sample-flow role names."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

TAG_WORKFLOW = "WORKFLOW"
TAG_CHECK = "CHECK"
TAG_HUMAN = "HUMAN"

_CHINA_TZ = ZoneInfo("Asia/Shanghai")
_STAMPED_RE = re.compile(r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} CST\] ")


def china_log_timestamp() -> str:
    return datetime.now(_CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S CST")


def stamp_log_line(line: str) -> str:
    text = line.strip()
    if not text or _STAMPED_RE.match(text):
        return line
    return f"[{china_log_timestamp()}] {text}"


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
