"""D33 — rich read_file helpers for images (OCR) and PDF (pdftotext)."""

from __future__ import annotations

import base64
import mimetypes
import shutil
import subprocess
from pathlib import Path

_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"})
_PDF_EXTENSIONS = frozenset({".pdf"})
_MAX_PDF_CHARS = 120_000


def is_rich_read_path(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix in _IMAGE_EXTENSIONS or suffix in _PDF_EXTENSIONS


def read_image_workspace_file(path: Path) -> str:
    data = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(data).decode("ascii")
    data_url = f"data:{mime};base64,{encoded}"
    try:
        from src.design.image_analysis import image_analysis_prompt_fragment_for_chat
    except ImportError:
        image_analysis_prompt_fragment_for_chat = None  # type: ignore[assignment]
    if image_analysis_prompt_fragment_for_chat is not None:
        fragment = (image_analysis_prompt_fragment_for_chat(data_url) or "").strip()
        if fragment:
            return fragment
    return (
        f"[Image file: {path.name}] Local OCR/vision analysis unavailable. "
        "Describe the image in text if the user needs content from it."
    )


def read_pdf_workspace_file(path: Path) -> str:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return (
            "Error executing tool: pdftotext not found on PATH. "
            "Install poppler-utils (e.g. `brew install poppler`) to read PDF files."
        )
    try:
        proc = subprocess.run(
            [pdftotext, str(path), "-"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Error executing tool: pdftotext timed out reading PDF"
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "pdftotext failed").strip()
        return f"Error executing tool: {err}"
    text = (proc.stdout or "").strip()
    if not text:
        return f"(PDF {path.name} — no extractable text)"
    if len(text) > _MAX_PDF_CHARS:
        text = text[:_MAX_PDF_CHARS] + "\n…[truncated]"
    return text
