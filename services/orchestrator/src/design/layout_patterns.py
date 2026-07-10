"""Layout pattern library and few-shot references for Design mode (P0)."""

from __future__ import annotations

import re
from typing import Any

LayoutPattern = str

LAYOUT_PATTERNS: tuple[str, ...] = (
    "landing",
    "dashboard",
    "crm",
    "settings",
    "analytics",
    "ecommerce",
    "chat",
    "mobile_app",
    "login",
    "pricing",
    "profile",
)

_FEWSHOT: dict[str, str] = {
    "login": """<!-- Few-shot: premium login -->
<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-indigo-50 p-6">
  <div class="w-full max-w-md rounded-2xl border border-slate-100 bg-white p-8 shadow-xl shadow-slate-200/50">
    <div class="mb-8 text-center">
      <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white font-bold">A</div>
      <h1 class="text-2xl font-bold tracking-tight text-slate-900">Welcome back</h1>
      <p class="mt-1 text-sm text-slate-500">Sign in to continue</p>
    </div>
    <form class="space-y-4">
      <label class="block text-xs font-semibold uppercase tracking-wide text-slate-500">Email
        <input class="mt-1.5 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 outline-none transition"/>
      </label>
      <button class="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-700 transition">Continue</button>
    </form>
  </div>
</div>""",
    "dashboard": """<!-- Few-shot: analytics dashboard -->
<div class="min-h-screen bg-slate-50">
  <aside class="fixed inset-y-0 w-64 border-r border-slate-200 bg-white p-6">
    <p class="text-lg font-bold">Acme</p>
    <nav class="mt-8 space-y-1 text-sm text-slate-600">
      <a class="block rounded-lg bg-indigo-50 px-3 py-2 font-medium text-indigo-700">Overview</a>
      <a class="block rounded-lg px-3 py-2 hover:bg-slate-50">Reports</a>
    </nav>
  </aside>
  <main class="ml-64 p-8">
    <h1 class="text-2xl font-bold">Dashboard</h1>
    <div class="mt-6 grid grid-cols-3 gap-4">
      <div class="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm"><p class="text-xs text-slate-500">Revenue</p><p class="text-2xl font-bold">$128k</p></div>
    </div>
  </main>
</div>""",
    "pricing": """<!-- Few-shot: pricing -->
<section class="py-20 px-6 max-w-6xl mx-auto">
  <h2 class="text-center text-4xl font-bold">Simple pricing</h2>
  <div class="mt-12 grid md:grid-cols-3 gap-6">
    <div class="rounded-2xl border border-slate-200 p-8 hover:shadow-lg transition"><p class="font-semibold">Starter</p><p class="mt-4 text-4xl font-bold">$9</p></div>
  </div>
</section>""",
    "profile": """<!-- Few-shot: profile -->
<div class="max-w-3xl mx-auto p-8">
  <div class="flex items-center gap-4">
    <div class="h-16 w-16 rounded-full bg-gradient-to-tr from-indigo-500 to-violet-400"></div>
    <div><h1 class="text-xl font-bold">Alex Chen</h1><p class="text-sm text-slate-500">Product Designer</p></div>
  </div>
</div>""",
    "analytics": """<!-- Few-shot: analytics -->
<div class="p-8 space-y-6">
  <div class="flex justify-between items-center"><h1 class="text-2xl font-bold">Analytics</h1></div>
  <div class="h-64 rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">Chart area</div>
</div>""",
    "tables": """<!-- Few-shot: data table -->
<div class="p-8">
  <table class="w-full text-sm">
    <thead><tr class="border-b text-left text-slate-500"><th class="py-3">Name</th><th>Status</th></tr></thead>
    <tbody><tr class="border-b"><td class="py-3 font-medium">Acme Corp</td><td><span class="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700 text-xs">Active</span></td></tr></tbody>
  </table>
</div>""",
}

_LAYOUT_WRAPPERS: dict[str, str] = {
    "landing": "Use a marketing landing layout: top nav, hero with headline + subcopy + dual CTAs, feature grid (3 cols), social proof strip, footer.",
    "dashboard": "Use an app dashboard: persistent sidebar (240px), top bar with search + avatar, stat cards row, main chart/table area.",
    "crm": "Use a CRM layout: pipeline kanban or contact list + detail drawer pattern, filters bar, action toolbar.",
    "settings": "Use settings layout: left settings nav groups, right content panel with form sections and save bar.",
    "analytics": "Use analytics layout: KPI cards, time-range filter, large chart, breakdown table below.",
    "ecommerce": "Use e-commerce layout: category nav, product grid, cart affordance, promotional banner.",
    "chat": "Use chat layout: conversation list sidebar, message thread center, composer sticky bottom.",
    "mobile_app": "Use mobile app layout: bottom tab bar, single-column scroll, large touch targets (min 44px).",
    "login": "Use centered auth card on subtle gradient background; logo, form fields, primary CTA, secondary links.",
    "pricing": "Use pricing page: hero headline, 3-tier card grid with highlighted middle plan, FAQ accordion.",
    "profile": "Use profile layout: avatar header, stats row, tabbed content sections.",
}


