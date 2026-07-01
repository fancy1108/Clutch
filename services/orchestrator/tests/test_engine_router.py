"""Tests for the engine router."""

from __future__ import annotations

from types import SimpleNamespace
import pytest

from src.engine_router import (
    CLI_ROUTING_CONFIGS,
    EngineResult,
    _cli_prompt_from_history,
    _effective_prepend_system_prompt,
    find_agent,
    route_engine,
)


def test_cli_prompt_from_history_appends_current_when_missing() -> None:
    history = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "answer"},
    ]
    prompt = _cli_prompt_from_history("follow up", history)
    assert "User: first" in prompt
    assert "Assistant: answer" in prompt
    assert prompt.endswith("User: follow up")


def test_cli_prompt_from_history_keeps_current_when_already_present() -> None:
    history = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "answer"},
        {"role": "user", "content": "follow up"},
    ]
    prompt = _cli_prompt_from_history("follow up", history)
    assert prompt.count("User: follow up") == 1


def test_effective_prepend_system_prompt_skips_history_replay_follow_up() -> None:
    assert _effective_prepend_system_prompt(
        True,
        conversation_mode="history_only",
        cli_session_id="sess-1",
    ) is False
    assert _effective_prepend_system_prompt(
        True,
        conversation_mode="history_only",
        cli_session_id=None,
    ) is True


def test_codex_history_replay_shell_cmd_omits_system_prompt() -> None:
    from src.shell_exec_runtime import _build_generic_cli_shell_cmd

    config = CLI_ROUTING_CONFIGS["codex-cli"]
    history_prompt = _cli_prompt_from_history(
        "我上句说的什么",
        [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "我上句说的什么"},
        ],
    )
    system_prompt = (
        "You are Codex, the active agent in the user's Clutch workspace.\n"
        "For conversational questions (identity, recall, small talk), answer directly "
        "from the conversation and your role above."
    )
    cmd = _build_generic_cli_shell_cmd(
        binary="codex",
        prompt=history_prompt,
        marker="__DONE__",
        resume_session_id="sess-1",
        system_prompt=system_prompt,
        conversation_mode=config["conversation_mode"],
        extra_args=config["extra_args"],
        prepend_system_prompt=_effective_prepend_system_prompt(
            config["prepend_system_prompt"],
            conversation_mode=config["conversation_mode"],
            cli_session_id="sess-1",
        ),
        prompt_flag=config["prompt_flag"],
        supports_append_system_prompt=config["supports_append_system_prompt"],
        close_stdin=config.get("close_stdin", False),
    )
    assert "User Request:" not in cmd
    assert "For conversational questions" not in cmd
    assert "User: 你好" in cmd
    assert "我上句说的什么" in cmd


@pytest.fixture
def mock_agents(monkeypatch) -> list[dict[str, str]]:
    agents = [
        {
            "id": "agent-builder",
            "name": "Builder Module (JSX VibeCoder)",
            "aiEngine": "Claude Code (Local CLI)",
        },
        {
            "id": "agent-evaluator",
            "name": "Evaluator Module",
            "aiEngine": "DeepSeek API",
        },
    ]
    monkeypatch.setattr("src.engine_router.list_agents", lambda: agents)
    return agents


def test_find_agent(mock_agents) -> None:
    # Exact name match
    assert find_agent("Builder Module (JSX VibeCoder)")["id"] == "agent-builder"
    # Exact id match
    assert find_agent("agent-evaluator")["id"] == "agent-evaluator"
    # Case-insensitive match
    assert find_agent("builder module (jsx vibecoder)")["id"] == "agent-builder"
    # Substring match
    assert find_agent("evaluator")["id"] == "agent-evaluator"
    # None match
    assert find_agent("Unknown Agent") is None


class FakeRouter:
    active_model_id = "fake-model"

    def get_active_model(self) -> SimpleNamespace:
        return SimpleNamespace(name="Fake Model", id="fake-model", model_kind="chat")

    def resolve_for_model(self, model_id: str | None = None):
        return SimpleNamespace(name="Fake Model", id=model_id or "fake-model", model_kind="chat"), "fake-key"

    def chat(self, history: list[dict[str, str]], *, model_id=None, tools=None) -> str:
        _ = (model_id, tools)
        return f"Fake response for: {history[-1]['content']}"


