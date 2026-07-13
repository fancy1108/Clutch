"""Browser-based design token extraction using Playwright.

When Playwright + Chromium are available, this module:
  1. Renders the target URL in a headless browser.
  2. Extracts computed styles from the full DOM tree (colors, fonts, spacing, layout, etc.).
  3. Takes a full-page screenshot.
  4. Returns structured data usable by both vision and non-vision LLMs.

Falls back gracefully if Playwright is not installed.
"""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

try:
    from playwright.sync_api import sync_playwright

    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False
    logger.debug("browser_extract: playwright not installed — browser extraction disabled")


# ---------------------------------------------------------------------------
# JS extraction script (injected into the rendered page)
# ---------------------------------------------------------------------------

_EXTRACT_SCRIPT = r"""
() => {
  const PROPS = [
    'fontSize','fontWeight','fontFamily','lineHeight','letterSpacing','color',
    'textTransform','textDecoration','backgroundColor','background',
    'padding','paddingTop','paddingRight','paddingBottom','paddingLeft',
    'margin','marginTop','marginRight','marginBottom','marginLeft',
    'width','height','maxWidth','minWidth','maxHeight','minHeight',
    'display','flexDirection','justifyContent','alignItems','gap',
    'gridTemplateColumns','gridTemplateRows',
    'borderRadius','border','borderTop','borderBottom','borderLeft','borderRight',
    'boxShadow','overflow','overflowX','overflowY',
    'position','top','right','bottom','left','zIndex',
    'opacity','transform','transition','cursor',
    'objectFit','objectPosition',
    'whiteSpace','textOverflow'
  ];
  const SKIP = new Set(['none','normal','auto','0px','rgba(0, 0, 0, 0)','transparent','matrix(1, 0, 0, 1, 0, 0)']);

  function extract(el) {
    const cs = getComputedStyle(el);
    const s = {};
    for (const p of PROPS) {
      const v = cs[p];
      if (v && !SKIP.has(v)) s[p] = v;
    }
    return s;
  }

  function walk(el, depth) {
    if (depth > 5) return null;
    const kids = [...el.children];
    const tag = el.tagName.toLowerCase();
    const text = (kids.length === 0 || (kids.length === 1 && kids[0].nodeType === 3))
      ? (el.textContent || '').trim().slice(0, 300) : null;
    return {
      tag,
      cls: (el.className || '').toString().split(' ').slice(0, 8).join(' '),
      text,
      styles: extract(el),
      img: tag === 'img' ? { src: el.src, alt: el.alt } : null,
      kids: kids.slice(0, 25).map(c => walk(c, depth + 1)).filter(Boolean)
    };
  }

  // Global page-level info
  const fonts = [...new Set(
    [...document.querySelectorAll('*')].slice(0, 300)
      .map(e => getComputedStyle(e).fontFamily)
  )].slice(0, 10);

  const root = document.documentElement;
  const rootStyles = extract(root);
  const bodyStyles = extract(document.body);

  // Collect CSS custom properties from :root / html / body
  const cssVars = {};
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        if (rule.selectorText === ':root' || rule.selectorText === 'html' || rule.selectorText === 'body') {
          for (let i = 0; i < rule.style.length; i++) {
            const prop = rule.style[i];
            if (prop.startsWith('--')) cssVars[prop] = rule.style.getPropertyValue(prop).trim();
          }
        }
      }
    } catch(e) { /* cross-origin sheet */ }
  }

  // Fallback: extract computed variables from root, body, and top-level container elements
  const collectFromEl = (el) => {
    if (!el) return;
    const style = getComputedStyle(el);
    for (let i = 0; i < style.length; i++) {
      const prop = style[i];
      if (prop.startsWith('--')) {
        cssVars[prop] = style.getPropertyValue(prop).trim();
      }
    }
  };
  collectFromEl(document.documentElement);
  collectFromEl(document.body);
  const containers = document.querySelectorAll('body > *, body > * > *');
  for (let i = 0; i < containers.length; i++) {
    collectFromEl(containers[i]);
  }

  return {
    title: document.title,
    url: location.href,
    fonts,
    cssVars,
    rootStyles,
    bodyStyles,
    dom: walk(document.body, 0)
  };
}
"""

_SCREENSHOT_SCRIPT = r"""
async () => {
  // Wait a bit for any lazy-loaded content
  await new Promise(r => setTimeout(r, 500));
  return document.documentElement.scrollHeight;
}
"""


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def _extract_with_playwright(
    url: str,
    *,
    timeout_sec: float = 25.0,
    viewport_width: int = 1440,
    viewport_height: int = 900,
) -> dict[str, Any]:
    """Launch headless Chromium, navigate to *url*, and extract computed styles + screenshot."""
    result: dict[str, Any] = {
        "available": False,
        "computed_styles": {},
        "screenshot_data_url": "",
        "error": "",
    }

    if not _PW_AVAILABLE:
        result["error"] = "playwright not installed"
        return result

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu"],
            )
            page = browser.new_page(
                viewport={"width": viewport_width, "height": viewport_height},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ClutchDesign/1.0",
            )

            resp = page.goto(url, wait_until="networkidle", timeout=int(timeout_sec * 1000))
            if resp and resp.status >= 400:
                result["error"] = f"HTTP {resp.status}"
                browser.close()
                return result

            # Extra wait for JS rendering
            page.wait_for_timeout(1500)

            # Scroll to trigger lazy loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            page.wait_for_timeout(500)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)

            # Extract computed styles
            computed = page.evaluate(_EXTRACT_SCRIPT)
            result["computed_styles"] = computed or {}

            # Take full-page screenshot
            scroll_h = page.evaluate(_SCREENSHOT_SCRIPT) or viewport_height
            screenshot_bytes = page.screenshot(
                full_page=True,
                type="png",
            )
            b64 = base64.b64encode(screenshot_bytes).decode("ascii")
            result["screenshot_data_url"] = f"data:image/png;base64,{b64}"
            result["available"] = True

            browser.close()

    except Exception as exc:
        logger.warning("browser_extract: failed url=%s err=%s", url, exc)
        result["error"] = str(exc)

    return result


