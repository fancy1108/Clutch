"""Read external CLI agent configuration (models / MCP / skills) for Settings & Agent Manager."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from src.credentials.claude_code import (
    _CC_SWITCH_DIR,
    read_claude_code_env,
    resolve_anthropic_api_model,
)

_SUPPORTED_AGENT_TYPES = frozenset({"claude-cli", "opencode-cli"})

_CC_SWITCH_APP_BY_AGENT: dict[str, str] = {
    "claude-cli": "claude",
    "opencode-cli": "opencode",
}

_CC_SWITCH_ACTIVE_KEY_BY_APP: dict[str, str] = {
    "claude": "currentProviderClaude",
    "opencode": "currentProviderOpencode",
}

_OPENCODE_CONFIG_CANDIDATES = (
    Path.home() / ".config" / "opencode" / "opencode.json",
    Path.home() / ".config" / "opencode" / "opencode.jsonc",
)

_OPENCODE_AUTH_PATH = Path.home() / ".local" / "share" / "opencode" / "auth.json"
_OPENCODE_MODEL_STATE_PATH = Path.home() / ".local" / "state" / "opencode" / "model.json"

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

_CC_SWITCH_RELEASE_BASE = "https://github.com/SaladDay/cc-switch-cli/releases/latest/download"


def normalize_cli_agent_type(raw: str) -> str:
    key = raw.strip().lower()
    if key in _SUPPORTED_AGENT_TYPES:
        return key
    if key in {"claude", "claude-cli"}:
        return "claude-cli"
    if key in {"opencode", "opencode-cli"}:
        return "opencode-cli"
    raise ValueError(f"Unsupported agent type: {raw}")


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if len(text) <= 8:
        return "••••"
    return f"{text[:4]}…{text[-4:]}"


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _strip_jsonc_comments(text: str) -> str:
    """Remove // and /* */ comments so jsonc can be parsed as JSON."""
    without_block = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    lines: list[str] = []
    for line in without_block.splitlines():
        in_string = False
        escaped = False
        cut = len(line)
        for index, char in enumerate(line):
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if not in_string and char == "/" and index + 1 < len(line) and line[index + 1] == "/":
                cut = index
                break
        lines.append(line[:cut])
    return "\n".join(lines)


def _read_jsonc_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(_strip_jsonc_comments(raw))
    except (json.JSONDecodeError, OSError):
        return {}


def _cc_switch_settings() -> dict[str, Any]:
    settings_path = _CC_SWITCH_DIR / "settings.json"
    if not settings_path.is_file():
        return {}
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def list_cc_switch_providers(*, app_type: str) -> list[dict[str, Any]]:
    db_path = _CC_SWITCH_DIR / "cc-switch.db"
    if not db_path.is_file():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, app_type, settings_config FROM providers WHERE app_type = ?",
            (app_type,),
        )
        rows = cursor.fetchall()
        conn.close()
    except Exception:
        return []

    providers: list[dict[str, Any]] = []
    for pid, name, row_app_type, settings_str in rows:
        if not settings_str:
            continue
        if pid in (
            "default",
            "claude-official",
            "claude-desktop-official",
            "codex-official",
            "gemini-official",
        ):
            continue
        try:
            config = json.loads(settings_str)
        except json.JSONDecodeError:
            continue
        model_id = _model_from_cc_switch_config(str(row_app_type), config)
        providers.append(
            {
                "id": str(pid),
                "name": str(name or pid),
                "app_type": str(row_app_type),
                "model_id": model_id,
                "is_active": False,
            }
        )
    return providers


def _model_from_cc_switch_config(app_type: str, config: dict[str, Any]) -> str | None:
    if app_type == "claude":
        env = config.get("env") or {}
        for key in (
            "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME",
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "ANTHROPIC_MODEL",
            "CLAUDE_CODE_SUBAGENT_MODEL",
        ):
            value = env.get(key)
            if value:
                return str(value)
    if app_type == "opencode":
        model = config.get("model")
        if model:
            return str(model)
        provider_block = config.get("provider")
        if isinstance(provider_block, dict):
            for provider_cfg in provider_block.values():
                if not isinstance(provider_cfg, dict):
                    continue
                models = provider_cfg.get("models")
                if isinstance(models, dict) and models:
                    return str(next(iter(models.keys())))
    if app_type == "codex":
        config_text = config.get("config") or ""
        if isinstance(config_text, str):
            for line in config_text.splitlines():
                if line.strip().startswith("model ="):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
    return None