def test_route_engine_fallback_no_agent(monkeypatch) -> None:
    monkeypatch.setattr("src.engine_router.list_agents", lambda: [])
    monkeypatch.setattr("src.engine_router.load_connected_ids", lambda: set())
    monkeypatch.setattr("src.models_config.get_router", lambda: FakeRouter())

    res = route_engine(agent_name="Builder", prompt="test prompt")
    assert res.engine == "Fake Model"
    assert "test prompt" in res.output
    assert any("Routing task to Clutch model" in log for log in res.logs)


def test_route_engine_claude_cli_not_connected(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: False)
    monkeypatch.setattr("src.models_config.get_router", lambda: FakeRouter())

    res = route_engine(
        agent_name="Builder Module (JSX VibeCoder)",
        prompt="hello",
    )
    assert res.engine == "Fake Model"
    assert "hello" in res.output
    assert any("回退到 LLM" in log or "falling back to LLM" in log for log in res.logs)


def test_route_engine_claude_cli_passes_conversation_history(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    captured: dict[str, object] = {}

    def fake_chat_claude(prompt, *, cwd, system_prompt, session_id=None, resume_session_id=None, **kwargs):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt or ""
        captured["session_id"] = session_id
        captured["resume_session_id"] = resume_session_id
        return "Claude CLI output"

    monkeypatch.setattr("src.engine_router.chat_claude_cli", fake_chat_claude)
    monkeypatch.setattr("src.engine_router.uuid.uuid4", lambda: "550e8400-e29b-41d4-a716-446655440000")

    history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "follow up"},
    ]
    res = route_engine(
        agent_name="Builder Module (JSX VibeCoder)",
        prompt="follow up",
        system_prompt="sys",
        history=history,
    )
    assert res.engine == "Claude CLI"
    assert res.cli_session_id == "550e8400-e29b-41d4-a716-446655440000"
    assert "User: first question" in str(captured["prompt"])
    assert "Assistant: first answer" in str(captured["prompt"])
    assert "User: follow up" in str(captured["prompt"])
    assert captured["session_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert captured["resume_session_id"] is None


def test_route_engine_claude_cli_resumes_existing_session(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    captured: dict[str, object] = {}

    def fake_chat_claude(prompt, *, cwd, system_prompt, session_id=None, resume_session_id=None, **kwargs):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt
        captured["session_id"] = session_id
        captured["resume_session_id"] = resume_session_id
        return "Claude CLI output"

    monkeypatch.setattr("src.engine_router.chat_claude_cli", fake_chat_claude)

    history = [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "follow up"},
    ]
    res = route_engine(
        agent_name="Builder Module (JSX VibeCoder)",
        prompt="follow up",
        system_prompt="sys",
        history=history,
        cli_session_id="550e8400-e29b-41d4-a716-446655440000",
    )
    assert res.engine == "Claude CLI"
    assert res.cli_session_id == "550e8400-e29b-41d4-a716-446655440000"
    assert "User: first question" in str(captured["prompt"])
    assert "Assistant: first answer" in str(captured["prompt"])
    assert "User: follow up" in str(captured["prompt"])
    assert captured["system_prompt"] is None
    assert captured["resume_session_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert captured["session_id"] is None


def test_route_engine_claude_cli_connected(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    called_prompt = None
    called_cwd = None
    called_system_prompt = None

    def fake_chat_claude(prompt, *, cwd, system_prompt, **kwargs):
        nonlocal called_prompt, called_cwd, called_system_prompt
        called_prompt = prompt
        called_cwd = cwd
        called_system_prompt = system_prompt
        return "Claude CLI output"

    monkeypatch.setattr("src.engine_router.chat_claude_cli", fake_chat_claude)

    res = route_engine(
        agent_name="Builder Module (JSX VibeCoder)",
        prompt="hello",
        system_prompt="sys prompt",
    )
    assert res.engine == "Claude CLI"
    assert res.output == "Claude CLI output"
    assert called_prompt == "hello"
    assert called_cwd == "/workspace"
    assert called_system_prompt == "sys prompt"
    assert any("Routing task to Claude Code" in log for log in res.logs)


def test_route_engine_claude_cli_streams_router_logs(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})
    monkeypatch.setattr("src.engine_router.chat_claude_cli", lambda **kwargs: "ok")

    streamed: list[str] = []
    res = route_engine(agent_name="Builder Module (JSX VibeCoder)", prompt="hi", on_log=streamed.append)

    assert res.output == "ok"
    assert any(line.startswith("[ROUTER]") for line in streamed)
    assert any("Starting new Claude CLI session" in line for line in streamed)
    assert streamed == res.logs


def test_route_engine_fallback_tool_claude_cli(monkeypatch) -> None:
    monkeypatch.setattr("src.engine_router.list_agents", lambda: [])
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})
    monkeypatch.setattr("src.engine_router.chat_claude_cli", lambda **k: "fallback claude output")

    res = route_engine(
        agent_name="Builder",
        prompt="hello",
        fallback_tool="claude-cli",
    )
    assert res.engine == "Claude CLI"
    assert res.output == "fallback claude output"


