"""Execute workflow agent_task nodes via configured LLM (M3 agent leg)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.chat_events import chat_message


@dataclass(frozen=True)
class AgentTaskResult:
    agent: str
    output: str
    logs: list[str]
    message: dict[str, Any]


def execute_agent_task(node_data: dict[str, Any], *, instruction: str = "") -> AgentTaskResult:
    agent = str(node_data.get("agent", "Builder"))
    task_instruction = instruction.strip() or str(node_data.get("instruction", "")).strip()
    tool = str(node_data.get("tool", "llm") or "llm")
    label = str(node_data.get("label", "")).strip()

    logs = [f"[{agent.upper()}] Starting: {label or task_instruction[:120] or 'agent task'}"]

    if not task_instruction:
        output = "No task instruction was provided for this agent step."
        logs.append(f"[{agent.upper()}] Skipped — empty instruction")
        return AgentTaskResult(
            agent=agent,
            output=output,
            logs=logs,
            message=chat_message(agent, output),
        )

    if tool in {"claude-cli", "llm", "cursor", ""}:
        from src.models_config import get_router

        router = get_router()
        model = router.get_active_model()
        prompt = (
            f"You are the {agent} agent in a supervised software workflow.\n\n"
            f"Task:\n{task_instruction}\n\n"
            "Respond concisely with what you would do, files touched, and next steps."
        )
        try:
            output = router.chat([{"role": "user", "content": prompt}])
            logs.append(f"[{agent.upper()}] Completed via {model.name}")
        except RuntimeError as exc:
            output = (
                f"Could not run task with {model.name}. "
                f"Configure an API key in Settings → Models. ({exc})"
            )
            logs.append(f"[{agent.upper()}] ERROR: {exc}")
    else:
        output = f"Tool {tool!r} is not wired yet for agent tasks."
        logs.append(f"[{agent.upper()}] {output}")

    logs.append(f"[{agent.upper()}] Output: {len(output)} chars")
    return AgentTaskResult(
        agent=agent,
        output=output,
        logs=logs,
        message=chat_message(agent, output),
    )
