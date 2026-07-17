"""Local AI tool detection and user connection preferences.

Scans a built-in candidate set covering both AI CLI binaries (via PATH) and
macOS desktop clients (via /Applications). Only candidates actually present on
the machine are surfaced. Connection state is a persisted preference flag — it
does not yet drive execution routing for desktop clients.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

CLI_CANDIDATES: list[dict[str, str]] = [
    {
        "id": "claude-cli",
        "name": "Claude Code CLI",
        "binary": "claude",
        "description": "Terminal-based Claude Code for scripting and local agent execution.",
        "icon": "terminal",
    },
    {
        "id": "agy-cli",
        "name": "Antigravity CLI",
        "binary": "agy",
        "description": "Antigravity command-line agent runtime.",
        "icon": "terminal",
    },
    {
        "id": "codex-cli",
        "name": "Codex CLI",
        "binary": "codex",
        "description": "Codex command-line coding agent.",
        "icon": "terminal",
    },
    {
        "id": "code-cli",
        "name": "VS Code CLI",
        "binary": "code",
        "description": "Visual Studio Code command-line interface.",
        "icon": "terminal",
    },
    {
        "id": "codeium-cli",
        "name": "Codeium CLI",
        "binary": "codeium",
        "description": "Codeium command-line assistant.",
        "icon": "terminal",
    },
    {
        "id": "aider-cli",
        "name": "Aider",
        "binary": "aider",
        "description": "Aider AI pair programmer in the terminal.",
        "icon": "terminal",
    },
    {
        "id": "gemini-cli",
        "name": "Gemini CLI",
        "binary": "gemini",
        "description": "Google Gemini command-line interface.",
        "icon": "terminal",
    },
    {
        "id": "ollama-cli",
        "name": "Ollama",
        "binary": "ollama",
        "description": "Local model runner and CLI.",
        "icon": "terminal",
    },
    {
        "id": "cursor-cli",
        "name": "Cursor Agent CLI",
        "binary": "cursor-agent",
        "binary_aliases": "agent",
        "description": "Cursor Agent for terminal workflows (curl cursor.com/install).",
        "icon": "terminal",
    },
    {
        "id": "rivet-cli",
        "name": "Rivet CLI (天枢)",
        "binary": "rivet",
        "description": "Tianshu (天枢) terminal AI agent runtime.",
        "icon": "terminal",
    },
    {
        "id": "opencode-cli",
        "name": "OpenCode CLI",
        "binary": "opencode",
        "description": "Open-source AI coding agent for the terminal.",
        "icon": "terminal",
    },
    {
        "id": "mimo-cli",
        "name": "MiMo Code CLI",
        "binary": "mimo",
        "description": "Xiaomi MiMo Code terminal-native AI coding agent (OpenCode fork).",
        "icon": "terminal",
    },
    {
        "id": "amazon-q-cli",
        "name": "Amazon Q Developer CLI",
        "binary": "q",
        "description": "Legacy Amazon Q Developer terminal agent (superseded by Kiro CLI).",
        "icon": "terminal",
    },
    {
        "id": "amp-cli",
        "name": "Amp CLI",
        "binary": "amp",
        "description": "Sourcegraph Amp frontier coding agent for the terminal.",
        "icon": "terminal",
    },
    {
        "id": "continue-cli",
        "name": "Continue CLI",
        "binary": "cn",
        "description": "Continue modular coding agent for context engineering and automation.",
        "icon": "terminal",
    },
    {
        "id": "copilot-cli",
        "name": "GitHub Copilot CLI",
        "binary": "copilot",
        "description": "GitHub-native agentic CLI for issues, PRs, and terminal workflows.",
        "icon": "terminal",
    },
    {
        "id": "crush-cli",
        "name": "Crush CLI",
        "binary": "crush",
        "description": "Charm Bracelet AI coding assistant TUI with MCP and LSP support.",
        "icon": "terminal",
    },
    {
        "id": "droid-cli",
        "name": "Factory Droid CLI",
        "binary": "droid",
        "description": "Factory AI Droid agent-native development CLI.",
        "icon": "terminal",
    },
    {
        "id": "goose-cli",
        "name": "Goose CLI",
        "binary": "goose",
        "description": "AAIF Goose open-source extensible AI agent with MCP and recipes.",
        "icon": "terminal",
    },
    {
        "id": "gptme-cli",
        "name": "gptme",
        "binary": "gptme",
        "description": "Personal AI assistant in the terminal with tool use and sessions.",
        "icon": "terminal",
    },
    {
        "id": "kiro-cli",
        "name": "Kiro CLI",
        "binary": "kiro-cli",
        "description": "Kiro AI coding agent (successor to Amazon Q Developer CLI).",
        "icon": "terminal",
    },
    {
        "id": "openclaw-cli",
        "name": "OpenClaw CLI",
        "binary": "openclaw",
        "description": "OpenClaw AI agent CLI with plugins and daemon onboarding.",
        "icon": "terminal",
    },
    {
        "id": "qwen-code-cli",
        "name": "Qwen Code CLI",
        "binary": "qwen",
        "description": "Qwen open-source AI coding agent for the terminal.",
        "icon": "terminal",
    },
    {
        "id": "codebuddy-cli",
        "name": "CodeBuddy CLI",
        "binary": "codebuddy",
        "description": "Tencent Cloud CodeBuddy AI coding agent for the terminal (codebuddy / cbc).",
        "icon": "terminal",
    },
    {
        "id": "zcode-cli",
        "name": "ZCode CLI",
        "binary": "zcode",
        "description": "Z.AI ZCode headless coding agent (GLM-family). Ships with the ZCode desktop app; expose the CJS entry via a `zcode` shim on PATH.",
        "icon": "terminal",
    },
    {
        "id": "qoder-cli",
        "name": "Qoder CLI",
        "binary": "qodercli",
        "description": "Qoder AI coding agent for the terminal (curl qoder.com/install).",
        "icon": "terminal",
    },
]

# Primary install recommendations (tested Clutch routing). Other whitelist CLIs are
# scanned when installed but omitted from the default install catalog until detected.
RECOMMENDED_CLI_IDS: frozenset[str] = frozenset(
    {
        "codebuddy-cli",
        "cursor-cli",
        "mimo-cli",
        "opencode-cli",
        "claude-cli",
        "ollama-cli",
        "codex-cli",
        "agy-cli",
        "zcode-cli",
        "qoder-cli",
    }
)

# macOS desktop client candidates probed under /Applications and ~/Applications.
CLIENT_CANDIDATES: list[dict[str, str]] = []


TOOLS_ENV = "CLUTCH_TOOLS_CONFIG"

_CLI_EXTRA_BIN_DIRS: tuple[Path, ...] = (
    Path.home() / ".local" / "bin",
    Path.home() / ".npm-global" / "bin",
    Path.home() / ".opencode" / "bin",
    Path.home() / ".mimocode" / "bin",
    Path.home() / ".openclaw" / "bin",
    Path.home() / ".qoder" / "bin",
    Path.home() / "bin",
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
    Path("/Applications/ChatGPT.app/Contents/Resources"),
    Path("/Applications/Codex.app/Contents/Resources"),
)


def _extra_cli_search_dirs() -> list[Path]:
    dirs = list(_CLI_EXTRA_BIN_DIRS)
    nvm_root = Path.home() / ".nvm" / "versions" / "node"
    if nvm_root.is_dir():
        for version_dir in sorted(nvm_root.iterdir(), reverse=True):
            if version_dir.is_dir():
                dirs.append(version_dir / "bin")
    return dirs


def config_path() -> Path:
    override = os.environ.get(TOOLS_ENV)
    if override:
        return Path(override)
    from src.storage_helper import get_storage_dir
    return get_storage_dir() / "tools.json"


def _cli_path(binary: str) -> str | None:
    found = shutil.which(binary)
    return found


def _client_path(app_name: str) -> str | None:
    if sys.platform != "darwin":
        return None
    candidates = [
        Path("/Applications") / app_name,
        Path.home() / "Applications" / app_name,
    ]
    for path in candidates:
        if path.is_dir():
            return str(path)
    return None


def _candidate_by_id(tool_id: str) -> dict[str, str] | None:
    for cand in CLI_CANDIDATES + CLIENT_CANDIDATES:
        if cand["id"] == tool_id:
            return cand
    return None


def _binary_names(cand: dict[str, str]) -> list[str]:
    names = [cand["binary"]]
    aliases = cand.get("binary_aliases", "")
    if aliases:
        names.extend(part.strip() for part in aliases.split(",") if part.strip())
    return names


def _resolve_path(tool_id: str) -> str | None:
    cand = _candidate_by_id(tool_id)
    if cand is None:
        return None
    if "binary" in cand:
        for binary in _binary_names(cand):
            found = _cli_path(binary)
            if found:
                return found
        return None
    return _client_path(cand["app_name"])


def _mimo_preferred_binary() -> str | None:
    """Prefer the official curl installer over the npm wrapper (postinstall may be blocked)."""
    preferred = Path.home() / ".mimocode" / "bin" / "mimo"
    if preferred.is_file() and os.access(preferred, os.X_OK):
        return str(preferred)
    return None


def _is_mimo_npm_shim(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return "@mimo-ai/cli" in normalized or normalized.endswith("/.bin/mimo")


def _should_prefer_mimocode_binary(resolved: str, preferred: str) -> bool:
    if _is_mimo_npm_shim(resolved):
        return True
    try:
        if os.path.samefile(resolved, preferred):
            return False
    except OSError:
        pass
    try:
        # npm ships a small launcher script; curl install is the full binary.
        return Path(resolved).stat().st_size < 20_000
    except OSError:
        return False


def resolve_tool_binary(tool_id: str) -> str | None:
    """Resolve CLI binary path, including common install dirs when PATH is narrow."""
    direct = _resolve_path(tool_id)
    if direct and tool_id != "mimo-cli":
        return direct
    cand = _candidate_by_id(tool_id)
    resolved = direct
    if cand is not None and "binary" in cand:
        if not resolved:
            for binary in _binary_names(cand):
                for directory in _extra_cli_search_dirs():
                    candidate = directory / binary
                    if candidate.is_file() and os.access(candidate, os.X_OK):
                        resolved = str(candidate)
                        break
                if resolved:
                    break
    if tool_id == "mimo-cli":
        preferred = _mimo_preferred_binary()
        if preferred:
            if not resolved:
                return preferred
            if _should_prefer_mimocode_binary(resolved, preferred):
                return preferred
    return resolved


def tool_available_for_routing(tool_id: str) -> bool:
    if resolve_tool_binary(tool_id):
        return True
    return tool_id in load_connected_ids()


def _is_claude_installed() -> bool:
    return _cli_path("claude") is not None


def _installed(tool_id: str) -> bool:
    cand = _candidate_by_id(tool_id)
    if cand is None:
        return False
    if "binary" in cand:
        return resolve_tool_binary(tool_id) is not None
    return _resolve_path(tool_id) is not None


def resolve_agent_type_for_tool(tool_id: str) -> str | None:
    """Map a tools panel id (e.g. agy-cli, ollama-cli) to the routing agent_type key."""
    from src.agent_type import AGENT_TYPES, normalize_agent_type
    from src.engine_router import CLI_ROUTING_CONFIGS
    from src.provider_registry import resolve_provider_spec
    from src.runtime_strategy import RuntimeStrategy

    key = tool_id.strip()
    for agent_type, cfg in CLI_ROUTING_CONFIGS.items():
        if isinstance(cfg, dict) and cfg.get("tool_id") == key:
            return agent_type
    if key in CLI_ROUTING_CONFIGS:
        return key

    normalized = normalize_agent_type(key)
    if normalized != "clutch":
        if normalized in AGENT_TYPES or normalized in CLI_ROUTING_CONFIGS:
            return normalized
        spec = resolve_provider_spec(normalized)
        if spec.runtime_strategy == RuntimeStrategy.HTTP_DAEMON:
            return normalized

    return None


def load_connected_ids() -> set[str]:
    path = config_path()
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    connected = data.get("connected")
    if not isinstance(connected, list):
        return set()
    known = {cand["id"] for cand in CLI_CANDIDATES + CLIENT_CANDIDATES}
    return {str(item) for item in connected if item in known}


def save_connected_ids(connected: set[str]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"connected": sorted(connected)}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def list_tools_status(*, include_all: bool = False) -> list[dict[str, Any]]:
    from src.engine_router import CLI_ROUTING_CONFIGS
    from src.agent_type import normalize_agent_type
    from src.provider_registry import resolve_provider_spec
    from src.runtime_strategy import RuntimeStrategy

    # Build a set of all tool_ids covered by CLI_ROUTING_CONFIGS entries.
    # Keys in CLI_ROUTING_CONFIGS are agent_type strings (e.g. "antigravity-cli"),
    # while the inner "tool_id" field is the canonical id (e.g. "agy-cli").
    # We need both directions for a correct lookup.
    registered_tool_ids: set[str] = set()
    for agent_type_key, cfg in CLI_ROUTING_CONFIGS.items():
        registered_tool_ids.add(agent_type_key)          # e.g. "antigravity-cli"
        if isinstance(cfg, dict) and "tool_id" in cfg:
            registered_tool_ids.add(cfg["tool_id"])      # e.g. "agy-cli"

    def _is_registered(tool_id: str) -> bool:
        if tool_id in registered_tool_ids:
            return True
        # Also try mapping via agent_type normalisation
        agent_type = normalize_agent_type(tool_id)
        if agent_type in registered_tool_ids:
            return True
        # Built-in HTTP providers (e.g. Ollama) are registered without shell CLI config.
        if resolve_provider_spec(agent_type).runtime_strategy == RuntimeStrategy.HTTP_DAEMON:
            return True
        return False

    connected = load_connected_ids()
    tools: list[dict[str, Any]] = []
    for cand in CLI_CANDIDATES:
        path = resolve_tool_binary(cand["id"])
        installed = path is not None
        recommended = cand["id"] in RECOMMENDED_CLI_IDS
        if not installed:
            if include_all:
                if not recommended:
                    continue
            else:
                continue
        tools.append(
            {
                "id": cand["id"],
                "name": cand["name"],
                "description": cand["description"],
                "icon": cand["icon"],
                "kind": "cli",
                "path": path or "",
                "installed": installed,
                "connected": cand["id"] in connected,
                "registered": _is_registered(cand["id"]),
                "agentType": resolve_agent_type_for_tool(cand["id"]),
                "recommended": recommended,
            }
        )
    for cand in CLIENT_CANDIDATES:
        path = _client_path(cand["app_name"])
        installed = path is not None
        recommended = cand["id"] in RECOMMENDED_CLI_IDS
        if not installed:
            if include_all:
                if not recommended:
                    continue
            else:
                continue
        tools.append(
            {
                "id": cand["id"],
                "name": cand["name"],
                "description": cand["description"],
                "icon": cand["icon"],
                "kind": "client",
                "path": path or "",
                "installed": installed,
                "connected": cand["id"] in connected,
                "registered": _is_registered(cand["id"]),
                "agentType": resolve_agent_type_for_tool(cand["id"]),
                "recommended": recommended,
            }
        )
    return tools



def connect_tool(tool_id: str) -> dict[str, Any]:
    if _candidate_by_id(tool_id) is None:
        raise ValueError(f"Unknown tool: {tool_id}")
    if not _installed(tool_id):
        raise ValueError(f"Tool not installed: {tool_id}")
    connected = load_connected_ids()
    connected.add(tool_id)
    save_connected_ids(connected)
    return {"id": tool_id, "connected": True}


def disconnect_tool(tool_id: str) -> dict[str, Any]:
    if _candidate_by_id(tool_id) is None:
        raise ValueError(f"Unknown tool: {tool_id}")
    connected = load_connected_ids()
    connected.discard(tool_id)
    save_connected_ids(connected)
    return {"id": tool_id, "connected": False}


def auto_configure_cli_via_llm(tool_id: str, binary_path: str) -> dict[str, Any]:
    import subprocess
    try:
        res = subprocess.run([binary_path, "--help"], capture_output=True, text=True, timeout=5.0)
        help_text = res.stdout or res.stderr
    except Exception as exc:
        raise RuntimeError(f"Failed to run binary --help: {exc}")

    if not help_text:
        help_text = "No help text returned."

    from src.models_config import get_router
    router = get_router()

    # Use the user's currently active model for analysis
    active_spec = router.get_active_model()
    has_key = bool(router.get_api_key(active_spec.provider_id))
    model_id = active_spec.id if (active_spec.model_kind not in {"image", "video"} and has_key) else None

    if not model_id:
        # Try any other chat model that has a key
        for spec in router.list_models():
            if spec.model_kind not in {"image", "video"} and router.get_api_key(spec.provider_id):
                model_id = spec.id
                break

    if not model_id:
        # No LLM with a valid API key configured — return safe defaults
        return {
            "tool_id": tool_id,
            "binary_name": tool_id.replace("-cli", ""),
            "conversation_mode": "none",
            "prepend_system_prompt": True,
            "extra_args": [],
            "prompt_flag": "-p",
        }

    prompt = f"""You are a command-line interface parameter analyzer.
