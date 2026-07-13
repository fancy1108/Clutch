"""LLM generation loops and iteration workflows for design canvas sessions."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

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

def _normalize_preset_id(preset_id: str | None) -> str:
    try:
        from src.design import service
        if hasattr(service, "normalize_preset_id"):
            return service.normalize_preset_id(preset_id)
    except ImportError:
        pass
    from src.design.builtin_presets import normalize_preset_id as orig_normalize
    return orig_normalize(preset_id)

logger = logging.getLogger(__name__)

_generate_jobs: dict[str, threading.Thread] = {}
_generate_lock = threading.Lock()
_LLM_TIMEOUT_SEC = 45.0
_LLM_UI_TIMEOUT_SEC = 90.0
_DESIGN_REVIEW_ENABLED = os.environ.get("CLUTCH_DESIGN_REVIEW", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_DESIGN_ROW_Y = 56


def get_generator_jobs_and_lock() -> tuple[dict[str, threading.Thread], threading.Lock]:
    return _generate_jobs, _generate_lock


def append_design_run_log(run_id: str, message: str, *, reasoning: str | None = None) -> None:
    """Best-effort: mirror Design progress into persisted run terminal_logs (Terminal panel)."""
    if not run_id:
        return
    if reasoning and reasoning.strip():
        append_design_run_log(
            run_id,
            f"[DESIGN:REASONING] {reasoning.strip().replace(chr(10), ' ↵ ')}",
        )
    if not message:
        return
    try:
        from src.run_state_store import load_run_state, save_run_state
        from src.terminal_logs import TAG_DESIGN, stamp_log_line, tagged

        state = load_run_state(run_id)
        if state is None:
            return
        line = stamp_log_line(tagged(TAG_DESIGN, message))
        logs = list(state.get("terminal_logs") or [])
        if logs and logs[-1] == line:
            return
        logs.append(line)
        state["terminal_logs"] = logs[-200:]
        save_run_state(state)
    except Exception:
        logger.debug("design terminal log skip run_id=%s", run_id, exc_info=True)


def _resolve_model_label(router: Any, model_id: str) -> tuple[str, str]:
    try:
        spec, _ = router.resolve_for_model(model_id)
        return model_id, str(spec.name or model_id)
    except Exception:
        return model_id, model_id


def _append_model_process_entry(
    log: list[dict[str, Any]],
    *,
    model_id: str,
    model_name: str,
    insert_after_user: bool = False,
) -> None:
    entry = {
        "role": "assistant",
        "kind": "model",
        "text": f"Model: {model_name}",
        "model_id": model_id,
        "model_name": model_name,
        "status": "info",
        "at": now_iso(),
    }
    if insert_after_user:
        for i in range(len(log) - 1, -1, -1):
            if log[i].get("role") == "user":
                log.insert(i + 1, entry)
                return
    log.append(entry)


def _round_has_model_entry(log: list[dict[str, Any]]) -> bool:
    """True when the current round (after the latest user line) already has a Model entry."""
    for item in reversed(log):
        if item.get("role") == "user":
            break
        if item.get("kind") == "model":
            return True
    return False


def _stamp_session_model(
    manifest: dict[str, Any],
    router: Any,
    *,
    model_id: str,
    process_log: list[dict[str, Any]] | None = None,
    record_in_log: bool = True,
    insert_after_user: bool = False,
) -> tuple[str, str]:
    """Persist model on the session manifest and optionally append an Agent Log line."""
    model_id, model_name = _resolve_model_label(router, model_id)
    manifest["model_id"] = model_id
    manifest["model_name"] = model_name
    if record_in_log:
        log = process_log if process_log is not None else list(manifest.get("process_log") or [])
        if not _round_has_model_entry(log):
            _append_model_process_entry(
                log,
                model_id=model_id,
                model_name=model_name,
                insert_after_user=insert_after_user,
            )
        manifest["process_log"] = log
    return model_id, model_name


def _llm_text(result: object) -> str:
    if isinstance(result, dict):
        content = result.get("content")
        return str(content).strip() if content else ""
    return str(result).strip()


def _attach_step_metadata(
    entry: dict[str, Any],
    *,
    model_id: str | None = None,
    model_name: str | None = None,
    usage: dict[str, int] | None = None,
    usage_estimated: bool = False,
) -> dict[str, Any]:
    out = dict(entry)
    if model_name:
        out["model_id"] = model_id
        out["model_name"] = model_name
    merged = merge_token_usage(usage)
    if merged["total_tokens"] > 0:
        out["usage"] = merged
        out["usage_estimated"] = usage_estimated
    return out


def _finalize_assistant_step(
    log: list[dict[str, Any]],
    *,
    text: str,
    status: str,
    model_id: str | None = None,
    model_name: str | None = None,
    usage: dict[str, int] | None = None,
    usage_estimated: bool = False,
    replace_statuses: set[str] | None = None,
) -> None:
    """Replace the latest in-flight assistant step, or append if none found."""
    statuses = replace_statuses or {"crafting_spec", "generating_ui", "iterating"}
    entry = _attach_step_metadata(
        {"role": "assistant", "text": text, "status": status, "at": now_iso()},
        model_id=model_id,
        model_name=model_name,
        usage=usage,
        usage_estimated=usage_estimated,
    )
    for i in range(len(log) - 1, -1, -1):
        item = log[i]
        if item.get("role") != "assistant":
            continue
        if item.get("kind") in {"model", "tokens"}:
            continue
        if item.get("status") in statuses:
            log[i] = entry
            return
    log.append(entry)


def _append_token_usage_entry(
    log: list[dict[str, Any]],
    *,
    label: str,
    usage: dict[str, int] | None,
    estimated: bool = False,
) -> None:
    merged = merge_token_usage(usage)
    if merged["total_tokens"] <= 0:
        return
    log.append(
        {
            "role": "assistant",
            "kind": "tokens",
            "text": format_token_usage_text(label, merged, estimated=estimated),
            "usage_label": label,
            "usage": merged,
            "usage_estimated": estimated,
            "status": "info",
            "at": now_iso(),
        }
    )


def _llm_result(
    result: object,
    *,
    prompt: str = "",
) -> tuple[str, str | None, dict[str, int], bool]:
    if isinstance(result, dict):
        content = result.get("content")
        text = str(content).strip() if content else ""
        reasoning = result.get("reasoning_content") or result.get("reasoning")
        reasoning_text = reasoning.strip() if isinstance(reasoning, str) and reasoning.strip() else None
        usage, estimated = usage_from_llm_result(
            result,
            prompt=prompt,
            response_text=text,
            reasoning=reasoning_text,
        )
        return text, reasoning_text, usage, estimated
    text = str(result).strip()
    usage, estimated = usage_from_llm_result(result, prompt=prompt, response_text=text)
    return text, None, usage, estimated


def _extract_json_data(text: str) -> Any:
    raw = (text or "").strip()
    if not raw:
        return None
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
    if m:
        raw = m.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start_dict = raw.find("{")
        end_dict = raw.rfind("}")
        start_list = raw.find("[")
        end_list = raw.rfind("]")
        
        # If both are present, pick the one that starts first
        if start_dict >= 0 and (start_list < 0 or start_dict < start_list):
            if end_dict > start_dict:
                try:
                    return json.loads(raw[start_dict : end_dict + 1])
                except json.JSONDecodeError:
                    pass
        elif start_list >= 0:
            if end_list > start_list:
                try:
                    return json.loads(raw[start_list : end_list + 1])
                except json.JSONDecodeError:
                    pass
        raise


def _extract_json_block(text: str) -> dict[str, Any]:
    data = _extract_json_data(text)
    if isinstance(data, dict):
        return data
    return {}


def _parse_multi_screens(
    prompt: str,
    model_id: str,
    router: Any,
) -> list[dict[str, Any]]:
    """
    Parse a user prompt to see if they want multiple screens/pages.
    Returns a list of dicts: [{"id": str, "name": str, "prompt": str, "layout_pattern": str}]
    """
    from src.models_config import is_model_available
    default_screen = [{"id": "main", "name": "Interface", "prompt": prompt, "layout_pattern": None}]
    if not is_model_available(router, model_id):
        return default_screen

    planning_prompt = (
        "You are an AI UI/UX architect planning screens/pages for a design workflow.\n"
        f"User prompt: {prompt}\n\n"
        "Analyze the prompt. If the user wants multiple pages, screens, or features generated (for example, 'a homepage, a profile page, and a login page'), "
        "plan a list of screens to generate.\n"
        "If the user only wants a single screen or page, or if it is ambiguous, return a list with a single element representing the requested screen.\n\n"
        "Return ONLY a valid JSON list of objects, representing each planned screen in order. "
        "Each object must have the following keys:\n"
        "- 'id': a short lowercase alphanumeric string (e.g. 'home', 'profile', 'login', 'dashboard', 'settings'). The first screen MUST have id 'main'.\n"
        "- 'name': a user-friendly name in the prompt's language (e.g. '首页', '个人中心', '登录页面', 'Home', 'Profile', 'Login').\n"
        "- 'prompt': a specific UI generation instruction for this screen, combining the global design system/topic with the screen's specific purpose.\n"
        "- 'layout_pattern': one of 'landing', 'dashboard', 'crm', 'settings', 'analytics', 'ecommerce', 'chat', 'mobile_app', 'login', 'pricing', 'profile'.\n\n"
        "Do NOT wrap in markdown code blocks like ```json or ```. Return ONLY the raw JSON string."
    )

    try:
        raw, _, _, _ = _llm_complete(router, planning_prompt, model_id=model_id)
        parsed = _extract_json_data(raw)
        if isinstance(parsed, list) and len(parsed) > 0:
            valid_screens = []
            for i, item in enumerate(parsed):
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("id") or "").strip().lower()
                item_name = str(item.get("name") or "").strip()
                item_prompt = str(item.get("prompt") or "").strip()
                item_pattern = str(item.get("layout_pattern") or "").strip().lower()
                
                if not item_name or not item_prompt:
                    continue
                
                if i == 0:
                    sid = "main"
                else:
                    sid = re.sub(r"[^a-z0-9_-]", "", item_id) or f"screen-{i+1}"
                    if sid == "main":
                        sid = f"screen-{i+1}"
                
                if item_pattern not in {
                    "landing", "dashboard", "crm", "settings", "analytics",
                    "ecommerce", "chat", "mobile_app", "login", "pricing", "profile"
                }:
                    item_pattern = None

                valid_screens.append({
                    "id": sid,
                    "name": item_name,
                    "prompt": item_prompt,
                    "layout_pattern": item_pattern
                })
            if valid_screens:
                return valid_screens
    except Exception as exc:
        logger.warning("Failed to parse multi-screen plan, falling back to single: %s", exc)

    return default_screen


def _fallback_spec(prompt: str) -> dict[str, Any]:
    return {
        "name": "Design Spec",
        "rationale": f"Fallback offline spec for prompt: {prompt[:80]}",
        "colors": {
            "primary": ["#2563eb", "#1d4ed8"],
            "secondary": ["#64748b", "#475569"],
            "neutral": ["#ffffff", "#f8fafc", "#0f172a"],
        },
        "typography": {
            "fontFamily": "Inter, system-ui, sans-serif",
            "samples": [
                {"label": "Heading", "size": "1.875rem", "weight": "700"},
                {"label": "Body", "size": "1rem", "weight": "400"},
            ],
        },
        "components": ["Header", "Card Grid", "Footer"],
    }


def _prompt_intent(prompt: str) -> str:
    """Coarse UI intent from the user brief — drives fallback HTML, not LLM."""
    p = (prompt or "").strip().lower()
    if any(
        k in p
        for k in (
            "登录",
            "登陆",
            "注册",
            "signin",
            "sign-in",
            "sign in",
            "log in",
            "login",
            "sign up",
            "signup",
            "auth",
        )
    ):
        return "login"
    if any(
        k in p
        for k in (
            "购物",
            "商城",
            "电商",
            "商品",
            "shop",
            "store",
            "ecommerce",
            "e-commerce",
            "product",
            "cart",
            "marketplace",
        )
    ):
        return "shop"
    if any(k in p for k in ("仪表", "dashboard", "后台", "admin", "analytics", "控制台")):
        return "dashboard"
    if any(
        k in p
        for k in (
            "音乐",
            "播放器",
            "歌词",
            "歌单",
            "切歌",
            "music",
            "player",
            "playlist",
            "lyrics",
            "spotify",
            "song",
            "album",
        )
    ):
        return "music"
    if any(k in p for k in ("落地", "landing", "官网", "首页", "home page", "marketing", "hero")):
        return "landing"
    return "generic"


def _detect_html_intent(html: str) -> str | None:
    l = html.lower()
    if "type=\"password\"" in l or "placeholder=\"••••••••\"" in l or "sign in" in l or "log in" in l:
        return "login"
    if "cart" in l or "product" in l or "price" in l or "shop" in l:
        return "shop"
    if "chart" in l or "dashboard" in l or "graph" in l or "metrics" in l:
        return "dashboard"
    if "playlist" in l or "lyrics" in l or "track" in l or "music" in l:
        return "music"
    return None


def _html_matches_brief_intent(prompt: str, html: str) -> bool:
    expected = _prompt_intent(prompt)
    detected = _detect_html_intent(html)
    if expected == "landing" and detected == "login":
        return False
    if expected in {"landing", "generic"}:
        return True
    return detected == expected or detected is None


def _screen_html_rel(screen: dict[str, Any]) -> str:
    sid = str(screen.get("id") or "main")
    return str(screen.get("html_path") or f"screens/{sid}.html")


def _resolve_screen_html_path(session_dir: Path, screen: dict[str, Any]) -> Path:
    return session_dir / _screen_html_rel(screen)


def _next_round_index(manifest: dict[str, Any], screen_id: str) -> int:
    history = list(manifest.get("round_history") or [])
    indices = [
        int(r.get("round_index", 0))
        for r in history
        if str(r.get("screen_id") or "") == screen_id
    ]
    return (max(indices) + 1) if indices else 0


def _record_screen_round(
    session_dir: Path,
    manifest: dict[str, Any],
    *,
    screen_id: str,
    html: str,
    prompt: str,
    reasoning_content: str | None,
    process_log_slice: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write versioned HTML and append round metadata to manifest."""
    round_index = _next_round_index(manifest, screen_id)
    rel = f"screens/{screen_id}_r{round_index}.html"
    (session_dir / "screens").mkdir(exist_ok=True)
    (session_dir / rel).write_text(html, encoding="utf-8")
    entry: dict[str, Any] = {
        "round_index": round_index,
        "screen_id": screen_id,
        "html_path": rel,
        "prompt": prompt,
        "reasoning_content": reasoning_content,
        "process_log": process_log_slice,
        "at": now_iso(),
    }
    history = list(manifest.get("round_history") or [])
    history.append(entry)
    manifest["round_history"] = history
    for screen in manifest.get("screens") or []:
        if str(screen.get("id")) == screen_id:
            screen["html_path"] = rel
            screen["active_round_index"] = round_index
    return entry


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


