"""Codex-compatible apply_patch parser and workspace executor (P2 apply_patch)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

BEGIN_PATCH = "*** Begin Patch"
END_PATCH = "*** End Patch"
ADD_MARKER = "*** Add File: "
DELETE_MARKER = "*** Delete File: "
UPDATE_MARKER = "*** Update File: "
ADD_HEADER = "*** Add File"
DELETE_HEADER = "*** Delete File"
UPDATE_HEADER = "*** Update File"
MOVE_MARKER = "*** Move to: "
EOF_MARKER = "*** End of File"
CTX_MARKER = "@@ "

_PATH_MARKERS = (
    (ADD_MARKER, "add"),
    (DELETE_MARKER, "delete"),
    (UPDATE_MARKER, "update"),
    (MOVE_MARKER, "move"),
)


def _split_file_header(trimmed: str, header: str) -> str | None:
    """Return path from `*** X File: path` or None if path is on the next line."""
    if trimmed == header:
        return None
    colon_prefix = f"{header}:"
    if trimmed.startswith(colon_prefix):
        return trimmed[len(colon_prefix) :].strip()
    return None


class ApplyPatchError(ValueError):
    """Invalid patch text or failed apply."""


@dataclass
class UpdateChunk:
    change_context: str | None = None
    old_lines: list[str] = field(default_factory=list)
    new_lines: list[str] = field(default_factory=list)
    is_end_of_file: bool = False


@dataclass
class Hunk:
    kind: Literal["add", "delete", "update"]
    path: str
    contents: str = ""
    move_path: str | None = None
    chunks: list[UpdateChunk] = field(default_factory=list)


@dataclass(frozen=True)
class ApplyPatchResult:
    ok: bool
    summary: str
    changed_paths: list[str]
    details: list[str] = field(default_factory=list)


def normalize_patch_text(patch: str) -> str:
    text = patch.strip()
    lines = text.splitlines()
    if len(lines) >= 4 and lines[0] in ("<<EOF", "<<'EOF'", '<<"EOF"') and lines[-1].endswith("EOF"):
        inner = lines[1:-1]
        if inner and inner[0].strip() == BEGIN_PATCH and inner[-1].strip() == END_PATCH:
            return "\n".join(inner)
    return text


def extract_patch_paths(patch: str) -> list[str]:
    paths: list[str] = []
    pending: str | None = None
    for line in normalize_patch_text(patch).splitlines():
        trimmed = line.strip()
        if trimmed in {BEGIN_PATCH, END_PATCH}:
            continue
        for marker, _kind in _PATH_MARKERS:
            if trimmed.startswith(marker):
                raw = trimmed[len(marker) :].strip()
                if raw and raw not in paths:
                    paths.append(raw)
        for header in (ADD_HEADER, DELETE_HEADER, UPDATE_HEADER):
            split = _split_file_header(trimmed, header)
            if split is None and trimmed == header:
                pending = header
                break
            if split:
                if split not in paths:
                    paths.append(split)
                pending = None
                break
        else:
            if pending and trimmed and not trimmed.startswith("***"):
                if trimmed not in paths:
                    paths.append(trimmed)
                pending = None
    return paths


def parse_patch(patch: str) -> list[Hunk]:
    text = normalize_patch_text(patch)
    lines = text.splitlines()
    if not lines or lines[0].strip() != BEGIN_PATCH:
        raise ApplyPatchError("The first line of the patch must be '*** Begin Patch'")
    if lines[-1].strip() != END_PATCH:
        raise ApplyPatchError("The last line of the patch must be '*** End Patch'")

    hunks: list[Hunk] = []
    mode = "start"
    pending_header: str | None = None
    current: Hunk | None = None
    chunk: UpdateChunk | None = None

    def start_hunk(kind: Literal["add", "delete", "update"], path: str) -> None:
        nonlocal current, mode, chunk, pending_header
        finish_hunk()
        if not path:
            pending_header = kind
            mode = "pending_path"
            return
        current = Hunk(kind=kind, path=path)
        pending_header = None
        mode = kind
        if kind == "update":
            chunk = UpdateChunk()

    def finish_chunk() -> None:
        nonlocal chunk
        if current and current.kind == "update" and chunk is not None:
            if chunk.old_lines or chunk.new_lines or chunk.change_context:
                current.chunks.append(chunk)
        chunk = None

    def finish_hunk() -> None:
        nonlocal current
        finish_chunk()
        if current is not None:
            if current.kind == "update" and not current.chunks:
                raise ApplyPatchError(f"Update file hunk for path '{current.path}' is empty")
            hunks.append(current)
        current = None

    for raw in lines[1:-1]:
        line = raw.rstrip("\r")
        trimmed = line.strip()
        if trimmed == END_PATCH:
            break
        if mode == "pending_path" and pending_header and trimmed and not trimmed.startswith("***"):
            start_hunk(pending_header, trimmed)  # type: ignore[arg-type]
            continue
        add_path = _split_file_header(trimmed, ADD_HEADER)
        if add_path is not None or trimmed == ADD_HEADER:
            start_hunk("add", add_path or "")
            continue
        delete_path = _split_file_header(trimmed, DELETE_HEADER)
        if delete_path is not None or trimmed == DELETE_HEADER:
            start_hunk("delete", delete_path or "")
            continue
        update_path = _split_file_header(trimmed, UPDATE_HEADER)
        if update_path is not None or trimmed == UPDATE_HEADER:
            start_hunk("update", update_path or "")
            continue
        if trimmed.startswith(ADD_MARKER):
            start_hunk("add", trimmed[len(ADD_MARKER) :].strip())
            continue
        if trimmed.startswith(DELETE_MARKER):
            start_hunk("delete", trimmed[len(DELETE_MARKER) :].strip())
            continue
        if trimmed.startswith(UPDATE_MARKER):
            start_hunk("update", trimmed[len(UPDATE_MARKER) :].strip())
            continue
        if mode == "update" and current and trimmed.startswith(MOVE_MARKER):
            current.move_path = trimmed[len(MOVE_MARKER) :].strip()
            continue
        if mode == "add" and current and line.startswith("+"):
            current.contents += line[1:] + "\n"
            continue
        if mode == "update" and current:
            if trimmed == EOF_MARKER:
                if chunk:
                    chunk.is_end_of_file = True
                continue
            if trimmed in ("@@", CTX_MARKER.rstrip()) or trimmed.startswith("@@"):
                finish_chunk()
                ctx = trimmed[2:].strip() if trimmed.startswith("@@") else None
                chunk = UpdateChunk(change_context=ctx or None)
                continue
            if line.startswith(("+", "-", " ")):
                if chunk is None:
                    chunk = UpdateChunk()
                body = line[1:]
                if line[0] == "+":
                    chunk.new_lines.append(body)
                elif line[0] == "-":
                    chunk.old_lines.append(body)
                else:
                    chunk.old_lines.append(body)
                    chunk.new_lines.append(body)
                continue
        if mode in {"delete", "add", "update"} and trimmed.startswith("*** "):
            add_path = _split_file_header(trimmed, ADD_HEADER)
            if add_path is not None or trimmed == ADD_HEADER:
                start_hunk("add", add_path or "")
            elif trimmed.startswith(DELETE_MARKER) or trimmed == DELETE_HEADER or trimmed.startswith(
                f"{DELETE_HEADER}:"
            ):
                delete_path = _split_file_header(trimmed, DELETE_HEADER) or (
                    trimmed[len(DELETE_MARKER) :].strip() if trimmed.startswith(DELETE_MARKER) else ""
                )
                start_hunk("delete", delete_path)
            elif trimmed.startswith(UPDATE_MARKER) or trimmed == UPDATE_HEADER or trimmed.startswith(
                f"{UPDATE_HEADER}:"
            ):
                update_path = _split_file_header(trimmed, UPDATE_HEADER) or (
                    trimmed[len(UPDATE_MARKER) :].strip() if trimmed.startswith(UPDATE_MARKER) else ""
                )
                start_hunk("update", update_path)
    finish_hunk()
    if not hunks:
        raise ApplyPatchError(
            "Patch contains no file changes. Use one line like "
            "'*** Delete File: path' or '*** Delete File' followed by the path on the next line."
        )
    return hunks


def _seek_sequence(lines: list[str], pattern: list[str], start: int, eof: bool) -> int | None:
    if not pattern:
        return start
    if len(pattern) > len(lines):
        return None
    search_start = max(0, len(lines) - len(pattern)) if eof and len(lines) >= len(pattern) else start
    for i in range(search_start, len(lines) - len(pattern) + 1):
        window = lines[i : i + len(pattern)]
        if window == pattern:
            return i
        if [w.rstrip() for w in window] == [p.rstrip() for p in pattern]:
            return i
        if [w.strip() for w in window] == [p.strip() for p in pattern]:
            return i
    return None


def _apply_chunks(content: str, chunks: list[UpdateChunk], path: str) -> str:
    lines = content.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    replacements: list[tuple[int, int, list[str]]] = []
    line_index = 0
    for piece in chunks:
        if piece.change_context:
            idx = _seek_sequence(lines, [piece.change_context], line_index, False)
            if idx is None:
                raise ApplyPatchError(f"Failed to find context '{piece.change_context}' in {path}")
            line_index = idx + 1
        if not piece.old_lines:
            insert_at = len(lines) - 1 if lines and lines[-1] == "" else len(lines)
            replacements.append((insert_at, 0, piece.new_lines))
            continue
        pattern = piece.old_lines
        new_slice = piece.new_lines
        found = _seek_sequence(lines, pattern, line_index, piece.is_end_of_file)
        if found is None and pattern and pattern[-1] == "":
            pattern = pattern[:-1]
            new_slice = new_slice[:-1] if new_slice and new_slice[-1] == "" else new_slice
            found = _seek_sequence(lines, pattern, line_index, piece.is_end_of_file)
        if found is None:
            raise ApplyPatchError(f"Failed to find replacement target in {path}")
        replacements.append((found, len(pattern), new_slice))
        line_index = found + len(pattern)
    for start, old_len, new_lines in sorted(replacements, key=lambda item: item[0], reverse=True):
        lines[start : start + old_len] = new_lines
    if not lines or lines[-1] != "":
        lines.append("")
    return "\n".join(lines)


def _resolve_target(relative_path: str) -> Path:
    from src.workspace import resolve_allowed_path

    return resolve_allowed_path(relative_path)


def apply_patch_in_workspace(patch: str) -> ApplyPatchResult:
    hunks = parse_patch(patch)
    changed: list[str] = []
    details: list[str] = []
    for hunk in hunks:
        target = _resolve_target(hunk.path)
        rel = hunk.path
        if hunk.kind == "add":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(hunk.contents, encoding="utf-8")
            details.append(f"Added {rel}")
            changed.append(rel)
        elif hunk.kind == "delete":
            if target.is_dir():
                raise ApplyPatchError(f"Cannot delete directory as file: {rel}")
            if target.exists():
                target.unlink()
            details.append(f"Deleted {rel}")
            changed.append(rel)
        elif hunk.kind == "update":
            if not target.is_file():
                raise ApplyPatchError(f"Update target not found: {rel}")
            new_content = _apply_chunks(target.read_text(encoding="utf-8"), hunk.chunks, rel)
            dest = _resolve_target(hunk.move_path) if hunk.move_path else target
            dest_rel = hunk.move_path or rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(new_content, encoding="utf-8")
            if hunk.move_path and dest != target:
                target.unlink(missing_ok=True)
                details.append(f"Moved {rel} -> {dest_rel}")
                changed.extend([rel, dest_rel])
            else:
                details.append(f"Updated {rel}")
                changed.append(rel)
    summary = "; ".join(details) if details else "No changes applied"
    unique = list(dict.fromkeys(changed))
    return ApplyPatchResult(ok=True, summary=summary, changed_paths=unique, details=details)


def format_apply_patch_result(result: ApplyPatchResult) -> str:
    import json

    payload: dict[str, Any] = {
        "ok": result.ok,
        "summary": result.summary,
        "changed_paths": result.changed_paths,
        "details": result.details,
    }
    return json.dumps(payload, ensure_ascii=False)
