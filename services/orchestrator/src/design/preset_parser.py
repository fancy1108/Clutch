"""Extract spec JSON from DESIGN.md files (YAML frontmatter or structured markdown)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def parse_yaml_frontmatter(text: str) -> dict[str, Any] | None:
    """Parse YAML frontmatter between --- markers using pyyaml."""
    import yaml as _yaml
    m = re.match(r"^---\s*\n(.*?)\n(?:---|\.\.\.)", text, re.DOTALL)
    if not m:
        m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    raw = m.group(1)
    try:
        data = _yaml.safe_load(raw)
        if isinstance(data, dict):
            return data
    except _yaml.YAMLError:
        pass
    # Fallback: quote description field which may contain unescaped colons
    fixed = _fix_yaml_colons(raw)
    if fixed:
        try:
            data = _yaml.safe_load(fixed)
            if isinstance(data, dict):
                return data
        except _yaml.YAMLError:
            pass
    return None


def _fix_yaml_colons(raw: str) -> str | None:
    """If YAML has unquoted colons in description, wrap description value in quotes."""
    lines = raw.split("\n")
    desc_line_idx = None
    desc_val_started = False
    desc_lines: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if stripped.startswith("description:"):
            desc_line_idx = i
            after = stripped[len("description:"):].strip()
            if not after:
                # Multi-line description starts
                desc_val_started = True
                desc_lines = [""]
                continue
            # Single-line description
            if not (after.startswith('"') and after.endswith('"')):
                lines[i] = f'description: "{after}"'
            break
        if desc_val_started:
            # Check if this line starts a new top-level key (no indent)
            if stripped and not stripped[0].isspace():
                desc_val_started = False
                # Wrap the collected description in quotes
                body = "\n".join(desc_lines).strip()
                lines[desc_line_idx] = f'description: "{body}"'
                break
            desc_lines.append(stripped)
    return "\n".join(lines)


def _yaml_colors_to_spec(color_dict: dict[str, str]) -> dict[str, list[str]]:
    """Map named YAML colors to spec role-based structure."""
    colors: dict[str, list[str]] = {
        "primary": [], "secondary": [], "neutral": [], "accent": [], "status": [],
    }
    for name, hex_val in color_dict.items():
        hl = hex_val.lower()
        n = name.lower().replace("_", "-").replace(" ", "-")
        if n == "primary" or n == "brand":
            colors["primary"].insert(0, hl)
        elif "primary" in n and n != "primary":
            colors["primary"].append(hl)
        elif n in ("success", "error", "warning", "danger", "negative"):
            colors["status"].append(hl)
        elif "accent" in n:
            colors["accent"].append(hl)
        elif n in ("secondary",):
            colors["secondary"].insert(0, hl)
        elif "secondary" in n:
            colors["secondary"].append(hl)
        elif "canvas" in n or "surface" in n or n in ("white", "black", "neutral"):
            colors["neutral"].append(hl)
        elif n in ("ink", "body", "text", "muted") or "ink" in n or "body" in n:
            colors["neutral"].append(hl)
        elif "hairline" in n or "border" in n:
            colors["neutral"].append(hl)
        elif "on-" in n:
            colors["neutral"].append(hl)
        else:
            colors["neutral"].append(hl)

    # Only add defaults if no colors were found at all
    all_empty = all(not v for v in colors.values())
    if all_empty:
        colors["primary"] = ["#000000"]
        colors["neutral"] = ["#ffffff", "#000000"]
    return colors


def _yaml_typography_to_spec(type_dict: dict[str, Any]) -> dict[str, Any]:
    """Extract font families and hierarchy samples from YAML typography."""
    font_families: list[str] = []
    samples: list[dict[str, str]] = []
    mono_family = "ui-monospace, monospace"

    for token_name, token in type_dict.items():
        if not isinstance(token, dict):
            continue
        ff = token.get("fontFamily", "")
        if ff and ff not in font_families:
            font_families.append(ff)
        if "mono" in ff.lower() or "jetbrains" in ff.lower() or "fira" in ff.lower():
            mono_family = ff
        fs = token.get("fontSize", 16)
        samples.append({
            "label": _friendly_token_name(token_name),
            "size": f"{fs}px" if isinstance(fs, (int, float)) else str(fs),
            "weight": str(token.get("fontWeight", 400)),
        })

    rank_map = {"display": 0, "hero": 1, "headline": 2, "title": 2, "lead": 3, "body": 4, "caption": 5, "button": 6, "code": 7}
    samples.sort(key=lambda s: (
        rank_map.get(s["label"].split(" ")[0].lower().rstrip("-0123456789"), 99),
        s["label"],
    ))

    return {
        "fontFamily": font_families[0] if font_families else "system-ui, sans-serif",
        "monoFamily": mono_family,
        "samples": samples[:6],
    }


def _friendly_token_name(key: str) -> str:
    return key.replace("-", " ").replace("_", " ").title()


def _yaml_components_to_spec(comp_dict: dict[str, Any]) -> list[str]:
    if not comp_dict:
        return []
    names: list[str] = []
    for name in comp_dict:
        display = _friendly_token_name(name)
        if display not in names:
            names.append(display)
    return names[:15]


def _yaml_radius_to_spec(rounded: dict[str, str]) -> dict[str, str]:
    level_map = {
        "sm": ("xxs", "xs", "sm"),
        "md": ("sm", "md"),
        "lg": ("md", "lg", "xl"),
        "xl": ("lg", "xl", "2xl", "xxl"),
    }
    result: dict[str, str] = {}
    for level, candidates in level_map.items():
        for c in candidates:
            if c in rounded:
                result[level] = rounded[c]
                break
        if level not in result:
            result[level] = {"sm": "6px", "md": "12px", "lg": "16px", "xl": "24px"}[level]
    return result


def yaml_to_spec(preset_id: str, yaml: dict[str, Any]) -> dict[str, Any]:
    """Convert parsed YAML frontmatter to spec JSON."""
    desc = yaml.get("description", "")
    name_str = yaml.get("name", preset_id)
    colors = _yaml_colors_to_spec(yaml.get("colors", {}))
    typography = _yaml_typography_to_spec(yaml.get("typography", {}))
    rounded = _yaml_radius_to_spec(yaml.get("rounded", {}))
    components = _yaml_components_to_spec(yaml.get("components", {}))

    return {
        "name": _friendly_name(preset_id),
        "rationale": desc[:200] if desc else f"Design system for {_friendly_name(preset_id)}",
        "brand": {
            "name": _friendly_name(preset_id),
            "voice": _infer_brand_voice(desc),
        },
        "visual_style": desc[:500] if desc else "Clean, modern design system",
        "layout_system": "12-column responsive grid",
        "layout_pattern": "marketing",
        "grid": {"columns": 12, "gutter": "24px", "max_width": "1280px"},
        "colors": colors,
        "typography": typography,
        "radius": rounded,
        "shadow": {"card": "0 1px 3px rgba(0,0,0,0.08)", "elevated": "0 8px 24px rgba(0,0,0,0.12)"},
        "components": components,
        "motion": {"duration": "200ms", "easing": "cubic-bezier(0.4,0,0.2,1)", "hover_lift": "-2px"},
        "responsive": "Mobile-first; stack columns below md; hide sidebar behind menu on sm",
        "accessibility": "WCAG AA contrast; focus rings; semantic headings; aria-labels",
    }


def _friendly_name(preset_id: str) -> str:
    """Convert preset slug to display name."""
    from src.design.builtin_presets import resolve_preset_meta
    meta = resolve_preset_meta(preset_id)
    if meta:
        return meta["name"]
    return preset_id.replace(".", " ").title().strip()


def _infer_brand_voice(desc: str) -> str:
    words = desc.lower()
    if "luxury" in words or "premium" in words:
        return "Premium, sophisticated, aspirational"
    if "dark" in words or "monochrome" in words:
        return "Bold, minimal, technical"
    if "warm" in words or "friendly" in words or "playful" in words:
        return "Warm, approachable, human"
    if "editorial" in words or "magazine" in words:
        return "Editorial, authoritative, refined"
    if "cinematic" in words or "immersive" in words:
        return "Cinematic, immersive, dramatic"
    if "developer" in words or "technical" in words or "code" in words:
        return "Technical, precise, developer-oriented"
    return "Professional, modern, trustworthy"


# ── Markdown (non-YAML) extraction ──────────────────────────────────


def _markdown_extract_name(text: str) -> str:
    m = re.search(r"^# (.+)", text, re.MULTILINE)
    if m:
        raw = m.group(1)
        raw = re.sub(r"^Design System Inspired by ", "", raw, flags=re.IGNORECASE).strip()
        return raw
    return "Design System"


def _section_of(text: str, pos: int) -> str:
    """Find the nearest section heading before position pos."""
    before = text[:pos]
    headings = list(re.finditer(r"^#{1,4}\s+(.+)$", before, re.MULTILINE))
    if headings:
        return headings[-1].group(1).strip().lower()
    return ""


def _markdown_extract_colors(text: str) -> dict[str, list[str]]:
    """Extract hex colors with role names from markdown."""
    colors: dict[str, list[str]] = {
        "primary": [], "secondary": [], "neutral": [], "accent": [], "status": [],
    }
    seen: set[str] = set()

    # Pattern: **Name** (`#hex`) or **Name** (#hex) 
    for m in re.finditer(r"\*\*([^*]+)\*\*\s*[`(]+(#[0-9a-fA-F]{3,8})[`)]*", text):
        name = m.group(1).strip().lower()
        hex_val = m.group(2).lower()
        if hex_val in seen:
            continue
        seen.add(hex_val)
        section = _section_of(text, m.start())
        _assign_color(name, hex_val, colors, section)

    # Also find bare hex codes like `#hex` after a label
    for m in re.finditer(r"([a-z\s-]+?)\s*[`(]+(#[0-9a-fA-F]{3,8})[`)]+", text):
        name = m.group(1).strip().lower()
        hex_val = m.group(2).lower()
        if len(name) <= 2 or hex_val in seen:
            continue
        seen.add(hex_val)
        section = _section_of(text, m.start())
        _assign_color(name, hex_val, colors, section)

    # Only add defaults if no colors were found at all
    all_empty = all(not v for v in colors.values())
    if all_empty:
        colors["primary"] = ["#000000"]
        colors["neutral"] = ["#ffffff", "#000000"]
    return colors


_BRAND_COLORS = {"green", "blue", "red", "purple", "orange", "yellow", "pink", "teal", "coral", "indigo", "violet", "amber", "emerald", "rose", "lime"}


def _assign_color(name: str, hex_val: str, colors: dict[str, list[str]], section: str = ""):
    n = name.replace(" ", "-").replace("_", "-")

    # Section-based assignment (more specific matches first)
    if "primary" in section or "brand" in section:
        colors["primary"].append(hex_val)
        return
    # Handle "Secondary & Accent" section - assign to accent
    if "secondary" in section and "accent" in section:
        colors["accent"].append(hex_val)
        return
    if "accent" in section:
        colors["accent"].append(hex_val)
        return
    if "semantic" in section or "status" in section or "error" in section:
        colors["status"].append(hex_val)
        return
    if "surface" in section or "background" in section:
        colors["neutral"].append(hex_val)
        return
    if "neutral" in section or "text" in section:
        colors["neutral"].append(hex_val)
        return
    if "border" in section or "hairline" in section:
        colors["neutral"].append(hex_val)
        return
    if "shadow" in section:
        colors["neutral"].append(hex_val)
        return

    # Name-based assignment
    if n in ("primary", "brand"):
        colors["primary"].insert(0, hex_val)
    elif "primary" in n:
        colors["primary"].append(hex_val)
    elif n == "secondary":
        colors["secondary"].insert(0, hex_val)
    elif "secondary" in n:
        colors["secondary"].append(hex_val)
    elif "accent" in n:
        colors["accent"].append(hex_val)
    elif n in ("success", "error", "warning", "danger", "negative"):
        colors["status"].append(hex_val)
    elif "canvas" in n or "surface" in n or n in ("white", "black", "neutral", "separator"):
        colors["neutral"].append(hex_val)
    elif n in ("ink", "body", "text", "muted") or "ink" in n or "body" in n:
        colors["neutral"].append(hex_val)
    elif "hairline" in n or "border" in n:
        colors["neutral"].append(hex_val)
    elif "shadow" in n:
        colors["neutral"].append(hex_val)
    else:
        # Brand-named colors like "spotify green", "airbnb rausch" → promote to primary
        for kw in _BRAND_COLORS:
            if kw in n:
                colors["primary"].append(hex_val)
                return
        colors["neutral"].append(hex_val)


def _markdown_extract_typography(text: str) -> dict[str, Any]:
    """Extract typography from markdown tables and font listings."""
    font_families: list[str] = []
    mono_family = "ui-monospace, monospace"
    samples: list[dict[str, str]] = []

    # Look for font family mentions in bold markers or plain text
    for m in re.finditer(r"\*\*(?:Font[^:]*|Font[^:]*family)[^:]*:\*\*\s*(.+?)(?:\n|$)", text):
        ff = re.sub(r"[`*\"'']", "", m.group(1).strip())
        if ff and ff not in font_families:
            font_families.append(ff)

    for m in re.finditer(r"(?:Font[^:]*|Font family)[^:]*:\s*(.+?)(?:\n|$)", text):
        ff = re.sub(r"[`*\"'']", "", m.group(1).strip())
        if ff and ff not in font_families:
            font_families.append(ff)

    # Look for tables with size/weight info
    lines = text.split("\n")
    in_table = False
    for i, line in enumerate(lines):
        if "|" in line and "---" not in line and i > 0 and "---" in lines[i - 1] if i > 0 else False:
            in_table = True
        if in_table and "|" in line and "---" not in line:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) >= 3:
                label = cells[0]
                size = cells[1]
                weight = cells[2] if len(cells) > 2 else "400"
                samples.append({
                    "label": label,
                    "size": size,
                    "weight": weight,
                })
            elif len(cells) >= 2:
                samples.append({
                    "label": cells[0],
                    "size": cells[1],
                    "weight": "400",
                })

    for m in re.finditer(r"\*\*(JetBrains|Fira|mono)[^*]*\*\*", text, re.IGNORECASE):
        mono_family = "JetBrains Mono, ui-monospace, monospace"

    return {
        "fontFamily": font_families[0] if font_families else "system-ui, sans-serif",
        "monoFamily": mono_family,
        "samples": samples[:6] if samples else [
            {"label": "Display", "size": "32px", "weight": "700"},
            {"label": "Title", "size": "20px", "weight": "600"},
            {"label": "Body", "size": "14px", "weight": "400"},
        ],
    }


def _markdown_extract_components(text: str) -> list[str]:
    """Extract component names from markdown headings."""
    components: list[str] = []
    for m in re.finditer(r"^#{3,4}\s+(.+)$", text, re.MULTILINE):
        name = m.group(1).strip()
        if not name or len(name) > 40:
            continue
        skip = {"overview", "key characteristics", "do's and don'ts", "responsive", "accessibility",
                "primary brand", "text", "surface & border", "shadows", "semantic", "colors",
                "typography", "hierarchy", "layout", "grid", "spacing", "elevation", "depth",
                "shapes", "principles"}
        if name.lower() in skip:
            continue
        components.append(name)
    return components[:15]


def _markdown_extract_radius(text: str) -> dict[str, str]:
    """Extract border radius from markdown."""
    radius: dict[str, str] = {}
    # Look for patterns like "8px radius", "rounded: 8px", "border-radius: 8px"
    vals = re.findall(r"(?:radius|rounded)[\s:]*(?:is\s*)?(\d+)px", text, re.IGNORECASE)
    if vals:
        nums = sorted(int(v) for v in vals)
        radius["sm"] = f"{nums[0]}px" if nums else "6px"
        radius["md"] = f"{nums[len(nums)//2]}px" if len(nums) > 2 else "12px"
        radius["lg"] = f"{nums[-1]}px" if nums else "16px"
        radius["xl"] = f"{min(nums[-1]*2, 32)}px" if nums else "24px"
    else:
        radius = {"sm": "6px", "md": "12px", "lg": "16px", "xl": "24px"}
    return radius


def markdown_to_spec(preset_id: str, text: str) -> dict[str, Any]:
    """Extract spec JSON from structured markdown (no YAML frontmatter)."""
    name = _markdown_extract_name(text)
    colors = _markdown_extract_colors(text)
    typography = _markdown_extract_typography(text)
    radius = _markdown_extract_radius(text)
    components = _markdown_extract_components(text)

    return {
        "name": _friendly_name(preset_id),
        "rationale": f"Design system for {_friendly_name(preset_id)}",
        "brand": {
            "name": _friendly_name(preset_id),
            "voice": _infer_brand_voice(text[:300]),
        },
        "visual_style": (re.sub(r"\s+", " ", text.split("\n\n")[1] if "\n\n" in text else ""))[:500] or "Clean design system",
        "layout_system": "12-column responsive grid",
        "layout_pattern": "marketing",
        "grid": {"columns": 12, "gutter": "24px", "max_width": "1280px"},
        "colors": colors,
        "typography": typography,
        "radius": radius,
        "shadow": {"card": "0 1px 3px rgba(0,0,0,0.08)", "elevated": "0 8px 24px rgba(0,0,0,0.12)"},
        "components": components,
        "motion": {"duration": "200ms", "easing": "cubic-bezier(0.4,0,0.2,1)", "hover_lift": "-2px"},
        "responsive": "Mobile-first; stack columns below md; hide sidebar behind menu on sm",
        "accessibility": "WCAG AA contrast; focus rings; semantic headings; aria-labels",
    }


# ── Entry point ─────────────────────────────────────────────────────


def preset_to_spec(preset_id: str) -> dict[str, Any]:
    """Load DESIGN.md and extract spec JSON."""
    from src.design.builtin_presets import resolve_preset_design_md

    text = resolve_preset_design_md(preset_id)
    if not text:
        raise ValueError(f"No DESIGN.md found for {preset_id}")

    yaml = parse_yaml_frontmatter(text)
    if yaml and yaml.get("colors"):
        return yaml_to_spec(preset_id, yaml)
    return markdown_to_spec(preset_id, text)


def extract_brand_color(spec: dict[str, Any]) -> str | None:
    """Extract best brand swatch color from spec, avoiding invisible ones."""
    colors = spec.get("colors", {})
    for key in ("primary", "accent", "secondary"):
        vals = colors.get(key, [])
        for v in vals:
            if v and v.lower() not in ("#000000", "#ffffff", "#fff", "#000"):
                return v
    for key in ("primary", "accent", "secondary"):
        vals = colors.get(key, [])
        if vals and vals[0]:
            return vals[0]
    return None


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    for pid in ("apple", "linear.app", "spotify", "starbucks"):
        spec = preset_to_spec(pid)
        color = extract_brand_color(spec)
        print(f"{pid}: color={color}, typography_font={spec['typography']['fontFamily'][:40]}, components={len(spec['components'])}")
