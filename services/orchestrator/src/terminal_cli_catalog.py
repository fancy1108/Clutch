"""Shared CLI display names for Terminal Orchestra dispatch + lanes."""

from __future__ import annotations

CLI_TO_DISPLAY: dict[str, str] = {
    "claude-cli": "Claude Code",
    "opencode-cli": "OpenCode",
    "antigravity-cli": "Antigravity CLI",
    "codex-cli": "Codex CLI",
    "aider-cli": "Aider CLI",
    "codebuddy-cli": "CodeBuddy CLI",
    "rivet-cli": "Rivet CLI",
    "ollama-cli": "Ollama",
}

DISPLAY_TO_CLI: dict[str, str] = {v: k for k, v in CLI_TO_DISPLAY.items()}

KNOWN_DISPATCH_AGENTS = tuple(CLI_TO_DISPLAY.values())
