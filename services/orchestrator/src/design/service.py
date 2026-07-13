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
    _llm_complete,
    _shell_html,
    generate_session,
    iterate_session,
    delete_screen,
    start_generate_session,
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
    parts = re.split(r"[^a-zA-Z0-9]+", screen_id)
    name = "".join(p[:1].upper() + p[1:] for p in parts if p)
    return name or "Screen"


def _html_to_react_component(
    router: Any,
    *,
    html: str,
    component_name: str,
    screen_id: str,
    all_screen_ids: list[str],
    design_md: str,
    model_id: str,
) -> str:
    """LLM translation chain: static HTML -> React 19 + Tailwind component."""
    nav_ids = [sid for sid in all_screen_ids if sid != screen_id]
    nav_hint = ""
    if nav_ids:
        nav_hint = (
            "Wire navigation: convert href links to react-router-dom <Link to=\"/{id}\"> "
            f"for screen ids: {', '.join(nav_ids)}.\n"
        )
    prompt = (
        "Convert this HTML UI into a React 19 functional component.\n"
        f"Component name: {component_name}\n"
        f"Screen route id: {screen_id}\n"
        f"{nav_hint}"
        "Rules:\n"
        "- Use Tailwind utility classes from the HTML (no CDN script tags).\n"
        "- Convert class -> className, for -> htmlFor, inline styles stay as style objects where needed.\n"
        "- For modals, drawers, dropdowns, mobile menus: add useState hooks and toggle handlers.\n"
        "- Export named function component; include `import { useState } from 'react'` when needed.\n"
        "- Include `import { Link } from 'react-router-dom'` for internal navigation.\n"
        "- Preserve visual fidelity — do NOT replace with placeholder skeleton UI.\n"
        f"Design system excerpt:\n{design_md[:4000]}\n\n"
        f"HTML:\n{html[:16000]}\n\n"
        f"Return ONLY the TSX file content for `{component_name}.tsx` inside ```tsx ... ```."
    )
    text, _reasoning, _usage, _estimated = _llm_complete(router, prompt, model_id=model_id)
    fence = re.search(r"```(?:tsx|typescript|jsx)?\s*([\s\S]*?)```", text)
    tsx = fence.group(1).strip() if fence else text.strip()
    if tsx and f"export function {component_name}" in tsx:
        return tsx + ("\n" if not tsx.endswith("\n") else "")
    # Minimal fallback preserving HTML body content
    body_match = re.search(r"<body[^>]*>([\s\S]*?)</body>", html, re.I)
    inner = body_match.group(1).strip() if body_match else html[:8000]
    inner = re.sub(r"\sclass=", " className=", inner)
    escaped_inner = inner.replace("`", "\\`")[:12000]
    return f"""import {{ useState }} from 'react';
import {{ Link }} from 'react-router-dom';

export function {component_name}() {{
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div dangerouslySetInnerHTML={{{{ __html: `{escaped_inner}` }}}} />
    </div>
  );
}}
"""


