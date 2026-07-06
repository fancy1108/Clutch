"""Shared CLI display names for Terminal Orchestra dispatch + lanes."""

from __future__ import annotations

CLI_TO_DISPLAY: dict[str, str] = {
    "claude-cli": "Claude Code",
    "opencode-cli": "OpenCode",
    "mimo-cli": "Mimo",
    "antigravity-cli": "Antigravity CLI",
    "codex-cli": "Codex CLI",
    "aider-cli": "Aider CLI",
    "codebuddy-cli": "CodeBuddy CLI",
    "cursor-cli": "Cursor",
    "rivet-cli": "Rivet CLI",
    "ollama-cli": "Ollama",
}

# Extra @-mention labels (longest-match wins in dispatch_parse).
DISPATCH_ALIASES: dict[str, str] = {
    "MiMo Code": "mimo-cli",
}

DISPLAY_TO_CLI: dict[str, str] = {v: k for k, v in CLI_TO_DISPLAY.items()}
DISPLAY_TO_CLI.update(DISPATCH_ALIASES)

KNOWN_DISPATCH_AGENTS = tuple(
    sorted({*CLI_TO_DISPLAY.values(), *DISPATCH_ALIASES.keys()}, key=len, reverse=True)
)