def test_route_engine_normalizes_claude_code_cli_alias(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr(
        "src.engine_router.list_agents",
        lambda: [
            {
                "id": "agent-cc",
                "name": "Claude Code Agent",
                "aiEngine": "Claude Code CLI",
            }
        ],
    )
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})
    monkeypatch.setattr("src.engine_router.chat_claude_cli", lambda **k: "alias routed")

    res = route_engine(agent_name="Claude Code Agent", prompt="hi")
    assert res.engine == "Claude CLI"
    assert res.output == "alias routed"
    assert any("Claude Code (Local CLI)" in log for log in res.logs)


def test_route_engine_antigravity_cli(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.engine_router.list_agents",
        lambda: [
            {
                "id": "agent-agy",
                "name": "Antigravity Agent",
                "aiEngine": "Antigravity CLI",
            }
        ],
    )
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda tool_id: tool_id == "agy-cli")
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    captured = {}

    def fake_chat_generic_cli(prompt, *, binary, conversation_mode, cwd, system_prompt, **kwargs):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt
        captured["binary"] = binary
        captured["conversation_mode"] = conversation_mode
        return "Antigravity CLI output"

    monkeypatch.setattr("src.adapters.cli_adapter.chat_generic_cli", fake_chat_generic_cli)

    def fake_try_shell_exec_hybrid(*, hybrid_route, legacy_route, **kwargs):
        return legacy_route()

    monkeypatch.setattr("src.engine_router.try_shell_exec_hybrid", fake_try_shell_exec_hybrid)

    res = route_engine(
        agent_name="Antigravity Agent",
        prompt="hello agy",
        system_prompt="system directive",
        cli_session_id="existing-session-456",
    )
    assert res.engine == "Antigravity CLI"
    assert res.output == "Antigravity CLI output"
    assert captured["prompt"] == "hello agy"
    assert captured["conversation_mode"] == "none"


def test_claude_hybrid_routes_from_flow_source(monkeypatch, mock_agents) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    captured: dict[str, object] = {}

    def fake_claude_hybrid(**kwargs: object) -> EngineResult:
        captured.update(kwargs)
        return EngineResult(
            engine="Claude CLI (Hybrid)",
            output="flow hybrid ok",
            logs=["[HYBRID] flow claude"],
            cli_session_id="sess-flow",
        )

    monkeypatch.setattr("src.engine_router._route_claude_hybrid", fake_claude_hybrid)

    res = route_engine(
        agent_name="Builder Module (JSX VibeCoder)",
        prompt="hello hybrid flow",
        run_id="run-flow-claude",
        source="flow",
        cli_session_id="sess-prev",
    )
    assert res.output == "flow hybrid ok"
    assert captured["run_id"] == "run-flow-claude"
    assert captured["cli_session_id"] == "sess-prev"


