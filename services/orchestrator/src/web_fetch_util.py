"""D12 helper — fetch a URL and return truncated text for agent summarization."""

from __future__ import annotations

import re
import time
from html.parser import HTMLParser
from typing import Any

import httpx

_MAX_BYTES = 400_000
_MAX_TEXT_CHARS = 24_000
_DEFAULT_TIMEOUT_S = 20
_MAX_ATTEMPTS = 2
_RETRY_SLEEP_S = 0.4
_USER_AGENT = (
    "Mozilla/5.0 (compatible; ClutchAgent/1.0; +https://github.com/fancy1108/Clutch) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


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


def _friendly_network_error(exc: BaseException) -> str:
    detail = str(exc).strip() or type(exc).__name__
    lowered = detail.lower()
    if "unexpected_eof_while_reading" in lowered or "eof occurred in violation of protocol" in lowered:
        return (
            "TLS connection closed early by the remote host (SSL UNEXPECTED_EOF). "
            "The site may block non-browser clients or the network interrupted the handshake. "
            "Try web_search for an alternate source, or a different URL."
        )
    if "certificate" in lowered or "ssl" in lowered or "tls" in lowered:
        return (
            f"TLS/SSL error talking to the URL: {detail}. "
            "Try web_search or another HTTPS endpoint."
        )
    if "timed out" in lowered or "timeout" in lowered:
        return f"Fetch timed out: {detail}"
    return f"fetch failed: {detail}"


def _should_retry(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(
        token in text
        for token in (
            "unexpected_eof_while_reading",
            "eof occurred in violation of protocol",
            "connection reset",
            "connection aborted",
            "temporarily unavailable",
            "timed out",
            "timeout",
        )
    )


# Search-engine result pages burn tool budget and return noisy HTML — prefer web_search.
# NOTE: do NOT match bare `baidu.com/s?` — that false-positives Baijiahao articles
# (`baijiahao.baidu.com/s?id=…`).
_SERP_HOST_PATH = (
    ("bing.com", "/search"),
    ("google.com", "/search"),
    ("google.com.hk", "/search"),
    ("google.co.jp", "/search"),
    ("search.yahoo.com", "/"),
    ("yandex.com", "/search"),
    ("yandex.ru", "/search"),
    ("sogou.com", "/web"),
)


def is_search_engine_serp_url(url: str) -> bool:
    """True when URL is a search-engine results page (not a concrete article)."""
    from urllib.parse import parse_qs, urlparse

    cleaned = (url or "").strip()
    if not cleaned.startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(cleaned)
    except Exception:
        return False
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").lower() or "/"
    query = (parsed.query or "").lower()

    # DuckDuckGo HTML/lite SERPs
    if "duckduckgo.com" in host:
        if path.startswith("/html") or path == "/" or path.startswith("/?"):
            return True
        if "q=" in query:
            return True

    # Baidu search only on the main search host — not baijiahao / zhidao / tieba.
    if host in {"baidu.com", "m.baidu.com"}:
        if path.rstrip("/") == "/s":
            qs = parse_qs(parsed.query)
            if any(k in qs for k in ("wd", "word", "q")):
                return True
            # `/s` without article-style `id=` is still treated as SERP.
            if "id" not in qs:
                return True
        return False

    # 360 so.com search
    if host in {"so.com", "www.so.com"} and path.rstrip("/").startswith("/s"):
        return True

    for serp_host, serp_path in _SERP_HOST_PATH:
        if host == serp_host or host.endswith("." + serp_host):
            if path.startswith(serp_path.rstrip("/")) or path == serp_path:
                return True
    return False


def extract_serp_query(url: str) -> str:
    """Pull the user query out of a Google/Bing/Baidu/DDG results URL when possible."""
    from urllib.parse import parse_qs, unquote_plus, urlparse

    cleaned = (url or "").strip()
    if not cleaned.startswith(("http://", "https://")):
        return ""
    try:
        parsed = urlparse(cleaned)
    except Exception:
        return ""
    qs = parse_qs(parsed.query)
    for key in ("q", "wd", "word", "query", "text", "keywords"):
        values = qs.get(key) or []
        if values and str(values[0]).strip():
            return unquote_plus(str(values[0]).strip())
    return ""


def serp_redirect_error_message(url: str) -> str:
    query = extract_serp_query(url)
    if query:
        return (
            "web_fetch cannot be used on search-engine result pages "
            f"(Google/Bing/…). Call web_search with query={query!r}, "
            "then web_fetch 1–2 concrete article URLs from the results — "
            "never google.com/search or bing.com/search."
        )
    return (
        "web_fetch cannot be used on search-engine result pages "
        "(Google/Bing/DuckDuckGo/Baidu/…). "
        "Call web_search with a query instead, then web_fetch a concrete result URL."
    )


def fetch_url_text(url: str, *, timeout_sec: int = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    """Fetch URL; return {url, status, content_type, text, truncated}."""
    cleaned = (url or "").strip()
    if not cleaned.startswith(("http://", "https://")):
        raise ValueError("url must start with http:// or https://")
    if is_search_engine_serp_url(cleaned):
        raise ValueError(serp_redirect_error_message(cleaned))

    timeout = max(5, int(timeout_sec))
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,text/plain,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    last_error: BaseException | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(cleaned, headers=headers)
            status = int(response.status_code)
            content_type = str(response.headers.get("content-type") or "")
            raw = response.content[: _MAX_BYTES + 1]
            if status >= 400:
                text = raw.decode("utf-8", errors="replace")[:_MAX_TEXT_CHARS]
                return {
                    "url": str(response.url),
                    "status": status,
                    "content_type": content_type,
                    "text": text,
                    "truncated": len(response.content) > _MAX_BYTES,
                    "error": f"HTTP {status}",
                }
            break
        except Exception as exc:
            # Catch SSLError / OSError as well as httpx wrappers — never leak raw urlopen.
            last_error = exc
            if attempt + 1 < _MAX_ATTEMPTS and _should_retry(exc):
                time.sleep(_RETRY_SLEEP_S)
                continue
            raise ValueError(_friendly_network_error(exc)) from exc
    else:
        raise ValueError(_friendly_network_error(last_error or RuntimeError("fetch failed")))

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
