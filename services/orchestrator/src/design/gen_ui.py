from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from src.workspace import WorkspaceError, require_workspace
from src.design.session_store import (
    DESIGN_MD,
    DESIGN_ROOT,
    MANIFEST,
    SPEC_JSON,
    DesignError,
    append_process_status,
    ensure_session,
    esc,
    find_existing_session_dir,
    first_screen_with_ui,
    get_session,
    load_reference_data_url,
    load_reference_md,
    load_url_snapshot,
    normalize_reference_url,
    now_iso,
    public_session_payload,
    read_manifest,
    save_reference_image,
    save_reference_md,
    save_url_snapshot,
    session_dir,
    sync_session_folder_name,
    update_process_status,
    write_manifest,
)
from src.design.layout import (
    default_ui_origin_x,
    ui_frame_width,
    ui_layout_step,
)
from src.design.thumbnail import (
    clear_fake_thumbnail,
    write_thumbnail_svg,
)
from src.design.token_usage import (
    empty_token_usage,
    format_token_usage_text,
    merge_token_usage,
    usage_from_llm_result,
)
from src.design.builtin_presets import resolve_builtin_spec
from src.design.layout_patterns import (
    detect_layout_pattern,
    enrich_fallback_spec,
    fewshot_for_pattern,
    layout_wrapper_hint,
    parse_review_score,
    review_threshold,
)

from src.design.gen_spec import (
    _detect_html_intent,
    _html_matches_brief_intent,
    _prompt_intent,
)

logger = logging.getLogger(__name__)


def _llm_result(
    result: object,
    *,
    prompt: str = "",
) -> tuple[str, str | None, dict[str, int], bool]:
    from src.design.generator import _llm_result as _impl

    return _impl(result, prompt=prompt)

