"""Normalize raw bash PTY output from Hybrid `claude -p` turns for chat UI."""

from __future__ import annotations

import json
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
    r"^(?:clutch\$|CLUTCH_P=|--(?:append-system-prompt|session-id|resume|conversation|dangerously-skip-permissions|"
    r"skip-git-repo-check|dangerously-bypass-approvals-and-sandbox|json)\b|"
    r".*(?:claude|agy) -p.*|.*__CLUTCH_.*|.*append-system-prompt.*|"
    r".*\bcodex exec\b.*)$",
    re.I,
)
_SHELL_LEAK_RE = re.compile(
    r"CLUTCH_P=|(?:claude|agy)\s+-p\b|dangerously-skip-permissions|__CLUTCH_",
    re.I,
)
_CODEX_STDERR_RE = re.compile(
    r"(?:\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\s+\w+\s+codex_core::|"
    r"failed to load skill|missing field description)",
    re.IGNORECASE,
)
_CODEX_TOKEN_COUNT_RE = re.compile(r"^[\d,]+$")
_MARKER_LINE_PATTERNS: dict[str, re.Pattern[str]] = {}
_CLI_ISSUE_LINE_MARKERS = (
    "individual quota reached",
    "quota reached",
    "rate limit",
    "authentication required",
    "authentication timed out",
    "please visit the url to log in",
    "paste the authorization code",
    "waiting for authentication",
    "not signed in",
    "not logged in",
    "login required",
    "upgrade your subscription",
    "timed out waiting for response",
    "timed out waiting",
)
_QUOTA_MESSAGE_RE = re.compile(
    r"Individual quota reached\.[^\n]*(?:Resets in[^\n.]*)?",
    re.IGNORECASE,
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


def _marker_line_pattern(marker: str) -> re.Pattern[str]:
    cached = _MARKER_LINE_PATTERNS.get(marker)
    if cached is not None:
        return cached
    pattern = re.compile(
        rf"(?:^|[\r\n]+)\s*({re.escape(marker)})\s*(?:[\r\n]+|$)",
        re.MULTILINE,
    )
    _MARKER_LINE_PATTERNS[marker] = pattern
    return pattern


def marker_completed_in_output(raw: str, marker: str) -> bool:
    """True when bash finished `echo <marker>` and the shell prompt returned."""
    plain = _erase_backspaces(strip_ansi(raw)).replace("\r", "\n")
    # After claude -p, marker is often glued to ANSI residue (e.g. `0;__CLUTCH_DONE_x__`)
    # or followed by the clutch$ prompt — not always on a clean standalone line.
    if re.search(rf"{re.escape(marker)}\s*(?:\n\s*)*clutch\$", plain):
        return True
    if _marker_line_pattern(marker).search(plain):
        return True
    return plain.count(marker) >= 2


def _last_standalone_marker_index(normalized: str, marker: str) -> int:
    last = -1
    for match in _marker_line_pattern(marker).finditer(normalized):
        last = match.start(1)
    clutch_match = re.search(rf"({re.escape(marker)})\s*(?:\n\s*)*clutch\$", normalized)
    if clutch_match:
        last = max(last, clutch_match.start(1))
    return last


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
    if "clutch_p" in lowered or "$clutch_p" in lowered:
        return True
    if "skip-permission" in lowered or "dangerously-skip" in lowered:
        return True
    if "/bin/claude" in lowered or "/bin/agy" in lowered or ".nvm/" in lowered:
        return True
    if re.search(r";\s*echo\s*$", clean, re.I):
        return True
    if "when asked who you are" in lowered:
        return True
    if "identify yourself as" in lowered:
        return True
    if "for conversational questions" in lowered:
        return True
    if "do not scan or modify the workspace" in lowered:
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
    if lowered.startswith("task summary:"):
        return True
    if lowered.startswith("working directory:"):
        return True
    if lowered.startswith("open todos:"):
        return True
    if clean.startswith("[Clutch session context]"):
        return True
    if clean in ("{", "}", "},", "[", "]"):
        return False
    if not re.search(r"[\w\u4e00-\u9fff]", clean):
        return True
    if re.fullmatch(r"[\d;]+", clean.strip()):
        return True
    if re.match(r"^(Assistant|User):\s", clean):
        return True
    if "since the last assistant message" in lowered:
        return True
    if "if you were asked to wait" in lowered:
        return True
    if "reached via the main channel" in lowered:
        return True
    if "take a look at the main channel" in lowered:
        return True
    if lowered.startswith("reasoning summaries:"):
        return True
    if lowered.startswith("session id:"):
        return True
    if lowered == "user" or lowered == "codex":
        return True
    if lowered.startswith("user request:"):
        return True
    if lowered.startswith("tokens used"):
        return True
    if _CODEX_TOKEN_COUNT_RE.match(clean):
        return True
    if "reading additional input from stdin" in lowered:
        return True
    if "model metadata for" in lowered and "not found" in lowered:
        return True
    if _CODEX_STDERR_RE.search(clean):
        return True
    if clean.startswith("{") and '"type"' in clean:
        return True
    return False


def _sanitize_assistant(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    if _SHELL_LEAK_RE.search(cleaned):
        return ""
    return cleaned


def _collapse_match_whitespace(text: str) -> str:
    return re.sub(r"\s+", "", text)


def extract_trailing_json_object(text: str) -> str | None:
    """Return the last parseable JSON object in CLI PTY output (e.g. agy echo + JSON)."""
    plain = _erase_backspaces(strip_ansi(text)).replace("\r", "")
    start = plain.rfind("{")
    while start >= 0:
        depth = 0
        for idx in range(start, len(plain)):
            ch = plain[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = plain[start : idx + 1]
                    try:
                        obj = json.loads(candidate)
                    except json.JSONDecodeError:
                        break
                    if isinstance(obj, dict) and obj:
                        return json.dumps(obj, ensure_ascii=False, indent=2)
                    break
        start = plain.rfind("{", 0, max(0, start - 1))
    return None


def _strip_echoed_protocol_lines(
    assistant: str,
    *,
    system_prompt: str | None,
    user_prompt: str | None,
) -> str:
    """Drop leading lines that match echoed system/user prompt (PTY whitespace tolerant)."""
    sp_norm = _collapse_match_whitespace(system_prompt or "")
    user_norm = _collapse_match_whitespace(user_prompt or "")
    kept: list[str] = []
    skipping = True
    for line in assistant.splitlines():
        clean = _normalize_output_line(line)
        if not clean:
            if not skipping:
                kept.append(line)
            continue
        line_norm = _collapse_match_whitespace(clean)
        if skipping:
            if sp_norm and line_norm and line_norm in sp_norm:
                continue
            if user_norm and line_norm and line_norm in user_norm:
                continue
            if clean.lower().startswith("user request:"):
                continue
            if clean == "JSON":
                continue
            skipping = False
        kept.append(line)
    return "\n".join(kept).strip()


def sanitize_assistant_cli_output(
    assistant: str,
    *,
    raw_body: str = "",
    system_prompt: str | None = None,
    user_prompt: str | None = None,
) -> str:
    """Prefer structured CLI payload over echoed embedded prompts in chat UI."""
    for source in (raw_body, assistant):
        if not source.strip():
            continue
        json_payload = extract_trailing_json_object(source)
        if json_payload:
            return json_payload

    text = strip_leading_embedded_prompt(
        assistant,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    text = _strip_echoed_protocol_lines(
        text,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    return strip_leading_embedded_prompt(
        text,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    ).strip()


def strip_leading_embedded_prompt(
    output: str,
    *,
    system_prompt: str | None = None,
    user_prompt: str | None = None,
) -> str:
    """Remove CLI echo of embedded system/user prompt prefix from assistant-visible text."""
    text = output.strip()
    if not text:
        return text

    sp = (system_prompt or "").strip()
    if sp:
        if text.startswith(sp):
            text = text[len(sp) :].lstrip()
        elif sp in text:
            # agy sometimes repeats the protocol before the actual answer
            idx = text.find(sp)
            if idx >= 0 and idx < min(200, len(text) // 2):
                text = text[idx + len(sp) :].lstrip()

    if user_prompt:
        embedded_user = f"User Request:\n{user_prompt.strip()}"
        if text.startswith(embedded_user):
            text = text[len(embedded_user) :].lstrip()
        elif text.startswith("User Request:"):
            text = text.split("\n", 1)[-1].lstrip() if "\n" in text else ""

    return text.strip()


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


def extract_cli_issue_message(raw: str) -> str | None:
    """Return a user-visible agy/CLI failure line (quota, auth, etc.) from raw PTY output."""
    normalized = _erase_backspaces(strip_ansi(raw)).replace("\r", "\n")
    quota_match = _QUOTA_MESSAGE_RE.search(normalized)
    if quota_match:
        return quota_match.group(0).strip()
    for ln in normalized.splitlines():
        clean = _normalize_output_line(ln)
        if not clean:
            continue
        lowered = clean.lower()
        if any(marker in lowered for marker in _CLI_ISSUE_LINE_MARKERS):
            return clean
    return None


def parse_codex_jsonl_output(text: str) -> str | None:
    """Extract the last Codex agent_message from `codex exec --json` JSONL stdout."""
    messages: list[str] = []
    for line in text.splitlines():
        clean = strip_ansi(line).strip()
        if not clean.startswith("{"):
            continue
        try:
            obj = json.loads(clean)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "item.completed":
            continue
        item = obj.get("item")
        if not isinstance(item, dict):
            continue
        if item.get("type") != "agent_message":
            continue
        body = str(item.get("text", "")).strip()
        if body:
            messages.append(body)
    return messages[-1] if messages else None


def extract_codex_assistant_output(raw: str, *, marker: str | None = None) -> str:
    """Parse Codex hybrid or subprocess output (JSONL preferred, TUI fallback)."""
    normalized = _erase_backspaces(strip_ansi(raw)).replace("\r", "")
    body = normalized
    if marker and marker in normalized:
        end = _last_standalone_marker_index(normalized, marker)
        if end < 0:
            end = normalized.rfind(marker)
        body = _strip_shell_preamble(normalized[:end], marker=marker) if end >= 0 else normalized

    json_text = parse_codex_jsonl_output(body) or parse_codex_jsonl_output(normalized)
    if json_text:
        return json_text

    tui = _sanitize_assistant(_extract_assistant_lines(body))
    if tui:
        return tui
    issue = extract_cli_issue_message(raw)
    return issue or ""


def extract_tty_cli_output(raw: str) -> str:
    """Strip TUI/PTY noise and return assistant text from a headless CLI capture."""
    if "codex exec" in raw.lower() or '"agent_message"' in raw:
        codex = extract_codex_assistant_output(raw)
        if codex:
            return codex
    normalized = _erase_backspaces(strip_ansi(raw)).replace("\r", "")
    assistant = _sanitize_assistant(_extract_assistant_lines(normalized))
    if assistant:
        return assistant
    issue = extract_cli_issue_message(raw)
    return issue or ""


def _extract_assistant_lines(body: str) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for ln in body.splitlines():
        clean = _normalize_output_line(ln)
        if clean and not _is_noise_line(clean):
            if clean in seen:
                continue
            seen.add(clean)
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
        user_prompt: str | None = None,
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

        end = _last_standalone_marker_index(normalized, marker)
        if end < 0:
            end = normalized.rfind(marker)
        body = _strip_shell_preamble(normalized[:end], marker=marker) if end >= 0 else ""
        assistant = _sanitize_assistant(_extract_assistant_lines(body))
        assistant = sanitize_assistant_cli_output(
            assistant,
            raw_body=body,
            system_prompt=parsed_prompt or system_prompt,
            user_prompt=user_prompt,
        )
        events.append(OutputEvent(type="boundary_marker", visible=False, content=marker))
        if assistant:
            events.append(OutputEvent(type="assistant", visible=True, content=assistant))
        return HybridParseResult(raw=raw, assistant=assistant, events=tuple(events))

    def parse(self, raw: str, *, marker: str) -> str:
        return self.parse_structured(raw, marker=marker).assistant


_default_parser = ClaudeHybridOutputParser()


def parse_hybrid_claude_output(raw: str, *, marker: str) -> str:
    return _default_parser.parse(raw, marker=marker)
