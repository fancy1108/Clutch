"""Chat deliverables under `.clutch/…` — not the project root."""

from __future__ import annotations

from src.artifact_layout import (
    CLUTCH_ARTIFACTS_DIR,
    block_html_for_non_page_intent,
    relocate_chat_deliverable_path,
    rewrite_apply_patch_paths,
)
from src.deliverable_intent import classify_deliverable_intent


def test_infographic_is_image_intent() -> None:
    text = "搜索 AI Agent 知识点并生成信息图可视化"
    assert classify_deliverable_intent(text) == "image"


def test_relocate_root_html_and_md() -> None:
    text = "总结一下并画一张好看的"
    assert relocate_chat_deliverable_path("ai_agent_summary.md", user_text=text) == (
        f"{CLUTCH_ARTIFACTS_DIR}/ai_agent_summary.md"
    )
    assert relocate_chat_deliverable_path("ai_agent_infographic.html", user_text=text) == (
        f"{CLUTCH_ARTIFACTS_DIR}/ai_agent_infographic.html"
    )


def test_does_not_relocate_source_or_nested() -> None:
    text = "总结一下"
    assert relocate_chat_deliverable_path("src/main.py", user_text=text) == "src/main.py"
    assert relocate_chat_deliverable_path("docs/guide.md", user_text=text) == "docs/guide.md"


def test_block_html_when_image_intent() -> None:
    text = "生成一张信息图"
    err = block_html_for_non_page_intent("poster.html", user_text=text)
    assert err and "generate_image" in err


def test_rewrite_patch_paths() -> None:
    patch = (
        "*** Begin Patch\n"
        "*** Add File: notes.md\n"
        "+hello\n"
        "*** End Patch\n"
    )
    rewritten, notes = rewrite_apply_patch_paths(patch, user_text="总结一下金华")
    assert f"{CLUTCH_ARTIFACTS_DIR}/notes.md" in rewritten
    assert notes
