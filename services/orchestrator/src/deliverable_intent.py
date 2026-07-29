"""Infer deliverable shape from natural-language needs (not file-type keywords).

Users rarely say “HTML deliverable” / “image deliverable”. We decompose goals
(search / summarize / visualize / present / implement / ask) then map to kinds.
"""

from __future__ import annotations

import re
from typing import Literal

DeliverableKind = Literal["html", "image", "video", "code", "answer", "mixed"]
Goal = Literal["search", "summarize", "visualize", "present", "implement", "ask"]

_GOAL_PATTERNS: dict[Goal, re.Pattern[str]] = {
    "search": re.compile(
        r"("
        r"搜索|搜一下|查一下|查下|查找|检索|look\s*up|search\s+(for|the)|"
        r"关于.+的介绍|资料|相关信息"
        r")",
        re.IGNORECASE,
    ),
    "summarize": re.compile(
        r"("
        r"总结|概括|归纳|简介|介绍一下|講講|讲讲|summarize|summary|"
        r"概述|梳理一下"
        r")",
        re.IGNORECASE,
    ),
    "visualize": re.compile(
        r"("
        r"生成图片|画[一张張]|画个|画一|出图|配图|配一张|海报|插画|封面|"
        r"示意图|视觉|好看的图|一张图|圖像|图像|图片|写真|"
        r"信息图|資訊圖|可视化|視覺化|图表|圖表|infographic|"
        r"短视频|短片|视频|片头|动画|动图|"
        r"\b(image|picture|photo|poster|illustration|cover|video|clip|animation|"
        r"infographic|chart|diagram)\b|"
        r"(generate|create|make|draw)\s+(an?\s+)?(image|picture|photo|poster|video|infographic)"
        r")",
        re.IGNORECASE,
    ),
    "present": re.compile(
        r"("
        r"\bhtml\b|\.html?\b|网页|落地页|站点页|单页|首页|"
        r"展示页|介绍页|介绍站|展示站|打开看|能打开|可浏览|"
        r"做成页|做成一个页|做个页|页面展示|"
        r"登录页|注册页|登錄頁|註冊頁|"
        r"登录|登錄|注册|註冊|"
        r"\b(login|signup|sign[-_ ]?up|sign[-_ ]?in|auth)\b|"
        r"\b(web\s*page|webpage|landing\s*page|static\s*site|single[- ]page)\b"
        r")",
        re.IGNORECASE,
    ),
    "implement": re.compile(
        r"("
        r"写[一段]?代码|写个脚本|实现|函数|pytest|单元测试|"
        r"\b(python|typescript|javascript|rust|go)\b|"
        r"\b(code|script|function|implement|refactor)\b|"
        r"跑一下测试|写测试"
        r")",
        re.IGNORECASE,
    ),
    "ask": re.compile(
        r"("
        r"^(什么|什麼|谁|誰|为什么|為什麼|怎么|怎麼|哪|是否|是不是|怎么样|怎麼樣)\b|"
        r"\b(what|who|why|how|which|is)\b|"
        r"[?？]\s*$"
        r")",
        re.IGNORECASE,
    ),
}

_VIDEO_RE = re.compile(
    r"(短视频|短片|视频|片头|动画|\b(video|clip|animation|mp4)\b)",
    re.IGNORECASE,
)


def decompose_user_goals(user_text: str | None) -> frozenset[str]:
    """Split a natural-language ask into goal tags."""
    text = (user_text or "").strip()
    if not text:
        return frozenset()

    goals: set[str] = set()
    for name, pattern in _GOAL_PATTERNS.items():
        if pattern.search(text):
            goals.add(name)

    # Bare “做一个介绍” without present/visualize → summarize, not a page.
    if re.search(r"(做|写|生成).{0,8}介绍", text) and "present" not in goals and "visualize" not in goals:
        goals.add("summarize")

    if not goals:
        goals.add("ask" if len(text) < 40 else "summarize")
    return frozenset(goals)


def classify_deliverable_intent(user_text: str | None) -> DeliverableKind:
    """Map decomposed goals → primary deliverable kind."""
    goals = decompose_user_goals(user_text)
    text = (user_text or "").strip()

    wants_present = "present" in goals
    wants_visual = "visualize" in goals
    wants_video = wants_visual and bool(_VIDEO_RE.search(text))
    wants_code = "implement" in goals and not wants_present and not wants_visual

    if wants_present and wants_visual:
        return "mixed"
    if wants_present:
        return "html"
    if wants_video:
        return "video"
    if wants_visual:
        return "image"
    if wants_code:
        return "code"
    return "answer"


def wants_browser_preview(user_text: str | None) -> bool:
    """Auto-open system browser only when a page/site was inferred."""
    kind = classify_deliverable_intent(user_text)
    return kind in {"html", "mixed"}