# ---------------------------------------------------------------------------
# Prompt fragment builders
# ---------------------------------------------------------------------------

def _styles_to_prompt_fragment(computed: dict[str, Any]) -> str:
    """Convert extracted computed styles into a text prompt fragment for LLMs."""
    if not computed:
        return ""

    lines: list[str] = ["[Browser-Rendered Design Tokens]"]

    # Page info
    title = computed.get("title", "")
    if title:
        lines.append(f"Page title: {title}")

    # CSS custom properties (design tokens)
    css_vars = computed.get("cssVars") or {}
    if css_vars:
        # Prioritize variables that look like brand colors or theme values,
        # and exclude standard Tailwind utility variables.
        def is_brand_var(k: str) -> bool:
            k_lower = k.lower()
            # Exclude standard utility prefixes
            for prefix in ('--tw-', '--font-', '--leading-', '--container-', '--animate-', '--blur-', '--tracking-', '--radius-', '--ease-', '--text-'):
                if k_lower.startswith(prefix):
                    return False
            return True

        filtered_vars = {k: v for k, v in css_vars.items() if is_brand_var(k)}
        # Fallback to unfiltered if nothing left
        if not filtered_vars:
            filtered_vars = css_vars

        var_strs = [f"{k}: {v}" for k, v in list(filtered_vars.items())[:35]]
        lines.append(f"CSS custom properties (design tokens): {'; '.join(var_strs)}")

    # Fonts
    fonts = computed.get("fonts") or []
    if fonts:
        lines.append(f"Font families used on page: {', '.join(fonts)}")

    # Root & body styles
    for label, key in [("Root (<html>)", "rootStyles"), ("Body", "bodyStyles")]:
        styles = computed.get(key) or {}
        if styles:
            parts = [f"{k}: {v}" for k, v in list(styles.items())[:12]]
            lines.append(f"{label} computed styles: {'; '.join(parts)}")

    # DOM tree summary (top-level structure)
    dom = computed.get("dom") or {}
    if dom:
        sections = _summarize_dom(dom, depth=0, max_depth=3)
        if sections:
            lines.append("Page structure (computed):")
            lines.extend(sections)

    if len(lines) > 1:
        lines.append(
            "\nIMPORTANT: These are the ACTUAL computed styles from the rendered page. "
            "Use these exact values (colors, fonts, spacing, layout) in your design spec. "
            "Do NOT invent or substitute — the spec must match the source website."
        )

    return "\n".join(lines)


def _summarize_dom(node: dict, *, depth: int, max_depth: int) -> list[str]:
    """Recursively summarize DOM nodes into indented text lines."""
    if depth > max_depth or not node:
        return []

    lines: list[str] = []
    tag = node.get("tag", "?")
    cls = node.get("cls", "")
    text = node.get("text")
    styles = node.get("styles") or {}

    # Build a concise description
    desc_parts = [f"{'  ' * depth}<{tag}>"]
    if cls:
        desc_parts.append(f".{cls.split()[0]}")

    # Extract key visual properties
    visual = []
    for prop in ("color", "backgroundColor", "fontSize", "fontWeight", "fontFamily",
                 "padding", "margin", "display", "flexDirection", "gap",
                 "borderRadius", "boxShadow", "maxWidth", "width"):
        v = styles.get(prop)
        if v:
            visual.append(f"{prop}={v}")

    if visual:
        desc_parts.append(f"  [{', '.join(visual[:6])}]")

    if text and len(text) < 80:
        desc_parts.append(f'  "{text}"')

    lines.append("".join(desc_parts))

    # Recurse into children
    for child in node.get("kids", []):
        lines.extend(_summarize_dom(child, depth=depth + 1, max_depth=max_depth))

    return lines[:100]  # cap output size


def computed_styles_prompt_fragment(computed: dict[str, Any]) -> str:
    """Public API: return a ready-to-inject prompt string from browser-extracted styles."""
    return _styles_to_prompt_fragment(computed)


def screenshot_data_url(result: dict[str, Any]) -> str:
    """Public API: extract the screenshot data URL from extraction result."""
    return result.get("screenshot_data_url", "")


# ---------------------------------------------------------------------------
# Main entry point (called from generator.py)
# ---------------------------------------------------------------------------

def extract_website_tokens(
    url: str,
    *,
    timeout_sec: float = 25.0,
) -> dict[str, Any]:
    """High-level extraction: returns dict with computed_styles, screenshot, prompt fragment."""
    result = _extract_with_playwright(url, timeout_sec=timeout_sec)

    prompt_fragment = ""
    if result["available"] and result["computed_styles"]:
        prompt_fragment = computed_styles_prompt_fragment(result["computed_styles"])

    return {
        "available": result["available"],
        "computed_styles": result["computed_styles"],
        "screenshot_data_url": result["screenshot_data_url"],
        "prompt_fragment": prompt_fragment,
        "error": result["error"],
    }
