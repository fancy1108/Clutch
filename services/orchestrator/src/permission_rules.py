"""D13 — per-command allow/ask/deny rules + dangerous-command force-ask."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

RuleAction = Literal["allow", "ask", "deny"]

_DANGEROUS_PATTERNS = (
    re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|--recursive)", re.I),
    re.compile(r"\bsudo\b", re.I),
    re.compile(r"\bchmod\s+777\b", re.I),
    re.compile(r"\bmkfs\b", re.I),
    re.compile(r"\bdd\s+if=", re.I),
    re.compile(r">\s*/dev/sd", re.I),
)

_SHELL_TOOL_NAMES = frozenset(
    {
        "run_terminal_cmd",
        "run_command",
        "shell",
        "bash",
        "execute",
        "terminal",
    }
)


def _rules_file() -> Path:
    from src.preferences_storage import preferences_dir

    path = preferences_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path / "permission_rules.json"


def load_permission_rules() -> list[dict[str, str]]:
    path = _rules_file()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rules: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return []
    for item in raw:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern") or "").strip()
        action = str(item.get("action") or "").strip().lower()
        if not pattern or action not in {"allow", "ask", "deny"}:
            continue
        rules.append({"pattern": pattern, "action": action})
    return rules


def save_permission_rules(rules: list[dict[str, Any]]) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for item in rules:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern") or "").strip()
        action = str(item.get("action") or "").strip().lower()
        if not pattern or action not in {"allow", "ask", "deny"}:
            continue
        cleaned.append({"pattern": pattern, "action": action})
    _rules_file().write_text(
        json.dumps(cleaned, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return cleaned


def extract_shell_command(tool_name: str, func_args: dict[str, Any]) -> str:
    basename = tool_name.lower().replace("-", "_").split("__")[-1]
    if basename not in _SHELL_TOOL_NAMES and "terminal" not in basename and "shell" not in basename:
        # still check common arg keys for aliased tools
        pass
    for key in ("command", "cmd", "script", "code"):
        raw = func_args.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return ""


def is_dangerous_command(command: str) -> bool:
    text = (command or "").strip()
    if not text:
        return False
    return any(pat.search(text) for pat in _DANGEROUS_PATTERNS)


def match_rule(command: str, rules: list[dict[str, str]] | None = None) -> RuleAction | None:
    text = (command or "").strip()
    if not text:
        return None
    for rule in rules if rules is not None else load_permission_rules():
        pattern = rule.get("pattern") or ""
        if not pattern:
            continue
        try:
            if re.search(pattern, text, flags=re.I):
                return rule["action"]  # type: ignore[return-value]
        except re.error:
            if pattern.lower() in text.lower():
                return rule["action"]  # type: ignore[return-value]
    return None


def resolve_tool_gate(
    *,
    tool_name: str,
    func_args: dict[str, Any],
    permission_mode: str,
    rules: list[dict[str, str]] | None = None,
) -> RuleAction | None:
    """
    Return an explicit gate override, or None to keep mode-default behaviour.

    - deny: block with tool error
    - ask: force approval pause (even in full / auto_edit)
    - allow: skip pause for this call
    """
    command = extract_shell_command(tool_name, func_args)
    ruled = match_rule(command, rules) if command else None
    if ruled == "deny":
        return "deny"
    if ruled == "ask" or (command and is_dangerous_command(command)):
        return "ask"
    if ruled == "allow":
        return "allow"
    # Catastrophic default even when no explicit rule: never silent-allow rm -rf /
    if command and is_dangerous_command(command) and permission_mode == "full":
        return "ask"
    return None