def read_cc_switch_active_provider_id(app_type: str) -> str | None:
    settings = _cc_switch_settings()
    key = _CC_SWITCH_ACTIVE_KEY_BY_APP.get(app_type)
    if not key:
        return None
    active = settings.get(key)
    return str(active).strip() if active else None


def resolve_cc_switch_cli_path() -> str | None:
    found = shutil.which("cc-switch")
    if found and _verify_cc_switch_cli(found):
        return found
    from src.tools_status import _extra_cli_search_dirs

    for directory in _extra_cli_search_dirs():
        candidate = directory / "cc-switch"
        if candidate.is_file() and os.access(candidate, os.X_OK) and _verify_cc_switch_cli(str(candidate)):
            return str(candidate)
    return None


def _verify_cc_switch_cli(path: str) -> bool:
    try:
        completed = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _cc_switch_bundle_cache_dir() -> Path:
    from src.storage_helper import get_storage_dir

    path = get_storage_dir() / "bundles" / "cc-switch-cli"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cc_switch_asset_name() -> str | None:
    if sys.platform == "darwin":
        return "cc-switch-cli-darwin-universal.tar.gz"
    if sys.platform == "win32":
        return "cc-switch-cli-windows-x64.zip"
    if sys.platform.startswith("linux"):
        return "cc-switch-cli-linux-x64-musl.tar.gz"
    return None


def _cc_switch_binary_name() -> str:
    return "cc-switch.exe" if sys.platform == "win32" else "cc-switch"


def _find_cc_switch_binary_in_dir(directory: Path) -> Path | None:
    preferred = directory / _cc_switch_binary_name()
    if preferred.is_file() and os.access(preferred, os.X_OK) and _verify_cc_switch_cli(str(preferred)):
        return preferred
    for candidate in directory.rglob(_cc_switch_binary_name()):
        if candidate.is_file() and os.access(candidate, os.X_OK) and _verify_cc_switch_cli(str(candidate)):
            return candidate
    return None


def _download_cc_switch_archive(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Clutch"})
    with urllib.request.urlopen(request, timeout=120) as response:
        dest.write_bytes(response.read())


def _extract_cc_switch_archive(archive: Path, dest_dir: Path) -> Path | None:
    if archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "r:gz") as tar:
            try:
                tar.extractall(dest_dir, filter="data")
            except TypeError:
                tar.extractall(dest_dir)
    elif archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as archive_file:
            archive_file.extractall(dest_dir)
    else:
        return None
    return _find_cc_switch_binary_in_dir(dest_dir)


def prefetch_cc_switch_cli_bundle() -> dict[str, Any]:
    installed = resolve_cc_switch_cli_path()
    if installed:
        return {"ok": True, "cached": True, "already_installed": True, "path": installed}

    cache_dir = _cc_switch_bundle_cache_dir()
    cached = _find_cc_switch_binary_in_dir(cache_dir)
    if cached:
        return {"ok": True, "cached": True, "path": str(cached)}

    asset = _cc_switch_asset_name()
    if not asset:
        return {"ok": False, "message": f"cc-switch CLI install is not supported on {sys.platform}."}

    archive_path = cache_dir / asset
    url = f"{_CC_SWITCH_RELEASE_BASE}/{asset}"
    try:
        if not archive_path.is_file():
            _download_cc_switch_archive(url, archive_path)
        binary = _extract_cc_switch_archive(archive_path, cache_dir)
    except Exception as exc:
        return {"ok": False, "message": f"Failed to download cc-switch CLI bundle: {exc}"}

    if not binary:
        return {"ok": False, "message": "Downloaded cc-switch archive did not contain a usable binary."}

    if sys.platform == "darwin":
        subprocess.run(["xattr", "-cr", str(binary)], capture_output=True, check=False)

    return {"ok": True, "cached": True, "path": str(binary)}


