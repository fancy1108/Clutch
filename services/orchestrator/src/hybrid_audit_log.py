"""Append-only JSONL audit for hybrid shell turns (HRT-05)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from src.storage_helper import get_storage_dir

HybridTurnResult = Literal["ok", "timeout", "empty", "error", "blocked", "rejected"]


@dataclass(frozen=True)
class HybridTurnAuditLine:
    run_id: str
    turn_id: str
    marker: str
    duration_ms: int
    result: HybridTurnResult
    cli_session_id: str | None
    agent: str
    command_summary: str
    node_id: str
    source: str
    level: str
    message: str
    timestamp: str


def get_hybrid_audit_dir() -> Path:
    return get_storage_dir() / "logs" / "hybrid"


def hybrid_audit_path_for_date(when: datetime | None = None) -> Path:
    dt = when or datetime.now(UTC)
    return get_hybrid_audit_dir() / f"{dt.strftime('%Y-%m-%d')}.jsonl"


def summarize_shell_command(cmd: str) -> str:
    """Redact prompt/system values; keep binary and flags for debugging."""
    summary = re.sub(
        r"CLUTCH_P='(?:[^'\\]|\\.|'\"'\"')*'",
        "CLUTCH_P='[redacted]'",
        cmd,
    )
    summary = re.sub(
        r"--append-system-prompt '(?:[^'\\]|\\.|'\"'\"')*'",
        "--append-system-prompt '[redacted]'",
        summary,
    )
    if len(summary) > 300:
        return summary[:297] + "..."
    return summary


def build_turn_audit_line(
    *,
    run_id: str,
    turn_id: str,
    marker: str,
    duration_ms: int,
    result: HybridTurnResult,
    cli_session_id: str | None,
    agent: str,
    command_summary: str,
    node_id: str,
    message: str,
    timestamp: datetime | None = None,
    source: str = "shell_exec_runtime",
    level: str | None = None,
) -> HybridTurnAuditLine:
    ts = timestamp or datetime.now(UTC)
    resolved_level = level or ("error" if result not in ("ok",) else "info")
    if result == "rejected":
        resolved_level = level or "warn"
    return HybridTurnAuditLine(
        run_id=run_id,
        turn_id=turn_id,
        marker=marker,
        duration_ms=duration_ms,
        result=result,
        cli_session_id=cli_session_id,
        agent=agent,
        command_summary=command_summary,
        node_id=node_id,
        source=source,
        level=resolved_level,
        message=message,
        timestamp=ts.isoformat(),
    )


def append_hybrid_turn_audit(
    line: HybridTurnAuditLine,
    *,
    path: Path | None = None,
) -> Path:
    target = path or hybrid_audit_path_for_date()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(line), ensure_ascii=False) + "\n")
    return target


def read_hybrid_audit_lines(
    *,
    run_id: str | None = None,
    limit: int = 50,
    audit_dir: Path | None = None,
) -> list[dict[str, object]]:
    """Return recent audit lines, newest last, optionally filtered by run_id."""
    root = audit_dir or get_hybrid_audit_dir()
    if not root.is_dir():
        return []

    files = sorted(root.glob("*.jsonl"))
    lines: list[dict[str, object]] = []
    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        for raw_line in text.splitlines():
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if run_id is not None and record.get("run_id") != run_id:
                continue
            lines.append(record)

    if limit <= 0:
        return lines
    return lines[-limit:]


def append_hybrid_rejection_audit(
    *,
    run_id: str,
    reason: str,
    message: str,
    node_id: str = "plain_chat",
) -> None:
    import uuid

    append_hybrid_turn_audit(
        build_turn_audit_line(
            run_id=run_id,
            turn_id=uuid.uuid4().hex[:8],
            marker="",
            duration_ms=0,
            result="rejected",
            cli_session_id=None,
            agent="hybrid",
            command_summary="",
            node_id=node_id,
            message=f"{reason}: {message}",
            source="orchestrator",
        )
    )