def _react_scaffold(
    app_name: str,
    screens: list[dict[str, Any]],
    design_md: str,
    *,
    screen_components: dict[str, str] | None = None,
) -> dict[str, str]:
    first = screens[0]["id"] if screens else "main"
    imports = "\n".join(
        f"import {{ {_component_name(s['id'])} }} from './screens/{_component_name(s['id'])}';"
        for s in screens
    )
    routes = "\n".join(
        f'        <Route path="/{s["id"]}" element={{<{_component_name(s["id"])} />}} />'
        for s in screens
    )
    files: dict[str, str] = {
        "package.json": json.dumps(
            {
                "name": re.sub(r"[^a-z0-9-]+", "-", app_name.lower()).strip("-") or "clutch-design-app",
                "private": True,
                "version": "0.0.1",
                "type": "module",
                "scripts": {"dev": "vite --host 127.0.0.1", "build": "vite build"},
                "dependencies": {
                    "react": "^19.0.0",
                    "react-dom": "^19.0.0",
                    "react-router-dom": "^7.0.0",
                },
                "devDependencies": {
                    "@tailwindcss/vite": "^4.0.0",
                    "@vitejs/plugin-react": "^4.3.0",
                    "tailwindcss": "^4.0.0",
                    "typescript": "^5.6.0",
                    "vite": "^6.0.0",
                },
            },
            indent=2,
        )
        + "\n",
        "vite.config.ts": "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\nimport tailwindcss from '@tailwindcss/vite';\nexport default defineConfig({ plugins: [react(), tailwindcss()], server: { host: '127.0.0.1', strictPort: false } });\n",
        "index.html": "<!doctype html><html><head><meta charset=\"UTF-8\"/><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"/><title>Clutch Design</title></head><body><div id=\"root\"></div><script type=\"module\" src=\"/src/main.tsx\"></script></body></html>\n",
        "src/index.css": '@import "tailwindcss";\n',
        "src/main.tsx": "import { StrictMode } from 'react';\nimport { createRoot } from 'react-dom/client';\nimport { BrowserRouter } from 'react-router-dom';\nimport App from './App';\nimport './index.css';\ncreateRoot(document.getElementById('root')!).render(<StrictMode><BrowserRouter><App /></BrowserRouter></StrictMode>);\n",
        "src/App.tsx": f"import {{ Navigate, Route, Routes }} from 'react-router-dom';\n{imports}\nexport default function App() {{\n  return (\n    <Routes>\n      <Route path=\"/\" element={{<Navigate to=\"/{first}\" replace />}} />\n{routes}\n    </Routes>\n  );\n}}\n",
        "DESIGN.md": design_md,
    }
    screen_components = screen_components or {}
    for s in screens:
        cname = _component_name(s["id"])
        files[f"src/screens/{cname}.tsx"] = screen_components.get(
            s["id"],
            f"""export function {cname}() {{
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-8">
      <h1 className="text-2xl font-bold mb-2">{s.get("name", s["id"])}</h1>
      <p className="text-slate-500 text-sm">Generated by Clutch Design</p>
    </div>
  );
}}
""",
        )
    return files


def generate_react(run_id: str) -> dict[str, Any]:
    from src.models_config import get_router, is_model_available

    session_dir_path = session_dir(run_id)
    manifest = read_manifest(session_dir_path)
    if not manifest.get("prototype_approved"):
        raise DesignError("Approve the prototype before generating UI code")
    screens = [s for s in (manifest.get("screens") or []) if not s.get("deleted")]
    if not screens:
        raise DesignError("No screens to codegen")
    design_md = (session_dir_path / DESIGN_MD).read_text(encoding="utf-8") if (session_dir_path / DESIGN_MD).is_file() else ""
    router = get_router()
    model_id = router.active_model_id
    all_ids = [str(s["id"]) for s in screens]
    screen_components: dict[str, str] = {}
    for s in screens:
        sid = str(s["id"])
        html_path = resolve_screen_html_path(session_dir_path, s)
        if not html_path.is_file():
            html_path = session_dir_path / "screens" / f"{sid}.html"
        html = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
        cname = _component_name(sid)
        if html and is_model_available(router, model_id):
            try:
                screen_components[sid] = _html_to_react_component(
                    router,
                    html=html,
                    component_name=cname,
                    screen_id=sid,
                    all_screen_ids=all_ids,
                    design_md=design_md,
                    model_id=model_id,
                )
            except Exception as exc:
                logger.warning("design react LLM failed screen=%s err=%s", sid, exc)
    files = _react_scaffold(
        str(manifest.get("name") or "App"),
        screens,
        design_md,
        screen_components=screen_components,
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
        f"Implement business logic for approved Clutch Design «{manifest.get('name')}».\n"
        f"Design system: {design_md_path}\n"
        f"React scaffold: {react_path}\n"
        f"Brief: {manifest.get('prompt') or '(none)'}\n"
        "Respect DESIGN.md. Wire real data; do not redesign unless asked."
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