def install_cc_switch_cli() -> dict[str, Any]:
    existing = resolve_cc_switch_cli_path()
    if existing:
        return {
            "ok": True,
            "message": "cc-switch CLI is already available.",
            "cli_path": existing,
            "method": "existing",
        }

    bundle = prefetch_cc_switch_cli_bundle()
    if not bundle.get("ok"):
        return bundle

    if bundle.get("already_installed"):
        installed = resolve_cc_switch_cli_path()
        if installed:
            return {
                "ok": True,
                "message": "cc-switch CLI is already available.",
                "cli_path": installed,
                "method": "existing",
            }

    source = Path(str(bundle.get("path") or ""))
    if not source.is_file():
        return {"ok": False, "message": "cc-switch bundle is missing after prefetch."}

    install_dir = Path.home() / ".local" / "bin"
    install_dir.mkdir(parents=True, exist_ok=True)
    target = install_dir / _cc_switch_binary_name()
    shutil.copy2(source, target)
    target.chmod(0o755)
    if sys.platform == "darwin":
        subprocess.run(["xattr", "-cr", str(target)], capture_output=True, check=False)

    installed = resolve_cc_switch_cli_path()
    if installed:
        return {
            "ok": True,
            "message": "Installed cc-switch CLI from Clutch bundle cache.",
            "cli_path": installed,
            "method": "cached_bundle",
        }
    return {"ok": False, "message": "Copied cc-switch binary but verification failed."}


def cc_switch_cli_available() -> bool:
    return resolve_cc_switch_cli_path() is not None


def activate_cc_switch_provider(provider_id: str, *, app_type: str) -> dict[str, Any]:
    cli_path = resolve_cc_switch_cli_path()
    if not cli_path:
        if (_CC_SWITCH_DIR / "cc-switch.db").is_file():
            return {
                "ok": False,
                "message": (
                    "CC Switch app data was found, but the cc-switch CLI is not on PATH. "
                    "Install the cc-switch CLI or switch providers in the CC Switch desktop app."
                ),
            }
        return {
            "ok": False,
            "message": "cc-switch CLI not found on PATH. Install CC Switch or switch providers in its desktop app.",
        }
    pid = provider_id.strip()
    if not pid:
        return {"ok": False, "message": "provider_id is required"}
    cmd = [cli_path, "--app", app_type, "provider", "switch", pid]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": "cc-switch timed out while switching provider."}
    except OSError as exc:
        return {"ok": False, "message": f"Failed to run cc-switch: {exc}"}

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        return {
            "ok": False,
            "message": detail or "cc-switch provider switch failed.",
        }
    return {"ok": True, "message": "Provider switched via cc-switch."}


def _annotate_active_providers(providers: list[dict[str, Any]], active_id: str | None) -> None:
    for item in providers:
        item["is_active"] = bool(active_id and item.get("id") == active_id)


def scan_claude_code_models() -> dict[str, Any]:
    app_type = "claude"
    providers = list_cc_switch_providers(app_type=app_type)
    active_id = read_cc_switch_active_provider_id(app_type)
    _annotate_active_providers(providers, active_id)

    claude_env = read_claude_code_env()
    active_model = resolve_anthropic_api_model()
    base_url = claude_env.get("ANTHROPIC_BASE_URL")

    return {
        "agent_type": "claude-cli",
        "cc_switch_found": (_CC_SWITCH_DIR / "cc-switch.db").is_file(),
        "cc_switch_cli_available": cc_switch_cli_available(),
        "active_provider_id": active_id,
        "active_model_id": active_model,
        "base_url": base_url,
        "credential_source": "cc_switch" if active_id else ("claude_settings" if claude_env else None),
        "providers": providers,
        "settings_path": str(Path.home() / ".claude" / "settings.json"),
        "env_preview": {
            key: (_mask_secret(value) if "TOKEN" in key or "KEY" in key else value)
            for key, value in claude_env.items()
            if key.startswith("ANTHROPIC_") or key.startswith("CLAUDE_")
        },
    }


