"""Design sessions facade orchestrating Prototype approve, React code generation, and Handoff."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from src.workspace import WorkspaceError, require_workspace
from src.design.builtin_presets import normalize_preset_id

# Import exceptions & constants
from src.design.session_store import (
    DESIGN_MD,
    DESIGN_ROOT,
    MANIFEST,
    SPEC_JSON,
    DesignError,
    delete_session_artifacts,
    ensure_session,
    find_existing_session_dir,
    first_screen_with_ui,
    get_session,
    list_sessions,
    prune_orphan_session_dirs,
    public_session_payload,
    read_manifest,
    resolve_screen_html_path,
    session_dir,
    sync_session_folder_name,
    write_manifest,
)

# Import preview handlers
from src.design.preview_manager import (
    preview_lock,
    preview_procs,
    start_preview,
    stop_preview,
)

# Import generators
from src.design.generator import (
    _coerce_ui_html,
    _extract_css_tokens,
    _fetch_url_snapshot,
    _format_css_tokens_for_prompt,
    _generate_ui_html,
    _html_has_visible_content,
    _infer_iterate_mode,
    _shell_html,
    confirm_spec,
    generate_session,
    iterate_session,
    delete_screen,
    start_confirm_spec,
    start_generate_session,
    start_iterate_session,
)

# Import thumbnail helpers
from src.design.thumbnail import (
    thumbnail_data_url_for_run,
)

# --- Private aliases/variables accessed by unit tests for back-compat ---
_preview_procs = preview_procs
_preview_lock = preview_lock
_find_existing_session_dir = find_existing_session_dir
_write_manifest = write_manifest
_read_manifest = read_manifest
_session_dir = session_dir


def _is_windows() -> bool:
    return os.name == "nt"


def _free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])

from src.design.session_store import now_iso as _now_iso
from src.design.session_store import esc as _esc
from src.design.session_store import resolve_screen_html_path as _resolve_screen_html_path

logger = logging.getLogger(__name__)


def design_ui_preview_path_for_run(run_id: str) -> str | None:
    """API path for live HTML preview when the session has real UI (else None)."""
    try:
        root = require_workspace() / DESIGN_ROOT
    except WorkspaceError:
        return None
    session_dir_path = find_existing_session_dir(root, run_id)
    if session_dir_path is None:
        return None
    sid = first_screen_with_ui(session_dir_path)
    if not sid:
        return None
    return f"/api/design/sessions/{run_id}/screens/{sid}"


def read_screen_html(run_id: str, screen_id: str) -> str:
    """Return screen HTML for live sidebar / canvas preview."""
    session_dir_path = session_dir(run_id)
    manifest = read_manifest(session_dir_path)
    raw_id = re.sub(r"[^a-zA-Z0-9_-]", "", (screen_id or "").strip()) or "main"
    versioned = re.match(r"^(?P<base>[a-zA-Z0-9_-]+)_r(?P<round>\d+)$", raw_id)
    if versioned:
        version_path = session_dir_path / "screens" / f"{raw_id}.html"
        if version_path.is_file():
            return version_path.read_text(encoding="utf-8")
        raw_id = versioned.group("base")
    screen_meta = next(
        (s for s in (manifest.get("screens") or []) if str(s.get("id")) == raw_id),
        {"id": raw_id},
    )
    path = resolve_screen_html_path(session_dir_path, screen_meta)
    if not path.is_file():
        legacy = session_dir_path / "screens" / f"{raw_id}.html"
        if legacy.is_file():
            path = legacy
        else:
            raise DesignError(f"Screen not found: {raw_id}")
    return path.read_text(encoding="utf-8")


def design_device_for_run(run_id: str) -> str:
    """Return design device for a run (`web` | `app`)."""
    try:
        root = require_workspace() / DESIGN_ROOT
    except WorkspaceError:
        return "web"
    session_dir_path = find_existing_session_dir(root, run_id)
    if session_dir_path is None or not (session_dir_path / MANIFEST).is_file():
        return "web"
    try:
        manifest = read_manifest(session_dir_path)
    except (OSError, json.JSONDecodeError, DesignError):
        return "web"
    device = str(manifest.get("device") or "web").strip().lower()
    return device if device in {"web", "app"} else "web"


def session_status_for_run(run_id: str) -> str | None:
    """Return Design manifest status for sidebar history sync (None if missing)."""
    try:
        root = require_workspace() / DESIGN_ROOT
    except WorkspaceError:
        return None
    session_dir_path = find_existing_session_dir(root, run_id)
    if session_dir_path is None or not (session_dir_path / MANIFEST).is_file():
        return None
    try:
        manifest = read_manifest(session_dir_path)
    except (OSError, json.JSONDecodeError, DesignError):
        return None
    status = str(manifest.get("status") or "").strip()
    return status or None


def approve_prototype(run_id: str) -> dict[str, Any]:
    session_dir_path = session_dir(run_id)
    manifest = read_manifest(session_dir_path)
    if not manifest.get("screens"):
        raise DesignError("Generate UI before approving")
    manifest["prototype_approved"] = True
    manifest["status"] = "prototype_approved"
    write_manifest(session_dir_path, manifest)
    return public_session_payload(manifest, session_dir_path)


def _component_name(screen_id: str) -> str:
    from src.design.fidelity_export import component_name

    return component_name(screen_id)


def _load_interaction_contract(session_dir_path: Path) -> list[dict[str, Any]]:
    path = session_dir_path / "interaction_contract.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        flows = data.get("flows") or data.get("interactions") or []
        return [x for x in flows if isinstance(x, dict)] if isinstance(flows, list) else []
    return []


def generate_react(run_id: str) -> dict[str, Any]:
    """D41: Deterministic HTML → React pages (no LLM redraw)."""
    from src.design.fidelity_export import build_react_files

    session_dir_path = session_dir(run_id)
    manifest = read_manifest(session_dir_path)
    if not manifest.get("prototype_approved"):
        raise DesignError("Approve the prototype before generating UI code")
    screens = [s for s in (manifest.get("screens") or []) if not s.get("deleted")]
    if not screens:
        raise DesignError("No screens to codegen")
    design_md = (
        (session_dir_path / DESIGN_MD).read_text(encoding="utf-8")
        if (session_dir_path / DESIGN_MD).is_file()
        else ""
    )
    contract = _load_interaction_contract(session_dir_path)
    html_by_id: dict[str, str] = {}
    for s in screens:
        sid = str(s["id"])
        html_path = resolve_screen_html_path(session_dir_path, s)
        if not html_path.is_file():
            html_path = session_dir_path / "screens" / f"{sid}.html"
        html_by_id[sid] = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""

    files = build_react_files(
        app_name=str(manifest.get("name") or "App"),
        screens=screens,
        design_md=design_md,
        html_by_id=html_by_id,
        contract=contract,
    )
    react_dir = session_dir_path / "react"
    if react_dir.exists():
        stop_preview(run_id)
        shutil.rmtree(react_dir)
    for rel, content in files.items():
        path = react_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    manifest["react_ready"] = True
    manifest["react_approved"] = False
    manifest["react_path"] = str(react_dir)
    manifest["status"] = "react_generated"
    write_manifest(session_dir_path, manifest)
    return public_session_payload(manifest, session_dir_path)


def approve_react(run_id: str) -> dict[str, Any]:
    session_dir_path = session_dir(run_id)
    manifest = read_manifest(session_dir_path)
    if not manifest.get("react_ready"):
        raise DesignError("Generate UI code before approving")
    manifest["react_approved"] = True
    manifest["status"] = "react_approved"
    write_manifest(session_dir_path, manifest)
    return public_session_payload(manifest, session_dir_path)


def coding_handoff_payload(run_id: str) -> dict[str, Any]:
    session_dir_path = session_dir(run_id)
    manifest = read_manifest(session_dir_path)
    if not manifest.get("react_approved"):
        raise DesignError("Approve UI code before sending to Coding")
    design_md_path = session_dir_path / DESIGN_MD
    react_path = session_dir_path / "react"
    instruction = (
        f"Frontend UI + client navigation are ready for «{manifest.get('name')}» "
        "(deterministic export from approved Prototype).\n"
        f"Design system: {design_md_path}\n"
        f"React app: {react_path}\n"
        f"Brief: {manifest.get('prompt') or '(none)'}\n"
        "Do not redesign screens. Wire real APIs, auth, and business logic; "
        "keep visual fidelity to the exported pages."
    )
    return {
        "run_id": run_id,
        "project_id": run_id,
        "name": manifest.get("name"),
        "instruction": instruction,
        "design_md_path": str(design_md_path),
        "react_path": str(react_path),
        "workspace_relative": str(session_dir_path.relative_to(require_workspace())),
    }


# --- Back-compat aliases used by older tests (map project_id -> run_id) ---

def create_project(*, name: str, prompt: str = "", template_id: str = "neutral") -> dict[str, Any]:
    run_id = f"design-{uuid.uuid4().hex[:10]}"
    return ensure_session(run_id, title=name, prompt=prompt)


def list_projects() -> list[dict[str, Any]]:
    return list_sessions()


def get_project(project_id: str) -> dict[str, Any]:
    return get_session(project_id)


def delete_project(project_id: str) -> None:
    delete_session_artifacts(project_id)


def generate_prototype(project_id: str, *, prompt: str | None = None, template_id: str | None = None, vision_note: str | None = None) -> dict[str, Any]:
    ensure_session(project_id, prompt=prompt or "")
    text = (prompt or "") + (f"\n{vision_note}" if vision_note else "")
    return generate_session(project_id, prompt=text or "Design a screen")


def iterate_screen(project_id: str, screen_id: str, instruction: str) -> dict[str, Any]:
    return iterate_session(project_id, instruction)


def delete_screen_from_session(run_id: str, screen_id: str) -> dict[str, Any]:
    return delete_screen(run_id, screen_id)


def list_templates() -> list[dict[str, str]]:
    return [
        {"id": "neutral", "name": "Neutral Product"},
        {"id": "linear", "name": "Linear-inspired"},
        {"id": "stripe", "name": "Stripe-inspired"},
    ]


def update_graph(project_id: str, *, screens=None, edges=None) -> dict[str, Any]:
    return get_session(project_id)


def apply_vision_note(project_id: str, note: str, image_data_url: str | None = None) -> dict[str, Any]:
    ensure_session(project_id)
    return generate_session(project_id, prompt=note or "Match the reference UI")
