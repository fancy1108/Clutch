"""Built-in design system presets for Design mode (no user style reference)."""

from __future__ import annotations

from typing import Any

from src.design.layout_patterns import detect_layout_pattern, enrich_fallback_spec, layout_wrapper_hint

_BUILTIN_PRESET_META: tuple[dict[str, str], ...] = (
    {"id": "clutch", "name": "Clutch", "description": "Built-in Clutch design system — clean developer-tool aesthetic"},
    {"id": "airbnb", "name": "Airbnb", "description": "Travel marketplace. Warm coral accent, photography-driven, rounded UI"},
    {"id": "airtable", "name": "Airtable", "description": "Spreadsheet-database hybrid. Colorful, friendly, structured data aesthetic"},
    {"id": "apple", "name": "Apple", "description": "Consumer electronics. Premium white space, SF Pro, cinematic imagery"},
    {"id": "binance", "name": "Binance", "description": "Crypto exchange. Bold Binance Yellow on monochrome, trading-floor urgency"},
    {"id": "bmw", "name": "BMW", "description": "Luxury automotive. Dark premium surfaces, precise German engineering aesthetic"},
    {"id": "bmw-m", "name": "BMW M", "description": "Performance automotive. Motorsport-inspired contrast, M color accents, precision-driven layout"},
    {"id": "bugatti", "name": "Bugatti", "description": "Luxury hypercar. Cinema-black canvas, monochrome austerity, monumental display type"},
    {"id": "cal", "name": "Cal.com", "description": "Open-source scheduling. Clean neutral UI, developer-oriented simplicity"},
    {"id": "claude", "name": "Claude", "description": "Anthropic's AI assistant. Warm terracotta accent, clean editorial layout"},
    {"id": "clay", "name": "Clay", "description": "Creative agency. Organic shapes, soft gradients, art-directed layout"},
    {"id": "clickhouse", "name": "ClickHouse", "description": "Fast analytics database. Yellow-accented, technical documentation style"},
    {"id": "cohere", "name": "Cohere", "description": "Enterprise AI platform. Vibrant gradients, data-rich dashboard aesthetic"},
    {"id": "coinbase", "name": "Coinbase", "description": "Crypto exchange. Clean blue identity, trust-focused, institutional feel"},
    {"id": "composio", "name": "Composio", "description": "Tool integration platform. Modern dark with colorful integration icons"},
    {"id": "cursor", "name": "Cursor", "description": "AI-first code editor. Sleek dark interface, gradient accents"},
    {"id": "dell-1996", "name": "Dell (1996)", "description": "Catalog-era enterprise web. Literal black page frame, flat color-block ribbon cards, chunky Helvetica-Black titles over Times Roman body"},
    {"id": "elevenlabs", "name": "ElevenLabs", "description": "AI voice platform. Dark cinematic UI, audio-waveform aesthetics"},
    {"id": "expo", "name": "Expo", "description": "React Native platform. Dark theme, tight letter-spacing, code-centric"},
    {"id": "ferrari", "name": "Ferrari", "description": "Luxury automotive. Chiaroscuro black-white editorial, Ferrari Red with extreme sparseness"},
    {"id": "figma", "name": "Figma", "description": "Collaborative design tool. Vibrant multi-color, playful yet professional"},
    {"id": "framer", "name": "Framer", "description": "Website builder. Bold black and blue, motion-first, design-forward"},
    {"id": "hashicorp", "name": "HashiCorp", "description": "Infrastructure automation. Enterprise-clean, black and white"},
    {"id": "hp", "name": "HP", "description": "PC and printer maker. Pure white canvas, HP Electric Blue signal CTA, geometric Forma DJR Micro, blue chevron decorations"},
    {"id": "ibm", "name": "IBM", "description": "Enterprise technology. Carbon design system, structured blue palette"},
    {"id": "intercom", "name": "Intercom", "description": "Customer messaging. Friendly blue palette, conversational UI patterns"},
    {"id": "kraken", "name": "Kraken", "description": "Crypto trading platform. Purple-accented dark UI, data-dense dashboards"},
    {"id": "lamborghini", "name": "Lamborghini", "description": "Luxury automotive. True black cathedral, gold accent, LamboType custom Neo-Grotesk"},
    {"id": "linear.app", "name": "Linear", "description": "Project management for engineers. Ultra-minimal, precise, purple accent"},
    {"id": "lovable", "name": "Lovable", "description": "AI full-stack builder. Playful gradients, friendly dev aesthetic"},
    {"id": "mastercard", "name": "Mastercard", "description": "Global payments network. Warm cream canvas, orbital pill shapes, editorial warmth"},
    {"id": "meta", "name": "Meta", "description": "Tech retail store. Photography-first, binary light/dark surfaces, Meta Blue CTAs"},
    {"id": "minimax", "name": "Minimax", "description": "AI model provider. Bold dark interface with neon accents"},
    {"id": "mintlify", "name": "Mintlify", "description": "Documentation platform. Clean, green-accented, reading-optimized"},
    {"id": "miro", "name": "Miro", "description": "Visual collaboration. Bright yellow accent, infinite canvas aesthetic"},
    {"id": "mistral.ai", "name": "Mistral AI", "description": "Open-weight LLM provider. French-engineered minimalism, purple-toned"},
    {"id": "mongodb", "name": "MongoDB", "description": "Document database. Green leaf branding, developer documentation focus"},
    {"id": "nike", "name": "Nike", "description": "Athletic retail. Monochrome UI, massive uppercase Futura, full-bleed photography"},
    {"id": "nintendo-2001", "name": "Nintendo.com (2001)", "description": "Y2K console chrome web. Brushed-periwinkle beveled metal panels, halftone-dotted carbon nav glowing amber, outlined Arial-Black box-art wordmarks"},
    {"id": "notion", "name": "Notion", "description": "All-in-one workspace. Warm minimalism, serif headings, soft surfaces"},
    {"id": "nvidia", "name": "NVIDIA", "description": "GPU computing. Green-black energy, technical power aesthetic"},
    {"id": "ollama", "name": "Ollama", "description": "Run LLMs locally. Terminal-first, monochrome simplicity"},
    {"id": "opencode.ai", "name": "OpenCode AI", "description": "AI coding platform. Developer-centric dark theme"},
    {"id": "pinterest", "name": "Pinterest", "description": "Visual discovery platform. Red accent, masonry grid, image-first"},
    {"id": "playstation", "name": "PlayStation", "description": "Gaming console retail. Three-surface channel layout, cyan hover-scale interaction"},
    {"id": "posthog", "name": "PostHog", "description": "Product analytics. Playful hedgehog branding, developer-friendly dark UI"},
    {"id": "raycast", "name": "Raycast", "description": "Productivity launcher. Sleek dark chrome, vibrant gradient accents"},
    {"id": "renault", "name": "Renault", "description": "French automotive. Vivid aurora gradients, NouvelR proprietary typeface, zero-radius buttons"},
    {"id": "replicate", "name": "Replicate", "description": "Run ML models via API. Clean white canvas, code-forward"},
    {"id": "resend", "name": "Resend", "description": "Email API for developers. Minimal dark theme, monospace accents"},
    {"id": "revolut", "name": "Revolut", "description": "Digital banking. Sleek dark interface, gradient cards, fintech precision"},
    {"id": "runwayml", "name": "Runway", "description": "AI creative-tools platform with an editorial film-festival aesthetic — cinematic dark heroes, paper-white reading bands, single proprietary sans, and pure black pill CTAs"},
    {"id": "sanity", "name": "Sanity", "description": "Headless content platform with a dark-first editorial marketing surface — 112px display type, IBM Plex Mono technical eyebrows, and a single coral-red accent reserved for the highest-priority CTA"},
    {"id": "sentry", "name": "Sentry", "description": "Error monitoring. Dark dashboard, data-dense, pink-purple accent"},
    {"id": "shopify", "name": "Shopify", "description": "E-commerce platform. Dark-first cinematic, neon green accent, ultra-light display type"},
    {"id": "slack", "name": "Slack", "description": "Team communication platform. Vibrant multi-color sidebar, clean messaging UI"},
    {"id": "spacex", "name": "SpaceX", "description": "Space technology. Stark black and white, full-bleed imagery, futuristic"},
    {"id": "spotify", "name": "Spotify", "description": "Music streaming. Vibrant green on dark, bold type, album-art-driven"},
    {"id": "starbucks", "name": "Starbucks", "description": "Coffee retail flagship. Four-tier earth-green system, warm cream canvas, proprietary SoDoSans typography"},
    {"id": "stripe", "name": "Stripe", "description": "Payment infrastructure. Signature purple gradients, weight-300 elegance"},
    {"id": "supabase", "name": "Supabase", "description": "Open-source Firebase alternative. Dark emerald theme, code-first"},
    {"id": "superhuman", "name": "Superhuman", "description": "Fast email client. Premium dark UI, keyboard-first, purple glow"},
    {"id": "tesla", "name": "Tesla", "description": "Electric vehicles. Radical subtraction, cinematic full-viewport photography, Universal Sans"},
    {"id": "theverge", "name": "The Verge", "description": "Tech editorial media. Acid-mint and ultraviolet accents, Manuka display type"},
    {"id": "together.ai", "name": "Together AI", "description": "Open-source AI infrastructure. Technical, blueprint-style design"},
    {"id": "uber", "name": "Uber", "description": "Mobility platform. Bold black and white, tight type, urban energy"},
    {"id": "vercel", "name": "Vercel", "description": "Frontend deployment platform. Black and white precision, Geist font"},
    {"id": "vodafone", "name": "Vodafone", "description": "Global telecom brand. Monumental uppercase display, Vodafone Red chapter bands"},
    {"id": "voltagent", "name": "VoltAgent", "description": "AI agent framework. Void-black canvas, emerald accent, terminal-native"},
    {"id": "warp", "name": "Warp", "description": "Modern terminal. Dark IDE-like interface, block-based command UI"},
    {"id": "webflow", "name": "Webflow", "description": "Visual web builder. Blue-accented, polished marketing site aesthetic"},
    {"id": "wired", "name": "WIRED", "description": "Tech magazine. Paper-white broadsheet density, custom serif, ink-blue links"},
    {"id": "wise", "name": "Wise", "description": "International money transfer. Bright green accent, friendly and clear"},
    {"id": "x.ai", "name": "xAI", "description": "Elon Musk's AI lab. Stark monochrome, futuristic minimalism"},
    {"id": "zapier", "name": "Zapier", "description": "Automation platform. Warm orange, friendly illustration-driven"},
)

