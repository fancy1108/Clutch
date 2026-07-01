#!/usr/bin/env python3
"""Bootstrap isolated E2E sandbox state for real-acceptance runs (no fake LLM)."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
E2E_DIR = ROOT / "e2e"
ORCH = ROOT / "services" / "orchestrator"
CONFIG_PATH = E2E_DIR / "acceptance.config.json"
CLI_EXCLUDE_DEFAULT = {"agy-cli"}


def _orch_import():
    if str(ORCH) not in sys.path:
        sys.path.insert(0, str(ORCH))


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        raise SystemExit(f"Missing {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _host_tools_connected() -> set[str]:
    host_tools = Path.home() / "Library" / "Application Support" / "clutch" / "tools.json"
    if not host_tools.is_file():
        return set()
    try:
        data = json.loads(host_tools.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    connected = data.get("connected")
    if not isinstance(connected, list):
        return set()
    return {str(item) for item in connected}


def _ollama_tags() -> list[str]:
    try:
        with request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []
    models = payload.get("models") or []
    names: list[str] = []
    for item in models:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return names


def _read_host_api_keys() -> dict[str, str]:
    host_models = Path.home() / "Library" / "Application Support" / "clutch" / "models.json"
    keys: dict[str, str] = {}
    if host_models.is_file():
        try:
            data = json.loads(host_models.read_text(encoding="utf-8"))
            raw = data.get("api_keys")
            if isinstance(raw, dict):
                keys = {str(k): str(v) for k, v in raw.items() if v}
        except (json.JSONDecodeError, OSError):
            pass
    if not keys:
        _orch_import()
        try:
            from src.credentials.keychain_store import load_all_provider_keys

            keys = {k: v for k, v in load_all_provider_keys().items() if v}
        except Exception:
            pass
    return keys


def _resolve_api_key(provider_id: str, env_key: str) -> str | None:
    value = os.environ.get(env_key, "").strip()
    if value:
        return value
    host_val = _read_host_api_keys().get(provider_id)
    if isinstance(host_val, str) and host_val.strip():
        return host_val.strip()
    return None


def _cli_matrix(config: dict) -> tuple[list[str], list[str]]:
    _orch_import()
    from src.tools_status import resolve_agent_type_for_tool, resolve_tool_binary

    exclude = set(config.get("cli_exclude") or CLI_EXCLUDE_DEFAULT)
    host_connected = _host_tools_connected()
    selected: list[str] = []
    skipped: list[str] = []
    for tool_id in sorted(host_connected):
        if tool_id in exclude:
            continue
        if resolve_tool_binary(tool_id) is None:
            skipped.append(f"{tool_id}: connected on host but binary not found")
            continue
        if resolve_agent_type_for_tool(tool_id) is None:
            skipped.append(f"{tool_id}: connected but not routable — skipped")
            continue
        selected.append(tool_id)
    return selected, skipped


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _ollama_model_id(tag: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")
    return f"ollama-local-{slug}" if slug else "ollama-local-unknown"


def _cli_test_agents(cli_tools: list[str]) -> list[dict]:
    _orch_import()
    from src.tools_status import resolve_agent_type_for_tool

    agents: list[dict] = []
    for tool_id in cli_tools:
        agent_type = resolve_agent_type_for_tool(tool_id) or tool_id
        agent_id = f"agent-e2e-cli-{tool_id}"
        label = tool_id.replace("-cli", "").replace("-", " ").title()
        agents.append(
            {
                "id": agent_id,
                "name": f"E2E {label}",
                "description": f"Real acceptance agent for {tool_id}",
                "markdownDoc": f"# E2E {label}\n\nReply concisely for automated acceptance tests.\n",
                "lastModified": "e2e",
                "avatar": "",
                "deliverables": [],
                "mcpTools": [],
                "mcpServerIds": [],
                "agentType": agent_type,
                "skills": [],
            }
        )
    return agents


def main() -> None:
    state = os.environ.get("CLUTCH_E2E_ROOT")
    if not state:
        raise SystemExit("CLUTCH_E2E_ROOT is required")
    state_path = Path(state) / "clutch-state"
    config = _load_config()

    workflow_cfg = config["workflow"]
    wf_src = E2E_DIR / workflow_cfg["fixture_path"]
    agents_src = E2E_DIR / workflow_cfg["agents_fixture_path"]
    wf_dst_dir = state_path / "storage" / "workflows"
    wf_dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wf_src, wf_dst_dir / f"{workflow_cfg['id']}.json")

    workflow_agents = json.loads(agents_src.read_text(encoding="utf-8"))
    cli_tools, skipped = _cli_matrix(config)
    all_agents = workflow_agents + _cli_test_agents(cli_tools)
    _write_json(state_path / "agents" / "agents.json", all_agents)
    _write_json(state_path / "tools.json", {"connected": cli_tools})

    api_cfg = config["api_models"]
    api_keys: dict[str, str] = {}
    text_key = _resolve_api_key(api_cfg["text_provider_id"], api_cfg["text_env_key"])
    image_key = _resolve_api_key(api_cfg["image_provider_id"], api_cfg["image_env_key"])
    if text_key:
        api_keys[api_cfg["text_provider_id"]] = text_key
    if image_key:
        api_keys[api_cfg["image_provider_id"]] = image_key

    ollama_tags = _ollama_tags()
    if text_key:
        active_model = api_cfg["text_model_id"]
    elif ollama_tags:
        active_model = _ollama_model_id(ollama_tags[0])
    else:
        active_model = api_cfg["text_model_id"]

    _write_json(
        state_path / "models.json",
        {
            "active_model_id": active_model,
            "api_keys": api_keys,
            "hidden_model_ids": [],
        },
    )

    manifest = {
        "cli_tools": cli_tools,
        "cli_skipped": skipped,
        "ollama_tags": ollama_tags,
        "text_model_id": api_cfg["text_model_id"],
        "image_model_id": api_cfg["image_model_id"],
        "text_key_present": bool(text_key),
        "image_key_present": bool(image_key),
        "workflow_id": workflow_cfg["id"],
        "start_instruction": workflow_cfg.get("start_instruction", ""),
    }
    _write_json(state_path / "acceptance-manifest.json", manifest)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if skipped:
        print("\n[acceptance] CLI skip warnings:", file=sys.stderr)
        for line in skipped:
            print(f"  - {line}", file=sys.stderr)


if __name__ == "__main__":
    main()
