"""Goal decompose → deliverable kind (users need not name file types)."""

from __future__ import annotations

from types import SimpleNamespace

from src.deliverable_intent import (
    allows_html_feature_plan,
    classify_deliverable_intent,
    decompose_user_goals,
    forbids_html_substitute,
    wants_browser_preview,
)
from src.mcp_react import run_mcp_react_loop


def test_decompose_jinhua_search_summary_visual() -> None:
    text = "搜索一下关于金华的介绍，总结一下，再画一张好看的"
    goals = decompose_user_goals(text)
    assert "search" in goals
    assert "summarize" in goals
    assert "visualize" in goals
    assert "present" not in goals
    assert classify_deliverable_intent(text) == "image"
    assert not wants_browser_preview(text)
    assert forbids_html_substitute(text)


def test_explicit_generate_image() -> None:
    text = "搜索一下关于金华的介绍，总结一下，生成图片"
    assert classify_deliverable_intent(text) == "image"
    assert not wants_browser_preview(text)


def test_present_without_saying_html() -> None:
    text = "帮我做个能打开看的金华介绍"
    assert "present" in decompose_user_goals(text)
    assert classify_deliverable_intent(text) == "html"
    assert wants_browser_preview(text)
    assert allows_html_feature_plan(text)


def test_plain_ask_is_answer() -> None:
    text = "金华怎么样"
    assert classify_deliverable_intent(text) == "answer"
    assert not wants_browser_preview(text)
    assert not allows_html_feature_plan(text)


def test_code_intent() -> None:
    text = "用 Python 算一下金华 GDP 增速"
    assert classify_deliverable_intent(text) == "code"
    assert not wants_browser_preview(text)


def test_mixed_site_and_poster() -> None:
    text = "做个介绍站并配海报"
    assert classify_deliverable_intent(text) == "mixed"
    assert wants_browser_preview(text)


def test_video_intent() -> None:
    assert classify_deliverable_intent("做个金华旅游短视频") == "video"


def test_react_html_substitute_gets_correction(monkeypatch) -> None:
    phase = {"n": 0}

    class _Router:
        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Agnes 2.0 Flash"), model_id

        def chat(self, messages, tools=None, model_id=None, tool_choice=None):
            phase["n"] += 1
            if phase["n"] == 1:
                return {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "tc_write",
                            "type": "function",
                            "function": {
                                "name": "clutch-tools__search_replace",
                                "arguments": {
                                    "path": "jinhua-intro.html",
                                    "old_string": "",
                                    "new_string": "<html>ok</html>",
                                },
                            },
                        }
                    ],
                }
            assert any(
                isinstance(m.get("content"), str)
                and "wrong deliverable" in m.get("content", "").lower()
                for m in messages
            )
            return "Need an image model — cannot fake with HTML."

    monkeypatch.setattr("src.models_config.get_router", lambda: _Router())
    monkeypatch.setattr(
        "src.adapters.ollama_adapter.model_supports_tool_calling",
        lambda spec: True,
    )
    monkeypatch.setattr(
        "src.builtin_tools.list_builtin_tools",
        lambda: [
            {
                "name": "search_replace",
                "description": "write",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old_string": {"type": "string"},
                        "new_string": {"type": "string"},
                    },
                    "required": ["path", "new_string"],
                },
            }
        ],
    )
    monkeypatch.setattr(
        "src.builtin_tools.execute_builtin_tool",
        lambda name, args: '{"path":"jinhua-intro.html","changed_paths":["jinhua-intro.html"]}',
    )
    # Avoid harness auto-image finalize depending on real Models config in unit tests.
    monkeypatch.setattr(
        "src.media_deliverable.finalize_media_deliverables",
        lambda **kwargs: kwargs.get("output") or "",
    )

    outcome = run_mcp_react_loop(
        messages=[
            {
                "role": "user",
                "content": "搜索一下关于金华的介绍，总结一下，再画一张好看的",
            }
        ],
        servers=[
            {
                "id": "clutch-tools",
                "name": "Clutch Builtin Tools",
                "virtual": True,
                "transport": "virtual",
            }
        ],
        log_prefix="TEST",
        max_steps=6,
    )
    assert any("Wrong-deliverable HTML correction" in line for line in outcome.logs)
    assert not any("HTML deliverable wrap-up" in line for line in outcome.logs)