BUILTIN_PRESET_IDS: tuple[str, ...] = tuple(m["id"] for m in _BUILTIN_PRESET_META)

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
    return [dict(m) for m in _BUILTIN_PRESET_META]


def resolve_preset_meta(preset_id: str) -> dict[str, str] | None:
    """Return metadata for a built-in preset, or None if not found."""
    pid = normalize_preset_id(preset_id)
    for m in _BUILTIN_PRESET_META:
        if m["id"] == pid:
            return dict(m)
    return None


def resolve_preset_design_md(preset_id: str) -> str | None:
    """Load DESIGN.md content from the presets directory for a given preset id."""
    import os

    pid = normalize_preset_id(preset_id)
    if pid == "clutch":
        return _CLUTCH_DESIGN_MD
    path = os.path.join(os.path.dirname(__file__), "presets", f"{pid}.md")
    if os.path.isfile(path):
        with open(path) as f:
            return f.read()
    return None


def clutch_spec_for_prompt(prompt: str, *, device: str = "web") -> dict[str, Any]:
    """Return Clutch spec with layout pattern inferred from the user brief."""
    pattern = detect_layout_pattern(prompt, device=device)
    base = dict(_CLUTCH_SPEC_BASE)
    base["layout_system"] = layout_wrapper_hint(pattern)
    base["components"] = list(_CLUTCH_SPEC_BASE["components"])
    return enrich_fallback_spec(base, prompt, pattern)


def clutch_design_md_text() -> str:
    return _CLUTCH_DESIGN_MD


def resolve_preset_spec(preset_id: str) -> dict[str, Any] | None:
    """Load cached spec JSON from presets/<id>.spec.json, or None if not found."""
    import json, os
    pid = normalize_preset_id(preset_id)
    if pid == "clutch":
        return None
    path = os.path.join(os.path.dirname(__file__), "presets", f"{pid}.spec.json")
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return None


def resolve_builtin_spec(preset_id: str, prompt: str, *, device: str = "web") -> tuple[dict[str, Any], str]:
    """Structured spec + DESIGN.md for a built-in preset."""
    pid = normalize_preset_id(preset_id)
    if pid == "clutch":
        return clutch_spec_for_prompt(prompt, device=device), clutch_design_md_text()
    cached = resolve_preset_spec(pid)
    if cached:
        pattern = detect_layout_pattern(prompt, device=device)
        spec = enrich_fallback_spec(cached, prompt, pattern)
        md = resolve_preset_design_md(pid) or ""
        return spec, md
    return clutch_spec_for_prompt(prompt, device=device), clutch_design_md_text()
