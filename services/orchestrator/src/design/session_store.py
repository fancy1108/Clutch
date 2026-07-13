"""Session persistence, manifest directory mappings, and file storage CRUD."""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
import base64
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.workspace import WorkspaceError, require_workspace

try:
    from src.design import service
    os_mod = getattr(service, "os", os)
except (ImportError, AttributeError):
    os_mod = os

try:
    from src.design import service
    time_mod = getattr(service, "time", time)
except (ImportError, AttributeError):
    time_mod = time

logger = logging.getLogger(__name__)

DESIGN_ROOT = ".clutch/design/sessions"
MANIFEST = "manifest.json"
DESIGN_MD = "DESIGN.md"
SPEC_JSON = "spec.json"
THUMBNAIL_SVG = "thumbnail.svg"
THUMBNAIL_PNG = "thumbnail.png"
_REF_MD_REL = "reference_design.md"
_URL_SNAPSHOT_REL = "url_snapshot.json"
_MAX_MD_CHARS = 200_000

_DEFAULT_FOLDER_TITLES = frozenset(
    {
        "",
        "new design",
        "new-design",
        "design",
        "untitled",
        "新建设计",
    }
)


class DesignError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def safe_folder_slug(text: str, *, max_len: int = 40) -> str:
    """Filesystem-safe folder label — keeps CJK so users can recognize the session."""
    import re
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", (text or "").strip())
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip(".-")
    if not cleaned:
        return "design"
    return cleaned[:max_len].rstrip(".-") or "design"


def session_folder_name(run_id: str, *, title: str, device: str = "web") -> str:
    """Human-readable folder: `{slug}-{device_tag}__{run_id}` (run_id keeps uniqueness)."""
    slug = safe_folder_slug(title)
    device_tag = "mobile" if (device or "web").strip().lower() == "app" else "web"
    return f"{slug}-{device_tag}__{run_id}"


def find_existing_session_dir(root: Path, run_id: str) -> Path | None:
    """Resolve session dir: exact `run_id` (legacy) or `*__{run_id}` (readable)."""
    if not run_id:
        return None
    exact = root / run_id
    if exact.is_dir():
        return exact
    suffix = f"__{run_id}"
    if not root.is_dir():
        return None
    matches = [p for p in root.iterdir() if p.is_dir() and p.name.endswith(suffix)]
    if not matches:
        return None
    # Prefer the most recently modified if duplicates somehow exist.
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def session_dir(run_id: str, workspace: Path | None = None) -> Path:
    root = (workspace or require_workspace()) / DESIGN_ROOT
    root.mkdir(parents=True, exist_ok=True)
    existing = find_existing_session_dir(root, run_id)
    if existing is not None:
        return existing
    path = root / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_windows() -> bool:
    try:
        from src.design import service
        if hasattr(service, "_is_windows"):
            return service._is_windows()
    except ImportError:
        pass
    return os_mod.name == "nt"


def read_manifest(session_dir_path: Path) -> dict[str, Any]:
    path = session_dir_path / MANIFEST
    if not path.is_file():
        raise DesignError("Design session not found")
    last_err: Exception | None = None
    for _ in range(12):
        try:
            raw = path.read_text(encoding="utf-8").strip()
            if not raw:
                time_mod.sleep(0.01)
                continue
            return json.loads(raw)
        except (json.JSONDecodeError, OSError) as exc:
            last_err = exc
            time_mod.sleep(0.01)
    raise DesignError(f"Design session manifest unreadable: {last_err}")


def write_manifest(session_dir_path: Path, manifest: dict[str, Any]) -> None:
    """Atomic replace so concurrent readers never see a truncated JSON file."""
    manifest["updated_at"] = now_iso()
    path = session_dir_path / MANIFEST
    tmp = session_dir_path / f".{MANIFEST}.{os_mod.getpid()}.{threading.get_ident()}.tmp"
    payload = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(payload, encoding="utf-8")
    last_err: PermissionError | None = None
    for _ in range(12):
        try:
            os_mod.replace(tmp, path)
            return
        except PermissionError as exc:
            if not is_windows():
                raise
            last_err = exc
            time_mod.sleep(0.01)
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    if last_err is not None:
        raise last_err