def test_route_engine_flow_multiline_claude_skips_hybrid_pty(
    monkeypatch, mock_agents
) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})
    # CI runners may not have `claude` on PATH; multiline guard must not depend on discovery.
    monkeypatch.setattr("src.engine_router.resolve_tool_binary", lambda _tool_id: None)

    hybrid_called = {"value": False}
    legacy_called = {"value": False}

    def fake_claude_hybrid(**kwargs: object) -> EngineResult:
        hybrid_called["value"] = True
        return EngineResult(engine="Claude CLI (Hybrid)", output="hybrid", logs=[])

    def fake_legacy(**kwargs: object) -> EngineResult:
        legacy_called["value"] = True
        return EngineResult(
            engine="Claude CLI",
            output='{"climax_script":"done"}',
            logs=[],
            cli_session_id="sess-legacy",
        )

    monkeypatch.setattr("src.engine_router._route_claude_hybrid", fake_claude_hybrid)
    monkeypatch.setattr("src.engine_router._route_generic_cli_legacy", fake_legacy)

    step1_json = (
        '{\n  "world_background": "端阳仙境",\n'
        '  "protagonist_design": "阿包",\n'
        '  "core_conflict": "龙舟赛"\n}'
    )
    task = f"承接上游结构化数据，撰写具有强画面感的故事文本。\n\n{step1_json}"
    system_prompt = (
        "You are 2-Scriptwriter, the active agent in the user's Clutch workspace.\n"
        "Treat every instruction in the agent protocol below as mandatory.\n\n"
        "你是一位金牌编剧。\n\n"
        "必须且只能输出合法的 JSON 格式。\n"
    )

    res = route_engine(
        agent_name="Builder Module (JSX VibeCoder)",
        prompt=task,
        system_prompt=system_prompt,
        run_id="run-flow-multiline",
        source="flow",
    )
    assert "climax_script" in res.output
    assert legacy_called["value"] is True
    assert hybrid_called["value"] is False


def test_agy_hybrid_routes_to_shell_exec(monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    monkeypatch.setattr(
        "src.engine_router.list_agents",
        lambda: [
            {
                "id": "agent-agy",
                "name": "Antigravity Agent",
                "aiEngine": "Antigravity CLI",
            }
        ],
    )
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda tool_id: tool_id == "agy-cli")
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    def fake_agy_hybrid(**kwargs: object) -> EngineResult:
        return EngineResult(
            engine="Antigravity CLI (Hybrid)",
            output="agy hybrid ok",
            logs=["[HYBRID] agy"],
            cli_session_id="agy-conv-1",
            raw_output="raw agy",
            output_events=[{"type": "assistant", "visible": True, "content": "agy hybrid ok"}],
        )

    monkeypatch.setattr("src.engine_router._route_agy_hybrid", fake_agy_hybrid)

    # try_shell_exec_hybrid is now called since agy-cli is registered;
    # mock it to directly invoke the hybrid_route lambda.
    def fake_try_shell_exec_hybrid(*, hybrid_route, legacy_route, **kwargs):
        return hybrid_route()

    monkeypatch.setattr("src.engine_router.try_shell_exec_hybrid", fake_try_shell_exec_hybrid)

    res = route_engine(
        agent_name="Antigravity Agent",
        prompt="hello hybrid agy",
        run_id="run-agy-hybrid",
        source="plain_chat",
    )
    assert res.engine == "Antigravity CLI (Hybrid)"
    assert res.output == "agy hybrid ok"
    assert res.raw_output == "raw agy"
    assert res.output_events


def test_sanitize_engine_output() -> None:
    from src.engine_router import sanitize_engine_output
    text = "我是 Agy，运行于 Agnes 2.0 Flash (agnes-2.0-flash) 模型。这里是 agnes 测试，另一个词是 magnes。"
    res = sanitize_engine_output(text)
    assert "Gemini 2.0 Flash" in res
    assert "gemini-2.0-flash" in res
    assert "我是 Agy，运行于 Gemini 2.0 Flash (gemini-2.0-flash) 模型。" in res
    assert "这里是 gemini 测试" in res
    assert "另一个词是 magnes。" in res


