"""D35 — import capability packs (skills + hooks + MCP fragment)."""

from __future__ import annotations

import json
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any

from src.platform_lock import file_lock


def _packs_root() -> Path:
    from src.storage_helper import get_storage_dir

    path = get_storage_dir() / "capability_packs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _registry_path() -> Path:
    return _packs_root() / "registry.json"


def _load_registry() -> list[dict[str, Any]]:
    path = _registry_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return list(data)
    if isinstance(data, dict) and isinstance(data.get("packs"), list):
        return list(data["packs"])
    return []


def _save_registry(packs: list[dict[str, Any]]) -> None:
    path = _registry_path()
    path.write_text(json.dumps({"packs": packs}, indent=2, ensure_ascii=False), encoding="utf-8")


def list_installed_packs() -> list[dict[str, Any]]:
    return list(_load_registry())


def installed_pack_hooks_paths() -> list[Path]:
    paths: list[Path] = []
    for pack in _load_registry():
        pack_id = str(pack.get("id") or "").strip()
        if not pack_id:
            continue
        hook = _packs_root() / pack_id / "hooks.json"
        if hook.is_file():
            paths.append(hook)
    return paths


def _read_pack_manifest(source: Path) -> dict[str, Any]:
    manifest = source / "pack.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"name": source.name}


def _register_pack_contents(pack_id: str, pack_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    skills_dir = pack_dir / "skills"
    skills_mount = ""
    if skills_dir.is_dir():
        from src.skills_storage import load_registry, save_registry

        resolved = str(skills_dir.resolve())
        data = load_registry()
        mounted = list(data.get("mounted_directories") or [])
        if resolved not in mounted:
            mounted.append(resolved)
            save_registry(mounted_directories=mounted)
        skills_mount = resolved

    hooks_file = pack_dir / "hooks.json"
    mcp_fragment = pack_dir / "mcpServers.json"
    mcp_ids: list[str] = []
    if mcp_fragment.is_file():
        try:
            fragment = json.loads(mcp_fragment.read_text(encoding="utf-8"))
            servers = fragment.get("mcpServers") if isinstance(fragment, dict) else fragment
            if isinstance(servers, dict):
                from src.mcp_storage import register_server

                for name, cfg in servers.items():
                    if not isinstance(cfg, dict):
                        continue
                    command = str(cfg.get("command") or cfg.get("endpoint") or "").strip()
                    if not command:
                        continue
                    transport = str(cfg.get("transport") or "stdio")
                    env = cfg.get("env") if isinstance(cfg.get("env"), dict) else None
                    registered = register_server(
                        name=f"{pack_id}:{name}",
                        transport=transport,
                        endpoint=command,
                        env=env,
                    )
                    mcp_ids.append(str(registered.get("id") or ""))
        except (json.JSONDecodeError, OSError, Exception):
            pass

    record = {
        "id": pack_id,
        "name": str(manifest.get("name") or pack_id),
        "path": str(pack_dir),
        "skills_mount": skills_mount,
        "hooks_path": str(hooks_file) if hooks_file.is_file() else "",
        "mcp_server_ids": mcp_ids,
    }
    packs = _load_registry()
    packs = [p for p in packs if p.get("id") != pack_id]
    packs.append(record)
    _save_registry(packs)
    return record


def import_pack(source_path: str) -> dict[str, Any]:
    raw = Path(source_path).expanduser().resolve()
    if not raw.exists():
        raise ValueError(f"Pack path not found: {source_path}")
    pack_id = f"pack_{uuid.uuid4().hex[:8]}"
    dest = _packs_root() / pack_id
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    if raw.is_dir():
        shutil.copytree(raw, dest, dirs_exist_ok=True)
        manifest = _read_pack_manifest(dest)
    elif raw.is_file() and raw.suffix.lower() == ".zip":
        with zipfile.ZipFile(raw, "r") as zf:
            zf.extractall(dest)
        manifest = _read_pack_manifest(dest)
    else:
        raise ValueError("Pack must be a directory or .zip file")

    return _register_pack_contents(pack_id, dest, manifest)


def uninstall_pack(pack_id: str) -> dict[str, Any]:
    packs = _load_registry()
    target = next((p for p in packs if p.get("id") == pack_id), None)
    if target is None:
        raise ValueError(f"Pack not found: {pack_id}")

    skills_mount = str(target.get("skills_mount") or "").strip()
    if skills_mount:
        from src.skills_storage import load_registry, save_registry

        data = load_registry()
        mounted = [m for m in data.get("mounted_directories") or [] if m != skills_mount]
        skills = [s for s in data.get("skills") or [] if s.get("source") != skills_mount]
        save_registry(mounted_directories=mounted, skills=skills)

    for mcp_id in target.get("mcp_server_ids") or []:
        mid = str(mcp_id or "").strip()
        if mid:
            try:
                from src.mcp_storage import remove_server

                remove_server(mid)
            except Exception:
                pass

    pack_dir = Path(str(target.get("path") or ""))
    if pack_dir.is_dir():
        shutil.rmtree(pack_dir, ignore_errors=True)

    remaining = [p for p in packs if p.get("id") != pack_id]
    _save_registry(remaining)
    return {"id": pack_id, "removed": True}