We have a local AI tool binary help documentation. We need to extract the correct configuration options so we can route prompts to it automatically.

Help output for the binary:
\"\"\"
{help_text}
\"\"\"

Please analyze the help text and output a JSON object containing the following keys (DO NOT output markdown code blocks, just raw JSON text):
1. "binary_name": the binary name (e.g. "ollama", "gemini", "codeium")
2. "conversation_mode": either "resume_or_new" (if it supports conversation IDs / resume), "separate", or "none" (if it only supports single prompt execution)
3. "prepend_system_prompt": boolean (true if it doesn't support a system prompt flag and we need to prepend it to the user prompt, false if it has a native system prompt flag)
4. "extra_args": list of strings for flags needed for normal operation (e.g. ["--yes-always"])
5. "prompt_flag": the string flag used to pass the prompt or message (e.g. "-p", "--prompt", "--message", or empty "" if prompt is passed as positional argument). Look carefully at the help text for prompt input flags!

Example Output:
{{
  "binary_name": "ollama",
  "conversation_mode": "none",
  "prepend_system_prompt": true,
  "extra_args": ["run"],
  "prompt_flag": ""
}}
"""

    chat_history = [{"role": "user", "content": prompt}]
    try:
        from src.llm.router import LLMProviderRouter

        raw = router.chat(chat_history, model_id=model_id)
        reply_clean = LLMProviderRouter.extract_content(raw).strip()
        if reply_clean.startswith("```"):
            lines = reply_clean.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            reply_clean = "\n".join(lines).strip()

        config = json.loads(reply_clean)
        config["tool_id"] = tool_id
        return config
    except Exception:
        # Fallback default configuration if JSON parsing fails
        return {
            "tool_id": tool_id,
            "binary_name": tool_id.replace("-cli", ""),
            "conversation_mode": "none",
            "prepend_system_prompt": True,
            "extra_args": [],
            "prompt_flag": "-p",
        }