_TASTE_ANTI_PATTERNS = (
    "Taste / anti-patterns (must follow):\n"
    "- No Inter font; no pure black #000000; no neon purple/blue glow CTAs.\n"
    "- No generic 3 equal feature cards; prefer asymmetric or 2-column layouts.\n"
    "- No AI copy clichés (Elevate, Seamless, Unleash, Next-Gen) or invented metrics.\n"
    "- No emoji decoration; no 'Scroll to explore' filler.\n"
)
_LLM_TIMEOUT_SEC = 45.0
_LLM_UI_TIMEOUT_SEC = 90.0
_DESIGN_REVIEW_ENABLED = os.environ.get("CLUTCH_DESIGN_REVIEW", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _shell_html(title: str, body: str, *, device: str = "web") -> str:
    is_app = (device or "web").strip().lower() == "app"
    canvas = (
        "width:390px;min-height:844px;margin:0 auto;"
        if is_app
        else "width:1920px;min-height:1080px;margin:0 auto;"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width={'390' if is_app else '1920'}, initial-scale=1"/>
<title>{esc(title)}</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  html, body {{ margin:0; background:#f8fafc; font-family: system-ui, -apple-system, sans-serif; }}
  .clutch-canvas {{ {canvas} background:#fff; }}
</style>
</head>
<body>
<div class="clutch-canvas">
{body}
</div>
</body>
</html>
"""


def _html_has_visible_content(html: str) -> bool:
    """True when the document body has real UI — not an empty shell after wrap."""
    if not (html or "").strip():
        return False
    lower = html.lower()
    if "<html" in lower and "<body" not in lower:
        return False
    if "<style" in lower and "</style>" not in lower:
        return False
    if "<script" in lower and "</script>" not in lower:
        return False
    m = re.search(
        r'class=["\']clutch-canvas["\'][^>]*>([\s\S]*?)</div>\s*</body>',
        html,
        re.I,
    )
    if not m:
        m = re.search(r"<body[^>]*>([\s\S]*?)</body>", html, re.I)
    chunk = m.group(1) if m else html
    chunk = re.sub(r"<script[\s\S]*?</script>", "", chunk, flags=re.I)
    chunk = re.sub(r"<style[\s\S]*?</style>", "", chunk, flags=re.I)
    chunk = re.sub(r"<!--[\s\S]*?-->", "", chunk)
    compact = re.sub(r">\s+<", "><", chunk.strip())
    if not compact:
        return False
    if re.fullmatch(r"(?:<div\b[^>]*>\s*</div>\s*)+", compact, flags=re.I):
        return False
    text = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", chunk))
    if len(text) >= 2:
        return True
    return bool(
        re.search(
            r"<(?:div|section|main|header|nav|footer|article|aside|h[1-6]|p|button|a|"
            r"img|ul|ol|li|form|input|table|span|svg)\b[^>]*>",
            chunk,
            re.I,
        )
    )


def _fallback_login_html(prompt: str, spec: dict[str, Any]) -> str:
    return "<div>Login stub</div>"


def _fallback_ui_html(prompt: str, spec: dict[str, Any], *, device: str = "web") -> str:
    """Offline-only stub when no model/API key is configured."""
    primary = (spec.get("colors") or {}).get("primary") or ["#2563eb"]
    accent = primary[0] if isinstance(primary, list) else str(primary)
    title = (prompt.strip() or str(spec.get("name") or "Welcome")).split("\n")[0][:48]
    intent = _prompt_intent(prompt)
    is_app = (device or "web").strip().lower() == "app"
    shell = "px-4" if is_app else "px-16"
    cols = "grid-cols-2" if is_app else "grid-cols-4"
    cards = "".join(
        f"""
      <div class="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm">
        <div class="{'h-28' if is_app else 'h-44'}" style="background:{accent};opacity:0.85"></div>
        <div class="p-3 space-y-1">
          <p class="text-sm font-semibold">Product {i}</p>
          <p class="text-xs text-slate-500">¥{(i * 129)}</p>
          <button style="background:{accent}" class="mt-2 w-full rounded-lg text-white text-xs font-semibold py-1.5">Add to cart</button>
        </div>
      </div>"""
        for i in range(1, 5)
    )

    if intent == "login":
        body = f"""
<div class="min-h-full flex items-center justify-center p-6 {shell}">
  <div class="w-full {'max-w-sm' if is_app else 'max-w-md'} space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div>
      <h1 class="text-2xl font-bold">Welcome back</h1>
      <p class="text-sm text-slate-500 mt-1">{esc(title)}</p>
    </div>
    <label class="block text-xs font-semibold text-slate-600">Email
      <input class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm" placeholder="you@company.com"/>
    </label>
    <label class="block text-xs font-semibold text-slate-600">Password
      <input type="password" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm" placeholder="••••••••"/>
    </label>
    <button style="background:{accent}" class="w-full rounded-xl text-white font-semibold py-2.5 text-sm">Log in</button>
  </div>
</div>
"""
    elif intent == "shop":
        body = f"""
<div class="min-h-full">
  <header class="py-4 border-b border-slate-100 flex items-center justify-between {shell}">
    <p class="font-bold text-sm">{esc(str(spec.get("name") or "Store"))}</p>
    <span class="text-xs text-slate-500">Cart (0)</span>
  </header>
  <main class="py-8 {shell}">
    <h1 class="{'text-xl' if is_app else 'text-3xl'} font-bold mb-1">Featured</h1>
    <p class="text-sm text-slate-500 mb-6">Shop the latest picks</p>
    <div class="grid {cols} gap-4">{cards}
    </div>
  </main>
</div>
"""
    elif intent == "dashboard":
        body = f"""
<div class="min-h-full flex {'flex-col' if is_app else ''}">
  <aside class="{'w-full border-b' if is_app else 'w-64 border-r min-h-[1080px]'} bg-slate-900 text-white p-5 space-y-3">
    <p class="font-bold text-sm">{esc(title)}</p>
    <p class="text-xs text-slate-400">Overview</p>
    <p class="text-xs text-slate-400">Orders</p>
    <p class="text-xs text-slate-400">Settings</p>
  </aside>
  <main class="flex-1 p-6 space-y-4">
    <h1 class="text-2xl font-bold">Dashboard</h1>
    <div class="grid grid-cols-2 {'md:grid-cols-3' if not is_app else ''} gap-4">
      <div class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-slate-500">Revenue</p><p class="text-lg font-bold">¥128k</p></div>
      <div class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-slate-500">Orders</p><p class="text-lg font-bold">1,284</p></div>
      <div class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-slate-500">Users</p><p class="text-lg font-bold">8.2k</p></div>
    </div>
    <div class="h-56 rounded-xl border border-slate-200 bg-white" style="background:linear-gradient(135deg,{accent}22,transparent)"></div>
  </main>
</div>
"""
    elif intent == "music":
        tracks = "".join(
            f"""
      <button type="button" class="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-left hover:bg-white/10 {'bg-white/15' if i == 1 else ''}">
        <span class="flex h-10 w-10 items-center justify-center rounded-lg text-xs font-bold text-white" style="background:{accent}">{i}</span>
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-semibold text-white">Track {i} · Night Drive</span>
          <span class="block truncate text-xs text-white/50">Artist {i}</span>
        </span>
        <span class="text-[10px] text-white/40">3:2{i}</span>
      </button>"""
            for i in range(1, 6)
        )
        if is_app:
            body = f"""
<div class="min-h-full text-white" style="background:linear-gradient(180deg,#0f172a,#020617)">
  <header class="px-4 pt-6 pb-3 flex items-center justify-between">
    <p class="text-sm font-bold">{esc(title)}</p>
    <span class="text-xs text-white/50">Library</span>
  </header>
  <main class="px-4 space-y-4 pb-28">
    <div class="rounded-2xl p-4" style="background:linear-gradient(135deg,{accent},#111827)">
      <p class="text-xs text-white/70">Now playing</p>
      <p class="mt-1 text-lg font-bold">Midnight Pulse</p>
      <p class="text-xs text-white/60">SonicFlow · Album</p>
    </div>
    <section>
      <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-white/50">Playlist</p>
      <div class="space-y-1">{tracks}</div>
    </section>
    <section class="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
      <p class="mb-2 text-xs font-semibold text-white/60">Lyrics</p>
      <p class="text-sm leading-relaxed text-white/90">City lights blur past the glass…</p>
      <p class="mt-2 text-sm leading-relaxed text-white/50">Hold the night a little longer…</p>
      <p class="mt-2 text-sm leading-relaxed text-white/35">Pulse under neon rain…</p>
    </section>
  </main>
  <footer class="fixed bottom-0 left-0 right-0 border-t border-white/10 bg-black/80 px-4 py-3 backdrop-blur">
    <div class="flex items-center justify-between gap-3">
      <button type="button" class="rounded-full bg-white/10 px-3 py-2 text-xs">Prev</button>
      <button type="button" class="rounded-full px-5 py-2 text-xs font-bold text-white" style="background:{accent}">Play</button>
      <button type="button" class="rounded-full bg-white/10 px-3 py-2 text-xs">Next</button>
    </div>
  </footer>
</div>
"""
        else:
            body = f"""
<div class="min-h-full flex text-white" style="background:#020617">
  <aside class="w-56 border-r border-white/10 p-5 space-y-3">
    <p class="font-bold">{esc(str(spec.get("name") or "SonicFlow"))}</p>
    <p class="text-xs text-white/50">Home</p>
    <p class="text-xs text-white/50">Search</p>
    <p class="text-xs text-white/80">Your Library</p>
  </aside>
  <main class="flex-1 flex flex-col min-h-[1080px]">
    <div class="flex-1 grid grid-cols-2 gap-6 p-8">
      <section class="space-y-4">
        <div class="rounded-3xl p-8" style="background:linear-gradient(135deg,{accent},#1e1b4b)">
          <p class="text-sm text-white/70">Featured</p>
          <h1 class="mt-2 text-4xl font-bold">Midnight Pulse</h1>
          <p class="mt-2 text-white/60">A dark immersive player with playlist + lyrics.</p>
        </div>
        <div>
          <p class="mb-3 text-sm font-semibold text-white/70">Playlist</p>
          <div class="space-y-1">{tracks}</div>
        </div>
      </section>
      <section class="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur flex flex-col">
        <p class="text-sm font-semibold text-white/70">Lyrics</p>
        <div class="mt-6 flex-1 space-y-4 text-lg leading-relaxed">
          <p class="text-white">City lights blur past the glass…</p>
          <p class="text-white/70">Hold the night a little longer…</p>
          <p class="text-white/45">Pulse under neon rain…</p>
          <p class="text-white/30">Switch tracks — keep the vibe.</p>
        </div>
      </section>
    </div>
    <footer class="border-t border-white/10 px-8 py-4 flex items-center justify-between bg-black/50">
      <div>
        <p class="text-sm font-semibold">Midnight Pulse</p>
        <p class="text-xs text-white/50">Now playing</p>
      </div>
      <div class="flex items-center gap-3">
        <button type="button" class="rounded-full bg-white/10 px-4 py-2 text-sm">Prev</button>
        <button type="button" class="rounded-full px-6 py-2 text-sm font-bold" style="background:{accent}">Play</button>
        <button type="button" class="rounded-full bg-white/10 px-4 py-2 text-sm">Next</button>
      </div>
    </footer>
  </main>
</div>
"""
    else:
        body = f"""
<div class="min-h-full">
  <header class="py-5 flex items-center justify-between {shell}">
    <p class="font-bold text-sm">{esc(str(spec.get("name") or "Brand"))}</p>
    <button style="background:{accent}" class="rounded-lg text-white text-xs font-semibold px-4 py-2">Get started</button>
  </header>
  <main class="py-16 {shell} text-center space-y-5">
    <h1 class="{'text-3xl' if is_app else 'text-5xl'} font-bold tracking-tight">{esc(title)}</h1>
    <p class="text-slate-500 {'text-sm' if is_app else 'text-lg'} max-w-2xl mx-auto">A polished interface draft for your brief. Iterate from the canvas to refine layout and copy.</p>
    <div class="flex justify-center gap-3">
      <button style="background:{accent}" class="rounded-xl text-white font-semibold px-6 py-3 text-sm">Primary action</button>
      <button class="rounded-xl border border-slate-200 px-6 py-3 text-sm font-medium">Learn more</button>
    </div>
    <div class="mt-10 grid grid-cols-1 {'md:grid-cols-3' if not is_app else ''} gap-4 text-left">
      <div class="rounded-2xl border border-slate-200 bg-white p-5"><p class="font-semibold text-sm mb-1">Feature A</p><p class="text-xs text-slate-500">Describe value here.</p></div>
      <div class="rounded-2xl border border-slate-200 bg-white p-5"><p class="font-semibold text-sm mb-1">Feature B</p><p class="text-xs text-slate-500">Describe value here.</p></div>
      <div class="rounded-2xl border border-slate-200 bg-white p-5"><p class="font-semibold text-sm mb-1">Feature C</p><p class="text-xs text-slate-500">Describe value here.</p></div>
    </div>
  </main>
</div>
"""
    return _shell_html(title, body, device=device)


def _coerce_ui_html(
    raw: str,
    *,
    title: str,
    prompt: str,
    spec: dict[str, Any],
    device: str,
    fallback_html: str | None = None,
    allow_template_fallback: bool = True,
) -> str:
    """Wrap fragment if needed; optional offline template when LLM output is blank."""
    html = (raw or "").strip()
    if html and "<html" not in html.lower():
        html = _shell_html(title, html, device=device)
    if html and "charset" not in html.lower()[:500]:
        if "<head>" in html.lower():
            html = html.replace("<head>", '<head>\n<meta charset="utf-8"/>', 1)
        elif "<head " in html.lower():
            import re as _re
            html = _re.sub(r"(<head\s[^>]*>)", r'\1\n<meta charset="utf-8"/>', html, count=1, flags=_re.I)
    if _html_has_visible_content(html):
        return html
    if fallback_html is not None and _html_has_visible_content(fallback_html):
        return fallback_html
    if allow_template_fallback:
        return _fallback_ui_html(prompt, spec, device=device)
    return ""


def _first_hex(colors: dict[str, Any] | None, key: str, fallback: str) -> str:
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


def _llm_complete(
    router: Any, prompt: str, *, model_id: str, timeout_sec: float = _LLM_TIMEOUT_SEC
) -> tuple[str, str | None, dict[str, int], bool]:
    """Run router.complete with a hard timeout; returns content, reasoning, usage, estimated."""
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(router.complete, prompt, model_id=model_id)
        try:
            return _llm_result(future.result(timeout=timeout_sec), prompt=prompt)
        except FuturesTimeout as exc:
            future.cancel()
            raise DesignError(f"Model timed out after {int(timeout_sec)}s") from exc


def _check_vision_ok(router: Any, model_id: str, image_data_url: str | None) -> bool:
    """Return True only if the model provider is known to support multimodal vision."""
    if not image_data_url:
        return False
    try:
        from src.adapters.ollama_adapter import model_supports_vision
        spec, _ = router.resolve_for_model(model_id)
        return model_supports_vision(spec)
    except Exception:
        return False


def _looks_like_vision_error(text: str) -> bool:
    """Return True if LLM output looks like a vision-capability error instead of real content."""
    from src.chat_content import looks_like_vision_error

    return looks_like_vision_error(text)


def _llm_complete_vision(
    router: Any,
    prompt: str,
    *,
    model_id: str,
    image_data_url: str | None = None,
    timeout_sec: float = _LLM_TIMEOUT_SEC,
    image_analysis_text: str = "",
) -> tuple[str, str | None, dict[str, int], bool]:
    """Complete with optional vision image via router.chat multimodal content.

    Always tries sending the image first when present; on soft/API vision failure,
    retries with local image analysis prefix (OCR/palette).
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
    from src.chat_content import looks_like_vision_api_error, user_message_content_for_llm

    if image_data_url:
        content = user_message_content_for_llm(
            f"[image: {image_data_url}]\n{prompt}",
            vision_enabled=True,
        )
        messages = [{"role": "user", "content": content}]

        def _call() -> object:
            return router.chat(messages, model_id=model_id)

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_call)
                try:
                    result = _llm_result(future.result(timeout=timeout_sec), prompt=prompt)
                except FuturesTimeout as exc:
                    future.cancel()
                    raise DesignError(f"Model timed out after {int(timeout_sec)}s") from exc

            text, reasoning, usage, estimated = result
            if not _looks_like_vision_error(text):
                return result
            logger.warning(
                "vision call returned error-like response (model=%s) — falling back to local analysis",
                model_id,
            )
        except DesignError:
            raise
        except Exception as exc:
            if not looks_like_vision_api_error(exc):
                raise
            logger.warning(
                "vision API error (model=%s) — falling back to local analysis: %s",
                model_id,
                exc,
            )

    prefix = ""
    if image_data_url:
        if image_analysis_text:
            prefix = image_analysis_text + "\n\n"
        else:
            try:
                from src.design.image_analysis import image_analysis_prompt_fragment
                analysis = image_analysis_prompt_fragment(image_data_url)
                prefix = (analysis + "\n\n") if analysis else (
                    "A reference screenshot was attached; the model could not process vision input. "
                    "Use the product brief to infer colors and layout.\n"
                )
            except Exception:
                prefix = (
                    "A reference screenshot was attached but the model could not process it. "
                    "Infer a polished UI that matches the product brief alone.\n"
                )
    return _llm_complete(router, prefix + prompt, model_id=model_id, timeout_sec=timeout_sec)


def _try_llm_complete_vision(
    router: Any,
    prompt: str,
    *,
    model_id: str,
    image_data_url: str | None = None,
    timeout_sec: float = _LLM_UI_TIMEOUT_SEC,
) -> tuple[str, str | None, dict[str, int], bool, str | None]:
    """Best-effort LLM call for UI HTML; never aborts pipeline."""
    try:
        text, reasoning, usage, estimated = _llm_complete_vision(
            router,
            prompt,
            model_id=model_id,
            image_data_url=image_data_url,
            timeout_sec=timeout_sec,
        )
        return text, reasoning, usage, estimated, None
    except DesignError as exc:
        logger.warning("design ui llm call failed model=%s err=%s", model_id, exc)
        return "", None, empty_token_usage(), False, str(exc)
    except Exception as exc:
        logger.warning("design ui llm call error model=%s err=%s", model_id, exc)
        return "", None, empty_token_usage(), False, str(exc)


def _extract_html_from_llm(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""

    stripped = re.sub(r"^```[\w#\-]*\s*\n?", "", raw, flags=re.I, count=1)
    stripped = re.sub(r"\n?```\s*$", "", stripped, flags=re.I)

    for candidate in (stripped, raw):
        doc = re.search(r"(<!DOCTYPE[\s\S]*?</html>)", candidate, re.I)
        if doc:
            return doc.group(1).strip()
        html_open = re.search(r"(<html[\s\S]*?</html>)", candidate, re.I)
        if html_open:
            return html_open.group(1).strip()

    fence = re.search(r"```(?:html)?\s*([\s\S]*?)```", raw, re.I)
    if fence:
        body = fence.group(1).strip()
        if len(body) > 20 or re.search(r"<[a-z!]", body, re.I):
            return body

    return stripped


def _html_from_llm_response(text: str, reasoning: str | None = None) -> str:
    tag_re = re.compile(r"<(?:html|body|div|main|section|header|nav|form|button|h[1-6]|p)\b", re.I)
    for chunk in (text, reasoning or ""):
        if not (chunk or "").strip():
            continue
        extracted = _extract_html_from_llm(chunk)
        if extracted and tag_re.search(extracted):
            return extracted
    return ""


def _extract_css_tokens(html: str, base_url: str = "") -> dict[str, Any]:
    """Extract real design tokens from raw HTML: colors, fonts, CSS vars, Tailwind classes."""
    from collections import Counter
    from html import unescape
    from urllib.parse import urljoin, urlparse

    tokens: dict[str, Any] = {}

    style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", html, re.I | re.S)
    all_css = " ".join(style_blocks)

    css_vars: dict[str, str] = {}
    for k, v in re.findall(r"--([\.\w-]+)\s*:\s*([^;}\n]{1,80})", all_css):
        css_vars[k.strip()] = v.strip().rstrip(",")
    if css_vars:
        tokens["css_vars"] = css_vars

    css_var_refs: set[str] = set()
    for ref in re.findall(r"var\(--([a-zA-Z][\w-]*)\)", html):
        css_var_refs.add(ref)
    if css_var_refs:
        tokens["css_var_references"] = sorted(css_var_refs)

    font_families: list[str] = []
    for ff in re.findall(r"font-family\s*:\s*([^;}\n]+)", all_css):
        cleaned = re.sub(r"['\"/]", "", ff.split(",")[0]).strip()
        if cleaned and cleaned not in font_families and len(cleaned) < 60:
            font_families.append(cleaned)
    for family in re.findall(r"family=([A-Za-z+]+)", html):
        name = family.replace("+", " ")
        if name not in font_families:
            font_families.append(name)
    if font_families:
        tokens["font_families"] = font_families[:6]

    hex_counts: Counter = Counter()
    for h in re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", html):
        norm = h.upper()
        if len(norm) == 3:
            norm = norm[0]*2 + norm[1]*2 + norm[2]*2
        hex_counts["#" + norm] += 1
    if hex_counts:
        tokens["hex_colors"] = [h for h, _ in hex_counts.most_common(16)]
        tokens["hex_colors_with_count"] = [[h, cnt] for h, cnt in hex_counts.most_common(16)]

    tw_palette: Counter = Counter()
    for cls in re.findall(r'(?:bg|text|border|ring|fill|stroke|from|to|via)-([a-z]+-[0-9]{2,3})\b', html):
        tw_palette[cls] += 1
    if tw_palette:
        top_tw = [cls for cls, _ in tw_palette.most_common(12)]
        tokens["tailwind_color_classes"] = top_tw
        tw_theme_color = tw_palette.most_common(1)[0][0].split("-")[0] if tw_palette else ""
        if tw_theme_color:
            tokens["tailwind_theme_color"] = tw_theme_color

    theme_m = re.search(
        r'<meta[^>]+(name|property)=["\'](theme-color|msapplication-TileColor)["\'][^>]+content=["\']([^"\'>]+)',
        html, re.I
    ) or re.search(
        r'<meta[^>]+content=["\']([^"\'>]+)["\'][^>]+(name|property)=["\'](theme-color|msapplication-TileColor)',
        html, re.I
    )
    if theme_m:
        tokens["theme_color"] = theme_m.group(3).strip()

    og_m = re.search(r'og:image["\'][^>]*content=["\']([^"\'>]+)', html, re.I)
    if not og_m:
        og_m = re.search(r'content=["\']([^"\'>]+)["\'][^>]*og:image', html, re.I)
    if og_m:
        og_img = og_m.group(1).strip()
        if og_img.startswith("http"):
            tokens["og_image"] = og_img
        elif base_url and og_img:
            tokens["og_image"] = urljoin(base_url, og_img)

    dark_signals = (
        "class=\"dark\"" in html
        or "data-theme=\"dark\"" in html
        or re.search(r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)", all_css) is not None
    )
    dark_tw = len(re.findall(r'\bdark:', html)) > 5
    # If theme-color meta explicitly says a light colour, the page is light regardless of dark: prefixes
    tc = tokens.get("theme_color", "")
    tc_is_light = False
    if tc and re.match(r'^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$', tc):
        h = tc.lstrip("#")
        if len(h) == 3:
            h = h[0]*2 + h[1]*2 + h[2]*2
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        tc_is_light = (r + g + b) / 3 > 200
    tokens["dark_mode"] = dark_signals or (dark_tw and not tc_is_light)

    css_hrefs = re.findall(r'<link[^>]+href=["\']([^"\'>]+\.css[^"\'>]*)["\']', html, re.I)
    if css_hrefs and base_url:
        parsed = urlparse(base_url)
        css_base = f"{parsed.scheme}://{parsed.netloc}"
        total = len(css_hrefs)
        seen: set[int] = set()
        fetch_order: list[int] = []

        # Front: first 4 (global setup: fonts, reset)
        for i in range(min(4, total)):
            seen.add(i)
            fetch_order.append(i)
        # Back: last 4 (late-loaded page-specific styles for bundled apps)
        for i in range(total - 1, max(-1, total - 5), -1):
            if i not in seen:
                seen.add(i)
                fetch_order.append(i)
        # Middle: evenly-spaced samples across the full list
        remaining_slots = 24 - len(fetch_order)
        span = max(1, total - 8)
        step = max(1, span // remaining_slots)
        for i in range(4, total - 4, step):
            if i not in seen and len(fetch_order) < 24:
                seen.add(i)
                fetch_order.append(i)

        css_fetched = 0
        max_fetch = 20
        for idx in sorted(fetch_order):
            if css_fetched >= max_fetch:
                break
            href = css_hrefs[idx]
            css_url = href if href.startswith("http") else urljoin(css_base + "/", href.lstrip("/"))
            try:
                import urllib.request as _ureq
                css_req = _ureq.Request(
                    css_url,
                    headers={"User-Agent": "ClutchDesign/1.0"},
                )
                with _ureq.urlopen(css_req, timeout=8.0) as cr:
                    css_text = cr.read(300_000).decode("utf-8", errors="replace")
                if re.search(r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)", css_text):
                    tokens["dark_mode"] = True
                for hc in re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", css_text):
                    norm = hc.upper()
                    if len(norm) == 3:
                        norm = norm[0]*2 + norm[1]*2 + norm[2]*2
                    hex_counts["#" + norm] += 1
                # Allow later definitions to override earlier ones (CSS cascade order)
                for ck, cv in re.findall(r"--([\.\w-]+)\s*:\s*([^;}\n]{1,80})", css_text):
                    css_vars[ck.strip()] = cv.strip().rstrip(",")
                for rec in re.findall(r"var\(--([a-zA-Z][\w-]*)\)", css_text):
                    css_var_refs.add(rec)
                for ff in re.findall(r"font-family\s*:\s*([^;}\n]+)", css_text):
                    cleaned = re.sub(r"['\"/]", "", ff.split(",")[0]).strip()
                    if cleaned and cleaned not in font_families and len(cleaned) < 60:
                        font_families.append(cleaned)
                css_fetched += 1
            except Exception:
                continue
        if hex_counts:
            tokens["hex_colors"] = [h for h, _ in hex_counts.most_common(16)]
            tokens["hex_colors_with_count"] = [[h, cnt] for h, cnt in hex_counts.most_common(16)]
        if css_vars:
            tokens["css_vars"] = css_vars
        if css_var_refs:
            tokens["css_var_references"] = sorted(css_var_refs)
        if font_families:
            tokens["font_families"] = font_families[:6]

    return tokens


def _format_css_tokens_for_prompt(tokens: dict[str, Any], host: str = "") -> str:
    if not tokens:
        return ""

    lines: list[str] = ["[Extracted Design Tokens from Website]"]

    theme_color = tokens.get("theme_color")
    if theme_color:
        # Skip near-black / near-white defaults — these are rarely the actual brand color
        tc_is_default = False
        if re.match(r'^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$', theme_color):
            h = theme_color.lstrip("#")
            if len(h) == 3:
                h = h[0]*2 + h[1]*2 + h[2]*2
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            brightness = (r + g + b) / 3
            tc_is_default = brightness < 20 or brightness > 245
        if not tc_is_default:
            lines.append(f"Brand/theme color: {theme_color}")

    hex_colors = tokens.get("hex_colors_with_count") or []
    if hex_colors:
        color_strs = [f"{h} (x{c})" for h, c in hex_colors[:10]]
        lines.append(f"Hex colors found (by frequency): {', '.join(color_strs)}")

    css_vars = tokens.get("css_vars") or {}
    if css_vars:
        var_strs = [f"--{k}: {v}" for k, v in list(css_vars.items())[:12]]
        lines.append(f"CSS custom properties: {'; '.join(var_strs)}")

    css_var_refs = tokens.get("css_var_references") or []
    if css_var_refs:
        ref_strs = [f"--{r}" for r in css_var_refs[:20]]
        lines.append(f"CSS design token names referenced (hint at color palette): {', '.join(ref_strs)}")
        # Extract color family hints from variable names
        _skip_hints = {
            "color", "primary", "secondary", "accent", "text", "bg", "background",
            "muted", "dark", "alt", "neutral", "white", "black", "bold", "light",
        }
        color_hints = set()
        for r in css_var_refs:
            parts = r.lower().split("-")
            if "color" in parts:
                for p in parts[parts.index("color") + 1:]:
                    if p not in _skip_hints:
                        color_hints.add(p)
        if color_hints:
            lines.append(f"Color palette hints from variable names: {', '.join(sorted(color_hints))}")

    tw_classes = tokens.get("tailwind_color_classes") or []
    if tw_classes:
        lines.append(f"Tailwind color classes used: {', '.join(tw_classes[:10])}")
        tw_theme = tokens.get("tailwind_theme_color")
        if tw_theme:
            lines.append(f"Primary Tailwind color family: {tw_theme}-*")

    font_families = tokens.get("font_families") or []
    if font_families:
        lines.append(f"Font families: {', '.join(font_families[:4])}")

    dark_mode = tokens.get("dark_mode", False)
    if dark_mode:
        lines.append(
            "Color mode: DARK (use dark background tones like #1a1a2e, #16213e, or soft dark grays — "
            "avoid pure #000000 unless the site explicitly uses it)"
        )
        lines.append(
            "CRITICAL: The reference website uses a DARK color scheme — the generated page MUST have a dark background."
        )
    else:
        lines.append("Color mode: LIGHT (use white or very light backgrounds like #ffffff, #f8fafc, #fafafa)")
        lines.append(
            "CRITICAL: The reference website uses a LIGHT background — the generated page MUST have a white or very light background, with dark text. Do NOT generate a dark-themed page."
        )

    og_image = tokens.get("og_image")
    if og_image:
        lines.append(f"Reference screenshot (OG image): {og_image}")

    if len(lines) > 1:
        lines.append(
            "\nCRITICAL: You MUST use these exact colors and fonts in your design spec. "
            "Do NOT invent or substitute colors — the spec must faithfully match the source website's palette."
        )

    return "\n".join(lines) if len(lines) > 1 else ""


def _fetch_url_snapshot(url: str) -> dict[str, Any]:
    import urllib.error
    import urllib.request
    from html import unescape
    from urllib.parse import urlparse

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ClutchDesign/1.0",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            raw = resp.read(500_000)
            charset = "utf-8"
            ctype = resp.headers.get_content_charset()
            if ctype:
                charset = ctype
            html = raw.decode(charset, errors="replace")
            final_url = resp.geturl() or url
    except urllib.error.HTTPError as exc:
        raise DesignError(f"Could not fetch URL ({exc.code})") from exc
    except Exception as exc:
        raise DesignError(f"Could not fetch URL: {exc}") from exc

    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = unescape(re.sub(r"\s+", " ", title_m.group(1))).strip() if title_m else ""
    desc_m = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\'>]+)',
        html,
        re.I | re.S,
    ) or re.search(
        r'<meta[^>]+content=["\']([^"\'>]+)["\'][^>]+name=["\']description',
        html,
        re.I | re.S,
    )
    description = unescape(re.sub(r"\s+", " ", desc_m.group(1))).strip() if desc_m else ""
    cleaned = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = unescape(re.sub(r"\s+", " ", cleaned)).strip()
    excerpt = cleaned[:4000]
    host = urlparse(final_url).netloc or urlparse(url).netloc

    try:
        css_tokens = _extract_css_tokens(html, base_url=final_url)
    except Exception as exc:
        logger.debug("design url css_tokens extraction failed url=%s err=%s", url, exc)
        css_tokens = {}

    og_image_analysis: dict[str, Any] = {}
    og_img_url = css_tokens.get("og_image")
    if og_img_url:
        try:
            import base64 as _b64
            import io as _io
            og_req = urllib.request.Request(
                og_img_url,
                headers={"User-Agent": "ClutchDesign/1.0"},
            )
            with urllib.request.urlopen(og_req, timeout=10.0) as img_resp:
                img_bytes = img_resp.read(2_000_000)
            img_b64 = _b64.b64encode(img_bytes).decode("ascii")
            content_type = img_resp.headers.get_content_type() or "image/png"
            data_url = f"data:{content_type};base64,{img_b64}"
            from src.design.image_analysis import analyze_image_for_spec
            og_image_analysis = analyze_image_for_spec(data_url)
            logger.info(
                "design url OG image analyzed url=%s colors=%d",
                og_img_url, len(og_image_analysis.get("colors", [])),
            )
        except Exception as exc:
            logger.debug("design url OG image analysis failed url=%s err=%s", og_img_url, exc)

    # Browser-based extraction: render the page, extract computed styles + screenshot
    browser_tokens: dict[str, Any] = {}
    try:
        from src.design.browser_extract import extract_website_tokens
        browser_tokens = extract_website_tokens(final_url, timeout_sec=40.0)
        if browser_tokens.get("available"):
            logger.info(
                "design url browser extraction succeeded url=%s fonts=%d",
                final_url, len((browser_tokens.get("computed_styles") or {}).get("fonts", [])),
            )
        else:
            logger.debug(
                "design url browser extraction unavailable url=%s err=%s",
                final_url, browser_tokens.get("error", "unknown"),
            )
    except Exception as exc:
        logger.debug("design url browser extraction failed url=%s err=%s", final_url, exc)

    return {
        "url": final_url,
        "host": host,
        "title": title[:200],
        "description": description[:400],
        "excerpt": excerpt,
        "css_tokens": css_tokens,
        "og_image_analysis": og_image_analysis,
        "browser_computed_styles": browser_tokens.get("computed_styles") or {},
        "browser_screenshot": browser_tokens.get("screenshot_data_url") or "",
        "browser_prompt_fragment": browser_tokens.get("prompt_fragment") or "",
        "fetched_at": now_iso(),
    }


def _build_ui_compact_prompt(
    *,
    user_prompt: str,
    spec: dict[str, Any],
    device: str,
) -> str:
    pattern = str(spec.get("layout_pattern") or detect_layout_pattern(user_prompt, device=device))
    primary = _first_hex((spec.get("colors") or {}), "primary", "#171717")
    return (
        "Generate ONE complete HTML page with Tailwind CDN for this brief.\n"
        f"Brief: {user_prompt}\n"
        f"Device: {device}\n"
        f"Layout: {pattern}\n"
        f"Primary color: {primary}\n"
        f"Brand: {spec.get('name') or 'Clutch'}\n"
        "Rules: full <!DOCTYPE html>…</html>, visible UI in body, match the brief intent.\n"
        "Prefer semantic <button> / <a role=\"button\"> with data-clutch-id for IUE; "
        "do NOT add real navigation (href=\"#\" or javascript:) or <form> submit / onclick handlers.\n"
        "Return ONLY ```html ... ```."
    )


def _build_shared_layout_context(screens_to_gen: list[dict[str, Any]]) -> str:
    """Build a shared layout context string for multi-page generation.
    
    Tells the LLM that all non-login pages must share a consistent left sidebar
    with identical navigation items, colors, and ordering.
    """
    if len(screens_to_gen) <= 1:
        return ""
    login_keywords = ("login", "signin", "sign-in", "auth", "登", "注册")
    login_ids = set()
    for s in screens_to_gen:
        pid = (s.get("prompt") or "").lower()
        nid = (s.get("name") or "").lower()
        if any(kw in pid or kw in nid for kw in login_keywords):
            login_ids.add(s["id"])
    non_login = [s for s in screens_to_gen if s["id"] not in login_ids]
    if len(non_login) <= 1:
        return ""
    nav_names = [s["name"] for s in non_login]
    lines = [
        f"This is a multi-page prototype with {len(non_login)} non-login screens plus {len(login_ids)} login/auth screens.",
        "",
        "LAYOUT RULES:",
        f"- ALL {len(non_login)} non-login pages ({', '.join(nav_names)}) MUST share an identical left sidebar navigation.",
        "- Sidebar bg color: use the design system's primary or secondary color (consistent across all pages).",
        "- Sidebar text color: white or on-primary (consistent across all pages).",
        f"- Navigation items in exact order: {' > '.join(nav_names)}.",
        "- Every page must highlight its own nav item as active/selected.",
        "- Sidebar width, padding, font sizes, and spacing must be pixel-identical across all pages.",
        "- Login/auth pages: centered card layout WITHOUT sidebar (standalone authentication screen).",
        "",
        "These rules ensure visual consistency when users navigate between screens.",
    ]
    return "\n".join(lines)


def _build_ui_generation_prompt(
    *,
    user_prompt: str,
    spec: dict[str, Any],
    device: str,
    pattern: str,
    design_md: str = "",
    md_text: str | None = None,
    url_snapshot: dict[str, Any] | None = None,
    has_image: bool = False,
    image_attached: bool = False,
    current_html: str = "",
    instruction: str = "",
    shared_layout_context: str = "",
) -> str:
    fewshot = fewshot_for_pattern(pattern)
    layout_hint = layout_wrapper_hint(pattern)
    ui_parts = [
        "You are an expert web designer. Generate a single, fully-formed, beautiful HTML document "
        "using Tailwind CSS.\n",
        f"Brief: {user_prompt}\n",
    ]
    if instruction:
        ui_parts.append(f"Revision instruction: {instruction}\n")
    ui_parts.append(
        (
            "Device target: mobile app viewport 390×844 CSS pixels (iPhone-class). "
            "Use a single-column stacked layout, large touch targets, no desktop sidebar.\n"
            if device == "app"
            else
            "Device target: desktop web viewport 1920×1080 CSS pixels (16:9). "
            "Use a full-width desktop layout (top nav, multi-column grids, wide hero). "
            "Do NOT produce a narrow phone-only page.\n"
        )
    )
    intent = _prompt_intent(user_prompt)
    if intent == "login":
        intent_rule = (
            "5. Brief intent: login — build a polished sign-in / registration screen.\n"
        )
    else:
        intent_rule = (
            f"5. Brief intent: {intent} — the page MUST match this intent; "
            "do NOT default to a generic login/auth screen unless the brief asks for it.\n"
        )
    ui_parts += [
        f"Layout pattern: {pattern}\n",
        f"Layout constraints: {layout_hint}\n",
    ]
    if shared_layout_context:
        ui_parts.append(
            "\n=== SHARED PAGE LAYOUT (applies to ALL screens in this multi-page session) ===\n"
            + shared_layout_context + "\n"
            "=== END SHARED LAYOUT ===\n\n"
        )
    ui_parts += [
        (
            "CRITICAL Rules:\n"
            "1. Use Tailwind CDN: <script src=\"https://cdn.tailwindcss.com\"></script>\n"
            "2. Define design system colors via tailwind.config script — no custom <style> blocks.\n"
            "3. Complete HTML with closed </html>; keep body under 80 lines to avoid truncation.\n"
            "4. Implement the screen in the Brief — match the requested screen type.\n"
        )
        + intent_rule
        + (
            "6. COLOR RULES — VIOLATION CAUSES REJECTION:\n"
            "   a. Use ONLY color hex codes from the Design system JSON. NEVER invent arbitrary hex values like #1A73E8 or #3B82F6.\n"
            "   b. Do NOT use Tailwind default color names: NO bg-blue-*, bg-red-*, bg-green-*, bg-yellow-*, text-blue-*, etc.\n"
            "   c. Only use the custom color palette defined in the tailwind.config (e.g. bg-primary, bg-accent, bg-secondary, text-primary, bg-neutral). Reference the Design system JSON colors.\n"
            "   d. Page background MUST be solid white or the neutral/surface color from the design system. NO colorful gradient backgrounds like bg-gradient-to-br from-[...].\n"
            "   e. Primary buttons: bg-primary text-white rounded-xl. Secondary buttons: border-gray-300 text-gray-700 bg-white. Accent actions: bg-accent text-white.\n"
            "7. Select 3-5 core components; use rounded-2xl cards, professional horizontal padding px-6–px-10, hover opacity transitions only.\n"
            "8. Prototype interactivity: use semantic <button> / <a role=\"button\"> with data-clutch-id "
            "so IUE can detect hotspots; no real navigation hrefs, no <form> submit, no onclick/javascript.\n"
            f"9. {_TASTE_ANTI_PATTERNS}"
        ),
        f"Style reference (match quality & polish only — do NOT copy this layout verbatim):\n{fewshot}\n",
        f"Design system JSON:\n{json.dumps(spec, ensure_ascii=False)}\n",
    ]
    if design_md:
        cap = 2000 if str(spec.get("name") or "").strip().lower() == "clutch" else 8000
        ui_parts.append(f"DESIGN.md rules:\n{design_md[:cap]}\n")
    if md_text:
        ui_parts.append(
            f"\n=== MANDATORY DESIGN SPECIFICATION ({md_text[:60]!r}...) ===\n"
            f"{md_text[:8000]}\n"
            "=== END MANDATORY SPECIFICATION ===\n"
            "CRITICAL COMPLIANCE RULES for the above specification:\n"
            "- Use ONLY the exact color hex codes specified — NEVER substitute or invent colors.\n"
            "- Use ONLY the font families named in the specification — load via Google Fonts @import if needed.\n"
            "- Apply all spacing, border-radius, and shadow values exactly as specified.\n"
            "- Implement every component mentioned in the specification.\n"
            "- The generated HTML must be a faithful implementation of this spec. No deviations.\n"
        )
    if url_snapshot:
        browser_frag = url_snapshot.get("browser_prompt_fragment") or ""
        if browser_frag:
            ui_parts.append(
                f"Reference website: {url_snapshot.get('url')} "
                f"({url_snapshot.get('title') or url_snapshot.get('host')}).\n"
                + browser_frag + "\n"
                "Apply the above design tokens faithfully in your HTML output.\n"
                "Determine the background color from the Body computed styles or CSS custom properties. "
                "If the reference body background is transparent, white, or light (<#ccc), you MUST use a light background (#ffffff or similar). "
                "If it's dark (>#333), use a dark background. Match what the reference actually renders.\n"
            )
        else:
            css_tokens = url_snapshot.get("css_tokens") or {}
            token_desc = _format_css_tokens_for_prompt(css_tokens, host=str(url_snapshot.get("host") or ""))
            if token_desc:
                ui_parts.append(
                    f"Reference website: {url_snapshot.get('url')} "
                    f"({url_snapshot.get('title') or url_snapshot.get('host')}).\n"
                    + token_desc + "\n"
                    "Apply the above design tokens faithfully in your HTML output.\n"
                )
            else:
                ui_parts.append(
                    f"Visual inspiration from {url_snapshot.get('url')} "
                    f"({url_snapshot.get('title') or url_snapshot.get('host')}).\n"
                )
    if image_attached:
        ui_parts.append(
            "Match the attached reference screenshot (structure, hierarchy, spacing).\n"
        )
    if current_html:
        ui_parts.append(
            "=== REVISION MODE — CRITICAL ===\n"
            "You are REVISING an existing page, NOT creating a new one from scratch.\n"
            "1. KEEP the existing page layout, structure, and content type unchanged.\n"
            "2. Only apply the specific changes requested in the Revision instruction above.\n"
            "3. Do NOT replace the page with a different screen type (e.g., don't turn a dashboard into a login form).\n"
            "4. The page type and purpose must remain the same as the current HTML below.\n"
            f"Current HTML to revise:\n{current_html[:14000]}\n"
        )
    ui_parts.append("Return ONLY the HTML document inside ```html ... ```.")
    return "".join(ui_parts)


def _design_review_and_improve(
    router: Any,
    *,
    html: str,
    spec: dict[str, Any],
    user_prompt: str,
    model_id: str,
    device: str,
) -> tuple[str, str | None, int, dict[str, int], bool]:
    """Design Review Pass: score HTML; refine once if below threshold."""
    review_prompt = (
        "You are a senior UI design reviewer. Score this HTML mockup 1-10 on:\n"
        "- Visual hierarchy & modern aesthetics\n"
        "- Spacing & typography consistency\n"
        "- Color consistency & contrast\n"
        "- CTA clarity & accessibility\n"
        "- Responsive layout\n\n"
        f"Brief: {user_prompt}\nDevice: {device}\n"
        f"Design system: {json.dumps(spec, ensure_ascii=False)[:4000]}\n\n"
        f"HTML:\n{html[:12000]}\n\n"
        'Return ONLY JSON: {"score": N, "feedback": "..."}'
    )
    review_text, review_reasoning, review_usage, review_estimated = _llm_complete(
        router, review_prompt, model_id=model_id
    )
    score, feedback = parse_review_score(review_text)
    combined_reasoning = review_reasoning
    usage = review_usage
    estimated = review_estimated
    if score >= review_threshold():
        return html, combined_reasoning, score, usage, estimated
    improve_prompt = (
        "Improve this HTML UI based on the design review feedback. "
        "Apply concrete fixes to spacing, hierarchy, CTAs, and contrast.\n"
        "Keep semantic buttons with data-clutch-id; no real navigation / form submit / onclick handlers.\n"
        f"Feedback (score {score}/10): {feedback}\n"
        f"Brief: {user_prompt}\n"
        f"HTML:\n{html[:14000]}\n"
        "Use Tailwind CDN + tailwind.config for colors. Return ONLY ```html ... ```."
    )
    improved_text, improve_reasoning, improve_usage, improve_estimated = _llm_complete(
        router, improve_prompt, model_id=model_id
    )
    improved = _extract_html_from_llm(improved_text)
    usage = merge_token_usage(usage, improve_usage)
    estimated = estimated or improve_estimated
    if improve_reasoning:
        combined_reasoning = "\n---\n".join(filter(None, [combined_reasoning, improve_reasoning]))
    if _html_has_visible_content(improved):
        return improved, combined_reasoning, score, usage, estimated
    return html, combined_reasoning, score, usage, estimated


def _build_ui_correction_prompt(
    *,
    user_prompt: str,
    spec: dict[str, Any],
    device: str,
    reason: str,
) -> str:
    layout_hint = layout_wrapper_hint(
        str(spec.get("layout_pattern") or detect_layout_pattern(user_prompt, device=device))
    )
    return (
        "You are an expert web designer. Your previous HTML was rejected.\n"
        f"Rejection reason: {reason}\n"
        f"Brief (follow exactly): {user_prompt}\n"
        f"Layout constraints: {layout_hint}\n"
        f"Design system JSON:\n{json.dumps(spec, ensure_ascii=False)[:6000]}\n"
        "Rules:\n"
        "- Generate a NEW complete HTML document using Tailwind CDN.\n"
        "- Fulfill the brief — do NOT default to login/auth unless explicitly requested.\n"
        "- Use colors and typography from the design system; make it visually distinct.\n"
        "- Prefer semantic <button> with data-clutch-id for IUE; no real navigation / form submit / onclick.\n"
        f"- {_TASTE_ANTI_PATTERNS}"
        "Return ONLY ```html ... ```."
    )


def _generate_ui_html(
    router: Any,
    *,
    user_prompt: str,
    spec: dict[str, Any],
    device: str,
    model_id: str,
    design_md: str = "",
    md_text: str | None = None,
    url_snapshot: dict[str, Any] | None = None,
    has_image: bool = False,
    image_data_url: str | None = None,
    current_html: str = "",
    instruction: str = "",
    fallback_html: str | None = None,
    shared_layout_context: str = "",
) -> tuple[str, str | None, dict[str, int], bool, str | None]:
    last_fail: str | None = None
    pattern = str(spec.get("layout_pattern") or detect_layout_pattern(user_prompt, device=device))
    meta = _build_ui_generation_prompt(
        user_prompt=user_prompt,
        spec=spec,
        device=device,
        pattern=pattern,
        design_md=design_md,
        md_text=md_text,
        url_snapshot=url_snapshot,
        has_image=has_image,
        image_attached=bool(image_data_url),
        current_html=current_html,
        instruction=instruction,
        shared_layout_context=shared_layout_context,
    )
    text, reasoning, usage, estimated, fail = _try_llm_complete_vision(
        router, meta, model_id=model_id, image_data_url=image_data_url
    )
    if fail:
        last_fail = fail
    usage_acc = usage
    estimated_acc = estimated
    raw = _html_from_llm_response(text, reasoning)
    html = _coerce_ui_html(
        raw,
        title=str(spec.get("name") or "UI"),
        prompt=user_prompt,
        spec=spec,
        device=device,
        fallback_html=fallback_html,
        allow_template_fallback=False,
    )
    # If the HTML itself contains a vision error message, drop image and retry immediately
    if _html_has_visible_content(html) and image_data_url and _looks_like_vision_error(html):
        logger.warning("design ui HTML contains vision error — dropping image, retrying text-only")
        no_img_meta = _build_ui_generation_prompt(
            user_prompt=user_prompt,
            spec=spec,
            device=device,
            pattern=pattern,
            design_md=design_md,
            md_text=md_text,
            url_snapshot=url_snapshot,
            has_image=False,
            image_attached=False,
            current_html=current_html,
            instruction=instruction,
            shared_layout_context=shared_layout_context,
        )
        ni_text, ni_reasoning, ni_usage, ni_estimated, ni_fail = _try_llm_complete_vision(
            router, no_img_meta, model_id=model_id, image_data_url=None,
        )
        usage_acc = merge_token_usage(usage_acc, ni_usage)
        estimated_acc = estimated_acc or ni_estimated
        ni_raw = _html_from_llm_response(ni_text, ni_reasoning)
        ni_html = _coerce_ui_html(
            ni_raw,
            title=str(spec.get("name") or "UI"),
            prompt=user_prompt,
            spec=spec,
            device=device,
            fallback_html=fallback_html,
            allow_template_fallback=True,
        )
        if _html_has_visible_content(ni_html):
            html = ni_html
            raw = ni_raw
            text = ni_text
            reasoning = ni_reasoning
            last_fail = None
    if _html_has_visible_content(html) and not _html_matches_brief_intent(user_prompt, html):
        detected = _detect_html_intent(html)
        expected = _prompt_intent(user_prompt)
        logger.warning(
            "design ui intent mismatch prompt=%r detected=%s expected=%s — LLM retry",
            user_prompt[:80],
            detected,
            expected,
        )
        correction = _build_ui_correction_prompt(
            user_prompt=user_prompt,
            spec=spec,
            device=device,
            reason=(
                f"Page looks like '{detected}' but brief requires '{expected}'. "
                "Do not output login/auth unless the brief asks for it."
            ),
        )
        retry_text, retry_reasoning, retry_usage, retry_estimated, fail = _try_llm_complete_vision(
            router, correction, model_id=model_id, image_data_url=image_data_url
        )
        if fail:
            last_fail = fail
        usage_acc = merge_token_usage(usage_acc, retry_usage)
        estimated_acc = estimated_acc or retry_estimated
        retry_raw = _html_from_llm_response(retry_text, retry_reasoning)
        retry_html = _coerce_ui_html(
            retry_raw,
            title=str(spec.get("name") or "UI"),
            prompt=user_prompt,
            spec=spec,
            device=device,
            fallback_html=html,
            allow_template_fallback=False,
        )
        if _html_has_visible_content(retry_html):
            html = retry_html
            reasoning = "\n---\n".join(filter(None, [reasoning, retry_reasoning]))
    elif not _html_has_visible_content(html):
        logger.warning("design ui blank output prompt=%r — compact LLM retry", user_prompt[:80])
        compact = _build_ui_compact_prompt(user_prompt=user_prompt, spec=spec, device=device)
        retry_text, retry_reasoning, retry_usage, retry_estimated, fail = _try_llm_complete_vision(
            router, compact, model_id=model_id, image_data_url=image_data_url
        )
        if fail:
            last_fail = fail
        usage_acc = merge_token_usage(usage_acc, retry_usage)
        estimated_acc = estimated_acc or retry_estimated
        retry_raw = _html_from_llm_response(retry_text, retry_reasoning)
        retry_html = _coerce_ui_html(
            retry_raw,
            title=str(spec.get("name") or "UI"),
            prompt=user_prompt,
            spec=spec,
            device=device,
            fallback_html=fallback_html,
            allow_template_fallback=False,
        )
        if _html_has_visible_content(retry_html):
            html = retry_html
            reasoning = "\n---\n".join(filter(None, [reasoning, retry_reasoning]))
        else:
            retry_meta = (
                meta
                + "\n\nIMPORTANT: Your previous response was empty or invalid. "
                "Output a complete, visible HTML document that fulfills the brief."
            )
            retry2_text, retry2_reasoning, retry2_usage, retry2_estimated, fail = _try_llm_complete_vision(
                router, retry_meta, model_id=model_id, image_data_url=image_data_url
            )
            if fail:
                last_fail = fail
            usage_acc = merge_token_usage(usage_acc, retry2_usage)
            estimated_acc = estimated_acc or retry2_estimated
            retry2_raw = _html_from_llm_response(retry2_text, retry2_reasoning)
            retry2_html = _coerce_ui_html(
                retry2_raw,
                title=str(spec.get("name") or "UI"),
                prompt=user_prompt,
                spec=spec,
                device=device,
                fallback_html=fallback_html,
                allow_template_fallback=False,
            )
            if _html_has_visible_content(retry2_html):
                html = retry2_html
                reasoning = "\n---\n".join(
                    filter(None, [reasoning, retry_reasoning, retry2_reasoning])
                )
    # --- Final degradation: if image was attached but all retries failed, drop image and retry ---
    if not _html_has_visible_content(html) and image_data_url:
        logger.warning("design ui all retries failed with image — dropping image, retrying text-only")
        fallback_meta = _build_ui_generation_prompt(
            user_prompt=user_prompt,
            spec=spec,
            device=device,
            pattern=pattern,
            design_md=design_md,
            md_text=md_text,
            url_snapshot=url_snapshot,
            has_image=False,
            image_attached=False,
            current_html=current_html,
            instruction=instruction,
            shared_layout_context=shared_layout_context,
        )
        fb_text, fb_reasoning, fb_usage, fb_estimated, fb_fail = _try_llm_complete_vision(
            router, fallback_meta, model_id=model_id, image_data_url=None,
        )
        usage_acc = merge_token_usage(usage_acc, fb_usage)
        estimated_acc = estimated_acc or fb_estimated
        fb_raw = _html_from_llm_response(fb_text, fb_reasoning)
        fb_html = _coerce_ui_html(
            fb_raw,
            title=str(spec.get("name") or "UI"),
            prompt=user_prompt,
            spec=spec,
            device=device,
            fallback_html=fallback_html,
            allow_template_fallback=True,
        )
        if _html_has_visible_content(fb_html):
            html = fb_html
            reasoning = "\n---\n".join(filter(None, [reasoning, fb_reasoning]))
            last_fail = None
            logger.info("design ui text-only fallback succeeded after image failure")
    if _html_has_visible_content(html) and _DESIGN_REVIEW_ENABLED:
        reviewed, review_reasoning, _score, review_usage, review_estimated = _design_review_and_improve(
            router,
            html=html,
            spec=spec,
            user_prompt=user_prompt,
            model_id=model_id,
            device=device,
        )
        usage_acc = merge_token_usage(usage_acc, review_usage)
        estimated_acc = estimated_acc or review_estimated
        html = _coerce_ui_html(
            reviewed,
            title=str(spec.get("name") or "UI"),
            prompt=user_prompt,
            spec=spec,
            device=device,
            fallback_html=html,
            allow_template_fallback=False,
        )
        if review_reasoning:
            reasoning = "\n---\n".join(filter(None, [reasoning, review_reasoning]))
    if not _html_has_visible_content(html) and not last_fail:
        last_fail = "the model returned no valid HTML"
    return html, reasoning, usage_acc, estimated_acc, last_fail

