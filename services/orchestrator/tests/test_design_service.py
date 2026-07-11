"""Tests for Design mode service (D36) — session-scoped two-phase, no live LLM."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.design import service


def _session_path(workspace: Path, run_id: str) -> Path:
    found = service._find_existing_session_dir(
        workspace / ".clutch" / "design" / "sessions", run_id
    )
    assert found is not None, f"missing design session dir for {run_id}"
    return found


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "workspaces.json"))
    from src import workspace as ws

    ws._workspaces = {}
    ws._repository_groups = {}
    ws._active_id = None
    ws._loaded = False
    ws._persistence_disabled = False
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    entry = ws.add_workspace(str(repo))
    assert entry["id"]
    service._preview_procs.clear()
    yield Path(entry["workspace_path"])
    service._preview_procs.clear()


class _ReadySocket:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _FakePreviewProcess:
    def __init__(self, *, pid: int = 4321, running: bool = True, wait_timeout: bool = False) -> None:
        self.pid = pid
        self.running = running
        self.wait_timeout = wait_timeout
        self.terminated = False
        self.killed = False
        self.wait_calls = 0

    def poll(self):
        return None if self.running else 0

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True
        self.running = False

    def wait(self, timeout=None):
        self.wait_calls += 1
        if self.wait_timeout and not self.killed:
            raise subprocess.TimeoutExpired("preview", timeout)
        self.running = False
        return 0


def _write_preview_session(workspace: Path, run_id: str, *, node_modules: bool = False) -> Path:
    session_dir = workspace / ".clutch" / "design" / "sessions" / run_id
    react_dir = session_dir / "react"
    react_dir.mkdir(parents=True, exist_ok=True)
    if node_modules:
        (react_dir / "node_modules").mkdir(parents=True, exist_ok=True)
    service._write_manifest(
        session_dir,
        {
            "id": run_id,
            "run_id": run_id,
            "name": "Preview",
            "created_at": service._now_iso(),
            "updated_at": service._now_iso(),
            "prototype_approved": True,
            "react_ready": True,
            "react_path": str(react_dir),
            "screens": [{"id": "main", "name": "Main"}],
        },
    )
    return session_dir


def test_write_manifest_retries_windows_replace_permission_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    original_replace = service.os.replace
    calls = {"count": 0}

    def flaky_replace(src, dst):
        calls["count"] += 1
        if calls["count"] == 1:
            raise PermissionError("locked")
        return original_replace(src, dst)

    monkeypatch.setattr(service, "_is_windows", lambda: True)
    monkeypatch.setattr(service.os, "replace", flaky_replace)
    monkeypatch.setattr(service.time, "sleep", lambda _seconds: None)

    service._write_manifest(session_dir, {"run_id": "manifest-retry"})

    assert calls["count"] == 2
    assert service._read_manifest(session_dir)["run_id"] == "manifest-retry"


def test_session_generate_iterate_approve_react_handoff(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeRouter:
        active_model_id = "agnes-2.0-flash"

        def complete(self, *args, **kwargs):
            raise RuntimeError("no llm")

    monkeypatch.setattr("src.models_config.get_router", lambda: FakeRouter())
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)

    run_id = "design-test-run"
    session = service.ensure_session(run_id, title="Login", prompt="")
    assert session["run_id"] == run_id
    assert (workspace / ".clutch" / "design" / "sessions" / run_id / "manifest.json").is_file()

    generated = service.generate_session(run_id, prompt="设计一个登录页面", device="web")
    assert generated.get("spec")
    assert generated["spec"]["colors"]
    session_dir = service._find_existing_session_dir(
        workspace / ".clutch" / "design" / "sessions", run_id
    )
    assert session_dir is not None
    assert (session_dir / "DESIGN.md").is_file()
    assert (session_dir / "spec.json").is_file()
    assert session_dir.name.endswith(f"__{run_id}")
    assert len(generated["screens"]) >= 1
    assert "html" in generated["screens"][0]["html"].lower()
    assert generated.get("generate_source") == "builtin_clutch"
    log = generated.get("process_log") or []
    assert not any(e.get("kind") in {"model", "tokens"} for e in log), (
        "Model/Tokens must be tags on steps, not standalone log lines"
    )
    tagged = [e for e in log if e.get("role") == "assistant" and e.get("model_name")]
    assert tagged, "Agent Log steps should carry model_name tags"
    assert generated.get("model_id") == "agnes-2.0-flash"

    iterated = service.iterate_session(run_id, "Make the primary button larger")
    assert len(iterated["screens"]) >= 1

    approved = service.approve_prototype(run_id)
    assert approved["prototype_approved"] is True

    react = service.generate_react(run_id)
    assert react["react_ready"] is True
    react_dir = Path(react["path"]) / "react"
    assert (react_dir / "package.json").is_file()
    assert (react_dir / "src" / "App.tsx").is_file()

    react_ok = service.approve_react(run_id)
    assert react_ok["react_approved"] is True

    handoff = service.coding_handoff_payload(run_id)
    assert "Design system" in handoff["instruction"]
    assert handoff["react_path"].endswith("react")

    listed = service.list_sessions()
    assert any(s["run_id"] == run_id for s in listed)


def test_start_generate_async_completes(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)

    run_id = "design-async-run"
    started = service.start_generate_session(run_id, prompt="设计一个登录页面", device="web")
    assert started["status"] in {"crafting_spec", "generating_ui", "ready"}
    assert started["prompt"]

    # Worker is daemon thread; wait briefly for fallback path to finish.
    import time

    deadline = time.time() + 5
    final = started
    while time.time() < deadline:
        final = service.get_session(run_id)
        if final["status"] == "ready" and final.get("screens"):
            break
        time.sleep(0.05)
    assert final["status"] == "ready"
    assert final.get("spec")
    assert len(final["screens"]) >= 1


def test_start_generate_no_race_500(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: concurrent worker rewrite must not 500 the start response."""
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)

    # Slow down generate slightly so worker overlaps with start return path.
    real_generate = service.generate_session

    def slow_generate(*args, **kwargs):
        import time

        time.sleep(0.05)
        return real_generate(*args, **kwargs)

    monkeypatch.setattr(service, "generate_session", slow_generate)

    for i in range(8):
        run_id = f"design-race-{i}"
        started = service.start_generate_session(run_id, prompt=f"login {i}", device="web")
        assert started["status"] == "crafting_spec"
        assert started["prompt"] == f"login {i}"
        # Immediate poll must also succeed (atomic manifest).
        polled = service.get_session(run_id)
        assert polled["run_id"] == run_id


