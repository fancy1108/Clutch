"""Chat-generated deliverables live under `.clutch/…` — not the project root.

Mirrors common agent layouts (Claude `.claude/`, agentic `_agentic_output/`, and
Clutch’s existing `.clutch/generated/videos` / attachments / handoffs).
"""

from __future__ import annotations

import contextvars
import re
from pathlib import PurePosixPath

CLUTCH_ARTIFACTS_DIR = ".clutch/artifacts"
CLUTCH_IMAGE_DIR = ".clutch/generated/images"

_user_turn_text: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "clutch_user_turn_text", default=None
)


def bind_user_turn_text(text: str | None) -> contextvars.Token[str | None]:
    return _user_turn_text.set((text or "").strip() or None)


def release_user_turn_text(token: contextvars.Token[str | None]) -> None:
    _user_turn_text.reset(token)


def current_user_turn_text() -> str | None:
    return _user_turn_text.get()

# New chat “research / visual / summary” files — never dump at repo root.
_DELIVERABLE_SUFFIXES = frozenset(
    {
        ".html",
        ".htm",
        ".md",
        ".markdown",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
        ".svg",
        ".pdf",
    }
)

_SOURCE_SUFFIXES = frozenset(
    {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".swift",
        ".c",
        ".cpp",
        ".h",
        ".cs",
        ".rb",
        ".php",
        ".vue",
        ".svelte",
        ".css",
        ".scss",
        ".json",
        ".toml",
        ".yaml",
        ".yml",
        ".sh",
    }
)


def _norm(path: str) -> str:
    return (path or "").strip().replace("\\", "/").lstrip("./")


def is_under_clutch_dir(path: str) -> bool:
    p = _norm(path)
    return p == ".clutch" or p.startswith(".clutch/")


def is_root_level_file(path: str) -> bool:
    p = _norm(path)
    if not p or "/" in p or p.startswith("."):
        return False
    return True


def looks_like_chat_deliverable(path: str) -> bool:
    p = _norm(path)
    if not p or is_under_clutch_dir(p):
        return False
    suffix = PurePosixPath(p).suffix.lower()
    if suffix in _SOURCE_SUFFIXES:
        return False
    return suffix in _DELIVERABLE_SUFFIXES


def relocate_chat_deliverable_path(path: str, *, user_text: str | None = None) -> str:
    """If the model dumps a deliverable at repo root, move it under `.clutch/artifacts/`.

    Does not relocate when the turn is clearly implementing project source code
    (kind == code) or the path already lives under a package/subdir.
    """
    from src.deliverable_intent import classify_deliverable_intent

    p = _norm(path)
    if not p or is_under_clutch_dir(p):
        return path.strip() if path else path
    if not looks_like_chat_deliverable(p):
        return path.strip() if path else path
    if not is_root_level_file(p):
        return path.strip() if path else path

    kind = classify_deliverable_intent(user_text)
    # Real coding turns may still add README.md / docs at root — leave those alone.
    if kind == "code" and PurePosixPath(p).suffix.lower() in {".md", ".markdown"}:
        return path.strip()
    return f"{CLUTCH_ARTIFACTS_DIR}/{PurePosixPath(p).name}"


def rewrite_apply_patch_paths(patch: str, *, user_text: str | None) -> tuple[str, list[str]]:
    """Rewrite *** Add/Update File paths that would pollute the repo root."""
    notes: list[str] = []
    lines = (patch or "").splitlines(keepends=True)
    out: list[str] = []
    path_line = re.compile(
        r"^(\*\*\* (?:Add|Update|Delete) File:\s*)(.+?)(\s*)$"
    )
    for line in lines:
        m = path_line.match(line.rstrip("\n"))
        if not m:
            out.append(line)
            continue
        prefix, raw_path, _ = m.group(1), m.group(2).strip(), m.group(3)
        new_path = relocate_chat_deliverable_path(raw_path, user_text=user_text)
        if new_path.replace("\\", "/") != raw_path.replace("\\", "/"):
            notes.append(f"{raw_path} → {new_path}")
            nl = "\n" if line.endswith("\n") else ""
            out.append(f"{prefix}{new_path}{nl}")
        else:
            out.append(line)
    return "".join(out), notes


def block_html_for_non_page_intent(path: str, *, user_text: str | None) -> str | None:
    """Return an error message if writing this HTML would fake a non-page deliverable."""
    from src.deliverable_intent import forbids_html_substitute

    p = _norm(path)
    if not re.search(r"\.html?$", p, re.IGNORECASE):
        return None
    if not forbids_html_substitute(user_text):
        return None
    return (
        f"Refusing to write {p}: this turn needs an image/video/code/answer, not an HTML page. "
        "Call `generate_image` for pictures/infographics (or switch the footer model to an "
        "image model). Put research notes under `.clutch/artifacts/` as `.md` if needed."
    )