def _spec_to_design_md(spec: dict[str, Any]) -> str:
    lines = [
        f"# DESIGN SPECIFICATION: {spec.get('name') or 'Design System'}",
        "",
        "## Rationale",
        str(spec.get("rationale") or "Polished visual structure."),
        "",
        "## Colors",
    ]
    colors = spec.get("colors") or {}
    for k, v in colors.items():
        if isinstance(v, list) and v:
            lines.append(f"- **{k}**: {', '.join(v)}")
        elif v:
            lines.append(f"- **{k}**: {v}")
    lines += [
        "",
        "## Typography",
        f"- **Font Family**: {spec.get('typography', {}).get('fontFamily', 'Inter')}",
        "",
        "## Components",
    ]
    for comp in spec.get("components") or []:
        lines.append(f"- {comp}")
    lines += [
        "",
        "## Accessibility",
        str(spec.get("accessibility") or "WCAG AA contrast; focus rings; semantic headings."),
        "",
    ]
    return "\n".join(lines)


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


_VISION_ERROR_RE = re.compile(
    r"(?:cannot\s+read|does\s+not\s+support\s+(?:image|vision)|"
    r"unable\s+to\s+(?:read|process|view)\s+(?:the\s+)?(?:image|picture|screenshot)|"
    r"inform\s+the\s+user|no\s+image\s+(?:input|support))",
    re.IGNORECASE,
)


