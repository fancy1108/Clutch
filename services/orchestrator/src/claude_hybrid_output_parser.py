"""Normalize raw bash PTY output from Hybrid `claude -p` turns for chat UI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

OutputEventType = Literal[
    "assistant",
    "tool",
    "shell_echo",
    "system_prompt",
    "boundary_marker",
    "ansi",
    "debug",
    "stderr",
]

ANSI_RE = re.compile(
    r"\x1B(?:"
    r"[@-Z\\-_0-9]"
    r"|\[[0-?]*[ -/]*[@-~]"
    r"|\][^\x07]*(?:\x07|\x1B\\)"
    r"|\([A-Z0-9]"
    r")"
)
_BACKSPACE = "\b"
_PREAMBLE_RE = re.compile(r"CLUTCH_P=.*?echo\s+(__CLUTCH_[A-Z0-9_]+__)", re.DOTALL | re.IGNORECASE)
_SYSTEM_PROMPT_RE = re.compile(
    r"--append-system-prompt\s+'((?:[^']|'\"'\"')*)'",
    re.DOTALL | re.IGNORECASE,
)
_NOISE_LINE_RE = re.compile(
    r"^(?:clutch\$|CLUTCH_P=|--(?:append-system-prompt|session-id|resume|conversation|dangerously-skip-permissions)\b|"
    r".*(?:claude|agy) -p.*|.*__CLUTCH_.*|.*append-system-prompt.*)$",
    re.I,
)


@dataclass(frozen=True)
class OutputEvent:
    type: OutputEventType
    visible: bool
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "visible": self.visible, "content": self.content}


@dataclass(frozen=True)
class HybridParseResult:
    raw: str
    assistant: str
    events: tuple[OutputEvent, ...]

    def output_event_dicts(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.events]


def strip_ansi(text: str) -> str:
    prev = None
    out = text
    while out != prev:
        prev = out
        out = ANSI_RE.sub("", out)
    return out.replace("\x0f", "").replace("\x07", "")


def _erase_backspaces(text: str) -> str:
    out: list[str] = []
    for ch in text:
        if ch == _BACKSPACE:
            if out:
                out.pop()
            continue
        out.append(ch)
    return "".join(out)


def _unshell_single_quoted(value: str) -> str:
    return value.replace("'\"'\"'", "'")


def _strip_shell_preamble(text: str, *, marker: str) -> str:
    pattern = re.compile(
        rf"CLUTCH_P=.*?echo\s+{re.escape(marker)}",
        re.DOTALL | re.IGNORECASE,
    )
    return pattern.sub("", text, count=1)


def _normalize_output_line(line: str) -> str:
    clean = strip_ansi(line).strip()
    while clean.startswith(">"):
        clean = clean[1:].strip()
    return clean


def _is_noise_line(line: str) -> bool:
    clean = _normalize_output_line(line)
    if not clean:
        return True
    if _NOISE_LINE_RE.match(clean):
        return True
    lowered = clean.lower()
    if "when asked who you are" in lowered:
        return True
    if "identify yourself as" in lowered:
        return True
    if lowered.startswith("runtime model:"):
        return True
    if "custom agent prompt" in lowered:
        return True
    if "define custom parameters or directives" in lowered:
        return True
    if "process orchestration" in lowered and clean.startswith("- "):
        return True
    if clean.startswith("#"):
        return True
    if clean.startswith("- ") and "task validation" in lowered:
        return True
    if "treat every instruction in the agent protocol" in lowered:
        return True
    if "runtime model" in lowered and "protocol" in lowered:
        return True
    if clean.startswith("You are ") and (
        "Clutch workspace" in clean or "active agent" in clean
    ):
        return True
    if lowered.startswith("workspace root:"):
        return True
    if not re.search(r"[\w\u4e00-\u9fff]", clean):
        return True
    if re.fullmatch(r"[\d;]+", clean.strip()):
        return True
    return False


def _extract_shell_echo(text: str, *, marker: str) -> str | None:
    match = _PREAMBLE_RE.search(text)
    if not match or match.group(1) != marker:
        return None
    echo = strip_ansi(_erase_backspaces(match.group(0))).replace("\r", "").strip()
    return echo or None


def _summarize_shell_echo(shell_echo: str) -> str:
    """Omit embedded system prompt body from shell echo shown in UI blocks."""
    summarized = _SYSTEM_PROMPT_RE.sub(
        "--append-system-prompt '<see System prompt>'",
        shell_echo,
        count=1,
    )
    return summarized.strip()


def _extract_system_prompt(shell_echo: str | None) -> str | None:
    if not shell_echo:
        return None
    match = _SYSTEM_PROMPT_RE.search(shell_echo)
    if not match:
        return None
    prompt = _unshell_single_quoted(match.group(1)).strip()
    return prompt or None


def _extract_assistant_lines(body: str) -> str:
    lines: list[str] = []
    for ln in body.splitlines():
        clean = _normalize_output_line(ln)
        if clean and not _is_noise_line(clean):
            lines.append(clean)
    return "\n".join(lines).strip()


class ClaudeHybridOutputParser:
    """Raw shell PTY output → assistant text + structured debug events."""

    def parse_structured(
        self,
        raw: str,
        *,
        marker: str,
        shell_command: str | None = None,
        system_prompt: str | None = None,
    ) -> HybridParseResult:
        events: list[OutputEvent] = []
        if marker not in raw:
            return HybridParseResult(raw=raw, assistant="", events=tuple(events))

        normalized = _erase_backspaces(strip_ansi(raw)).replace("\r", "")
        shell_echo = _extract_shell_echo(normalized, marker=marker) or shell_command
        if shell_echo:
            events.append(
                OutputEvent(
                    type="shell_echo",
                    visible=False,
                    content=_summarize_shell_echo(shell_echo),
                )
            )

        parsed_prompt = _extract_system_prompt(shell_echo) or (system_prompt or "").strip() or None
        if parsed_prompt:
            events.append(OutputEvent(type="system_prompt", visible=False, content=parsed_prompt))

        end = normalized.rfind(marker)
        body = _strip_shell_preamble(normalized[:end], marker=marker) if end >= 0 else ""
        assistant = _extract_assistant_lines(body)
        events.append(OutputEvent(type="boundary_marker", visible=False, content=marker))
        if assistant:
            events.append(OutputEvent(type="assistant", visible=True, content=assistant))
        return HybridParseResult(raw=raw, assistant=assistant, events=tuple(events))

    def parse(self, raw: str, *, marker: str) -> str:
        return self.parse_structured(raw, marker=marker).assistant


_default_parser = ClaudeHybridOutputParser()


def parse_hybrid_claude_output(raw: str, *, marker: str) -> str:
    return _default_parser.parse(raw, marker=marker)