def _read_opencode_config_paths() -> list[Path]:
    paths: list[Path] = []
    for candidate in _OPENCODE_CONFIG_CANDIDATES:
        if candidate.is_file():
            paths.append(candidate)
    return paths


def _read_opencode_config_merged(*, workspace_path: str | None = None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for path in _read_opencode_config_paths():
        if path.suffix == ".jsonc":
            merged.update(_read_jsonc_file(path))
        else:
            merged.update(_read_json_file(path))
    if workspace_path:
        project_cfg = Path(workspace_path) / "opencode.json"
        if project_cfg.is_file():
            merged = {**merged, **_read_json_file(project_cfg)}
    return merged


def _read_opencode_auth_providers() -> list[dict[str, Any]]:
    if not _OPENCODE_AUTH_PATH.is_file():
        return []
    data = _read_json_file(_OPENCODE_AUTH_PATH)
    providers: list[dict[str, Any]] = []
    for provider_id, cfg in data.items():
        if not isinstance(cfg, dict):
            continue
        providers.append(
            {
                "id": str(provider_id),
                "name": str(provider_id),
                "auth_type": str(cfg.get("type") or "api"),
                "has_credential": bool(cfg.get("key") or cfg.get("token")),
            }
        )
    return providers


def _read_opencode_active_model_ref() -> str | None:
    if not _OPENCODE_MODEL_STATE_PATH.is_file():
        return None
    data = _read_json_file(_OPENCODE_MODEL_STATE_PATH)
    recent = data.get("recent")
    if not isinstance(recent, list) or not recent:
        return None
    first = recent[0]
    if not isinstance(first, dict):
        return None
    provider_id = first.get("providerID")
    model_id = first.get("modelID")
    if provider_id and model_id:
        return f"{provider_id}/{model_id}"
    return None


def _list_opencode_models_via_cli() -> list[dict[str, Any]]:
    opencode_bin = shutil.which("opencode")
    if not opencode_bin:
        return []
    try:
        completed = subprocess.run(
            [opencode_bin, "models"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []

    models: list[dict[str, Any]] = []
    for raw_line in completed.stdout.splitlines():
        line = _ANSI_ESCAPE_RE.sub("", raw_line).strip()
        if not line or line.lower().startswith("error"):
            continue
        if "/" not in line:
            continue
        provider, model_id = line.split("/", 1)
        models.append(
            {
                "provider": provider,
                "model_id": model_id,
                "name": model_id,
                "model_ref": line,
                "is_builtin": provider == "opencode",
            }
        )
    return models


def _catalog_from_opencode_config(provider_block: dict[str, Any]) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for provider_name, cfg in provider_block.items():
        if not isinstance(cfg, dict):
            continue
        models = cfg.get("models")
        if isinstance(models, dict):
            for model_id, meta in models.items():
                label = model_id
                if isinstance(meta, dict) and meta.get("name"):
                    label = str(meta["name"])
                catalog.append(
                    {
                        "provider": str(provider_name),
                        "model_id": str(model_id),
                        "name": label,
                        "model_ref": f"{provider_name}/{model_id}",
                    }
                )
    return catalog


def activate_opencode_model(model_ref: str) -> dict[str, Any]:
    normalized = model_ref.strip()
    if "/" not in normalized:
        return {"ok": False, "message": "model_ref must be provider/model (e.g. deepseek/deepseek-v4-pro)."}
    provider_id, model_id = normalized.split("/", 1)
    if not provider_id or not model_id:
        return {"ok": False, "message": "model_ref must be provider/model."}

    config_dir = Path.home() / ".config" / "opencode"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_paths = _read_opencode_config_paths()
    target = config_paths[0] if config_paths else (config_dir / "opencode.jsonc")
    if target.suffix == ".jsonc":
        existing = _read_jsonc_file(target)
    else:
        existing = _read_json_file(target)
    existing["model"] = normalized
    target.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    state_dir = _OPENCODE_MODEL_STATE_PATH.parent
    state_dir.mkdir(parents=True, exist_ok=True)
    state = _read_json_file(_OPENCODE_MODEL_STATE_PATH)
    recent = state.get("recent") if isinstance(state.get("recent"), list) else []
    entry = {"providerID": provider_id, "modelID": model_id}
    recent = [entry] + [
        item
        for item in recent
        if not (
            isinstance(item, dict)
            and item.get("providerID") == provider_id
            and item.get("modelID") == model_id
        )
    ]
    state["recent"] = recent[:10]
    variants = state.get("variant") if isinstance(state.get("variant"), dict) else {}
    variants[normalized] = variants.get(normalized, "default")
    state["variant"] = variants
    _OPENCODE_MODEL_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False) + "\n", encoding="utf-8")

    return {"ok": True, "message": f"OpenCode default model set to {normalized}."}


def scan_opencode_models(*, workspace_path: str | None = None) -> dict[str, Any]:
    app_type = "opencode"
    providers = list_cc_switch_providers(app_type=app_type)
    active_id = read_cc_switch_active_provider_id(app_type)
    _annotate_active_providers(providers, active_id)

    config_paths = _read_opencode_config_paths()
    merged = _read_opencode_config_merged(workspace_path=workspace_path)
    provider_block = merged.get("provider") if isinstance(merged.get("provider"), dict) else {}
    catalog = _catalog_from_opencode_config(provider_block)

    auth_providers = _read_opencode_auth_providers()
    available_models = _list_opencode_models_via_cli()
    seen_refs = {item.get("model_ref") for item in catalog if item.get("model_ref")}
    for item in available_models:
        model_ref = item.get("model_ref")
        if model_ref and model_ref not in seen_refs:
            catalog.append(
                {
                    "provider": item["provider"],
                    "model_id": item["model_id"],
                    "name": item["name"],
                    "model_ref": model_ref,
                    "is_builtin": item.get("is_builtin", False),
                }
            )
            seen_refs.add(model_ref)

    active_model = _read_opencode_active_model_ref() or merged.get("model")
    if not active_model and catalog:
        first_ref = catalog[0].get("model_ref")
        active_model = first_ref or catalog[0]["model_id"]

    return {
        "agent_type": "opencode-cli",
        "cc_switch_found": (_CC_SWITCH_DIR / "cc-switch.db").is_file(),
        "cc_switch_cli_available": cc_switch_cli_available(),
        "active_provider_id": active_id,
        "active_model_id": str(active_model) if active_model else None,
        "default_agent": merged.get("default_agent"),
        "providers": providers,
        "auth_providers": auth_providers,
        "available_models": available_models,
        "catalog": catalog,
        "config_paths": [str(path) for path in config_paths],
        "auth_path": str(_OPENCODE_AUTH_PATH) if _OPENCODE_AUTH_PATH.is_file() else None,
        "model_state_path": str(_OPENCODE_MODEL_STATE_PATH)
        if _OPENCODE_MODEL_STATE_PATH.is_file()
        else None,
        "project_config_path": str(Path(workspace_path) / "opencode.json") if workspace_path else None,
        "opencode_cli_available": shutil.which("opencode") is not None,
    }


def scan_cli_models(agent_type: str, *, workspace_path: str | None = None) -> dict[str, Any]:
    normalized = normalize_cli_agent_type(agent_type)
    if normalized == "claude-cli":
        return scan_claude_code_models()
    return scan_opencode_models(workspace_path=workspace_path)


def _skill_roots_for_agent(agent_type: str, *, workspace_path: str | None = None) -> list[Path]:
    roots: list[Path] = []
    if agent_type == "claude-cli":
        roots.extend(
            [
                Path.home() / ".claude" / "skills",
                _CC_SWITCH_DIR / "skills",
            ]
        )
        if workspace_path:
            ws = Path(workspace_path)
            roots.extend([ws / ".claude" / "skills", ws / "skills"])
    elif agent_type == "opencode-cli":
        roots.extend(
            [
                Path.home() / ".opencode" / "skills",
                Path.home() / ".config" / "opencode" / "skills",
            ]
        )
        if workspace_path:
            roots.extend(
                [
                    Path(workspace_path) / ".opencode" / "skills",
                    Path(workspace_path) / "opencode" / "skills",
                ]
            )
    return [root for root in roots if root.is_dir()]


def scan_cli_skills(agent_type: str, *, workspace_path: str | None = None) -> dict[str, Any]:
    from src.skills_scanner import scan_mounted_directories

    normalized = normalize_cli_agent_type(agent_type)
    roots = _skill_roots_for_agent(normalized, workspace_path=workspace_path)
    if not roots:
        return {"agent_type": normalized, "skills": [], "roots": []}

    scanned = scan_mounted_directories([str(root) for root in roots], existing_skills=[])
    return {
        "agent_type": normalized,
        "roots": [str(root) for root in roots],
        "skills": [
            {
                "key": item.get("key"),
                "label": item.get("label"),
                "desc": item.get("desc"),
                "source": item.get("source"),
            }
            for item in scanned
        ],
    }


def _parse_mcp_server_entry(name: str, cfg: dict[str, Any], source: str) -> dict[str, Any] | None:
    if not isinstance(cfg, dict):
        return None
    transport = str(cfg.get("type") or cfg.get("transport") or "stdio")
    url = cfg.get("url") or cfg.get("endpoint")
    command = cfg.get("command")
    args = cfg.get("args") or []
    if url:
        endpoint = str(url)
        if str(url).startswith("http"):
            transport = "http"
    elif command:
        endpoint = str(command)
        if args:
            endpoint = command + " " + " ".join(shlex.quote(str(arg)) for arg in args)
    else:
        return None
    return {
        "name": str(name),
        "transport": transport,
        "endpoint": endpoint,
        "source": source,
    }


def _collect_mcp_servers_from_block(
    mcp_servers: Any,
    *,
    source: str,
    seen: set[str],
    servers: list[dict[str, Any]],
) -> None:
    if not isinstance(mcp_servers, dict):
        return
    for name, cfg in mcp_servers.items():
        entry = _parse_mcp_server_entry(str(name), cfg if isinstance(cfg, dict) else {}, source)
        if not entry:
            continue
        key = f"{entry['name']}:{entry['endpoint']}"
        if key in seen:
            continue
        seen.add(key)
        servers.append(entry)


def _mcp_from_cc_switch(*, enabled_field: str, include_all: bool = False) -> list[dict[str, Any]]:
    db_path = _CC_SWITCH_DIR / "cc-switch.db"
    if not db_path.is_file():
        return []
    servers: list[dict[str, Any]] = []
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        if include_all:
            cursor.execute(
                "SELECT id, name, server_config, enabled_claude, enabled_opencode FROM mcp_servers"
            )
        else:
            cursor.execute(
                f"SELECT id, name, server_config, enabled_claude, enabled_opencode FROM mcp_servers WHERE {enabled_field} = 1"
            )
        rows = cursor.fetchall()
        conn.close()
    except Exception:
        return []

    for server_id, name, config_str, enabled_claude, enabled_opencode in rows:
        if not config_str:
            continue
        try:
            config = json.loads(config_str)
        except json.JSONDecodeError:
            continue
        if not isinstance(config, dict):
            continue
        entry = _parse_mcp_server_entry(
            str(name or server_id),
            config,
            f"{_CC_SWITCH_DIR / 'cc-switch.db'} (cc-switch)",
        )
        if not entry:
            continue
        entry["enabled_for_agent"] = bool(
            enabled_claude if enabled_field == "enabled_claude" else enabled_opencode
        )
        servers.append(entry)
    return servers


def _mcp_from_claude_json(*, workspace_path: str | None = None) -> list[dict[str, Any]]:
    paths: list[Path] = []
    if sys.platform == "darwin":
        paths.append(Path.home() / "Library/Application Support/Claude/claude_desktop_config.json")
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(Path(appdata) / "Claude" / "claude_desktop_config.json")
    paths.append(Path.home() / ".claude.json")

    servers: list[dict[str, Any]] = []
    seen: set[str] = set()

    for path in paths:
        if not path.is_file():
            continue
        data = _read_json_file(path)
        _collect_mcp_servers_from_block(
            data.get("mcpServers"),
            source=str(path),
            seen=seen,
            servers=servers,
        )

    claude_json = Path.home() / ".claude.json"
    if claude_json.is_file():
        data = _read_json_file(claude_json)
        projects = data.get("projects")
        if isinstance(projects, dict):
            for project_path, pdata in projects.items():
                if not isinstance(pdata, dict):
                    continue
                _collect_mcp_servers_from_block(
                    pdata.get("mcpServers"),
                    source=f"{claude_json} (project: {project_path})",
                    seen=seen,
                    servers=servers,
                )

    if workspace_path:
        project_mcp = Path(workspace_path) / ".mcp.json"
        if project_mcp.is_file():
            data = _read_json_file(project_mcp)
            _collect_mcp_servers_from_block(
                data.get("mcpServers"),
                source=str(project_mcp),
                seen=seen,
                servers=servers,
            )

    for entry in _mcp_from_cc_switch(enabled_field="enabled_claude", include_all=True):
        key = f"{entry['name']}:{entry['endpoint']}"
        if key in seen:
            continue
        seen.add(key)
        servers.append(entry)

    return servers


def _mcp_from_opencode_config() -> list[dict[str, Any]]:
    servers: list[dict[str, Any]] = []
    for path in _read_opencode_config_paths():
        data = _read_json_file(path)
        mcp_block = data.get("mcp")
        if isinstance(mcp_block, dict):
            for name, cfg in mcp_block.items():
                if not isinstance(cfg, dict):
                    continue
                command = cfg.get("command") or cfg.get("url") or cfg.get("endpoint")
                if not command:
                    continue
                servers.append(
                    {
                        "name": str(name),
                        "transport": str(cfg.get("type") or cfg.get("transport") or "stdio"),
                        "endpoint": str(command),
                        "source": str(path),
                    }
                )
    return servers


def scan_cli_mcp(agent_type: str, *, workspace_path: str | None = None) -> dict[str, Any]:
    normalized = normalize_cli_agent_type(agent_type)
    if normalized == "claude-cli":
        servers = _mcp_from_claude_json(workspace_path=workspace_path)
    else:
        servers = _mcp_from_opencode_config()
        if workspace_path:
            project_mcp = Path(workspace_path) / ".mcp.json"
            if project_mcp.is_file():
                data = _read_json_file(project_mcp)
                seen = {f"{s['name']}:{s['endpoint']}" for s in servers}
                extra: list[dict[str, Any]] = []
                _collect_mcp_servers_from_block(
                    data.get("mcpServers"),
                    source=str(project_mcp),
                    seen=seen,
                    servers=extra,
                )
                servers.extend(extra)
        seen = {f"{s['name']}:{s['endpoint']}" for s in servers}
        for entry in _mcp_from_cc_switch(enabled_field="enabled_opencode", include_all=True):
            key = f"{entry['name']}:{entry['endpoint']}"
            if key in seen:
                continue
            seen.add(key)
            servers.append(entry)
    return {
        "agent_type": normalized,
        "servers": servers,
        "cc_switch_found": (_CC_SWITCH_DIR / "cc-switch.db").is_file(),
        "cc_switch_cli_available": cc_switch_cli_available(),
    }


def activate_cli_provider(agent_type: str, provider_id: str) -> dict[str, Any]:
    normalized = normalize_cli_agent_type(agent_type)
    app_type = _CC_SWITCH_APP_BY_AGENT.get(normalized)
    if not app_type:
        return {"ok": False, "message": f"Provider switching is not supported for {normalized}."}
    return activate_cc_switch_provider(provider_id, app_type=app_type)


def activate_cli_model(agent_type: str, model_ref: str) -> dict[str, Any]:
    normalized = normalize_cli_agent_type(agent_type)
    if normalized != "opencode-cli":
        return {"ok": False, "message": f"Model switching is not supported for {normalized}."}
    return activate_opencode_model(model_ref)