def update_process_status(
    session_dir_path: Path,
    manifest: dict[str, Any],
    *,
    text: str,
    status: str,
    model_id: str | None = None,
    model_name: str | None = None,
) -> None:
    """Refresh the latest assistant line (in-flight heartbeat for polling UI)."""
    log = list(manifest.get("process_log") or [])
    updated = False
    for i in range(len(log) - 1, -1, -1):
        entry = log[i]
        if entry.get("role") != "assistant" or entry.get("kind") in {"model", "tokens"}:
            continue
        next_entry = {**entry, "text": text, "status": status, "at": now_iso()}
        # Preserve prior model tags; refresh when caller provides the active model.
        if model_name:
            next_entry["model_id"] = model_id
            next_entry["model_name"] = model_name
        elif manifest.get("model_name") and not next_entry.get("model_name"):
            next_entry["model_id"] = manifest.get("model_id")
            next_entry["model_name"] = manifest.get("model_name")
        log[i] = next_entry
        updated = True
        break
    if not updated:
        entry: dict[str, Any] = {"role": "assistant", "text": text, "status": status, "at": now_iso()}
        name = model_name or manifest.get("model_name")
        if name:
            entry["model_id"] = model_id or manifest.get("model_id")
            entry["model_name"] = name
        log.append(entry)
    manifest["process_log"] = log
    manifest["status"] = status
    write_manifest(session_dir_path, manifest)


def append_process_status(
    session_dir_path: Path,
    manifest: dict[str, Any],
    *,
    text: str,
    status: str,
    model_id: str | None = None,
    model_name: str | None = None,
) -> None:
    """Append a new assistant process_log entry (phase transition)."""
    log = list(manifest.get("process_log") or [])
    entry: dict[str, Any] = {"role": "assistant", "text": text, "status": status, "at": now_iso()}
    name = model_name or manifest.get("model_name")
    if name:
        entry["model_id"] = model_id or manifest.get("model_id")
        entry["model_name"] = name
    log.append(entry)
    manifest["process_log"] = log
    manifest["status"] = status
    write_manifest(session_dir_path, manifest)


def screen_html_rel(screen: dict[str, Any]) -> str:
    sid = str(screen.get("id") or "main")
    return str(screen.get("html_path") or f"screens/{sid}.html")


def resolve_screen_html_path(session_dir_path: Path, screen: dict[str, Any]) -> Path:
    return session_dir_path / screen_html_rel(screen)


def first_screen_with_ui(session_dir_path: Path, manifest: dict[str, Any] | None = None) -> str | None:
    """Return screen id of the first HTML file with visible UI content."""
    try:
        data = manifest if isinstance(manifest, dict) else read_manifest(session_dir_path)
    except (OSError, json.JSONDecodeError, DesignError):
        data = {}
    screens = list(data.get("screens") or [])
    candidates: list[str] = []
    for screen in screens:
        sid = str(screen.get("id") or "").strip()
        if sid:
            candidates.append(sid)
    if not candidates:
        screens_dir = session_dir_path / "screens"
        if screens_dir.is_dir():
            candidates = sorted(p.stem for p in screens_dir.glob("*.html"))
    for sid in candidates:
        screen_meta = next((s for s in screens if str(s.get("id")) == sid), {"id": sid})
        path = resolve_screen_html_path(session_dir_path, screen_meta)
        if not path.is_file():
            legacy = session_dir_path / "screens" / f"{sid}.html"
            if legacy.is_file():
                path = legacy
        if path.is_file():
            # Check if there is some UI content beyond headers
            return sid
    return None


def sync_session_folder_name(
    run_id: str,
    *,
    title: str = "",
    device: str = "web",
    workspace: Path | None = None,
) -> Path:
    """Rename Design artifact folder to a readable slug when the session has a real title."""
    root = (workspace or require_workspace()) / DESIGN_ROOT
    root.mkdir(parents=True, exist_ok=True)
    current = find_existing_session_dir(root, run_id)
    if current is None:
        current = session_dir(run_id, workspace=workspace)

    label = (title or "").strip()
    is_default = label.lower() in _DEFAULT_FOLDER_TITLES
    has_ui = first_screen_with_ui(current) is not None
    if is_default and not has_ui:
        desired_name = run_id
    else:
        desired_name = session_folder_name(
            run_id,
            title=label or "design",
            device=device,
        )

    desired = root / desired_name
    if current.resolve() == desired.resolve():
        return current
    if desired.exists():
        return current
    try:
        current.rename(desired)
        logger.info(
            "design session folder renamed run_id=%s from=%s to=%s",
            run_id,
            current.name,
            desired.name,
        )
        return desired
    except OSError as exc:
        logger.warning("design session folder rename failed run_id=%s err=%s", run_id, exc)
        return current


def delete_session_artifacts(run_id: str) -> None:
    """Remove `.clutch/design/sessions/*__{run_id}` (or legacy `{run_id}`) when a session is deleted."""
    if not run_id:
        return
    try:
        from src.design.preview_manager import stop_preview
        stop_preview(run_id)
    except Exception:
        pass
    try:
        root = require_workspace() / DESIGN_ROOT
    except WorkspaceError:
        return
    path = find_existing_session_dir(root, run_id)
    if path is None or not path.is_dir():
        return
    try:
        shutil.rmtree(path)
        logger.info("design session artifacts deleted run_id=%s path=%s", run_id, path)
    except OSError as exc:
        logger.warning("design session artifacts delete failed run_id=%s err=%s", run_id, exc)


