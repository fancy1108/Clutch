"""B-38: stop no-progress read/grep/list loops (same tool + same args)."""

from __future__ import annotations

import os
from typing import Any, Literal

from src.run_control import short_tool_name

READISH = frozenset({"read_file", "list_dir", "grep", "read_skill"})
Verdict = Literal["ok", "nudge", "stop"]


def repeat_limit() -> int:
    raw = os.environ.get("CLUTCH_PROGRESS_REPEAT", "3")
    try:
        return max(2, int(raw))
    except ValueError:
        return 3


def fingerprint(tool_name: str, arguments: dict[str, Any] | None) -> str | None:
    short = short_tool_name(tool_name)
    if short not in READISH:
        return None
    args = arguments if isinstance(arguments, dict) else {}
    if short == "grep":
        key = (str(args.get("pattern") or "").strip(), str(args.get("path") or ".").strip() or ".")
    elif short == "read_skill":
        key = (str(args.get("key") or args.get("path") or "").strip(),)
    elif short == "read_file":
        key = (
            str(args.get("path") or "").strip(),
            str(args.get("offset") or ""),
            str(args.get("limit") or ""),
        )
    else:
        key = (str(args.get("path") or ".").strip() or ".",)
    return f"{short}:" + "|".join(key)


def progress_nudge(tool_name: str) -> str:
    short = short_tool_name(tool_name) or "this tool"
    return (
        f"[System reminder] You already called `{short}` with the same arguments. "
        "Do not repeat that read. Edit, answer, or inspect a different path."
    )


def progress_stop_result(tool_name: str) -> str:
    from src.preferences_storage import tr

    short = short_tool_name(tool_name) or "tool"
    return tr(
        f"No-progress loop: `{short}` was repeated with the same arguments. "
        "Run stopped — click Continue or send a new message.",
        f"无进展循环：`{short}` 用同一参数重复调用。运行已停止，可点「继续」或发送新消息。",
    )


class ProgressTracker:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def _verdict(self, used: int) -> Verdict:
        hard = repeat_limit()
        if used >= hard:
            return "stop"
        if used == hard - 1:
            return "nudge"
        return "ok"

    def peek(self, tool_name: str, arguments: dict[str, Any] | None) -> Verdict:
        fp = fingerprint(tool_name, arguments)
        if not fp:
            return "ok"
        return self._verdict(self._counts.get(fp, 0) + 1)

    def observe(self, tool_name: str, arguments: dict[str, Any] | None) -> Verdict:
        fp = fingerprint(tool_name, arguments)
        if not fp:
            return "ok"
        self._counts[fp] = self._counts.get(fp, 0) + 1
        return self._verdict(self._counts[fp])
