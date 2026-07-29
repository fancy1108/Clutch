"""Auto-call configured image/video models; clear failure when missing keys."""

from __future__ import annotations

from types import SimpleNamespace

from src.media_deliverable import finalize_media_deliverables


def test_finalize_image_calls_configured_model(monkeypatch) -> None:
    called = {"n": 0}

    monkeypatch.setattr(
        "src.image_router.resolve_configured_image_model",
        lambda: (
            SimpleNamespace(id="agnes-image-2.1-flash", name="Agnes Image", provider_id="agnes"),
            "sk-test",
        ),
    )
    monkeypatch.setattr(
        "src.image_router.generate_image_for_model",
        lambda spec, prompt, api_key=None, **kwargs: (
            called.__setitem__("n", called["n"] + 1) or {"b64_json": "data:image/png;base64,aaa"}
        ),
    )
    monkeypatch.setattr(
        "src.image_router.persist_generated_image",
        lambda result, filename_stem=None: {
            **result,
            "local_media_path": ".clutch/generated/images/x.png",
        },
    )
    monkeypatch.setattr(
        "src.image_router.format_image_reply",
        lambda result: "![img](data:image/png;base64,aaa)\n\nSaved `.clutch/generated/images/x.png`",
    )

    files: list[str] = []
    logs: list[str] = []
    out = finalize_media_deliverables(
        output="调研完成。",
        user_text="搜索 AI Agent 并生成信息图",
        chat_messages=[{"role": "user", "content": "搜索 AI Agent 并生成信息图"}],
        files_changed=files,
        logs=logs,
        log_prefix="TEST",
    )
    assert called["n"] == 1
    assert ".clutch/generated/images/x.png" in files
    assert "调研完成" in out
    assert "img" in out.lower() or "Saved" in out or "images" in out


def test_finalize_image_missing_key_is_clear_failure(monkeypatch) -> None:
    monkeypatch.setattr("src.image_router.resolve_configured_image_model", lambda: None)
    logs: list[str] = []
    out = finalize_media_deliverables(
        output="先总结一下。",
        user_text="画一张好看的海报",
        chat_messages=[],
        files_changed=[],
        logs=logs,
        log_prefix="TEST",
    )
    assert "最后一步失败" in out or "Last step failed" in out
    assert "图像" in out or "image" in out.lower()


def test_finalize_video_missing_key_is_clear_failure(monkeypatch) -> None:
    monkeypatch.setattr("src.video_router.resolve_configured_video_model", lambda: None)
    out = finalize_media_deliverables(
        output="",
        user_text="做个金华旅游短视频",
        chat_messages=[],
        files_changed=[],
        logs=[],
        log_prefix="TEST",
    )
    assert "最后一步失败" in out or "Last step failed" in out
    assert "视频" in out or "video" in out.lower()


def test_finalize_skips_when_image_already_delivered(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.image_router.resolve_configured_image_model",
        lambda: (_ for _ in ()).throw(AssertionError("should not resolve")),
    )
    out = finalize_media_deliverables(
        output="done",
        user_text="生成图片",
        chat_messages=[],
        files_changed=[".clutch/generated/images/a.png"],
        logs=[],
        log_prefix="TEST",
    )
    assert out == "done"