def _looks_like_vision_error(text: str) -> bool:
    """Return True if LLM output looks like a vision-capability error instead of real content."""
    if not text:
        return False
    return bool(_VISION_ERROR_RE.search(text[:500]))


def _llm_complete_vision(
    router: Any,
    prompt: str,
    *,
    model_id: str,
    image_data_url: str | None = None,
    timeout_sec: float = _LLM_TIMEOUT_SEC,
    image_analysis_text: str = "",
) -> tuple[str, str | None, dict[str, int], bool]:
    """Complete with optional vision image via router.chat multimodal content."""
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
    from src.chat_content import user_message_content_for_llm

    vision_ok = _check_vision_ok(router, model_id, image_data_url)

    if image_data_url and vision_ok:
        content = user_message_content_for_llm(
            f"[image: {image_data_url}]\n{prompt}",
            vision_enabled=True,
        )
        messages = [{"role": "user", "content": content}]

        def _call() -> object:
            return router.chat(messages, model_id=model_id)

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
            "vision call returned error-like response (model=%s) — falling back to text-only",
            model_id,
        )

    prefix = ""
    if image_data_url and not vision_ok:
        if image_analysis_text:
            prefix = image_analysis_text + "\n\n"
        else:
            try:
                from src.design.image_analysis import image_analysis_prompt_fragment
                analysis = image_analysis_prompt_fragment(image_data_url)
                prefix = (analysis + "\n\n") if analysis else (
                    "A reference screenshot was attached; active model does not support vision. "
                    "Use the product brief to infer colors and layout.\n"
                )
            except Exception:
                prefix = (
                    "A reference screenshot was attached but the active model may not support vision. "
                    "Infer a polished UI that matches the product brief alone.\n"
                )
    elif image_data_url and vision_ok:
        try:
            from src.design.image_analysis import image_analysis_prompt_fragment
            analysis = image_analysis_prompt_fragment(image_data_url)
            prefix = (analysis + "\n\n") if analysis else (
                "A reference screenshot was attached but the model could not process it. "
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
        "Do NOT generate interactive elements — no <a href>, no <form>, no onclick handlers. Static prototype only.\n"
        "Return ONLY ```html ... ```."
    )


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
        (
            "CRITICAL Rules:\n"
            "1. Use Tailwind CDN: <script src=\"https://cdn.tailwindcss.com\"></script>\n"
            "2. Define design system colors via tailwind.config script — no custom <style> blocks.\n"
            "3. Complete HTML with closed </html>; keep body under 80 lines to avoid truncation.\n"
            "4. Implement the screen in the Brief — match the requested screen type.\n"
        )
        + intent_rule
        + (
            "6. Select 3-5 core components; high-fidelity modern aesthetics (rounded-2xl cards, "
            "subtle gradients, hover transitions, generous spacing py-12–py-20).\n"
            "7. CRITICAL: This is a static prototype — do NOT produce any interactive elements. "
            "No <a href=\"...\"> links, no <form> tags, no onclick attributes, no inline JavaScript handlers. "
            "Buttons may appear as visual decoration only (no click/tap behavior).\n"
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
        ui_parts.append(f"Current HTML to revise:\n{current_html[:14000]}\n")
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
        "Do NOT add interactive elements — no <a href>, no <form>, no onclick handlers. Static prototype only.\n"
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
        "- Do NOT generate interactive elements — no <a href>, no <form>, no onclick handlers. Static prototype only.\n"
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


def generate_session(
    run_id: str,
    *,
    prompt: str,
    device: str = "web",
    reference_image: str | None = None,
    reference_md: str | None = None,
    reference_md_name: str | None = None,
    reference_url: str | None = None,
    design_system: str | None = None,
    continue_inflight: bool = False,
) -> dict[str, Any]:
    """Two-phase: design spec first, then UI HTML (optional image / Design.md / URL)."""
    from src.models_config import get_router, is_model_available

    sdir = session_dir(run_id)
    if not (sdir / MANIFEST).is_file():
        ensure_session(run_id, title=prompt[:40], prompt=prompt)
    manifest = read_manifest(sdir)
    user_prompt = prompt.strip() or str(manifest.get("prompt") or "").strip()

    ref_rel = manifest.get("reference_image")
    if reference_image:
        ref_rel = save_reference_image(sdir, reference_image) or ref_rel
    image_data_url = load_reference_data_url(sdir, str(ref_rel) if ref_rel else None)

    md_rel = manifest.get("reference_md")
    if reference_md:
        md_rel = save_reference_md(sdir, reference_md, name=reference_md_name) or md_rel
    md_text, md_name = load_reference_md(sdir, str(md_rel) if md_rel else None)

    url = normalize_reference_url(reference_url) or manifest.get("reference_url")
    url_snapshot = load_url_snapshot(sdir)
    if url and (reference_url or not url_snapshot):
        try:
            from src.design import service
            url_snapshot = service._fetch_url_snapshot(str(url))
            save_url_snapshot(sdir, url_snapshot)
            url = url_snapshot.get("url") or url
        except DesignError as exc:
            logger.warning("design url fetch failed run_id=%s err=%s", run_id, exc)
            url_snapshot = {
                "url": url,
                "host": re.sub(r"^https?://", "", str(url)).split("/")[0],
                "title": "",
                "description": "",
                "excerpt": "",
                "error": str(exc),
                "fetched_at": now_iso(),
            }
            save_url_snapshot(sdir, url_snapshot)

    has_image = bool(image_data_url)
    has_md = bool(md_text)
    has_url = bool(url)
    if not user_prompt and not has_image and not has_md and not has_url:
        raise DesignError("Prompt or reference is required")
    if not user_prompt:
        if has_md:
            user_prompt = f"使用 the file [{md_name or 'DESIGN.md'}] 创建设计系统。设计一个登录页面。"
        elif has_url:
            user_prompt = "参考这个网站，生成一个登录页面"
        else:
            user_prompt = "参考图片的设计，生成界面"

    if has_md:
        intro = (
            f"I'll build a design system from «{md_name or 'DESIGN.md'}», then craft an interface that matches your brief."
        )
    elif has_url:
        intro = (
            f"I'll load {url_snapshot.get('host') if url_snapshot else url}, extract a design system, then craft a matching interface."
        )
    elif has_image:
        intro = (
            "I'll use your reference image to extract a design system (colors, type, components), then craft a matching interface."
        )
    else:
        _intro_pid = _normalize_preset_id(design_system or manifest.get("design_system"))
        if _intro_pid != "clutch":
            from src.design.builtin_presets import resolve_preset_meta
            _intro_meta = resolve_preset_meta(_intro_pid)
            if _intro_meta:
                intro = (
                    f"I'll apply the {_intro_meta['name']} design system, then craft the interface for your brief."
                )
            else:
                intro = "I'll start with a design specification (colors, type, components), then craft the interface to match."
        else:
            intro = (
                "I'll apply the built-in Clutch design system, then craft the interface for your brief."
            )

    attach_bits = []
    if has_image:
        attach_bits.append("reference image")
    if has_md:
        attach_bits.append(f"file {md_name or 'DESIGN.md'}")
    if has_url:
        attach_bits.append(f"url {url}")
    attach_note = f" [{', '.join(attach_bits)}]" if attach_bits else ""

    resume = continue_inflight and str(manifest.get("status") or "") in {
        "crafting_spec",
        "generating_ui",
    }
    if resume and manifest.get("process_log"):
        process_log = list(manifest.get("process_log") or [])
    else:
        process_log = [
            {
                "role": "user",
                "text": user_prompt + attach_note,
                "at": now_iso(),
            },
            {
                "role": "assistant",
                "text": intro,
                "status": "crafting_spec",
                "at": now_iso(),
            },
        ]
    manifest["prompt"] = user_prompt
    manifest["name"] = user_prompt[:48] or manifest.get("name") or "New Design"
    manifest["device"] = device if device in {"web", "app"} else "web"
    manifest["phase"] = "spec"
    manifest["status"] = "crafting_spec"
    manifest["process_log"] = process_log
    manifest["error"] = None
    if not resume:
        manifest["round_history"] = []
        manifest["screens"] = []
        manifest["spec"] = None
        manifest["design_system"] = _normalize_preset_id(design_system or manifest.get("design_system"))
    if ref_rel:
        manifest["reference_image"] = ref_rel
    if md_rel:
        manifest["reference_md"] = md_rel
        manifest["reference_md_name"] = md_name or reference_md_name or "DESIGN.md"
    if url:
        manifest["reference_url"] = url
        if url_snapshot:
            manifest["url_snapshot"] = {
                "url": url_snapshot.get("url"),
                "host": url_snapshot.get("host"),
                "title": url_snapshot.get("title"),
                "description": url_snapshot.get("description"),
            }
    write_manifest(sdir, manifest)

    spec: dict[str, Any] | None = None
    source = "fallback"
    router = get_router()
    model_id = router.active_model_id
    process_log = list(manifest.get("process_log") or [])
    model_id, model_name = _stamp_session_model(
        manifest,
        router,
        model_id=model_id,
        process_log=process_log,
        record_in_log=False,
    )
    write_manifest(sdir, manifest)
    preset_id = _normalize_preset_id(manifest.get("design_system"))
    use_builtin_preset = preset_id == "clutch" and not (has_image or has_md or has_url)
    if not use_builtin_preset and not has_image and not has_md and not has_url:
        from src.design.builtin_presets import resolve_preset_spec
        if preset_id != "clutch" and resolve_preset_spec(preset_id):
            use_builtin_preset = True
    spec_usage = empty_token_usage()
    spec_usage_estimated = False

    if use_builtin_preset:
        from src.design.builtin_presets import resolve_preset_meta
        preset_name = (resolve_preset_meta(preset_id) or {}).get("name") or preset_id
        update_process_status(
            sdir,
            manifest,
            text=f"Applying {preset_name} design system…",
            status="crafting_spec",
            model_id=model_id,
            model_name=model_name,
        )
        spec, design_md = resolve_builtin_spec(preset_id, user_prompt, device=device)
        source = "builtin_clutch" if preset_id == "clutch" else "builtin_preset"
    else:
        update_process_status(
            sdir,
            manifest,
            text="Extracting colors, typography, and layout tokens from your brief…",
            status="crafting_spec",
            model_id=model_id,
            model_name=model_name,
        )
        design_md = ""
        if is_model_available(router, model_id):
            try:
                context_parts = [
                    "You are a product design system generator.\n",
                    f"Brief: {user_prompt}\nDevice: {device}\n",
                ]
                if has_md and md_text:
                    context_parts.append(
                        f"\n=== AUTHORITATIVE DESIGN SPECIFICATION: {md_name} ===\n"
                        f"{md_text[:16000]}\n"
                        "=== END OF SPECIFICATION ===\n\n"
                        "CRITICAL: Extract EVERY color, font, spacing value, and component rule from "
                        "the specification above. Use them VERBATIM — do NOT invent or substitute values. "
                        "The JSON output must faithfully reflect the exact tokens defined in this document.\n"
                    )
                if has_url and url_snapshot:
                    browser_frag = url_snapshot.get("browser_prompt_fragment") or ""
                    context_parts.append(
                        "Reference website:\n"
                        f"URL: {url_snapshot.get('url')}\n"
                        f"Title: {url_snapshot.get('title')}\n"
                        f"Description: {url_snapshot.get('description')}\n"
                    )
                    if browser_frag:
                        context_parts.append(browser_frag + "\n")
                    else:
                        css_tokens = url_snapshot.get("css_tokens") or {}
                        token_desc = _format_css_tokens_for_prompt(css_tokens, host=str(url_snapshot.get("host") or ""))
                        if token_desc:
                            context_parts.append(token_desc + "\n")
                        else:
                            context_parts.append(
                                f"Excerpt: {(url_snapshot.get('excerpt') or '')[:3000]}\n"
                                "Infer a polished design system inspired by this site's visual language.\n"
                            )
                    og_analysis = url_snapshot.get("og_image_analysis") or {}
                    og_desc = og_analysis.get("description", "")
                    if og_desc:
                        context_parts.append(og_desc + "\n")
                if has_image:
                    vision_ok_spec = _check_vision_ok(router, model_id, image_data_url)
                    if vision_ok_spec:
                        context_parts.append(
                            "A reference UI screenshot is attached. Extract colors, typography, and component style from it.\n"
                        )
                    else:
                        try:
                            from src.design.image_analysis import image_analysis_prompt_fragment
                            img_analysis = image_analysis_prompt_fragment(image_data_url or "")
                            if img_analysis:
                                context_parts.append(img_analysis + "\n")
                            else:
                                context_parts.append(
                                    "A reference UI screenshot was provided; use the product brief to infer design tokens.\n"
                                )
                        except Exception:
                            context_parts.append(
                                "A reference UI screenshot was provided; use the product brief to infer design tokens.\n"
                            )
                # If URL has a browser screenshot and model supports vision, send it
                browser_ss = (url_snapshot or {}).get("browser_screenshot") or ""
                if browser_ss and not image_data_url:
                    vision_ok_browser = _check_vision_ok(router, model_id, browser_ss)
                    if vision_ok_browser:
                        image_data_url = browser_ss
                        context_parts.append(
                            "A browser-rendered screenshot of the reference website is attached. "
                            "Extract exact colors, typography, spacing, and layout from it.\n"
                        )
                context_parts.append(
                    "Return ONLY JSON with keys: name, rationale, brand (name, voice), visual_style, "
                    "layout_system, layout_pattern, grid (columns, gutter, max_width), colors "
                    "(object of arrays of hex), typography (fontFamily, samples[{label,size,weight}]), "
                    "radius (sm, md, lg, xl), shadow (card, elevated), components (string array), "
                    "motion (duration, easing, hover_lift), responsive (string), accessibility (string). "
                    "No markdown fences."
                )
                meta = "".join(context_parts)
                spec_raw, _spec_reasoning, call_usage, call_estimated = _llm_complete_vision(
                    router, meta, model_id=model_id, image_data_url=image_data_url
                )
                spec_usage = merge_token_usage(spec_usage, call_usage)
                spec_usage_estimated = spec_usage_estimated or call_estimated
                spec = _extract_json_block(spec_raw)
                pattern = detect_layout_pattern(user_prompt, device=device)
                spec = enrich_fallback_spec(spec, user_prompt, pattern)
                if has_image:
                    source = "llm_vision"
                elif has_md:
                    source = "llm_md"
                elif has_url:
                    source = "llm_url"
                else:
                    source = "llm"
            except Exception as exc:
                logger.warning("design spec LLM failed run_id=%s err=%s", run_id, exc)

        if not spec:
            seed = user_prompt
            if has_md and md_text:
                seed = f"{user_prompt}\n{md_text[:2000]}"
            elif has_url and url_snapshot:
                seed = f"{user_prompt}\n{url_snapshot.get('title')}\n{url_snapshot.get('description')}"
            pattern = detect_layout_pattern(seed, device=device)
            spec = enrich_fallback_spec(_fallback_spec(seed), seed, pattern)

        if has_md and md_text:
            design_md = md_text if md_text.endswith("\n") else md_text + "\n"
        else:
            design_md = _spec_to_design_md(spec)

    (sdir / SPEC_JSON).write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (sdir / DESIGN_MD).write_text(design_md, encoding="utf-8")

    process_log = list(manifest.get("process_log") or [])
    spec_ready_text = f"Design system «{spec.get('name')}» ready."
    if not is_model_available(router, model_id):
        spec_ready_text += f"\n\n⚠️ Warning: Model '{model_id}' is not available (API key missing in Settings -> Models). Using offline fallback templates."
    _finalize_assistant_step(
        process_log,
        text=spec_ready_text,
        status="spec_ready",
        model_id=model_id,
        model_name=model_name,
        usage=spec_usage if not use_builtin_preset else None,
        usage_estimated=spec_usage_estimated,
        replace_statuses={"crafting_spec"},
    )
    manifest["spec"] = spec
    manifest["phase"] = "ui"
    manifest["generate_source"] = source
    manifest["process_log"] = process_log
    write_manifest(sdir, manifest)
    append_process_status(
        sdir,
        manifest,
        text="Generating high-fidelity HTML with layout patterns and design review…",
        status="generating_ui",
        model_id=model_id,
        model_name=model_name,
    )
    append_design_run_log(
        run_id,
        f"spec ready name={spec.get('name')!s} → generating_ui device={device} model={model_id}",
    )

    sdir = session_dir(run_id)
    screens_to_gen = _parse_multi_screens(user_prompt, model_id, router)
    
    append_design_run_log(
        run_id,
        f"spec ready name={spec.get('name')!s} → generating_ui device={device} model={model_id} screens_count={len(screens_to_gen)}",
    )
    
    screens = []
    accumulated_usage = empty_token_usage()
    accumulated_estimated = False
    process_log = list(manifest.get("process_log") or [])
    design_md_text = design_md
    
    ui_origin_x = default_ui_origin_x(has_source=has_image or has_md or has_url)
    
    for idx, screen_info in enumerate(screens_to_gen):
        sid = screen_info["id"]
        sname = screen_info["name"]
        sprompt = screen_info["prompt"]
        spattern = screen_info.get("layout_pattern") or detect_layout_pattern(sprompt, device=device)
        
        update_process_status(
            sdir,
            manifest,
            text=f"Generating screen {idx + 1}/{len(screens_to_gen)}: «{sname}» ({spattern})…",
            status="generating_ui",
            model_id=model_id,
            model_name=model_name,
        )
        
        screen_spec = {**spec, "layout_pattern": spattern}
        html = ""
        ui_reasoning = None
        ui_fail_reason = None
        
        if is_model_available(router, model_id):
            try:
                ui_vision_ok = _check_vision_ok(router, model_id, image_data_url)
                use_img = image_data_url if (idx == 0 and ui_vision_ok) else None
                
                from src.design import service
                gen_ui = getattr(service, "_generate_ui_html", _generate_ui_html)
                html, ui_reasoning, ui_usage, ui_usage_estimated, ui_fail_reason = gen_ui(
                    router,
                    user_prompt=sprompt,
                    spec=screen_spec,
                    device=device,
                    model_id=model_id,
                    design_md=design_md_text,
                    md_text=md_text if has_md else None,
                    url_snapshot=url_snapshot if has_url else None,
                    has_image=has_image and (idx == 0),
                    image_data_url=use_img,
                )
                accumulated_usage = merge_token_usage(accumulated_usage, ui_usage)
                accumulated_estimated = accumulated_estimated or ui_usage_estimated
            except Exception as exc:
                logger.warning("design ui LLM failed for screen %s run_id=%s err=%s", sid, run_id, exc)
                ui_fail_reason = str(exc)

        llm_available = is_model_available(router, model_id)
        if not _html_has_visible_content(html):
            if llm_available:
                detail = ui_fail_reason or "the model returned no valid HTML"
                err_msg = f"Generation failed for screen «{sname}» — {detail}. Please try again."
                _finalize_assistant_step(
                    process_log,
                    text=err_msg,
                    status="error",
                    model_id=model_id,
                    model_name=model_name,
                    usage=accumulated_usage,
                    usage_estimated=accumulated_estimated,
                    replace_statuses={"generating_ui"},
                )
                manifest["status"] = "error"
                manifest["error"] = err_msg
                manifest["process_log"] = process_log
                manifest["screens"] = screens
                write_manifest(sdir, manifest)
                return public_session_payload(manifest, sdir)
            html = _fallback_ui_html(sprompt, screen_spec, device=device)

        round_entry = _record_screen_round(
            sdir,
            manifest,
            screen_id=sid,
            html=html,
            prompt=sprompt,
            reasoning_content=ui_reasoning,
            process_log_slice=list(process_log),
        )
        
        if idx == 0:
            x_pos = ui_origin_x
        else:
            step = ui_layout_step(device)
            x_pos = ui_origin_x + idx * step
            
        screens.append({
            "id": sid,
            "name": sname,
            "position": {"x": x_pos, "y": _DESIGN_ROW_Y},
            "html_path": round_entry["html_path"],
            "active_round_index": round_entry["round_index"],
        })
        manifest["screens"] = list(screens)

    ui_ready_text = (
        f"Interface draft is ready — generated {len(screens)} screens on the canvas:\n"
        + "\n".join(f"- **{s['name']}** (wrote `{s['html_path']}`)" for s in screens)
    )
    manifest["generate_source"] = source
    if not is_model_available(router, model_id):
        ui_ready_text += f"\n\n⚠️ Warning: Model '{model_id}' is not available (API key missing in Settings -> Models). Using offline fallback templates."
    _finalize_assistant_step(
        process_log,
        text=ui_ready_text,
        status="ready",
        model_id=model_id,
        model_name=model_name,
        usage=accumulated_usage,
        usage_estimated=accumulated_estimated,
        replace_statuses={"generating_ui"},
    )
    if manifest.get("round_history"):
        history = list(manifest["round_history"])
        if history:
            history[-1] = {**history[-1], "process_log": list(process_log)}
            manifest["round_history"] = history
            
    manifest["screens"] = screens
    manifest["phase"] = "canvas"
    manifest["status"] = "ready"
    manifest["process_log"] = process_log
    manifest["prototype_approved"] = False
    manifest["react_ready"] = False
    manifest["react_approved"] = False
    clear_fake_thumbnail(sdir)
    manifest.pop("thumbnail", None)
    write_manifest(sdir, manifest)
    sync_session_folder_name(
        run_id,
        title=str(manifest.get("name") or user_prompt or "design"),
        device=device,
    )
    append_design_run_log(
        run_id,
        f"generate done source={source} screens_count={len(screens)}",
    )
    logger.info("design generate done run_id=%s source=%s count=%d", run_id, source, len(screens))
    return get_session(run_id)


def start_generate_session(
    run_id: str,
    *,
    prompt: str,
    device: str = "web",
    reference_image: str | None = None,
    reference_md: str | None = None,
    reference_md_name: str | None = None,
    reference_url: str | None = None,
    design_system: str | None = None,
) -> dict[str, Any]:
    """Kick off two-phase generate in a background thread; return immediately for polling."""
    sdir = session_dir(run_id)
    if not (sdir / MANIFEST).is_file():
        ensure_session(run_id, title=prompt[:40], prompt=prompt)
    with _generate_lock:
        existing = _generate_jobs.get(run_id)
        if existing and existing.is_alive():
            return get_session(run_id)

    user_prompt = (prompt or "").strip()
    url = normalize_reference_url(reference_url)
    md_rel = save_reference_md(sdir, reference_md, name=reference_md_name) if reference_md else None
    md_text, md_name = load_reference_md(sdir, md_rel) if md_rel else (None, None)
    ref_rel = save_reference_image(sdir, reference_image) if reference_image else None

    if not user_prompt and not ref_rel and not md_rel and not url:
        raise DesignError("Prompt or reference is required")
    if not user_prompt:
        if md_rel:
            user_prompt = f"使用 the file [{md_name or 'DESIGN.md'}] 创建设计系统。设计一个登录页面。"
        elif url:
            user_prompt = "参考这个网站，生成一个登录页面"
        else:
            user_prompt = "参考图片的设计，生成界面"

    url_snapshot: dict[str, Any] | None = None
    if url:
        try:
            from src.design import service
            url_snapshot = service._fetch_url_snapshot(url)
            save_url_snapshot(sdir, url_snapshot)
            url = str(url_snapshot.get("url") or url)
        except DesignError as exc:
            logger.warning("design url fetch (start) failed run_id=%s err=%s", run_id, exc)
            url_snapshot = {
                "url": url,
                "host": re.sub(r"^https?://", "", url).split("/")[0],
                "title": "",
                "description": "",
                "excerpt": "",
                "error": str(exc),
                "fetched_at": now_iso(),
            }
            save_url_snapshot(sdir, url_snapshot)

    has_image = bool(ref_rel)
    has_md = bool(md_rel)
    has_url = bool(url)
    if has_md:
        intro = f"I'll build a design system from «{md_name or 'DESIGN.md'}», then craft a matching interface."
    elif has_url:
        host = (url_snapshot or {}).get("host") or url
        intro = f"I'll load {host} on the canvas, extract a design system, then craft a matching interface."
    elif has_image:
        intro = "I'll use your reference image to extract a design system, then craft a matching interface."
    elif _normalize_preset_id(design_system) == "clutch":
        intro = (
            "I'll apply the built-in Clutch design system, then craft the interface for your brief."
        )
    else:
        intro = "I'll start with a design specification (colors, type, components), then craft the interface to match."

    attach_bits = []
    if has_image:
        attach_bits.append("reference image")
    if has_md:
        attach_bits.append(f"file {md_name or 'DESIGN.md'}")
    if has_url:
        attach_bits.append(f"url {url}")
    attach_note = f" [{', '.join(attach_bits)}]" if attach_bits else ""

    manifest = read_manifest(sdir)
    manifest["prompt"] = user_prompt
    manifest["name"] = user_prompt[:48] or manifest.get("name") or "New Design"
    manifest["device"] = device if device in {"web", "app"} else "web"
    manifest["phase"] = "spec"
    manifest["status"] = "crafting_spec"
    manifest["error"] = None
    manifest["screens"] = []
    manifest["spec"] = None
    manifest["round_history"] = []
    manifest["design_system"] = _normalize_preset_id(design_system)
    if ref_rel:
        manifest["reference_image"] = ref_rel
    if md_rel:
        manifest["reference_md"] = md_rel
        manifest["reference_md_name"] = md_name or reference_md_name or "DESIGN.md"
    if url:
        manifest["reference_url"] = url
        if url_snapshot:
            manifest["url_snapshot"] = {
                "url": url_snapshot.get("url"),
                "host": url_snapshot.get("host"),
                "title": url_snapshot.get("title"),
                "description": url_snapshot.get("description"),
            }
    manifest["process_log"] = [
        {
            "role": "user",
            "text": user_prompt + attach_note,
            "at": now_iso(),
        },
        {
            "role": "assistant",
            "text": intro,
            "status": "crafting_spec",
            "at": now_iso(),
        },
    ]
    clear_fake_thumbnail(sdir)
    manifest.pop("thumbnail", None)
    write_manifest(sdir, manifest)
    sdir = sync_session_folder_name(
        run_id,
        title=str(manifest.get("name") or user_prompt or "design"),
        device=str(manifest.get("device") or device or "web"),
    )
    append_design_run_log(
        run_id,
        f"generate started device={device} prompt={user_prompt[:80]!r}",
    )

    def _worker() -> None:
        try:
            from src.design import service
            service.generate_session(
                run_id,
                prompt=user_prompt,
                device=device,
                reference_image=None,
                reference_md=None,
                reference_url=None,
                design_system=manifest.get("design_system"),
                continue_inflight=True,
            )
        except Exception as exc:
            logger.exception("design generate worker failed run_id=%s", run_id)
            try:
                err_dir = session_dir(run_id)
                m = read_manifest(err_dir)
                m["status"] = "error"
                m["error"] = str(exc)
                log = list(m.get("process_log") or [])
                log.append(
                    {
                        "role": "assistant",
                        "text": f"Generation failed: {exc}",
                        "status": "error",
                        "at": now_iso(),
                    }
                )
                m["process_log"] = log
                write_manifest(err_dir, m)
            except Exception:
                pass
        finally:
            with _generate_lock:
                _generate_jobs.pop(run_id, None)

    thread = threading.Thread(target=_worker, name=f"design-gen-{run_id}", daemon=True)
    with _generate_lock:
        _generate_jobs[run_id] = thread
    thread.start()
    return public_session_payload(manifest, sdir)


def _html_essentially_same(a: str, b: str) -> bool:
    def norm(s: str) -> str:
        out = re.sub(r"\s+", "", s or "")
        out = re.sub(r'data-note="[^"]*"', "", out, flags=re.I)
        return out
    return bool(a) and bool(b) and norm(a) == norm(b)


def _merged_design_prompt(manifest: dict[str, Any], instruction: str) -> str:
    base = str(manifest.get("prompt") or manifest.get("name") or "").strip()
    note = (instruction or "").strip()
    if base and note:
        return f"{base}\n{note}"
    return note or base or "Interface"


def _infer_iterate_mode(instruction: str, *, mode: str | None, target_kind: str | None) -> str:
    raw = (mode or "auto").strip().lower()
    if raw in {"modify", "add", "duplicate"}:
        return raw
    text = instruction.lower()
    add_keys = (
        "新增",
        "添加一",
        "再做",
        "另一个",
        "新页面",
        "新画板",
        "再来一",
        "add ",
        "new page",
        "another ",
        "create a new",
        "also create",
        "new screen",
        "new artboard",
    )
    mod_keys = (
        "改成",
        "修改",
        "优化",
        "调整",
        "换成",
        "改一下",
        "要体现",
        "需要",
        "显示",
        "加上",
        "增加",
        "完善",
        "深色",
        "fix",
        "change ",
        "update ",
        "make it",
        "dark mode",
        "improve",
        "tweak",
        "refine",
        "add lyrics",
        "show ",
    )
    has_add = any(k in text for k in add_keys)
    has_mod = any(k in text for k in mod_keys)
    if has_add and not has_mod:
        return "add"
    if has_mod and not has_add:
        return "modify"
    if has_mod and has_add and target_kind == "ui":
        return "modify"
    if target_kind == "ui":
        return "modify"
    return "add"


def _next_screen_id(screens: list[dict[str, Any]]) -> str:
    used = {str(s.get("id") or "") for s in screens}
    if "main" not in used:
        return "main"
    i = 2
    while f"screen-{i}" in used:
        i += 1
    return f"screen-{i}"


def _screen_layout_x(
    screens: list[dict[str, Any]], *, device: str = "web", has_source: bool = False
) -> int:
    xs = []
    for s in screens:
        pos = s.get("position") or {}
        if isinstance(pos, dict) and isinstance(pos.get("x"), (int, float)):
            xs.append(int(pos["x"]))
    step = ui_layout_step(device)
    return (max(xs) + step) if xs else default_ui_origin_x(has_source=has_source)


def iterate_session(
    run_id: str,
    instruction: str,
    *,
    target_kind: str | None = None,
    target_id: str | None = None,
    element_path: str | None = None,
    element_label: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    from src.models_config import get_router, is_model_available

    sdir = session_dir(run_id)
    manifest = read_manifest(sdir)
    instruction = instruction.strip()
    if not instruction:
        raise DesignError("Instruction is required")
    screens = [s for s in (manifest.get("screens") or []) if not s.get("deleted")]
    if not screens and (target_kind or "ui") == "ui":
        raise DesignError("Generate a design before iterating")

    kind = (target_kind or "ui").strip().lower()
    if kind not in {"ui", "spec", "md", "image", "url", "process"}:
        kind = "ui"
    action = _infer_iterate_mode(instruction, mode=mode, target_kind=kind)
    design_md = (sdir / DESIGN_MD).read_text(encoding="utf-8") if (sdir / DESIGN_MD).is_file() else ""
    spec = manifest.get("spec")
    if not isinstance(spec, dict) and (sdir / SPEC_JSON).is_file():
        try:
            spec = json.loads((sdir / SPEC_JSON).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            spec = None

    selection_note = f"Selected: {kind}"
    if target_id:
        selection_note += f"/{target_id}"
    if element_label or element_path:
        selection_note += f"; element={element_label or element_path}"

    log = list(manifest.get("process_log") or [])
    log_start = len(log)
    log.append(
        {
            "role": "user",
            "text": f"{instruction} [{selection_note}; mode={action}]",
            "at": now_iso(),
        }
    )
    log.append(
        {
            "role": "assistant",
            "text": (
                "Creating a new version…"
                if action == "add" and kind == "ui"
                else "Thinking… applying your changes to the selected design."
            ),
            "status": "iterating",
            "at": now_iso(),
        }
    )
    manifest["status"] = "iterating"
    manifest["process_log"] = log
    write_manifest(sdir, manifest)

    router = get_router()
    model_id = router.active_model_id
    model_id, model_name = _stamp_session_model(
        manifest,
        router,
        model_id=model_id,
        process_log=log,
        record_in_log=False,
    )
    for i in range(len(log) - 1, -1, -1):
        if log[i].get("role") == "assistant" and log[i].get("status") == "iterating":
            log[i] = {
                **log[i],
                "model_id": model_id,
                "model_name": model_name,
            }
            break
    manifest["process_log"] = log
    write_manifest(sdir, manifest)

    if kind in {"spec", "md"}:
        updated_spec = spec if isinstance(spec, dict) else _fallback_spec(instruction)
        spec_usage = empty_token_usage()
        spec_usage_estimated = False
        if is_model_available(router, model_id):
            try:
                meta = (
                    "You revise a product design system JSON.\n"
                    f"Instruction: {instruction}\n"
                    f"Current design system JSON:\n{json.dumps(updated_spec, ensure_ascii=False)}\n"
                    f"Source DESIGN.md (excerpt):\n{design_md[:8000]}\n"
                    "Return ONLY updated JSON with keys: name, rationale, colors, typography, components."
                )
                spec_raw, _, spec_usage, spec_usage_estimated = _llm_complete(
                    router, meta, model_id=model_id
                )
                parsed = _extract_json_block(spec_raw)
                if isinstance(parsed, dict):
                    updated_spec = enrich_fallback_spec(
                        parsed,
                        instruction,
                        str(parsed.get("layout_pattern") or detect_layout_pattern(instruction)),
                    )
            except Exception as exc:
                logger.warning("design iterate spec failed: %s", exc)
        (sdir / SPEC_JSON).write_text(
            json.dumps(updated_spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if kind == "md" or not design_md:
            (sdir / DESIGN_MD).write_text(_spec_to_design_md(updated_spec), encoding="utf-8")
        manifest["spec"] = updated_spec
        clear_fake_thumbnail(sdir)
        manifest.pop("thumbnail", None)
        spec_updated_text = "Design system updated."
        if not is_model_available(router, model_id):
            spec_updated_text += f"\n\n⚠️ Warning: Model '{model_id}' is not available (API key missing in Settings -> Models). Using offline fallback templates."
        _finalize_assistant_step(
            log,
            text=spec_updated_text,
            status="ready",
            model_id=model_id,
            model_name=model_name,
            usage=spec_usage,
            usage_estimated=spec_usage_estimated,
            replace_statuses={"iterating"},
        )
        manifest["process_log"] = log
        manifest["status"] = "ready"
        write_manifest(sdir, manifest)
        return public_session_payload(manifest, sdir)

    if not screens:
        raise DesignError("Generate a design before iterating")

    ref_rel = manifest.get("reference_image")
    image_data_url = load_reference_data_url(sdir, str(ref_rel) if ref_rel else None)
    has_image = bool(image_data_url)

    md_rel = manifest.get("reference_md")
    md_text, md_name = load_reference_md(sdir, str(md_rel) if md_rel else None)
    has_md = bool(md_text)

    url = manifest.get("reference_url")
    url_snapshot = load_url_snapshot(sdir) if url else None
    has_url = bool(url_snapshot)

    ui_vision_ok = _check_vision_ok(router, model_id, image_data_url)

    if action in {"add", "duplicate"}:
        base_id = str(target_id or screens[0].get("id") or "main")
        base = next((s for s in screens if str(s.get("id")) == base_id), screens[0])
        base_html_path = _resolve_screen_html_path(sdir, base)
        if not base_html_path.is_file():
            base_html_path = sdir / "screens" / f"{base['id']}.html"
        base_html = base_html_path.read_text(encoding="utf-8") if base_html_path.is_file() else ""
        new_id = _next_screen_id(screens)
        html = ""
        ui_reasoning: str | None = None
        ui_usage = empty_token_usage()
        ui_usage_estimated = False
        device = str(manifest.get("device") or "web")
        spec_dict = spec if isinstance(spec, dict) else _fallback_spec(instruction)
        if action == "duplicate":
            html = base_html
            ui_reasoning = None
        elif is_model_available(router, model_id):
            try:
                from src.design import service
                gen_ui = getattr(service, "_generate_ui_html", _generate_ui_html)
                html, ui_reasoning, ui_usage, ui_usage_estimated, _ui_fail = gen_ui(
                    router,
                    user_prompt=instruction,
                    spec=spec_dict,
                    device=device,
                    model_id=model_id,
                    design_md=design_md,
                    md_text=md_text if has_md else None,
                    url_snapshot=url_snapshot if has_url else None,
                    has_image=has_image,
                    image_data_url=image_data_url if ui_vision_ok else None,
                    current_html="",
                    instruction="",
                )
            except Exception as exc:
                logger.warning("design iterate add failed: %s", exc)
        if not _html_has_visible_content(html):
            if action == "add" and is_model_available(router, model_id):
                raise DesignError(
                    "Could not generate the new screen — model returned empty HTML. "
                    "Please try again."
                )
            html = _fallback_ui_html(instruction, spec_dict, device=device)
        round_entry = _record_screen_round(
            sdir,
            manifest,
            screen_id=new_id,
            html=html,
            prompt=instruction,
            reasoning_content=ui_reasoning,
            process_log_slice=log[log_start:],
        )
        new_screen = {
            "id": new_id,
            "name": instruction.strip()[:40] or f"Screen {new_id}",
            "position": {
                "x": _screen_layout_x(
                    screens,
                    device=device,
                    has_source=bool(
                        manifest.get("reference_image")
                        or manifest.get("reference_md")
                        or manifest.get("reference_url")
                    ),
                ),
                "y": _DESIGN_ROW_Y,
            },
            "html_path": round_entry["html_path"],
            "active_round_index": round_entry["round_index"],
        }
        screens.append(new_screen)
        manifest["screens"] = screens
        _finalize_assistant_step(
            log,
            text=(
                f"Added «{new_screen['name']}» — wrote {round_entry['html_path']}. "
                "Select it to refine further."
            ),
            status="ready",
            model_id=model_id,
            model_name=model_name,
            usage=ui_usage,
            usage_estimated=ui_usage_estimated,
            replace_statuses={"iterating"},
        )
        history = list(manifest.get("round_history") or [])
        if history:
            history[-1] = {**history[-1], "process_log": list(log[log_start:])}
            manifest["round_history"] = history
        manifest["last_iterate_action"] = action
        manifest["last_iterate_screen_id"] = new_id
    else:
        screen_id = str(target_id or screens[0].get("id") or "main")
        screen = next((s for s in screens if str(s.get("id")) == screen_id), screens[0])
        screen_id = str(screen["id"])
        html_path = _resolve_screen_html_path(sdir, screen)
        if not html_path.is_file():
            html_path = sdir / "screens" / f"{screen_id}.html"
        current = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
        html = current
        element_hint = ""
        if element_path or element_label:
            element_hint = (
                f"Focus ONLY on this element/region: {element_label or ''} "
                f"({element_path or ''}). Keep the rest of the page intact when possible.\n"
            )
        merged_prompt = _merged_design_prompt(manifest, instruction)
        device = str(manifest.get("device") or "web")
        spec_dict = spec if isinstance(spec, dict) else _fallback_spec(merged_prompt)
        ui_reasoning: str | None = None
        ui_usage = empty_token_usage()
        ui_usage_estimated = False
        if is_model_available(router, model_id):
            try:
                from src.design import service
                gen_ui = getattr(service, "_generate_ui_html", _generate_ui_html)
                candidate, ui_reasoning, ui_usage, ui_usage_estimated, _ui_fail = gen_ui(
                    router,
                    user_prompt=merged_prompt,
                    spec=spec_dict,
                    device=device,
                    model_id=model_id,
                    design_md=design_md,
                    md_text=md_text if has_md else None,
                    url_snapshot=url_snapshot if has_url else None,
                    has_image=False,
                    image_data_url=None,
                    current_html=current,
                    instruction=f"{instruction}\n{element_hint}",
                    fallback_html=current,
                )
                if _html_has_visible_content(candidate) and not _html_essentially_same(
                    candidate, current
                ):
                    html = candidate
                elif not is_model_available(router, model_id):
                    html = _fallback_ui_html(merged_prompt, spec_dict, device=device)
                else:
                    logger.warning(
                        "design iterate modify unchanged/blank run_id=%s — keeping current HTML",
                        run_id,
                    )
            except Exception as exc:
                logger.warning("design iterate modify failed: %s", exc)
                if not is_model_available(router, model_id):
                    html = _fallback_ui_html(merged_prompt, spec_dict, device=device)
        else:
            html = _fallback_ui_html(merged_prompt, spec_dict, device=device)
        if not is_model_available(router, model_id) and (
            not _html_has_visible_content(html) or _html_essentially_same(html, current)
        ):
            html = _fallback_ui_html(merged_prompt, spec_dict, device=device)
        rel = screen.get("html_path") or f"screens/{screen_id}_r0.html"
        (sdir / "screens").mkdir(exist_ok=True)
        (sdir / rel).write_text(html, encoding="utf-8")
        screen["html_path"] = rel
        iterate_ready_text = (
            f"Updated the artboard — wrote {rel}. What else?"
        )
        if not is_model_available(router, model_id):
            iterate_ready_text += f"\n\n⚠️ Warning: Model '{model_id}' is not available (API key missing in Settings -> Models). Using offline fallback templates."
        _finalize_assistant_step(
            log,
            text=iterate_ready_text,
            status="ready",
            model_id=model_id,
            model_name=model_name,
            usage=ui_usage,
            usage_estimated=ui_usage_estimated,
            replace_statuses={"iterating"},
        )
        manifest["last_iterate_action"] = "modify"
        manifest["last_iterate_screen_id"] = screen_id

    clear_fake_thumbnail(sdir)
    manifest.pop("thumbnail", None)
    manifest["process_log"] = log
    manifest["status"] = "ready"
    write_manifest(sdir, manifest)
    return public_session_payload(manifest, sdir)


def delete_screen(
    run_id: str,
    screen_id: str,
) -> dict[str, Any]:
    sdir = session_dir(run_id)
    manifest = read_manifest(sdir)
    screens = list(manifest.get("screens") or [])
    target = next((s for s in screens if str(s.get("id")) == screen_id), None)
    if not target:
        raise DesignError(f"Screen {screen_id} not found")
    if target.get("deleted"):
        raise DesignError(f"Screen {screen_id} is already deleted")
    removed_name = str(target.get("name") or screen_id)
    round_index = _next_round_index(manifest, screen_id)
    for s in screens:
        if str(s.get("id")) == screen_id:
            s["deleted"] = True
            s["deleted_at_round"] = round_index
            break

    instruction = f"Delete screen: {removed_name}"
    log = list(manifest.get("process_log") or [])
    log_start = len(log)
    log.append({"role": "user", "text": instruction, "at": now_iso()})
    log.append({"role": "assistant", "text": f"Removed «{removed_name}» from the canvas.", "status": "ready", "at": now_iso()})
    history = list(manifest.get("round_history") or [])
    history.append({
        "round_index": round_index,
        "screen_id": screen_id,
        "html_path": f"screens/{screen_id}_r{round_index}.html",
        "prompt": instruction,
        "reasoning_content": None,
        "process_log": list(log[log_start:]),
        "at": now_iso(),
        "action": "delete",
    })
    manifest["round_history"] = history
    manifest["process_log"] = log
    manifest["status"] = "ready"
    manifest["last_iterate_action"] = "delete"
    manifest["last_iterate_screen_id"] = None
    write_manifest(sdir, manifest)
    return public_session_payload(manifest, sdir)