def test_route_engine_ollama(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.engine_router.list_agents",
        lambda: [
            {
                "id": "agent-ollama",
                "name": "Ollama Agent",
                "aiEngine": "Ollama",
            }
        ],
    )
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda tool_id: tool_id == "ollama-cli")
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    captured = {}
    def fake_chat_ollama(prompt, *, model=None, system_prompt=None, history=None, on_log=None):
        captured["prompt"] = prompt
        captured["model"] = model
        captured["system_prompt"] = system_prompt
        captured["history"] = history
        return "qwen3.6:35b", "Ollama response output"

    monkeypatch.setattr("src.adapters.ollama_adapter.chat_ollama", fake_chat_ollama)

    res = route_engine(
        agent_name="Ollama Agent",
        prompt="hello ollama",
        system_prompt="system guide",
    )
    assert res.engine == "Ollama (qwen3.6:35b)"
    assert res.output == "Ollama response output"
    assert captured["prompt"] == "hello ollama"
    assert captured["system_prompt"] == "system guide"
    assert any("Routing task to Ollama" in log for log in res.logs)


def test_route_engine_ollama_ignores_shell_cli_auto_config(monkeypatch) -> None:
    """Ollama must use HTTP API even when auto-configure added a shell CLI entry."""
    from src.engine_router import CLI_ROUTING_CONFIGS

    monkeypatch.setattr(
        "src.engine_router.list_agents",
        lambda: [
            {
                "id": "agent-ollama",
                "name": "Ollama Agent",
                "agentType": "ollama-cli",
                "ollamaModel": "qwen2.5-coder",
            }
        ],
    )
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda tool_id: tool_id == "ollama-cli")
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})
    monkeypatch.setitem(
        CLI_ROUTING_CONFIGS,
        "ollama-cli",
        {
            "tool_id": "ollama-cli",
            "binary_name": "ollama",
            "conversation_mode": "none",
            "prepend_system_prompt": True,
            "extra_args": [],
            "prompt_flag": "-p",
        },
    )

    captured: dict[str, str | None] = {}

    def fake_chat_ollama(prompt, *, model=None, system_prompt=None, history=None, on_log=None):
        captured["model"] = model
        return "qwen2.5-coder", "HTTP ollama reply"

    monkeypatch.setattr("src.adapters.ollama_adapter.chat_ollama", fake_chat_ollama)

    res = route_engine(agent_name="Ollama Agent", prompt="你好")
    assert res.engine == "Ollama (qwen2.5-coder)"
    assert res.output == "HTTP ollama reply"
    assert captured["model"] == "qwen2.5-coder"
    assert any("Routing task to Ollama" in log for log in res.logs)


def test_route_engine_ollama_not_connected(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.engine_router.list_agents",
        lambda: [
            {
                "id": "agent-ollama",
                "name": "Ollama Agent",
                "aiEngine": "Ollama",
            }
        ],
    )
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda tool_id: False)
    monkeypatch.setattr("src.models_config.get_router", lambda: FakeRouter())

    res = route_engine(agent_name="Ollama Agent", prompt="hello")
    assert res.engine == "Fake Model"
    assert any("Ollama is not installed/connected" in log or "未安装或未连接" in log for log in res.logs)


def test_hybrid_fallback_to_legacy_on_failure(monkeypatch, mock_agents) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})
    monkeypatch.setattr(
        "src.engine_router._route_claude_hybrid",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("hybrid failed")),
    )

    legacy_called: dict[str, bool] = {"ok": False}

    def fake_chat_claude(prompt, *, cwd, system_prompt, session_id=None, resume_session_id=None, **kwargs):
        legacy_called["ok"] = True
        return "legacy output"

    monkeypatch.setattr("src.engine_router.chat_claude_cli", fake_chat_claude)
    monkeypatch.setattr("src.engine_router.uuid.uuid4", lambda: "new-session-id")

    res = route_engine(
        agent_name="Builder Module (JSX VibeCoder)",
        prompt="hello",
        run_id="run-hybrid-fallback",
        source="plain_chat",
    )
    assert legacy_called["ok"] is True
    assert res.output == "legacy output"
    assert any("fallback to legacy" in log for log in res.logs)