def prune_orphan_session_dirs(*, keep_run_ids: set[str]) -> list[str]:
    """Delete Design artifact folders whose run_id is not in the live session history."""
    try:
        root = require_workspace() / DESIGN_ROOT
    except WorkspaceError:
        return []
    if not root.is_dir():
        return []
    keep = {str(x) for x in keep_run_ids if x}
    removed: list[str] = []
    
    from src.design.generator import get_generator_jobs_and_lock
    _generate_jobs, _generate_lock = get_generator_jobs_and_lock()
    
    for child in list(root.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        run_id = name.rsplit("__", 1)[-1] if "__" in name else name
        if run_id in keep:
            continue
        with _generate_lock:
            job = _generate_jobs.get(run_id)
            if job is not None and job.is_alive():
                continue
        try:
            shutil.rmtree(child)
            removed.append(name)
            logger.info("design orphan folder pruned path=%s", child)
        except OSError as exc:
            logger.warning("design orphan prune failed path=%s err=%s", child, exc)
    return removed


def load_reference_data_url(session_dir_path: Path, rel: str | None) -> str | None:
    if not rel:
        return None
    path = session_dir_path / rel
    if not path.is_file():
        return None

    mime = "image/png"
    if rel.endswith(".jpg") or rel.endswith(".jpeg"):
        mime = "image/jpeg"
    elif rel.endswith(".webp"):
        mime = "image/webp"
    elif rel.endswith(".gif"):
        mime = "image/gif"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def save_reference_md(
    session_dir_path: Path,
    content: str | None,
    *,
    name: str | None = None,
) -> str | None:
    """Persist uploaded Design.md; return relative path or None."""
    text = (content or "").strip()
    if not text:
        return None
    if len(text) > _MAX_MD_CHARS:
        raise DesignError(f"Design.md too large (max {_MAX_MD_CHARS // 1000}k chars)")
    (session_dir_path / _REF_MD_REL).write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
    meta = {"name": (name or "DESIGN.md").strip() or "DESIGN.md"}
    (session_dir_path / "reference_md_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return _REF_MD_REL


def load_reference_md(session_dir_path: Path, rel: str | None = None) -> tuple[str | None, str | None]:
    """Return (markdown_text, display_name)."""
    path = session_dir_path / (rel or _REF_MD_REL)
    if not path.is_file():
        return None, None
    text = path.read_text(encoding="utf-8")
    name = "DESIGN.md"
    meta_path = session_dir_path / "reference_md_meta.json"
    if meta_path.is_file():
        try:
            name = str(json.loads(meta_path.read_text(encoding="utf-8")).get("name") or name)
        except json.JSONDecodeError:
            pass
    return text, name


def normalize_reference_url(url: str | None) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return None
    import re
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    if len(raw) > 2000:
        raise DesignError("URL too long")
    if not re.match(r"^https?://[^\s]+$", raw, re.I):
        raise DesignError("Invalid URL")
    return raw


def load_url_snapshot(session_dir_path: Path) -> dict[str, Any] | None:
    path = session_dir_path / _URL_SNAPSHOT_REL
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def save_url_snapshot(session_dir_path: Path, snapshot: dict[str, Any]) -> None:
    (session_dir_path / _URL_SNAPSHOT_REL).write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def save_reference_image(session_dir_path: Path, data_url: str) -> str | None:
    """Save reference image from data URL."""
    import re
    import base64
    m = re.match(r"^data:image/([a-zA-Z0-9+.-]+);base64,(.+)$", data_url.strip())
    if not m:
        raise DesignError("Invalid reference image data URL format")
    ext = m.group(1).lower()
    b64 = m.group(2)
    raw = base64.b64decode(b64)
    if len(raw) > 8_000_000:
        raise DesignError("Reference image too large (max 8MB)")
    rel = f"reference.{ext}"
    (session_dir_path / rel).write_bytes(raw)
    return rel


def public_session_payload(manifest: dict[str, Any], session_dir_path: Path, *, include_html: bool = True) -> dict[str, Any]:
    out = dict(manifest)
    out["path"] = str(session_dir_path)
    out["design_md"] = (
        (session_dir_path / DESIGN_MD).read_text(encoding="utf-8")
        if (session_dir_path / DESIGN_MD).is_file()
        else ""
    )
    if (session_dir_path / SPEC_JSON).is_file():
        try:
            out["spec"] = json.loads((session_dir_path / SPEC_JSON).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            out["spec"] = manifest.get("spec")
    ref_rel = manifest.get("reference_image")
    if include_html and ref_rel:
        out["reference_image_url"] = load_reference_data_url(session_dir_path, str(ref_rel))
    elif ref_rel:
        out["reference_image_url"] = None
        out["reference_image"] = ref_rel
    md_rel = manifest.get("reference_md")
    if md_rel:
        md_text, md_name = load_reference_md(session_dir_path, str(md_rel))
        out["reference_md_name"] = md_name or manifest.get("reference_md_name") or "DESIGN.md"
        out["reference_md_text"] = md_text if include_html else None
    else:
        out["reference_md_name"] = manifest.get("reference_md_name")
        out["reference_md_text"] = None
    out["reference_url"] = manifest.get("reference_url")
    snap = load_url_snapshot(session_dir_path) if include_html else None
    if snap:
        out["url_snapshot"] = {
            "url": snap.get("url"),
            "host": snap.get("host"),
            "title": snap.get("title"),
            "description": snap.get("description"),
        }
    else:
        out["url_snapshot"] = manifest.get("url_snapshot")

    try:
        from src.design.thumbnail import thumbnail_data_url_for_run
        out["thumbnail_url"] = thumbnail_data_url_for_run(manifest.get("run_id") or manifest.get("id", ""))
    except ImportError:
        out["thumbnail_url"] = None

    sid = first_screen_with_ui(session_dir_path, manifest)
    out["ui_preview_url"] = (
        f"/api/design/sessions/{manifest.get('run_id') or manifest.get('id')}/screens/{sid}"
        if sid
        else None
    )

    try:
        workspace_root = require_workspace()
        artifacts: list[str] = []
        for path in sorted(session_dir_path.rglob("*")):
            if path.is_file():
                artifacts.append(str(path.relative_to(workspace_root)))
        out["artifact_paths"] = artifacts
    except (WorkspaceError, OSError, ValueError):
        out["artifact_paths"] = []

    history = list(manifest.get("round_history") or [])
    out["round_history"] = history
    out["round_count"] = len(history)

    if include_html:
        screens = []
        for screen in manifest.get("screens") or []:
            item = dict(screen)
            sid = item.get("id")
            if sid:
                screen_meta = next(
                    (s for s in (manifest.get("screens") or []) if str(s.get("id")) == sid),
                    item,
                )
                html_path = resolve_screen_html_path(session_dir_path, screen_meta)
                if not html_path.is_file():
                    html_path = session_dir_path / "screens" / f"{sid}.html"
                item["html"] = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
                item["active_round_index"] = screen_meta.get("active_round_index")
            screens.append(item)
        out["screens"] = screens

    try:
        from src.design.preview_manager import preview_lock, preview_procs
        with preview_lock:
            preview = preview_procs.get(manifest.get("run_id") or manifest.get("id", ""))
            if preview:
                out["preview_url"] = preview.get("url")
    except ImportError:
        pass

    return out


def ensure_session(run_id: str, *, title: str = "", prompt: str = "") -> dict[str, Any]:
    sdir = session_dir(run_id)
    manifest_path = sdir / MANIFEST
    if manifest_path.is_file():
        return get_session(run_id)
    (sdir / "screens").mkdir(exist_ok=True)
    manifest: dict[str, Any] = {
        "id": run_id,
        "run_id": run_id,
        "name": title.strip() or "New Design",
        "prompt": prompt.strip(),
        "phase": "welcome",
        "status": "draft",
        "device": "web",
        "process_log": [],
        "round_history": [],
        "spec": None,
        "screens": [],
        "prototype_approved": False,
        "react_approved": False,
        "react_ready": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    write_manifest(sdir, manifest)
    return public_session_payload(manifest, sdir)


def get_session(run_id: str) -> dict[str, Any]:
    sdir = session_dir(run_id)
    if not (sdir / MANIFEST).is_file():
        raise DesignError(f"Design session not found: {run_id}")
    manifest = read_manifest(sdir)
    # Lazy-migrate legacy `run_*` folders to readable names.
    title = str(manifest.get("name") or manifest.get("prompt") or "")
    device = str(manifest.get("device") or "web")
    if title.strip() and title.strip().lower() not in _DEFAULT_FOLDER_TITLES:
        sdir = sync_session_folder_name(run_id, title=title, device=device)
        manifest = read_manifest(sdir)
    return public_session_payload(manifest, sdir)


def list_sessions() -> list[dict[str, Any]]:
    root = require_workspace() / DESIGN_ROOT
    if not root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for child in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not child.is_dir() or not (child / MANIFEST).is_file():
            continue
        try:
            items.append(public_session_payload(read_manifest(child), child, include_html=False))
        except (OSError, json.JSONDecodeError, DesignError):
            continue
    return items