def test_session_status_for_run_ready(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)
    run_id = "design-status-run"
    service.generate_session(run_id, prompt="登录页", device="web")
    assert service.session_status_for_run(run_id) == "ready"


def test_generate_with_reference_image(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Paste/upload path: persist reference.* and expose data URL on session."""
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)

    # 1x1 PNG
    tiny_png = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    run_id = "design-ref-run"
    generated = service.generate_session(
        run_id,
        prompt="参考图片的设计，帮我生成一个登录页",
        device="web",
        reference_image=tiny_png,
    )
    session_dir = _session_path(workspace, run_id)
    assert (session_dir / "reference.png").is_file()
    assert generated.get("reference_image_url", "").startswith("data:image/png;base64,")
    assert generated.get("spec")
    assert len(generated.get("screens") or []) >= 1

    loaded = service.get_session(run_id)
    assert loaded.get("reference_image_url", "").startswith("data:image/png;base64,")


def test_generate_with_design_md(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)
    md = "# Warm Humanist\n\nPrimary: #F7F4EF\nCharcoal buttons with soft shadows.\n"
    run_id = "design-md-run"
    generated = service.generate_session(
        run_id,
        prompt="",
        device="web",
        reference_md=md,
        reference_md_name="DESIGN-lovable.md",
    )
    session_dir = _session_path(workspace, run_id)
    assert (session_dir / "reference_design.md").is_file()
    assert "Warm Humanist" in (session_dir / "DESIGN.md").read_text(encoding="utf-8")
    assert generated["reference_md_name"] == "DESIGN-lovable.md"
    assert "Warm Humanist" in (generated.get("reference_md_text") or "")
    assert "DESIGN-lovable.md" in generated["prompt"]
    assert generated.get("spec")
    assert len(generated.get("screens") or []) >= 1


def test_iterate_add_creates_new_screen(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)
    run_id = "design-iterate-add"
    service.generate_session(run_id, prompt="登录页", device="web")
    before = service.get_session(run_id)
    assert len(before["screens"]) == 1
    after = service.iterate_session(
        run_id,
        "新增一个注册页面",
        target_kind="ui",
        target_id="main",
        mode="auto",
    )
    assert len(after["screens"]) == 2
    assert any(s["id"] != "main" for s in after["screens"])


def test_iterate_modify_keeps_screen_count(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)
    run_id = "design-iterate-mod"
    service.generate_session(run_id, prompt="登录页", device="web")
    after = service.iterate_session(
        run_id,
        "把主按钮改成深色",
        target_kind="ui",
        target_id="main",
        element_path="button.primary",
        element_label="button: Sign in",
        mode="auto",
    )
    assert len(after["screens"]) == 1
    html = (_session_path(workspace, run_id) / "screens" / "main_r0.html").read_text(encoding="utf-8")
    # Without LLM, modify uses intent-aware fallback (must visibly change).
    assert "html" in html.lower()
    assert "data-note" not in html or "Playlist" in html or "Lyrics" in html or "登录" in html or "Log in" in html or "Feature" in html


def test_generate_with_reference_url(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)

    def fake_fetch(url: str) -> dict:
        return {
            "url": url,
            "host": "example.com",
            "title": "Example Site",
            "description": "A clean product landing page",
            "excerpt": "Welcome to Example",
            "fetched_at": "2026-07-10T00:00:00Z",
        }

    monkeypatch.setattr(service, "_fetch_url_snapshot", fake_fetch)
    run_id = "design-url-run"
    generated = service.generate_session(
        run_id,
        prompt="参考这个网站，生成一个登录页面",
        device="web",
        reference_url="example.com",
    )
    session_dir = _session_path(workspace, run_id)
    assert (session_dir / "url_snapshot.json").is_file()
    assert generated.get("reference_url", "").startswith("https://example.com")
    assert generated.get("url_snapshot", {}).get("title") == "Example Site"
    assert generated.get("spec")
    assert len(generated.get("screens") or []) >= 1
    # Real UI → live preview path; no fake silhouette required.
    assert generated.get("ui_preview_url", "").endswith("/screens/main")
    assert (session_dir / "screens" / "main_r0.html").is_file()
    assert service.design_ui_preview_path_for_run(run_id)
    # Empty draft has no preview / no invented thumbnail.
    draft_id = "design-empty-draft"
    service.ensure_session(draft_id, title="New Design")
    assert service.design_ui_preview_path_for_run(draft_id) is None
    assert service.thumbnail_data_url_for_run(draft_id) is None


def test_iterate_modify_music_intent_changes_ui(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)
    run_id = "design-music-iter"
    service.generate_session(run_id, prompt="生成一个音乐播放器页面", device="app")
    before = (_session_path(workspace, run_id) / "screens" / "main_r0.html").read_text(encoding="utf-8")
    assert "Playlist" in before or "Lyrics" in before or "Play" in before
    after = service.iterate_session(
        run_id,
        "要体现音乐歌曲的列表，还有歌词的展示，切歌",
        target_kind="ui",
        target_id="main",
        mode="auto",
    )
    assert after.get("last_iterate_action") == "modify"
    html = (_session_path(workspace, run_id) / "screens" / "main_r0.html").read_text(encoding="utf-8")
    assert "Lyrics" in html or "歌词" in html
    assert "Prev" in html or "Next" in html or "切歌" in html
    assert service._infer_iterate_mode(
        "要体现音乐歌曲的列表，还有歌词的展示，切歌",
        mode="auto",
        target_kind="ui",
    ) == "modify"


def test_read_versioned_screen_html(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)
    run_id = "design-version-read"
    service.generate_session(run_id, prompt="登录页", device="web")
    html_r0 = service.read_screen_html(run_id, "main_r0")
    assert "html" in html_r0.lower()
    session = service.get_session(run_id)
    assert session.get("round_count") == 1
    assert len(session.get("round_history") or []) == 1
    assert session["round_history"][0]["round_index"] == 0
    assert session["round_history"][0]["html_path"] == "screens/main_r0.html"


def test_design_md_has_twelve_sections(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)
    run_id = "design-spec-sections"
    service.generate_session(run_id, prompt="设计一个登录页面", device="web")
    md = (_session_path(workspace, run_id) / "DESIGN.md").read_text(encoding="utf-8")
    for heading in (
        "# Brand",
        "# Visual Style",
        "# Layout System",
        "# Grid",
        "# Typography",
        "# Color Tokens",
        "# Radius",
        "# Shadow",
        "# Components",
        "# Motion",
        "# Responsive Rules",
        "# Accessibility Rules",
    ):
        assert heading in md


def test_versioned_screen_rounds(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)
    run_id = "design-version-run"
    service.generate_session(run_id, prompt="登录页", device="web")
    session = service.iterate_session(run_id, "把主按钮改成深色", target_kind="ui", target_id="main")
    session_dir = _session_path(workspace, run_id)
    assert (session_dir / "screens" / "main_r0.html").is_file()
    assert (session_dir / "screens" / "main_r1.html").is_file()
    history = session.get("round_history") or []
    assert len(history) >= 2
    assert history[-1]["html_path"] == "screens/main_r1.html"


def test_html_has_visible_content_rejects_empty_shell() -> None:
    empty = service._shell_html("Harmony", "", device="web")
    assert service._html_has_visible_content(empty) is False
    assert service._html_has_visible_content("") is False
    filled = service._shell_html("Harmony", "<h1>Player</h1>", device="web")
    assert service._html_has_visible_content(filled) is True

    # Truncated styles/scripts/body should be rejected
    assert service._html_has_visible_content("<html><head><style>body { color: red;") is False
    assert service._html_has_visible_content("<html><head><script>console.log('hi'") is False
    assert service._html_has_visible_content("<html><head></head></html>") is False


def test_coerce_ui_html_falls_back_on_blank_llm() -> None:
    spec = {
        "name": "Harmony",
        "colors": {"primary": ["#22c55e"]},
        "typography": {"fontFamily": "system-ui", "samples": []},
        "components": ["Player"],
    }
    html = service._coerce_ui_html(
        "",
        title="Harmony",
        prompt="生成一个音乐播放器的网页界面",
        spec=spec,
        device="web",
    )
    assert service._html_has_visible_content(html)
    assert "clutch-canvas" in html

    wrapped_empty = service._shell_html("Harmony", "   ", device="web")
    html2 = service._coerce_ui_html(
        wrapped_empty,
        title="Harmony",
        prompt="生成一个音乐播放器的网页界面",
        spec=spec,
        device="web",
    )
    assert service._html_has_visible_content(html2)
    # Prior good HTML is preserved when LLM returns blank
    prior = service._shell_html("Harmony", "<h1>Keep me</h1>", device="web")
    html3 = service._coerce_ui_html(
        "",
        title="Harmony",
        prompt="x",
        spec=spec,
        device="web",
        fallback_html=prior,
    )
    assert "Keep me" in html3


def test_session_folder_readable_name_and_delete(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: False)
    run_id = "run_foldertest01"
    service.ensure_session(run_id, title="New Design")
    legacy = workspace / ".clutch" / "design" / "sessions" / run_id
    assert legacy.is_dir()

    generated = service.generate_session(
        run_id, prompt="生成一个音乐播放器的网页界面", device="web"
    )
    assert generated.get("ui_preview_url")
    sessions_root = workspace / ".clutch" / "design" / "sessions"
    named = [
        p
        for p in sessions_root.iterdir()
        if p.is_dir() and p.name.endswith(f"__{run_id}")
    ]
    assert len(named) == 1
    assert "音乐播放器" in named[0].name or "web" in named[0].name
    assert not legacy.exists() or legacy.resolve() == named[0].resolve()

    service.delete_session_artifacts(run_id)
    assert not named[0].exists()
    assert service._find_existing_session_dir(sessions_root, run_id) is None


def test_generate_records_model_and_token_usage(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each Agent Log step must carry model_name + usage tags (not standalone lines)."""

    class FakeRouter:
        active_model_id = "agnes-2.0-flash"

        def resolve_for_model(self, model_id: str):
            return type("Spec", (), {"name": "Agnes 2.0 Flash"})(), None

        def complete(self, *args, **kwargs):
            return {
                "content": (
                    '{"name":"Login","rationale":"clean","colors":{"primary":["#111"]},'
                    '"typography":{"fontFamily":"Inter","samples":[]},"components":["Button"]}'
                ),
                "usage": {"input_tokens": 120, "output_tokens": 80, "total_tokens": 200},
            }

    monkeypatch.setattr("src.models_config.get_router", lambda: FakeRouter())
    monkeypatch.setattr("src.models_config.is_model_available", lambda *a, **k: True)
    # Force LLM spec path (not builtin) so Spec tokens are recorded.
    monkeypatch.setattr(
        "src.design.service.normalize_preset_id",
        lambda *_a, **_k: "custom",
    )

    run_id = "design-usage-run"
    service.ensure_session(run_id, title="Login", prompt="")
    # Skip heavy UI LLM — stub HTML generation after spec.
    monkeypatch.setattr(
        "src.design.service._generate_ui_html",
        lambda *a, **k: (
            "<!DOCTYPE html><html><body><h1>Login</h1><button>Go</button></body></html>",
            "plan steps",
            {"input_tokens": 50, "output_tokens": 40, "total_tokens": 90},
            False,
            None,
        ),
    )

    generated = service.generate_session(
        run_id, prompt="设计一个登录页面", device="web", design_system="custom"
    )
    log = generated.get("process_log") or []
    assert not any(e.get("kind") in {"model", "tokens"} for e in log)

    spec_step = next(e for e in log if e.get("status") == "spec_ready")
    assert spec_step.get("model_name") == "Agnes 2.0 Flash"
    assert (spec_step.get("usage") or {}).get("total_tokens", 0) > 0

    ready_step = next(e for e in log if e.get("status") == "ready")
    assert ready_step.get("model_name") == "Agnes 2.0 Flash"
    assert (ready_step.get("usage") or {}).get("total_tokens") == 90


def test_start_preview_uses_resolved_windows_cmd_paths(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "design-preview-windows-cmd"
    _write_preview_session(workspace, run_id)
    monkeypatch.setattr(service, "_is_windows", lambda: True)
    monkeypatch.setattr(service, "_free_port", lambda: 5173)
    monkeypatch.setattr(
        service.shutil,
        "which",
        lambda name: {
            "pnpm.cmd": r"C:\Tools\pnpm.CMD",
            "npx.cmd": r"C:\Tools\npx.CMD",
        }.get(name),
    )
    run_calls: list[tuple[list[str], dict]] = []
    popen_calls: list[tuple[list[str], dict]] = []

    def fake_run(args, **kwargs):
        run_calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    def fake_popen(args, **kwargs):
        popen_calls.append((args, kwargs))
        return _FakePreviewProcess()

    monkeypatch.setattr(service.subprocess, "run", fake_run)
    monkeypatch.setattr(service.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(service.socket, "create_connection", lambda *_a, **_k: _ReadySocket())

    result = service.start_preview(run_id)

    assert result["status"] == "running"
    assert run_calls[0][0] == [
        r"C:\Tools\pnpm.CMD",
        "install",
        "--config.dangerously-allow-all-builds=true",
    ]
    assert run_calls[0][1]["encoding"] == "utf-8"
    assert run_calls[0][1]["errors"] == "replace"
    assert popen_calls[0][0][0] == r"C:\Tools\npx.CMD"
    assert "shell" not in run_calls[0][1]
    assert "shell" not in popen_calls[0][1]


def test_start_preview_falls_back_to_npm_when_pnpm_fails(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "design-preview-npm-fallback"
    _write_preview_session(workspace, run_id)
    monkeypatch.setattr(service, "_free_port", lambda: 5174)
    monkeypatch.setattr(
        service.shutil,
        "which",
        lambda name: {
            "pnpm": "/usr/bin/pnpm",
            "npm": "/usr/bin/npm",
            "npx": "/usr/bin/npx",
        }.get(name),
    )
    run_calls: list[list[str]] = []

    def fake_run(args, **_kwargs):
        run_calls.append(args)
        code = 1 if args[0].endswith("pnpm") else 0
        return subprocess.CompletedProcess(args, code, stdout="", stderr="failed")

    monkeypatch.setattr(service.subprocess, "run", fake_run)
    monkeypatch.setattr(service.subprocess, "Popen", lambda *_a, **_k: _FakePreviewProcess())
    monkeypatch.setattr(service.socket, "create_connection", lambda *_a, **_k: _ReadySocket())

    service.start_preview(run_id)

    assert run_calls[:2] == [
        ["/usr/bin/pnpm", "install", "--config.dangerously-allow-all-builds=true"],
        ["/usr/bin/npm", "install"],
    ]


def test_start_preview_reports_missing_package_managers(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "design-preview-missing-pm"
    _write_preview_session(workspace, run_id)
    monkeypatch.setattr(service.shutil, "which", lambda _name: None)

    with pytest.raises(service.DesignError, match="pnpm or npm was not found"):
        service.start_preview(run_id)


def test_start_preview_reports_popen_oserror(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "design-preview-popen-error"
    _write_preview_session(workspace, run_id, node_modules=True)
    monkeypatch.setattr(service, "_free_port", lambda: 5175)
    monkeypatch.setattr(service.shutil, "which", lambda name: "/usr/bin/npx" if name == "npx" else None)

    def fail_popen(*_args, **_kwargs):
        raise OSError("spawn failed")

    monkeypatch.setattr(service.subprocess, "Popen", fail_popen)

    with pytest.raises(service.DesignError, match="Failed to start preview"):
        service.start_preview(run_id)


def test_start_preview_reuses_live_process(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "design-preview-reuse"
    _write_preview_session(workspace, run_id, node_modules=True)
    service._preview_procs[run_id] = {
        "proc": _FakePreviewProcess(),
        "port": 6188,
        "url": "http://127.0.0.1:6188",
    }
    monkeypatch.setattr(
        service.subprocess,
        "Popen",
        lambda *_a, **_k: pytest.fail("start_preview should reuse the live process"),
    )

    result = service.start_preview(run_id)

    assert result == {
        "run_id": run_id,
        "url": "http://127.0.0.1:6188",
        "port": 6188,
        "status": "running",
    }


def test_start_preview_timeout_cleans_up_process(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "design-preview-timeout"
    _write_preview_session(workspace, run_id, node_modules=True)
    proc = _FakePreviewProcess()
    now = [0.0]
    monkeypatch.setattr(service, "_is_windows", lambda: False)
    monkeypatch.setattr(service, "_free_port", lambda: 5176)
    monkeypatch.setattr(service.shutil, "which", lambda name: "/usr/bin/npx" if name == "npx" else None)
    monkeypatch.setattr(service.subprocess, "Popen", lambda *_a, **_k: proc)
    monkeypatch.setattr(service.socket, "create_connection", lambda *_a, **_k: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(service.time, "time", lambda: now[0])
    monkeypatch.setattr(service.time, "sleep", lambda seconds: now.__setitem__(0, now[0] + seconds + 15))

    with pytest.raises(service.DesignError, match="did not become ready"):
        service.start_preview(run_id)

    assert proc.terminated is True
    assert proc.wait_calls == 1


def test_stop_preview_uses_windows_process_tree_kill(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "design-preview-windows-stop"
    session_dir = _write_preview_session(workspace, run_id, node_modules=True)
    manifest = service._read_manifest(session_dir)
    manifest["preview_url"] = "http://127.0.0.1:6199"
    service._write_manifest(session_dir, manifest)
    proc = _FakePreviewProcess(pid=6199)
    service._preview_procs[run_id] = {
        "proc": proc,
        "port": 6199,
        "url": "http://127.0.0.1:6199",
    }
    taskkill_calls: list[list[str]] = []

    def fake_run(args, **_kwargs):
        taskkill_calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(service, "_is_windows", lambda: True)
    monkeypatch.setattr(service.subprocess, "run", fake_run)

    result = service.stop_preview(run_id)

    assert result["status"] == "stopped"
    assert taskkill_calls == [["taskkill", "/PID", "6199", "/T", "/F"]]
    assert proc.wait_calls == 1
    assert service._read_manifest(session_dir)["preview_url"] is None


def test_stop_preview_kills_after_wait_timeout(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "design-preview-stop-timeout"
    _write_preview_session(workspace, run_id, node_modules=True)
    proc = _FakePreviewProcess(wait_timeout=True)
    service._preview_procs[run_id] = {
        "proc": proc,
        "port": 6200,
        "url": "http://127.0.0.1:6200",
    }
    monkeypatch.setattr(service, "_is_windows", lambda: False)

    service.stop_preview(run_id)

    assert proc.terminated is True
    assert proc.killed is True
    assert proc.wait_calls == 2


def test_stop_preview_windows_kills_after_taskkill_wait_timeout(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "design-preview-windows-taskkill-timeout"
    _write_preview_session(workspace, run_id, node_modules=True)
    proc = _FakePreviewProcess(pid=6201, wait_timeout=True)
    service._preview_procs[run_id] = {
        "proc": proc,
        "port": 6201,
        "url": "http://127.0.0.1:6201",
    }
    monkeypatch.setattr(service, "_is_windows", lambda: True)
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda args, **_kwargs: subprocess.CompletedProcess(args, 0, stdout="", stderr=""),
    )

    service.stop_preview(run_id)

    assert proc.killed is True
    assert proc.wait_calls == 2


def test_generate_react_stops_live_preview_before_replacing_react_dir(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "design-generate-stops-preview"
    session_dir = workspace / ".clutch" / "design" / "sessions" / run_id
    screens_dir = session_dir / "screens"
    react_dir = session_dir / "react"
    screens_dir.mkdir(parents=True, exist_ok=True)
    react_dir.mkdir(parents=True, exist_ok=True)
    (screens_dir / "main.html").write_text("<html><body><h1>Main</h1></body></html>", encoding="utf-8")
    (react_dir / "old.txt").write_text("old", encoding="utf-8")
    service._write_manifest(
        session_dir,
        {
            "id": run_id,
            "run_id": run_id,
            "name": "Preview",
            "created_at": service._now_iso(),
            "updated_at": service._now_iso(),
            "prototype_approved": True,
            "screens": [{"id": "main", "name": "Main"}],
        },
    )

    class FakeRouter:
        active_model_id = "fake-model"

    call_order: list[str] = []
    original_rmtree = service.shutil.rmtree

    monkeypatch.setattr("src.models_config.get_router", lambda: FakeRouter())
    monkeypatch.setattr("src.models_config.is_model_available", lambda *_a, **_k: False)
    monkeypatch.setattr(service, "stop_preview", lambda _run_id: call_order.append("stop"))

    def record_rmtree(path):
        call_order.append("rmtree")
        original_rmtree(path)

    monkeypatch.setattr(service.shutil, "rmtree", record_rmtree)

    service.generate_react(run_id)

    assert call_order[:2] == ["stop", "rmtree"]