def detect_layout_pattern(prompt: str, *, device: str = "web") -> LayoutPattern:
    """Classify user brief into a layout pattern before HTML generation."""
    p = (prompt or "").strip().lower()
    if (device or "web").strip().lower() == "app":
        if any(k in p for k in ("chat", "消息", "对话", "messenger")):
            return "chat"
        return "mobile_app"
    rules: list[tuple[tuple[str, ...], LayoutPattern]] = [
        (("登录", "登陆", "注册", "signin", "sign-in", "login", "signup", "auth"), "login"),
        (("定价", "价格", "pricing", "plans", "subscription"), "pricing"),
        (("个人", "profile", "account settings", "我的"), "profile"),
        (("设置", "settings", "preferences", "配置"), "settings"),
        (("crm", "客户", "销售", "pipeline", "leads"), "crm"),
        (("分析", "analytics", "metrics", "报表", "report"), "analytics"),
        (("表格", "table", "列表", "list view", "datagrid"), "tables"),
        (("购物", "商城", "电商", "shop", "store", "ecommerce", "cart", "product"), "ecommerce"),
        (("聊天", "chat", "message", "对话"), "chat"),
        (("仪表", "dashboard", "后台", "admin", "控制台", "console"), "dashboard"),
        (("落地", "landing", "官网", "首页", "marketing", "hero"), "landing"),
    ]
    for keys, pattern in rules:
        if any(k in p for k in keys):
            return pattern
    return "landing"


def fewshot_for_pattern(pattern: LayoutPattern) -> str:
    """Return curated HTML snippet for the matched pattern."""
    key = pattern
    if pattern in {"crm", "settings", "ecommerce", "chat", "mobile_app"}:
        key = "dashboard" if pattern in {"crm", "settings", "ecommerce"} else "login"
    if pattern == "analytics":
        key = "analytics"
    if pattern == "landing":
        key = "pricing"
    return _FEWSHOT.get(key, _FEWSHOT["dashboard"])


def layout_wrapper_hint(pattern: LayoutPattern) -> str:
    return _LAYOUT_WRAPPERS.get(pattern, _LAYOUT_WRAPPERS["landing"])


def enrich_fallback_spec(spec: dict[str, Any], prompt: str, pattern: LayoutPattern) -> dict[str, Any]:
    """Ensure structured spec has fields needed for 12-section DESIGN.md."""
    out = dict(spec)
    out.setdefault("brand", {"name": out.get("name", "Brand"), "voice": "Professional, modern, trustworthy"})
    out.setdefault("visual_style", "Clean SaaS aesthetic with soft gradients and generous whitespace")
    out.setdefault("layout_system", layout_wrapper_hint(pattern))
    out.setdefault("grid", {"columns": 12, "gutter": "24px", "max_width": "1280px"})
    out.setdefault("radius", {"sm": "6px", "md": "12px", "lg": "16px", "xl": "24px"})
    out.setdefault("shadow", {"card": "0 1px 3px rgba(15,23,42,0.08)", "elevated": "0 20px 40px rgba(15,23,42,0.12)"})
    out.setdefault("motion", {"duration": "200ms", "easing": "cubic-bezier(0.4,0,0.2,1)", "hover_lift": "-2px"})
    out.setdefault(
        "responsive",
        "Mobile-first; stack columns below md; hide sidebar behind menu on sm; min touch 44px on app.",
    )
    out.setdefault(
        "accessibility",
        "WCAG AA contrast; focus rings on interactive elements; semantic headings; aria-labels on icon buttons.",
    )
    if not out.get("colors"):
        out["colors"] = {
            "primary": ["#2563eb", "#1d4ed8", "#93c5fd"],
            "secondary": ["#0f172a", "#334155", "#64748b"],
            "neutral": ["#ffffff", "#f8fafc", "#e2e8f0", "#94a3b8", "#0f172a"],
            "accent": ["#f59e0b", "#fef3c7"],
        }
    if not out.get("typography"):
        out["typography"] = {
            "fontFamily": "system-ui, Inter, sans-serif",
            "samples": [
                {"label": "Display", "size": "32px", "weight": "700"},
                {"label": "Title", "size": "20px", "weight": "600"},
                {"label": "Body", "size": "14px", "weight": "400"},
            ],
        }
    if not out.get("components"):
        out["components"] = ["Header", "Primary button", "Card", "Footer"]
    out["layout_pattern"] = pattern
    out.setdefault("rationale", f"Design system for: {(prompt or '')[:80]}")
    return out


_REVIEW_THRESHOLD = 7


def parse_review_score(text: str) -> tuple[int, str]:
    """Parse design review JSON: {score: 1-10, feedback: str}."""
    import json

    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return 8, raw[:500]
    try:
        data = json.loads(raw[start : end + 1])
        score = int(data.get("score", 8))
        feedback = str(data.get("feedback") or "")
        return max(1, min(10, score)), feedback
    except (json.JSONDecodeError, TypeError, ValueError):
        return 8, raw[:500]


def review_threshold() -> int:
    return _REVIEW_THRESHOLD
