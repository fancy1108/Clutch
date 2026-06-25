"""HTTP chat completion for configured LLM providers (stdlib only) with Tool Calling."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from src.credentials.claude_code import resolve_anthropic_transport
from src.llm.router import ProviderId

_TIMEOUT_SEC = 120
_MAX_TOKENS = 4096


def _anthropic_uses_messages_api(base_url: str) -> bool:
    """True when the endpoint speaks native Anthropic /messages (not OpenAI-compat gateways)."""
    host = urlparse(base_url.rstrip("/")).netloc.lower()
    if host in ("api.anthropic.com",):
        return True
    if host.startswith("127.0.0.1") or host.startswith("localhost"):
        return True
    return False


def _post_json(
    url: str, headers: dict[str, str], body: dict[str, Any], *, timeout_sec: float = _TIMEOUT_SEC
) -> dict[str, Any]:
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"LLM API error {exc.code}: {detail}") from exc


def _format_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize chat history for OpenAI-compatible gateways (strict serde on many proxies)."""
    formatted: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role", ""))
        if role == "system":
            content = message.get("content")
            if content:
                formatted.append({"role": "system", "content": str(content)})
            continue
        if role == "assistant":
            out: dict[str, Any] = {
                "role": "assistant",
                "content": message.get("content") or "",
            }
            if message.get("tool_calls"):
                tool_calls: list[dict[str, Any]] = []
                for tool_call in message["tool_calls"]:
                    func = tool_call.get("function") or {}
                    args = func.get("arguments", "{}")
                    if not isinstance(args, str):
                        args = json.dumps(args)
                    tool_calls.append(
                        {
                            "id": tool_call["id"],
                            "type": tool_call.get("type") or "function",
                            "function": {
                                "name": func["name"],
                                "arguments": args,
                            },
                        }
                    )
                out["tool_calls"] = tool_calls
            formatted.append(out)
            continue
        if role == "tool":
            formatted.append(
                {
                    "role": "tool",
                    "tool_call_id": message["tool_call_id"],
                    "content": str(message.get("content") or ""),
                }
            )
            continue
        formatted.append(
            {
                "role": role,
                "content": str(message.get("content") or ""),
            }
        )
    return formatted


def _openai_chat(
    *,
    base_url: str,
    api_model: str,
    api_key: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    timeout_sec: float = _TIMEOUT_SEC,
) -> dict[str, Any] | str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    body: dict[str, Any] = {
        "model": api_model,
        "messages": _format_openai_messages(messages),
        "max_tokens": _MAX_TOKENS,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    data = _post_json(url, headers, body, timeout_sec=timeout_sec)
    try:
        msg = data["choices"][0]["message"]
        if tools and msg.get("tool_calls"):
            return msg
        return str(msg.get("content") or "").strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected OpenAI-compatible response: {data!r}") from exc


def _anthropic_chat(
    *,
    base_url: str,
    api_model: str,
    api_key: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    timeout_sec: float = _TIMEOUT_SEC,
) -> dict[str, Any] | str:
    base_url, api_model, api_key = resolve_anthropic_transport(
        base_url=base_url, api_model=api_model, api_key=api_key
    )
    url = f"{base_url.rstrip('/')}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    system_parts: list[str] = []
    anthropic_messages: list[dict[str, Any]] = []

    for message in messages:
        role = message["role"]
        content = message.get("content")
        if role == "system":
            if content:
                system_parts.append(content)
            continue

        if role == "assistant" and message.get("tool_calls"):
            content_list: list[dict[str, Any]] = []
            if content:
                content_list.append({"type": "text", "text": content})
            for tc in message["tool_calls"]:
                args = tc["function"]["arguments"]
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        pass
                content_list.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "input": args,
                })
            anthropic_messages.append({"role": "assistant", "content": content_list})
        elif role == "tool" or (role == "user" and "tool_call_id" in message):
            tc_id = message.get("tool_call_id") or message.get("id")
            tool_msg = {
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tc_id,
                    "content": content,
                }],
            }
            if (
                anthropic_messages
                and anthropic_messages[-1]["role"] == "user"
                and isinstance(anthropic_messages[-1]["content"], list)
                and anthropic_messages[-1]["content"][0]["type"] == "tool_result"
            ):
                anthropic_messages[-1]["content"].append({
                    "type": "tool_result",
                    "tool_use_id": tc_id,
                    "content": content,
                })
            else:
                anthropic_messages.append(tool_msg)
        else:
            anthropic_messages.append({
                "role": "user" if role == "user" else "assistant",
                "content": content or "",
            })

    body: dict[str, Any] = {
        "model": api_model,
        "max_tokens": _MAX_TOKENS,
        "messages": anthropic_messages or [{"role": "user", "content": ""}],
    }
    if system_parts:
        body["system"] = "\n\n".join(system_parts)
    if tools:
        anthropic_tools = []
        for t in tools:
            func = t["function"]
            anthropic_tools.append({
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
            })
        body["tools"] = anthropic_tools

    data = _post_json(url, headers, body, timeout_sec=timeout_sec)
    try:
        blocks = data["content"]
        tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
        text_blocks = [b for b in blocks if b.get("type") == "text"]
        text_content = "".join(str(b.get("text", "")) for b in text_blocks).strip()

        if tools and tool_uses:
            tool_calls = []
            for tu in tool_uses:
                tool_calls.append({
                    "id": tu["id"],
                    "type": "function",
                    "function": {
                        "name": tu["name"],
                        "arguments": json.dumps(tu["input"]),
                    },
                })
            return {
                "role": "assistant",
                "content": text_content or None,
                "tool_calls": tool_calls,
            }
        return text_content
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Anthropic response: {data!r}") from exc


def http_chat_complete(
    *,
    provider_id: ProviderId,
    base_url: str,
    api_model: str,
    api_key: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    timeout_sec: float = _TIMEOUT_SEC,
) -> dict[str, Any] | str:
    if provider_id == "anthropic":
        resolved_base, resolved_model, resolved_key = resolve_anthropic_transport(
            base_url=base_url, api_model=api_model, api_key=api_key
        )
        # Third-party gateways (e.g. apihub.agnes-ai.com) speak OpenAI-compatible
        # /chat/completions; native /messages + Anthropic tool schema breaks on those hosts.
        if not _anthropic_uses_messages_api(resolved_base):
            return _openai_chat(
                base_url=resolved_base,
                api_model=resolved_model,
                api_key=resolved_key,
                messages=messages,
                tools=tools,
                timeout_sec=timeout_sec,
            )
        return _anthropic_chat(
            base_url=resolved_base,
            api_model=resolved_model,
            api_key=resolved_key,
            messages=messages,
            tools=tools,
            timeout_sec=timeout_sec,
        )
    return _openai_chat(
        base_url=base_url,
        api_model=api_model,
        api_key=api_key,
        messages=messages,
        tools=tools,
        timeout_sec=timeout_sec,
    )

