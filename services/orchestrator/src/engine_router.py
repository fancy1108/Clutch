"""Engine router for deciding between Claude CLI, Cursor workspace, or global LLM provider."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.agent_storage import list_agents
from src.tools_status import load_connected_ids, resolve_tool_binary, tool_available_for_routing
from src.adapters.claude_cli_adapter import chat_claude_cli
from src.agent_type import agent_type_from_record, resolve_model_for_agent
from src.runtime_registry import try_shell_exec_hybrid
from src.workspace import get_workspace
from src.preferences_storage import tr


def load_custom_cli_configs() -> dict[str, Any]:
    from src.storage_helper import get_storage_dir
    path = get_storage_dir() / "custom_clis.json"
    if not path.is_file():
        return {}
    try:
        import json
        configs = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    # Ollama is HTTP_DAEMON — shell CLI auto-config must not override native routing.
    if isinstance(configs, dict):
        configs.pop("ollama-cli", None)
    return configs if isinstance(configs, dict) else {}


def save_custom_cli_configs(configs: dict[str, Any]) -> None:
    from src.storage_helper import get_storage_dir
    path = get_storage_dir() / "custom_clis.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import json
        path.write_text(json.dumps(configs, indent=2), encoding="utf-8")
    except Exception:
        pass


CLI_ROUTING_CONFIGS = {
    "claude-cli": {
        "tool_id": "claude-cli",
        "binary_name": "claude",
        "conversation_mode": "separate",
        "prepend_system_prompt": False,
        "extra_args": ["--dangerously-skip-permissions"],
        "prompt_flag": "-p",
    },
    "antigravity-cli": {
        "tool_id": "agy-cli",
        "binary_name": "agy",
        "conversation_mode": "none",
        "prepend_system_prompt": False,
        "extra_args": ["--dangerously-skip-permissions"],
        "prompt_flag": "-p",
        "supports_append_system_prompt": False,
    },
    "codex-cli": {
        "tool_id": "codex-cli",
        "binary_name": "codex",
        "conversation_mode": "history_only",
        "prepend_system_prompt": True,
        "extra_args": [
            "exec",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            "--json",
        ],
        "prompt_flag": "",
        "supports_append_system_prompt": False,
        "close_stdin": True,
    },
    "aider-cli": {
        "tool_id": "aider-cli",
        "binary_name": "aider",
        "conversation_mode": "none",
        "prepend_system_prompt": True,
        "extra_args": ["--yes-always"],
        "prompt_flag": "--message",
    },
    "rivet-cli": {
        "tool_id": "rivet-cli",
        "binary_name": "rivet",
        "conversation_mode": "none",
        "prepend_system_prompt": True,
        "extra_args": [],
        "prompt_flag": "-p",
        "supports_append_system_prompt": False,
    },
}

try:
    CLI_ROUTING_CONFIGS.update(load_custom_cli_configs())
except Exception:
    pass


@dataclass(frozen=True)
class EngineResult:
    engine: str
    output: str
    logs: list[str]
    cli_session_id: str | None = None
    raw_output: str | None = None
    output_events: list[dict[str, object]] | None = None
    shell_recovered: bool = False


def _normalize_engine_type(engine_type: str) -> str:
    key = engine_type.strip().lower()
    if key in {
        "claude code (local cli)",
        "claude code cli",
        "claude-cli",
        "claude cli",
    }:
        return "Claude Code (Local CLI)"
    if key in {
        "antigravity cli",
        "antigravity-cli",
        "antigravity",
        "agenty cli",
        "agy-cli",
        "agy cli",
    }:
        return "Antigravity CLI"
    if key in {
        "ollama",
        "ollama-cli",
        "ollama (cli)",
    }:
        return "Ollama"
    if key in {
        "codex cli",
        "codex-cli",
        "codex",
        "openai codex cli",
    }:
        return "Codex CLI"
    return engine_type.strip()


def _format_history_for_cli_prompt(history: list[dict[str, str]] | None) -> str:
    if not history:
        return ""
    lines: list[str] = []
    for item in history:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if not content or role == "system":
            continue
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")
    return "\n\n".join(lines)


def _cli_prompt_from_history(
    prompt: str,
    history: list[dict[str, str]] | None,
) -> str:
    """Build a single CLI prompt that includes prior turns for plain-chat context."""
    history_prompt = _format_history_for_cli_prompt(history).strip()
    if not history_prompt:
        return prompt
    current = prompt.strip()
    if current and f"User: {current}" not in history_prompt:
        return f"{history_prompt}\n\nUser: {current}"
    return history_prompt


def _effective_prepend_system_prompt(
    prepend_system_prompt: bool,
    *,
    conversation_mode: str,
    cli_session_id: str | None,
) -> bool:
    """Skip prepending system prompt when resuming a CLI session with history replay."""
    if not prepend_system_prompt:
        return False
    if conversation_mode == "history_only" and cli_session_id:
        return False
    return True


def _ensure_cli_output(
    output: str,
    *,
    invoke: Callable[..., str],
    prompt: str,
    history: list[dict[str, str]] | None,
    system_prompt: str | None,
    logs: list[str],
    on_log: Callable[[str], None] | None,
    engine_title: str,
) -> str:
    if output.strip():
        return output
    _emit_log(
        logs,
        on_log,
        f"{engine_title} returned empty output; retrying with user prompt only.",
    )
    retry = invoke(cli_prompt=prompt, cli_system_prompt=None)
    if retry.strip():
        return retry
    history_prompt = _cli_prompt_from_history(prompt, history)
    if history_prompt != prompt:
        _emit_log(
            logs,
            on_log,
            f"{engine_title} still empty; retrying with conversation history.",
        )
        retry = invoke(cli_prompt=history_prompt, cli_system_prompt=system_prompt)
        if retry.strip():
            return retry
    raise RuntimeError(
        tr(
            f"{engine_title} returned empty output.",
            f"{engine_title} 返回了空输出。",
        )
    )


def find_agent(agent_name: str) -> dict[str, Any] | None:
    agents = list_agents()
    for agent in agents:
        if agent.get("name") == agent_name or agent.get("id") == agent_name:
            return agent
    for agent in agents:
        name = agent.get("name", "")
        aid = agent.get("id", "")
        if name.lower() == agent_name.lower() or aid.lower() == agent_name.lower():
            return agent
    for agent in agents:
        name = agent.get("name", "")
        aid = agent.get("id", "")
        if agent_name.lower() in name.lower() or agent_name.lower() in aid.lower():
            return agent
    return None


def _emit_log(logs: list[str], on_log: Callable[[str], None] | None, line: str) -> None:
    logs.append(line)
    if on_log:
        on_log(line)


def _persist_hybrid_turn_snapshot(
    *,
    run_id: str,
    workspace_path: str,
    cli_session_id: str | None,
    prompt: str,
) -> None:
    from src.session_snapshot import upsert_hybrid_turn_snapshot

    upsert_hybrid_turn_snapshot(
        run_id=run_id,
        workspace_path=workspace_path,
        cli_session_id=cli_session_id,
        task_summary=prompt,
    )


def _resolve_agent_type(agent: dict[str, Any] | None, fallback_tool: str | None) -> str:
    if agent:
        return agent_type_from_record(agent)
    if fallback_tool == "claude-cli":
        return "claude-cli"
    if fallback_tool in {"agy-cli", "agy", "antigravity-cli"}:
        return "antigravity-cli"
    if fallback_tool in {"codex-cli", "codex"}:
        return "codex-cli"
    if fallback_tool in {"ollama", "ollama-cli"}:
        return "ollama-cli"
    if fallback_tool in {"aider", "aider-cli"}:
        return "aider-cli"
    return "clutch"


def _route_generic_cli_hybrid(
    *,
    agent_type: str,
    binary_name: str,
    conversation_mode: str,
    prepend_system_prompt: bool = False,
    extra_args: list[str] | None = None,
    run_id: str,
    workspace_path: str,
    prompt: str,
    system_prompt: str | None,
    history: list[dict[str, str]] | None,
    cli_session_id: str | None,
    cli_binary: str | None,
    logs: list[str],
    on_log: Callable[[str], None] | None,
    prompt_flag: str = "-p",
    supports_append_system_prompt: bool = True,
    close_stdin: bool = False,
) -> EngineResult:
    import os
    from src.session_snapshot import format_handoff_prefix, load_snapshot
    from src.shell_exec_runtime import run_generic_cli_turn
    from src.shell_session import get_shell_session_manager

    timeout = float(os.environ.get("CLUTCH_CLAUDE_CLI_TIMEOUT", "600"))
    binary = cli_binary or binary_name
    manager = get_shell_session_manager()
    snapshot = load_snapshot(run_id)
    _emit_log(logs, on_log, f"[HYBRID] acquiring shell for {run_id}")
    session = manager.get_or_create(run_id, workspace_path=workspace_path)
    _emit_log(logs, on_log, f"[HYBRID] shell ready for {run_id}")
    shell_recovered = manager.consume_shell_recovery(run_id)
    context_prefix = None
    if shell_recovered and snapshot and (snapshot.task_summary or snapshot.open_todos):
        context_prefix = format_handoff_prefix(snapshot)

    def _lock_wait_log() -> None:
        _emit_log(
            logs,
            on_log,
            f"[HYBRID] acquiring workspace CLI lock for {workspace_path}",
        )

    engine_title = f"{agent_type.replace('-cli', '').title()} CLI"
    if engine_title == "Agy CLI":
        engine_title = "Antigravity CLI"

    try:
        if shell_recovered:
            _emit_log(
                logs,
                on_log,
                "[HYBRID] shell disconnected; new bash PTY spawned (snapshot handoff if available)",
            )
        if cli_session_id:
            _emit_log(logs, on_log, f"[HYBRID] resume {cli_session_id} in shell {run_id}")
            resume_prompt = _cli_prompt_from_history(prompt, history)
            turn = run_generic_cli_turn(
                session,
                agent_type=agent_type.replace("-cli", ""),
                prompt=resume_prompt,
                binary=binary,
                timeout_s=timeout,
                conversation_mode=conversation_mode,
                extra_args=extra_args,
                prepend_system_prompt=prepend_system_prompt,
                cli_session_id=cli_session_id,
                resume_session_id=cli_session_id,
                context_prefix=context_prefix,
                system_prompt=system_prompt,
                on_lock_wait=_lock_wait_log,
                prompt_flag=prompt_flag,
                supports_append_system_prompt=supports_append_system_prompt,
                close_stdin=close_stdin,
            )
            _persist_hybrid_turn_snapshot(
                run_id=run_id,
                workspace_path=workspace_path,
                cli_session_id=cli_session_id,
                prompt=prompt,
            )
            return EngineResult(
                engine=f"{engine_title} (Hybrid)",
                output=turn.stdout,
                logs=logs + turn.logs,
                cli_session_id=cli_session_id,
                raw_output=turn.raw_output,
                output_events=turn.output_events,
                shell_recovered=shell_recovered,
            )

        history_prompt = _format_history_for_cli_prompt(history).strip()
        bootstrap_prompt = _cli_prompt_from_history(prompt, history)
        new_session_id = str(uuid.uuid4())
        _emit_log(logs, on_log, f"[HYBRID] new session {new_session_id} in shell {run_id}")
        turn = run_generic_cli_turn(
            session,
            agent_type=agent_type.replace("-cli", ""),
            prompt=bootstrap_prompt,
            binary=binary,
            timeout_s=timeout,
            conversation_mode=conversation_mode,
            extra_args=extra_args,
            prepend_system_prompt=prepend_system_prompt,
            new_session_id=new_session_id,
            system_prompt=system_prompt,
            context_prefix=context_prefix,
            on_lock_wait=_lock_wait_log,
            prompt_flag=prompt_flag,
            supports_append_system_prompt=supports_append_system_prompt,
            close_stdin=close_stdin,
        )
        _persist_hybrid_turn_snapshot(
            run_id=run_id,
            workspace_path=workspace_path,
            cli_session_id=new_session_id,
            prompt=prompt,
        )
        return EngineResult(
            engine=f"{engine_title} (Hybrid)",
            output=turn.stdout,
            logs=logs + turn.logs,
            cli_session_id=new_session_id,
            raw_output=turn.raw_output,
            output_events=turn.output_events,
            shell_recovered=shell_recovered,
        )
    finally:
        manager.mark_idle(run_id)


def _route_generic_cli_legacy(
    *,
    agent_type: str,
    binary_name: str,
    conversation_mode: str,
    prepend_system_prompt: bool = False,
    extra_args: list[str] | None = None,
    workspace_path: str | None,
    prompt: str,
    system_prompt: str | None,
    history: list[dict[str, str]] | None,
    cli_session_id: str | None,
    cli_binary: str | None,
    logs: list[str],
    on_log: Callable[[str], None] | None,
    prompt_flag: str = "-p",
    supports_append_system_prompt: bool = True,
) -> EngineResult:
    from src.adapters.cli_adapter import chat_generic_cli

    engine_title = f"{agent_type.replace('-cli', '').title()} CLI"
    if engine_title == "Agy CLI":
        engine_title = "Antigravity CLI"

    # Select legacy function dynamically for mock compatibility
    legacy_fn = chat_generic_cli
    if binary_name == "claude":
        legacy_fn = chat_claude_cli

    def _invoke_cli(
        *,
        cli_prompt: str,
        cli_system_prompt: str | None,
        session_id: str | None = None,
        resume_session_id: str | None = None,
    ) -> str:
        if legacy_fn is chat_generic_cli:
            return chat_generic_cli(
                prompt=cli_prompt,
                binary=cli_binary or binary_name,
                conversation_mode=conversation_mode,
                extra_args=extra_args,
                prepend_system_prompt=prepend_system_prompt,
                cwd=workspace_path,
                system_prompt=cli_system_prompt,
                session_id=session_id,
                resume_session_id=resume_session_id,
                on_log=on_log,
                prompt_flag=prompt_flag,
                supports_append_system_prompt=supports_append_system_prompt,
            )
        else:
            return legacy_fn(
                prompt=cli_prompt,
                cwd=workspace_path,
                system_prompt=cli_system_prompt,
                session_id=session_id,
                resume_session_id=resume_session_id,
                binary=cli_binary or binary_name,
                on_log=on_log,
            )

    try:
        if cli_session_id and conversation_mode in ("none", "history_only"):
            replay_prompt = _cli_prompt_from_history(prompt, history)
            _emit_log(logs, on_log, f"Continuing {engine_title} with history replay.")
            output = _invoke_cli(
                cli_prompt=replay_prompt,
                cli_system_prompt=system_prompt,
            )
            output = _ensure_cli_output(
                output,
                invoke=_invoke_cli,
                prompt=prompt,
                history=history,
                system_prompt=system_prompt,
                logs=logs,
                on_log=on_log,
                engine_title=engine_title,
            )
            _emit_log(logs, on_log, f"{engine_title} execution completed successfully.")
            return EngineResult(
                engine=engine_title,
                output=output,
                logs=logs,
                cli_session_id=cli_session_id,
            )

        if cli_session_id:
            _emit_log(logs, on_log, f"Resuming {engine_title} session {cli_session_id}.")
            resume_prompt = _cli_prompt_from_history(prompt, history)
            output = _invoke_cli(
                cli_prompt=resume_prompt,
                cli_system_prompt=None,
                resume_session_id=cli_session_id,
            )
            if 'conversation "' in output.lower() and "not found" in output.lower():
                _emit_log(
                    logs,
                    on_log,
                    f"{engine_title} session resume failed (unknown conversation); replaying history.",
                )
                output = _invoke_cli(
                    cli_prompt=resume_prompt,
                    cli_system_prompt=system_prompt,
                )
            output = _ensure_cli_output(
                output,
                invoke=_invoke_cli,
                prompt=prompt,
                history=history,
                system_prompt=system_prompt,
                logs=logs,
                on_log=on_log,
                engine_title=engine_title,
            )
            _emit_log(logs, on_log, f"{engine_title} session resumed successfully.")
            return EngineResult(
                engine=engine_title,
                output=output,
                logs=logs,
                cli_session_id=cli_session_id,
            )

        history_prompt = _format_history_for_cli_prompt(history).strip()
        bootstrap_prompt = _cli_prompt_from_history(prompt, history)
        new_session_id = str(uuid.uuid4())
        _emit_log(logs, on_log, f"Starting new {engine_title} session {new_session_id}.")
        output = _invoke_cli(
            cli_prompt=bootstrap_prompt,
            cli_system_prompt=system_prompt,
            session_id=new_session_id,
        )
        output = _ensure_cli_output(
            output,
            invoke=_invoke_cli,
            prompt=prompt,
            history=history,
            system_prompt=system_prompt,
            logs=logs,
            on_log=on_log,
            engine_title=engine_title,
        )
        _emit_log(logs, on_log, f"{engine_title} execution completed successfully.")
        return EngineResult(
            engine=engine_title,
            output=output,
            logs=logs,
            cli_session_id=new_session_id,
        )
    except Exception as exc:
        if cli_session_id:
            _emit_log(logs, on_log, f"{engine_title} session resume failed ({exc}); replaying history.")
            try:
                replay_prompt = _cli_prompt_from_history(prompt, history)
                new_session_id = str(uuid.uuid4())
                _emit_log(logs, on_log, f"Starting fallback {engine_title} session {new_session_id}.")
                output = _invoke_cli(
                    cli_prompt=replay_prompt,
                    cli_system_prompt=system_prompt,
                    session_id=new_session_id,
                )
                _emit_log(logs, on_log, f"{engine_title} execution completed successfully.")
                return EngineResult(
                    engine=engine_title,
                    output=output,
                    logs=logs,
                    cli_session_id=new_session_id,
                )
            except Exception as retry_exc:
                _emit_log(logs, on_log, f"{engine_title} recovery failed: {retry_exc}")
                raise RuntimeError(
                    tr(
                        f"Failed to execute task via {engine_title}: {retry_exc}",
                        f"通过 {engine_title} 执行任务失败：{retry_exc}",
                    )
                ) from retry_exc
        _emit_log(logs, on_log, f"{engine_title} execution failed: {exc}")
        raise RuntimeError(
            tr(
                f"Failed to execute task via {engine_title}: {exc}",
                f"通过 {engine_title} 执行任务失败：{exc}",
            )
        ) from exc


def _route_engine_raw(
    agent_name: str,
    prompt: str,
    system_prompt: str | None = None,
    cwd: str | None = None,
    history: list[dict[str, str]] | None = None,
    fallback_tool: str | None = None,
    cli_session_id: str | None = None,
    on_log: Callable[[str], None] | None = None,
    *,
    run_id: str | None = None,
    source: str = "flow",
    session_model_id: str | None = None,
) -> EngineResult:
    agent = find_agent(agent_name)
    agent_type = _resolve_agent_type(agent, fallback_tool)
    from src.provider_registry import resolve_provider_spec

    provider_spec = resolve_provider_spec(agent_type)

    workspace_path = cwd
    if not workspace_path:
        workspace = get_workspace()
        if workspace:
            workspace_path = workspace.get("workspace_path")

    logs: list[str] = []
    _emit_log(
        logs,
        on_log,
        (
            f"[ROUTER] agent={agent_name!r} matched={agent is not None} "
            f"agentType={agent_type!r} "
            f"runtime_strategy={provider_spec.runtime_strategy.value} "
            f"claude_path={resolve_tool_binary('claude-cli')!r} "
            f"connected={'claude-cli' in load_connected_ids()}"
        ),
    )

    if agent_type == "clutch":
        from src.image_router import format_image_reply, generate_image_for_model, is_image_model
        from src.models_config import get_router

        router = get_router()
        spec, model_id = resolve_model_for_agent(router, agent)
        if is_image_model(spec):
            _emit_log(logs, on_log, f"Routing image generation to {spec.name} for agent {agent_name}.")
            api_key = router.resolve_for_model(model_id)[1]
            try:
                result = generate_image_for_model(
                    spec,
                    prompt,
                    api_key=router._require_api_key(spec.provider_id, api_key),
                    on_log=on_log,
                )
                output = format_image_reply(result)
                _emit_log(logs, on_log, f"Image generation completed via {spec.name}.")
                return EngineResult(engine=spec.name, output=output, logs=logs)
            except Exception as exc:
                _emit_log(logs, on_log, f"Image generation failed: {exc}")
                raise RuntimeError(
                    tr(
                        f"Image generation failed ({spec.name}): {exc}",
                        f"生图失败 ({spec.name})：{exc}",
                    )
                ) from exc




    if agent_type == "ollama-cli" and tool_available_for_routing("ollama-cli"):
        from src.adapters.ollama_adapter import chat_ollama
        _emit_log(logs, on_log, f"Routing task to Ollama for agent {agent_name}.")
        try:
            configured_model = str(agent.get("ollamaModel", "")) if agent else ""
            model_tag, output = chat_ollama(
                prompt=prompt,
                model=configured_model or None,
                system_prompt=system_prompt,
                history=history,
                on_log=on_log,
            )
            _emit_log(logs, on_log, f"Ollama execution completed successfully via {model_tag}.")
            return EngineResult(
                engine=f"Ollama ({model_tag})",
                output=output,
                logs=logs,
            )
        except Exception as exc:
            _emit_log(logs, on_log, f"Ollama execution failed: {exc}")
            raise RuntimeError(
                tr(
                    f"Failed to execute task via Ollama: {exc}",
                    f"通过 Ollama 执行任务失败：{exc}",
                )
            ) from exc

    if (
        agent_type in CLI_ROUTING_CONFIGS
        and agent_type != "ollama-cli"
        and tool_available_for_routing(CLI_ROUTING_CONFIGS[agent_type]["tool_id"])
    ):
        config = CLI_ROUTING_CONFIGS[agent_type]
        cli_binary = resolve_tool_binary(config["tool_id"])
        import os
        if not cli_binary and os.environ.get("CLUTCH_E2E_FAKE_HYBRID") == "1":
            cli_binary = config["binary_name"]
            
        display_name = "Antigravity" if config["binary_name"] == "agy" else (
            "Rivet" if config["binary_name"] == "rivet" else config["binary_name"].title()
        )
        _emit_log(logs, on_log, f"Routing task to {display_name} Code (Local CLI) for agent {agent_name}.")
        if cli_binary:
            _emit_log(logs, on_log, f"Using {display_name} binary: {cli_binary}")
        elif config["tool_id"] in load_connected_ids():
            raise RuntimeError(
                tr(
                    f"{display_name} CLI is connected but the `{config['binary_name']}` binary was not found. "
                    f"Restart Clutch after install, or ensure it is on PATH.",
                    f"{display_name} CLI 已连接，但未找到 `{config['binary_name']}` 可执行文件。"
                    f"请安装后重启 Clutch，或确认其在 PATH 中。",
                )
            )

        # Select hybrid function dynamically for mock compatibility
        hybrid_fn = _route_generic_cli_hybrid
        if config["binary_name"] == "claude":
            hybrid_fn = _route_claude_hybrid
        elif config["binary_name"] == "agy":
            hybrid_fn = _route_agy_hybrid

        effective_extra_args = list(config["extra_args"])

        legacy_kwargs = dict(
            agent_type=agent_type,
            binary_name=config["binary_name"],
            conversation_mode=config["conversation_mode"],
            prepend_system_prompt=config["prepend_system_prompt"],
            extra_args=effective_extra_args,
            workspace_path=workspace_path,
            prompt=prompt,
            system_prompt=system_prompt,
            history=history,
            cli_session_id=cli_session_id,
            cli_binary=cli_binary,
            logs=logs,
            on_log=on_log,
            prompt_flag=config.get("prompt_flag", "-p"),
            supports_append_system_prompt=config.get("supports_append_system_prompt", True),
        )

        if source == "flow" and agent_type == "claude-cli":
            from src.shell_exec_runtime import hybrid_pty_shell_command_risky

            if hybrid_pty_shell_command_risky(
                agent_type=agent_type,
                binary=cli_binary or config["binary_name"],
                prompt=prompt,
                system_prompt=system_prompt,
                conversation_mode=config["conversation_mode"],
                extra_args=effective_extra_args,
                prepend_system_prompt=config["prepend_system_prompt"],
                prompt_flag=config.get("prompt_flag", "-p"),
                supports_append_system_prompt=config.get("supports_append_system_prompt", True),
                close_stdin=config.get("close_stdin", False),
            ):
                _emit_log(
                    logs,
                    on_log,
                    "[HYBRID] multiline CLI payload — using legacy subprocess",
                )
                return _route_generic_cli_legacy(**legacy_kwargs)

        try:
            return try_shell_exec_hybrid(
                agent_type=agent_type,
                source=source,
                run_id=run_id,
                workspace_path=workspace_path,
                provider_spec=provider_spec,
                hybrid_route=lambda: hybrid_fn(
                    agent_type=agent_type,
                    binary_name=config["binary_name"],
                    conversation_mode=config["conversation_mode"],
                    prepend_system_prompt=config["prepend_system_prompt"],
                    extra_args=effective_extra_args,
                    run_id=run_id,
                    workspace_path=workspace_path,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history=history,
                    cli_session_id=cli_session_id,
                    cli_binary=cli_binary,
                    logs=logs,
                    on_log=on_log,
                    prompt_flag=config.get("prompt_flag", "-p"),
                    supports_append_system_prompt=config.get("supports_append_system_prompt", True),
                    close_stdin=config.get("close_stdin", False),
                ),
                legacy_route=lambda: _route_generic_cli_legacy(**legacy_kwargs),
                logs=logs,
                on_log=on_log,
                emit_log=_emit_log,
            )
        except Exception as exc:
            _emit_log(logs, on_log, f"{display_name} CLI execution failed: {exc}")
            raise RuntimeError(
                tr(
                    f"Failed to execute task via {display_name} CLI: {exc}",
                    f"通过 {display_name} CLI 执行任务失败：{exc}",
                )
            ) from exc

    if agent_type in CLI_ROUTING_CONFIGS and agent_type != "ollama-cli":
        config = CLI_ROUTING_CONFIGS[agent_type]
        display_name = "Antigravity" if config["binary_name"] == "agy" else (
            "Rivet" if config["binary_name"] == "rivet" else config["binary_name"].title()
        )
        logs.append(
            tr(
                f"Agent {agent_name} requests {display_name} CLI but `{config['binary_name']}` is not installed/connected — falling back to LLM.",
                f"Agent {agent_name} 需要 {display_name} CLI，但未安装或未连接，已回退到 LLM。",
            )
        )
    elif agent_type == "ollama-cli":
        logs.append(
            tr(
                f"Agent {agent_name} requests Ollama but Ollama is not installed/connected — falling back to LLM.",
                f"Agent {agent_name} 需要 Ollama，但未安装或未连接，已回退到 LLM。",
            )
        )

    from src.models_config import get_router

    router = get_router()
    spec, model_id = resolve_model_for_agent(router, agent)
    engine_name = spec.name
    logs.append(f"Routing task to Clutch model ({engine_name}) for agent {agent_name}.")

    chat_history = history
    if not chat_history:
        chat_history = []
        if system_prompt:
            chat_history.append({"role": "system", "content": system_prompt})
        chat_history.append({"role": "user", "content": prompt})

    try:
        output = router.chat(chat_history, model_id=model_id)
        logs.append(f"Clutch model execution completed successfully via {engine_name}.")
        return EngineResult(engine=engine_name, output=output, logs=logs)
    except Exception as exc:
        logs.append(f"Clutch model execution failed: {exc}")
        raise RuntimeError(
            tr(
                f"Cannot reach the configured model ({engine_name}). Add an API key in Settings → Models. ({exc})",
                f"无法访问配置的模型 ({engine_name})。请在 设置 → 模型 配置 API Key。({exc})",
            )
        ) from exc


import re

MODEL_BRAND_REPLACEMENTS = [
    (r"\bAgnes\b", "Gemini"),
    (r"\bagnes\b", "gemini"),
]


def sanitize_engine_output(text: str) -> str:
    if not text:
        return text
    for pattern, replacement in MODEL_BRAND_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    return text


def route_engine(
    agent_name: str,
    prompt: str,
    system_prompt: str | None = None,
    cwd: str | None = None,
    history: list[dict[str, str]] | None = None,
    fallback_tool: str | None = None,
    cli_session_id: str | None = None,
    on_log: Callable[[str], None] | None = None,
    *,
    run_id: str | None = None,
    source: str = "flow",
    session_model_id: str | None = None,
) -> EngineResult:
    res = _route_engine_raw(
        agent_name=agent_name,
        prompt=prompt,
        system_prompt=system_prompt,
        cwd=cwd,
        history=history,
        fallback_tool=fallback_tool,
        cli_session_id=cli_session_id,
        on_log=on_log,
        run_id=run_id,
        source=source,
        session_model_id=session_model_id,
    )
    sanitized_output = sanitize_engine_output(res.output)
    sanitized_raw = sanitize_engine_output(res.raw_output) if res.raw_output else res.raw_output
    sanitized_events = None
    if res.output_events:
        sanitized_events = []
        for event in res.output_events:
            evt = dict(event)
            if "content" in evt and isinstance(evt["content"], str):
                evt["content"] = sanitize_engine_output(evt["content"])
            sanitized_events.append(evt)

    return EngineResult(
        engine=res.engine,
        output=sanitized_output,
        logs=res.logs,
        cli_session_id=res.cli_session_id,
        raw_output=sanitized_raw,
        output_events=sanitized_events,
        shell_recovered=res.shell_recovered,
    )


def _route_claude_hybrid(*args, **kwargs):
    kwargs.pop("agent_type", None)
    kwargs.pop("binary_name", None)
    kwargs.pop("conversation_mode", None)
    kwargs.pop("prepend_system_prompt", None)
    kwargs.pop("extra_args", None)
    kwargs.pop("supports_append_system_prompt", None)
    return _route_generic_cli_hybrid(
        agent_type="claude-cli",
        binary_name="claude",
        conversation_mode="separate",
        prepend_system_prompt=False,
        extra_args=["--dangerously-skip-permissions"],
        *args,
        **kwargs
    )


def _route_agy_hybrid(*args, **kwargs):
    kwargs.pop("agent_type", None)
    kwargs.pop("binary_name", None)
    kwargs.pop("conversation_mode", None)
    kwargs.pop("prepend_system_prompt", None)
    kwargs.pop("extra_args", None)
    kwargs.pop("supports_append_system_prompt", None)
    return _route_generic_cli_hybrid(
        agent_type="antigravity-cli",
        binary_name="agy",
        conversation_mode="none",
        prepend_system_prompt=False,
        supports_append_system_prompt=False,
        extra_args=["--dangerously-skip-permissions"],
        *args,
        **kwargs
    )
