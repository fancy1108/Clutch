"""Built-in design system presets for Design mode (no user style reference)."""

from __future__ import annotations

from typing import Any

from src.design.layout_patterns import detect_layout_pattern, enrich_fallback_spec, layout_wrapper_hint

BUILTIN_PRESET_IDS: tuple[str, ...] = ("clutch",)

_CLUTCH_SPEC_BASE: dict[str, Any] = {
    "name": "Clutch",
    "rationale": "Clutch product design language — precise, calm, developer-tool aesthetic.",
    "brand": {
        "name": "Clutch",
        "voice": "Precise, calm, trustworthy; supervision console over marketing fluff",
    },
    "visual_style": (
        "Clean light theme with high contrast. White and soft gray surfaces (#ffffff, #f9f9f9, #f7f7f7), "
        "subtle borders (neutral-200), restrained shadows (shadow-sm). Rounded-2xl cards. "
        "Avoid garish gradients and default dark panels."
    ),
    "grid": {"columns": 12, "gutter": "24px", "max_width": "1280px"},
    "colors": {
        "primary": ["#171717", "#404040", "#737373"],
        "secondary": ["#0f172a", "#334155", "#64748b"],
        "neutral": ["#ffffff", "#f9f9f9", "#f7f7f7", "#e5e5e5", "#171717"],
        "accent": ["#10b981", "#d1fae5"],
        "status": ["#16a34a", "#dc2626", "#ca8a04"],
    },
    "typography": {
        "fontFamily": "Hanken Grotesk, system-ui, -apple-system, sans-serif",
        "monoFamily": "JetBrains Mono, ui-monospace, monospace",
        "samples": [
            {"label": "Display", "size": "24px", "weight": "700"},
            {"label": "Title", "size": "14px", "weight": "600"},
            {"label": "Body", "size": "13px", "weight": "400"},
            {"label": "Caption", "size": "11px", "weight": "500"},
        ],
    },
    "radius": {"sm": "8px", "md": "12px", "lg": "16px", "xl": "20px"},
    "shadow": {
        "card": "0 1px 3px rgba(15,23,42,0.08)",
        "elevated": "0 8px 24px rgba(15,23,42,0.10)",
    },
    "motion": {
        "duration": "200ms",
        "easing": "cubic-bezier(0.4,0,0.2,1)",
        "hover_lift": "-1px",
    },
    "responsive": (
        "Mobile-first; stack columns below md; hide dense sidebars behind menu on sm; "
        "min 44px touch targets on app device."
    ),
    "accessibility": (
        "WCAG AA contrast; visible focus rings on interactive elements; semantic headings; "
        "aria-labels on icon-only buttons."
    ),
    "components": [
        "Top navigation",
        "Surface card",
        "Primary button",
        "Secondary button",
        "Input field",
        "Status badge",
        "Data table",
    ],
}

_CLUTCH_DESIGN_MD = """# DESIGN.md — Clutch

# Brand

- **Name**: Clutch
- **Voice**: Precise, calm, trustworthy; supervision console over marketing fluff

# Visual Style

Clean light theme with high contrast. White and soft gray surfaces, subtle borders, restrained shadows.
Rounded-2xl cards. Avoid garish gradients and unsolicited dark mode.

# Layout System

12-column grid, generous whitespace, clear hierarchy. Page layout follows the user brief (ecommerce, dashboard, etc.)
while keeping Clutch surface tokens and typography.

# Grid

- **Columns**: 12
- **Gutter**: 24px
- **Max width**: 1280px

# Typography

- **Font family**: Hanken Grotesk, system-ui, -apple-system, sans-serif
- **Mono**: JetBrains Mono, ui-monospace, monospace
- **Display**: 24px / weight 700
- **Title**: 14px / weight 600
- **Body**: 13px / weight 400
- **Caption**: 11px / weight 500

# Color Tokens

- **primary**: #171717, #404040, #737373
- **secondary**: #0f172a, #334155, #64748b
- **neutral**: #ffffff, #f9f9f9, #f7f7f7, #e5e5e5, #171717
- **accent**: #10b981, #d1fae5
- **status**: #16a34a, #dc2626, #ca8a04

# Radius

- **sm**: 8px
- **md**: 12px
- **lg**: 16px
- **xl**: 20px

# Shadow

- **card**: 0 1px 3px rgba(15,23,42,0.08)
- **elevated**: 0 8px 24px rgba(15,23,42,0.10)

# Components

- Top navigation
- Surface card
- Primary button (bg-neutral-900 hover:bg-black text-white)
- Secondary button (border neutral-200, hover surface)
- Input field (neutral fill, subtle border)
- Status badge (emerald / rose semantic tints)
- Data table (mono numerics optional)

# Motion

- **duration**: 200ms
- **easing**: cubic-bezier(0.4,0,0.2,1)
- **hover_lift**: -1px

# Responsive Rules

Mobile-first; stack below md; 44px min touch targets on app.

# Accessibility Rules

WCAG AA contrast; focus rings; semantic headings; aria-labels on icon buttons.
"""


def normalize_preset_id(preset_id: str | None) -> str:
    raw = (preset_id or "clutch").strip().lower()
    return raw if raw in BUILTIN_PRESET_IDS else "clutch"


def list_builtin_presets() -> list[dict[str, str]]:
    return [
        {
            "id": "clutch",
            "name": "Clutch",
            "description": "Built-in Clutch design system — clean developer-tool aesthetic",
        }
    ]


def clutch_spec_for_prompt(prompt: str, *, device: str = "web") -> dict[str, Any]:
    """Return Clutch spec with layout pattern inferred from the user brief."""
    pattern = detect_layout_pattern(prompt, device=device)
    base = dict(_CLUTCH_SPEC_BASE)
    base["layout_system"] = layout_wrapper_hint(pattern)
    base["components"] = list(_CLUTCH_SPEC_BASE["components"])
    return enrich_fallback_spec(base, prompt, pattern)


def clutch_design_md_text() -> str:
    return _CLUTCH_DESIGN_MD


def resolve_builtin_spec(preset_id: str, prompt: str, *, device: str = "web") -> tuple[dict[str, Any], str]:
    """Structured spec + DESIGN.md for a built-in preset."""
    pid = normalize_preset_id(preset_id)
    if pid == "clutch":
        return clutch_spec_for_prompt(prompt, device=device), clutch_design_md_text()
    return clutch_spec_for_prompt(prompt, device=device), clutch_design_md_text()
