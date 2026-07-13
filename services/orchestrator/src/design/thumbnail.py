"""Thumbnail rendering and loading helpers for design canvas sessions."""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

from src.workspace import WorkspaceError, require_workspace
from src.design.session_store import (
    DESIGN_ROOT,
    THUMBNAIL_PNG,
    THUMBNAIL_SVG,
    find_existing_session_dir,
)


def first_hex(colors: dict[str, Any] | None, key: str, fallback: str) -> str:
    if not colors:
        return fallback
    values = colors.get(key)
    if isinstance(values, list) and values:
        raw = str(values[0]).strip()
        if re.match(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", raw):
            return raw
    if isinstance(values, str) and re.match(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", values.strip()):
        return values.strip()
    return fallback


def write_thumbnail_svg(
    session_dir: Path,
    spec: dict[str, Any] | None,
    *,
    device: str = "web",
) -> str:
    """Legacy silhouette SVG — kept for tests; prefer live HTML preview in the sidebar."""
    colors = (spec or {}).get("colors") if isinstance(spec, dict) else None
    if not isinstance(colors, dict):
        colors = {}
    primary = first_hex(colors, "primary", "#2563eb")
    secondary = first_hex(colors, "secondary", "#94a3b8")
    surface = first_hex(colors, "neutral", "#FFFFFF")
    is_app = (device or "web").strip().lower() == "app"

    if is_app:
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160">
  <rect width="160" height="160" rx="20" fill="#EEF2FF"/>
  <rect x="44" y="12" width="72" height="136" rx="14" fill="{surface}" stroke="#1E293B" stroke-width="3"/>
  <rect x="68" y="20" width="24" height="5" rx="2.5" fill="#CBD5E1"/>
  <rect x="54" y="36" width="52" height="8" rx="3" fill="#0F172A" opacity="0.85"/>
  <rect x="54" y="52" width="52" height="40" rx="6" fill="{primary}"/>
  <rect x="54" y="100" width="24" height="20" rx="4" fill="#E2E8F0"/>
  <rect x="82" y="100" width="24" height="20" rx="4" fill="{secondary}" opacity="0.65"/>
  <rect x="54" y="128" width="52" height="10" rx="4" fill="{primary}"/>
  <circle cx="80" cy="142" r="3.5" fill="#CBD5E1"/>
</svg>
"""
    else:
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160">
  <rect width="160" height="160" rx="20" fill="#F1F5F9"/>
  <rect x="10" y="36" width="140" height="96" rx="10" fill="{surface}" stroke="#1E293B" stroke-width="2.5"/>
  <rect x="10" y="36" width="140" height="22" rx="10" fill="#E2E8F0"/>
  <rect x="10" y="52" width="140" height="6" fill="#E2E8F0"/>
  <circle cx="26" cy="47" r="4" fill="#F87171"/>
  <circle cx="40" cy="47" r="4" fill="#FBBF24"/>
  <circle cx="54" cy="47" r="4" fill="#34D399"/>
  <rect x="68" y="43" width="68" height="8" rx="4" fill="#F8FAFC" stroke="#94A3B8"/>
  <rect x="22" y="70" width="116" height="10" rx="3" fill="#0F172A" opacity="0.8"/>
  <rect x="22" y="88" width="54" height="32" rx="5" fill="{primary}"/>
  <rect x="84" y="88" width="54" height="14" rx="3" fill="#E2E8F0"/>
  <rect x="84" y="106" width="54" height="14" rx="3" fill="{secondary}" opacity="0.55"/>
</svg>
"""
    path = session_dir / THUMBNAIL_SVG
    path.write_text(svg, encoding="utf-8")
    return THUMBNAIL_SVG


def clear_fake_thumbnail(session_dir: Path) -> None:
    """Remove legacy silhouette SVG so empty drafts stay gray in the sidebar."""
    for name in (THUMBNAIL_SVG, THUMBNAIL_PNG):
        path = session_dir / name
        if path.is_file():
            try:
                path.unlink()
            except Exception:
                pass


def load_thumbnail_data_url(session_dir: Path) -> str | None:
    """Load a real captured thumbnail only — never invent a silhouette for empty drafts."""
    png_path = session_dir / THUMBNAIL_PNG
    if png_path.is_file():
        encoded = base64.b64encode(png_path.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    # Legacy SVG silhouettes are intentionally ignored (they lied about empty sessions).
    return None


def thumbnail_data_url_for_run(run_id: str) -> str | None:
    """Resolve sidebar image thumbnail for a Design session (None → gray placeholder)."""
    try:
        root = require_workspace() / DESIGN_ROOT
    except WorkspaceError:
        return None
    session_dir = find_existing_session_dir(root, run_id)
    if session_dir is None:
        return None
    return load_thumbnail_data_url(session_dir)