def forbids_html_substitute(user_text: str | None) -> bool:
    """True when writing .html would be the wrong stand-in for the ask."""
    kind = classify_deliverable_intent(user_text)
    return kind in {"image", "video", "code", "answer"}


def is_html_deliverable_path(path: str) -> bool:
    return bool(re.search(r"\.html?$", (path or "").strip(), re.IGNORECASE))


def html_deliverable_wrapup_nudge(*, paths: list[str]) -> str:
    listed = ", ".join(p for p in paths if is_html_deliverable_path(p)) or "the HTML file"
    return (
        "[System reminder — HTML deliverable ready] You already wrote "
        f"{listed}. Clutch opens it in the system browser for the user. "
        "Now: (1) call `todo_write` to mark remaining todos completed, "
        "(2) give a short final reply with the file path — do NOT call "
        "web_search / web_fetch again, and do not start another large rewrite."
    )


def html_substitute_correction_nudge(*, paths: list[str], user_text: str | None) -> str:
    kind = classify_deliverable_intent(user_text)
    listed = ", ".join(p for p in paths if is_html_deliverable_path(p)) or "an HTML file"
    if kind == "image":
        need = "an image (poster/illustration), not an HTML page"
        tip = (
            "Switch the footer model to an image model (e.g. Agnes Image) and "
            "generate a real image, or tell the user they need an image model. "
            "Do NOT expand or polish the HTML as a substitute."
        )
    elif kind == "video":
        need = "a video, not an HTML page"
        tip = (
            "Switch the footer model to a video model and generate a real video, "
            "or tell the user they need a video model. Do NOT use HTML as a substitute."
        )
    elif kind == "code":
        need = "code/scripts, not an HTML page"
        tip = "Write the requested code file(s). Do NOT ship an HTML page instead."
    else:
        need = "a text answer / summary, not an HTML page"
        tip = (
            "Answer in chat from your research. Do NOT create or expand an HTML page "
            "unless the user asked for a browsable page/site."
        )
    return (
        f"[System reminder — wrong deliverable] You wrote {listed}, but this turn needs "
        f"{need}. {tip}"
    )


def deliverable_system_reminder(
    user_text: str | None,
    *,
    current_model_kind: str = "chat",
) -> str | None:
    """Short system layer: goals → what to deliver (and what not to fake)."""
    goals = decompose_user_goals(user_text)
    kind = classify_deliverable_intent(user_text)
    if not goals and kind == "answer":
        return None

    parts: list[str] = [
        "## Deliverable intent (inferred from the user ask — they may not name a file type)"
    ]
    goal_bits = ", ".join(sorted(goals)) if goals else "ask"
    parts.append(f"Decomposed goals: {goal_bits}. Primary deliverable: **{kind}**.")

    if kind == "image":
        parts.append(
            "Deliver a real image via `generate_image` (uses the user's configured image "
            "model, e.g. Agnes Image). Do NOT write an HTML/CSS page as a fake visual. "
            "Research notes go under `.clutch/artifacts/*.md` — never dump files at the "
            "project root. Clutch will also auto-call the configured image model at the "
            "end of the turn if you researched but did not generate yet."
        )
    elif kind == "video":
        parts.append(
            "Deliver a real video via `generate_video` (uses the user's configured "
            "video model, e.g. Agnes Video). Do NOT substitute an HTML page. "
            "Clutch will also auto-call the configured video model at the end of the turn."
        )
    elif kind == "html":
        parts.append(
            "Deliver a browsable HTML page under `.clutch/artifacts/` (not the project root). "
            "Clutch may open it in the system browser."
        )
    elif kind == "mixed":
        parts.append(
            "Deliver both a browsable page and the requested visual (image/video). "
            "Do not skip the visual by only shipping HTML decoration."
        )
    elif kind == "code":
        parts.append(
            "Deliver code/scripts in the workspace. Do NOT create an HTML showcase page "
            "unless explicitly asked."
        )
    else:
        parts.append(
            "Prefer a concise chat answer (and tools for research). "
            "If you save notes, use `.clutch/artifacts/` — do not pollute the project root. "
            "Do NOT create an HTML page unless the user asked for a browsable page/site."
        )

    model_kind = (current_model_kind or "chat").strip().lower()
    if kind in {"image", "video"} and model_kind == "chat":
        parts.append(
            f"Current model is chat — it cannot natively emit {kind} bytes. "
            "Be honest; do not invent a webpage as the deliverable."
        )

    return "\n".join(parts)


def allows_html_feature_plan(user_text: str | None) -> bool:
    """Feature-plan default stack (HTML+CSS+JS) only when a page was inferred."""
    return classify_deliverable_intent(user_text) in {"html", "mixed"}
