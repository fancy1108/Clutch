"""Smoke tests: agy hybrid kwargs + cross-agent history for Ollama."""

from __future__ import annotations

import inspect
import json

from src.engine_router import route_engine


def test_hybrid_accepts_supports_append_system_prompt(monkeypatch) -> None:
    from src.engine_router import _route_generic_cli_hybrid

    sig = inspect.signature(_route_generic_cli_hybrid)
    assert "supports_append_system_prompt" in sig.parameters

    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)

        class Turn:
            stdout = "agy ok"
            logs: list[str] = []
            raw_output = None
            output_events = None

        return Turn()

    class FakeManager:
        def get_or_create(self, run_id, workspace_path):
            return object()

        def consume_shell_recovery(self, run_id):
            return False

        def mark_idle(self, run_id):
            pass

    monkeypatch.setattr("src.shell_session.get_shell_session_manager", lambda: FakeManager())
    monkeypatch.setattr("src.session_snapshot.load_snapshot", lambda run_id: None)
    monkeypatch.setattr("src.shell_exec_runtime.run_generic_cli_turn", fake_run)

    result = _route_generic_cli_hybrid(
        agent_type="antigravity-cli",
        binary_name="agy",
        conversation_mode="none",
        prepend_system_prompt=False,
        extra_args=["--dangerously-skip-permissions"],
        run_id="run-smoke",
        workspace_path="/tmp",
        prompt="hello",
        system_prompt="You are Agytest",
        history=None,
        cli_session_id=None,
        cli_binary="/opt/homebrew/bin/agy",
        logs=[],
        on_log=None,
        prompt_flag="-p",
        supports_append_system_prompt=False,
    )
    assert result.output == "agy ok"
    assert captured.get("supports_append_system_prompt") is False


def test_history_includes_prior_agent_replies() -> None:
    from src.main import _history_for_llm

    history = _history_for_llm(
        [
            {"agent": "User", "text": "上海今天天气怎么样"},
            {
                "agent": "Clutch Agent",
                "text": "",
                "id": "msg-assistant-1",
                "outputEvents": [
                    {"type": "assistant", "visible": True, "content": "无法获取实时天气"},
                ],
            },
            {"agent": "User", "text": "我上句话说了什么"},
        ],
        hybrid_executions={
            "msg-assistant-1": {
                "outputEvents": [
                    {"type": "assistant", "visible": True, "content": "无法获取实时天气"},
                ],
            },
        },
    )
    assert any(m["role"] == "user" and "上海" in m["content"] for m in history)
    assert any(m["role"] == "assistant" and "无法获取实时天气" in m["content"] for m in history)
    assert any(m["role"] == "user" and "我上句话" in m["content"] for m in history)


def test_ollama_receives_full_context(monkeypatch) -> None:
    from src.adapters.ollama_adapter import chat_ollama
    from tests.test_ollama_adapter import MockHTTPResponse

    captured: dict[str, object] = {}

    def mock_urlopen(req, timeout=None):
        payload = json.loads(req.data.decode("utf-8"))
        captured["messages"] = payload["messages"]
        body = {"choices": [{"message": {"role": "assistant", "content": "你上句说的是上海天气"}}]}
        return MockHTTPResponse(json.dumps(body).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    _model, output = chat_ollama(
        prompt="我上句话说了什么",
        model="qwen2.5vl:7b",
        history=[
            {"role": "system", "content": "You are Ollama"},
            {"role": "user", "content": "上海今天天气怎么样"},
            {"role": "assistant", "content": "无法获取实时天气"},
            {"role": "user", "content": "我上句话说了什么"},
        ],
    )
    messages = captured["messages"]
    assert messages[1]["content"] == "上海今天天气怎么样"
    assert messages[2]["content"] == "无法获取实时天气"
    assert messages[-1]["content"] == "我上句话说了什么"
    assert "上海" in output or "天气" in output


def test_shell_cmd_codex_uses_exec_positional_prompt() -> None:
    from src.engine_router import CLI_ROUTING_CONFIGS
    from src.shell_exec_runtime import _build_generic_cli_shell_cmd

    config = CLI_ROUTING_CONFIGS["codex-cli"]
    cmd = _build_generic_cli_shell_cmd(
        binary="codex",
        prompt="你好",
        marker="__DONE__",
        system_prompt="You are Codex, the active agent in the user's Clutch workspace.",
        conversation_mode=config["conversation_mode"],
        extra_args=config["extra_args"],
        prepend_system_prompt=config["prepend_system_prompt"],
        prompt_flag=config["prompt_flag"],
        supports_append_system_prompt=config["supports_append_system_prompt"],
        close_stdin=config.get("close_stdin", False),
    )
    assert "codex exec" in cmd
    assert '"$CLUTCH_P"' in cmd
    assert "--json" in cmd
    assert "</dev/null" in cmd
    assert "-p " not in cmd
    assert "--append-system-prompt" not in cmd
    assert "--conversation" not in cmd
    assert "You are Codex" in cmd


def test_shell_cmd_no_append_system_prompt_for_agy() -> None:
    from src.shell_exec_runtime import _build_generic_cli_shell_cmd

    cmd = _build_generic_cli_shell_cmd(
        binary="agy",
        prompt="hello",
        marker="__DONE__",
        system_prompt="long system",
        conversation_mode="none",
        extra_args=["--dangerously-skip-permissions"],
        prepend_system_prompt=False,
        supports_append_system_prompt=False,
    )
    assert "--append-system-prompt" not in cmd
    assert "--model" not in cmd


def test_route_engine_antigravity_does_not_inject_clutch_model(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.engine_router.list_agents",
        lambda: [
            {
                "id": "agent-agy",
                "name": "Agytest",
                "aiEngine": "Antigravity CLI",
            }
        ],
    )
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda tool_id: tool_id == "agy-cli")
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    captured: dict[str, object] = {}

    def fake_chat_generic_cli(**kwargs):
        captured.update(kwargs)
        return "agy reply"

    monkeypatch.setattr("src.adapters.cli_adapter.chat_generic_cli", fake_chat_generic_cli)

    def fake_try_shell_exec_hybrid(*, hybrid_route, legacy_route, **kwargs):
        return legacy_route()

    monkeypatch.setattr("src.engine_router.try_shell_exec_hybrid", fake_try_shell_exec_hybrid)

    res = route_engine(
        agent_name="Agytest",
        prompt="你好",
        session_model_id="agnes-2.0-flash",
    )
    assert res.output == "agy reply"
    extra = captured.get("extra_args") or []
    assert "--model" not in extra
