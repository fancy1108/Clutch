"""D12 helper — fetch a URL and return truncated text for agent summarization."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_MAX_BYTES = 400_000
_MAX_TEXT_CHARS = 24_000
_DEFAULT_TIMEOUT_S = 20


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        joined = " ".join(self._chunks)
        joined = re.sub(r"\s+", " ", joined).strip()
        return joined


def fetch_url_text(url: str, *, timeout_sec: int = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    """Fetch URL; return {url, status, content_type, text, truncated}."""
    cleaned = (url or "").strip()
    if not cleaned.startswith(("http://", "https://")):
        raise ValueError("url must start with http:// or https://")
    req = Request(
        cleaned,
        headers={
            "User-Agent": "ClutchAgent/1.0 (+local; D12 web_fetch)",
            "Accept": "text/html,application/xhtml+xml,text/plain,application/json;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=max(5, int(timeout_sec))) as resp:  # noqa: S310 — intentional agent fetch
            status = int(getattr(resp, "status", 200) or 200)
            content_type = str(resp.headers.get("Content-Type") or "")
            raw = resp.read(_MAX_BYTES + 1)
    except HTTPError as exc:
        body = exc.read(_MAX_BYTES) if hasattr(exc, "read") else b""
        return {
            "url": cleaned,
            "status": int(exc.code),
            "content_type": str(exc.headers.get("Content-Type") or ""),
            "text": body.decode("utf-8", errors="replace")[:_MAX_TEXT_CHARS],
            "truncated": len(body) >= _MAX_BYTES,
            "error": str(exc),
        }
    except URLError as exc:
        raise ValueError(f"fetch failed: {exc.reason}") from exc

    truncated = len(raw) > _MAX_BYTES
    if truncated:
        raw = raw[:_MAX_BYTES]
    decoded = raw.decode("utf-8", errors="replace")
    ctype = content_type.lower()
    if "html" in ctype or decoded.lstrip().lower().startswith("<!doctype html") or "<html" in decoded[:200].lower():
        parser = _TextExtractor()
        try:
            parser.feed(decoded)
            text = parser.text()
        except Exception:
            text = re.sub(r"<[^>]+>", " ", decoded)
            text = re.sub(r"\s+", " ", text).strip()
    else:
        text = decoded
    if len(text) > _MAX_TEXT_CHARS:
        text = text[:_MAX_TEXT_CHARS]
        truncated = True
    return {
        "url": cleaned,
        "status": status,
        "content_type": content_type,
        "text": text,
        "truncated": truncated,
    }
