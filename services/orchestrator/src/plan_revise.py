"""D31 — parse plan revise payloads with per-step comments."""

from __future__ import annotations

import json
from typing import Any


def parse_plan_revise_instructions(instructions: str) -> tuple[str, list[dict[str, Any]]]:
    raw = (instructions or "").strip()
    if not raw:
        return "", []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw, []
    if not isinstance(payload, dict):
        return raw, []
    note = str(payload.get("note") or "").strip()
    annotations: list[dict[str, Any]] = []
    raw_comments = payload.get("stepComments")
    if isinstance(raw_comments, list):
        for item in raw_comments:
            if not isinstance(item, dict):
                continue
            comment = str(item.get("comment") or "").strip()
            if not comment:
                continue
            annotations.append(
                {
                    "step": int(item.get("step") or 0),
                    "text": str(item.get("text") or "").strip(),
                    "comment": comment,
                }
            )
    return note, annotations


def align_step_comments(steps: list[str], annotations: list[dict[str, Any]]) -> list[str]:
    aligned = [""] * len(steps)
    for ann in annotations:
        try:
            idx = int(ann.get("step") or 0) - 1
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(aligned):
            aligned[idx] = str(ann.get("comment") or "").strip()
    return aligned


def format_plan_feedback(note: str, annotations: list[dict[str, Any]]) -> str:
    lines = [note] if note else []
    for ann in annotations:
        step_no = ann.get("step")
        text = ann.get("text") or ""
        comment = ann.get("comment") or ""
        prefix = f"Step {step_no}"
        if text:
            prefix += f" ({text})"
        lines.append(f"{prefix}: {comment}")
    return "\n".join(lines).strip()
