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

logger = logging.getLogger(__name__)

def _enhance_brief(prompt: str, device: str) -> str:
    """Structure vague UI briefs before Spec/UI (local port of Stitch enhance-prompt)."""
    text = (prompt or "").strip()
    if not text:
        return text
    if "**PAGE STRUCTURE:**" in text.upper() or "**PLATFORM:**" in text.upper():
        return text
    platform = "Mobile, Mobile-first" if device == "app" else "Web, Desktop-first"
    upgraded = text
    for pat, repl in (
        (r"(?i)\bmenu at the top\b", "navigation bar with logo and menu items"),
        (r"(?i)\blist of items\b", "card grid layout"),
        (r"(?i)\bpicture area\b", "hero section with full-width image"),
    ):
        upgraded = re.sub(pat, repl, upgraded)
    return (
        f"{upgraded}\n\n"
        f"**PLATFORM:** {platform}\n\n"
        "**PAGE STRUCTURE:** Infer numbered sections from the brief; preserve all user intent.\n"
        "1. **Header / Nav**\n"
        "2. **Primary content**\n"
        "3. **Supporting sections / footer as needed**\n"
    )


def _spec_confirm_enabled() -> bool:
    """D40: Spec soft-confirm gate (default off). Set CLUTCH_DESIGN_SPEC_CONFIRM=1 to pause after Spec."""
    return os.environ.get("CLUTCH_DESIGN_SPEC_CONFIRM", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


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
        from src.design.gen_ui import _llm_complete

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


def _extract_colors_from_design_md(design_md: str) -> dict[str, str]:
    colors = {}
    if not design_md:
        return colors
    in_colors = False
    for line in design_md.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if line_stripped.startswith("colors:"):
            in_colors = True
            continue
        if in_colors:
            if line_stripped.startswith("typography:") or line_stripped.startswith("#") or (not line.startswith(" ") and not line.startswith("-") and ":" not in line_stripped):
                in_colors = False
                continue
            match = re.search(r"^\s*-\s*([^:]+):\s*['\"]?(#[0-9a-fA-F]{3,8}|[a-zA-Z0-9]+)['\"]?", line)
            if not match:
                match = re.search(r"^\s*([^:]+):\s*['\"]?(#[0-9a-fA-F]{3,8}|[a-zA-Z0-9]+)['\"]?", line)
            if match:
                k = match.group(1).strip().strip("-").strip()
                v = match.group(2).strip()
                colors[k] = v
    return colors


def _get_unified_tailwind_config(spec: dict[str, Any] | None, design_md: str) -> dict[str, Any]:
    colors = {}
    if spec and isinstance(spec, dict):
        raw_colors = spec.get("colors") or {}
        for k, v in raw_colors.items():
            if isinstance(v, list):
                if len(v) > 0:
                    colors[k] = v[0]
                    if len(v) > 1:
                        colors[f"{k}-light"] = v[1]
                        colors[f"{k}-hover"] = v[1]
                    if len(v) > 2:
                        colors[f"{k}-dark"] = v[2]
                        colors[f"{k}-active"] = v[2]
            elif isinstance(v, str):
                colors[k] = v
                
    md_colors = _extract_colors_from_design_md(design_md)
    for k, v in md_colors.items():
        if k not in colors:
            colors[k] = v

    theme_config = {
        "colors": colors,
        "borderRadius": {
            "DEFAULT": "0.125rem",
            "sm": "0.25rem",
            "md": "0.375rem",
            "lg": "0.5rem",
            "xl": "0.75rem",
            "2xl": "1rem",
            "3xl": "1.5rem",
            "full": "9999px"
        },
        "spacing": {
            "unit": "4px",
            "xs": "4px",
            "sm": "8px",
            "md": "16px",
            "lg": "24px",
            "xl": "32px",
            "2xl": "48px",
            "3xl": "64px",
            "container-max": "1440px",
            "sidebar-width": "240px",
            "gutter": "16px"
        }
    }
    
    if spec and isinstance(spec, dict):
        font_family = spec.get("typography", {}).get("fontFamily")
        if font_family:
            theme_config["fontFamily"] = {
                "sans": [font_family, "Inter", "system-ui", "-apple-system", "sans-serif"],
                "body": [font_family, "Inter", "system-ui", "-apple-system", "sans-serif"]
            }
    return theme_config


def inject_unified_tailwind_config(html: str, spec: dict[str, Any] | None, design_md: str) -> str:
    if not html:
        return html
    theme_config = _get_unified_tailwind_config(spec, design_md)
    theme_config_json = json.dumps(theme_config, indent=6, ensure_ascii=False)
    
    script_content = f"""<script id="tailwind-config">
      tailwind.config = {{
        darkMode: "class",
        theme: {{
          extend: {theme_config_json}
        }}
      }};
    </script>"""
    
    pattern = re.compile(
        r'<script[^>]*id=["\']tailwind-config["\'][^>]*>[\s\S]*?</script>|<script[^>]*>\s*tailwind\.config\s*=\s*\{[\s\S]*?\}\s*;?\s*</script>',
        re.I
    )
    if pattern.search(html):
        html = pattern.sub(script_content, html)
    else:
        cdn_pattern = re.compile(r'(<script[^>]*src=["\'][^"\']*tailwindcss\.com[^"\']*["\'][^>]*>\s*</script>)', re.I)
        if cdn_pattern.search(html):
            html = cdn_pattern.sub(r'\1\n' + script_content, html)
        elif "</head>" in html:
            html = html.replace("</head>", f"{script_content}\n</head>")
        else:
            html = f"{script_content}\n{html}"
    return html