def test_route_engine_passes_hybrid_execution_metadata(monkeypatch) -> None:
    events = [{"type": "shell_echo", "visible": False, "content": "claude -p hi"}]

    def fake_raw(**_kwargs: object) -> EngineResult:
        return EngineResult(
            engine="Claude CLI (Hybrid)",
            output="assistant reply",
            logs=["[HYBRID] ok"],
            cli_session_id="sess-1",
            raw_output="raw shell bytes",
            output_events=events,
        )

    monkeypatch.setattr("src.engine_router._route_engine_raw", fake_raw)
    res = route_engine(agent_name="Claude test Session", prompt="hi")
    assert res.raw_output == "raw shell bytes"
    assert res.output_events == events


def test_route_engine_aider_cli(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.engine_router.list_agents",
        lambda: [
            {
                "id": "agent-aider",
                "name": "Aider Agent",
                "agentType": "aider-cli",
            }
        ],
    )
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda tool_id: tool_id == "aider-cli")
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})
    
    captured = {}
    def fake_chat_generic(prompt, *, binary, prompt_flag, extra_args=None, **kwargs):
        captured["prompt"] = prompt
        captured["binary"] = binary
        captured["prompt_flag"] = prompt_flag
        captured["extra_args"] = extra_args
        return "aider mock output"
        
    monkeypatch.setattr("src.engine_router._route_generic_cli_legacy", 
                        lambda *args, **kwargs: EngineResult(
                            engine="Aider CLI",
                            output=fake_chat_generic(kwargs["prompt"], binary=kwargs["cli_binary"] or "aider", prompt_flag=kwargs["prompt_flag"], extra_args=kwargs["extra_args"]),
                            logs=[]
                        ))
    
    res = route_engine(agent_name="Aider Agent", prompt="optimize this file")
    assert res.output == "aider mock output"
    assert captured["prompt_flag"] == "--message"
    assert "--yes-always" in captured["extra_args"]


def test_cli_failure_already_wrapped_detects_prefixed_runtime_error() -> None:
    from src.engine_router import _cli_failure_already_wrapped

    assert _cli_failure_already_wrapped(RuntimeError("通过 Claude CLI 执行任务失败：inner"))
    assert not _cli_failure_already_wrapped(RuntimeError("API Error: 529"))


def test_raise_cli_execution_error_avoids_double_wrap() -> None:
    from src.engine_router import _raise_cli_execution_error

    inner = RuntimeError("通过 Claude CLI 执行任务失败：API Error: 529 busy")
    with pytest.raises(RuntimeError) as exc_info:
        _raise_cli_execution_error("Claude CLI", inner)
    assert str(exc_info.value).count("执行任务失败") == 1


def test_raise_cli_execution_error_529_uses_gateway_busy_copy() -> None:
    from src.engine_router import _raise_cli_execution_error

    with pytest.raises(RuntimeError) as exc_info:
        _raise_cli_execution_error("Claude CLI", Exception("API Error: 529 overloaded"))
    msg = str(exc_info.value)
    assert "529" in msg
    assert "繁忙" in msg or "gateway" in msg.lower()


def test_route_engine_hybrid_legacy_failure_not_double_wrapped(monkeypatch, mock_agents) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    def fake_hybrid(**kwargs: object) -> EngineResult:
        raise RuntimeError("hybrid transport failed")

    def fake_legacy(**kwargs: object) -> EngineResult:
        raise RuntimeError("通过 Claude CLI 执行任务失败：API Error: 529")

    monkeypatch.setattr("src.engine_router._route_claude_hybrid", fake_hybrid)
    monkeypatch.setattr("src.engine_router._route_generic_cli_legacy", fake_legacy)

    with pytest.raises(RuntimeError) as exc_info:
        route_engine(
            agent_name="Builder Module (JSX VibeCoder)",
            prompt="hello",
            run_id="run-double-wrap",
            source="plain_chat",
        )
    assert str(exc_info.value).count("执行任务失败") == 1
