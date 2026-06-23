"""HTTP chat completion for configured LLM providers (stdlib only)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from src.llm.router import ProviderId

_TIMEOUT_SEC = 120
_MAX_TOKENS = 4096


def _post_json(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"LLM API error {exc.code}: {detail}") from exc


def _openai_chat(
    *, base_url: str, api_model: str, api_key: str, messages: list[dict[str, str]]
) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    data = _post_json(
        url,
        headers,
        {"model": api_model, "messages": messages, "max_tokens": _MAX_TOKENS},
    )
    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected OpenAI-compatible response: {data!r}") from exc


def _anthropic_chat(
    *, base_url: str, api_model: str, api_key: str, messages: list[dict[str, str]]
) -> str:
    url = f"{base_url.rstrip('/')}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    system_parts: list[str] = []
    chat_messages: list[dict[str, str]] = []
    for message in messages:
        role = message["role"]
        content = message["content"]
        if role == "system":
            system_parts.append(content)
            continue
        chat_messages.append(
            {"role": "user" if role == "user" else "assistant", "content": content}
        )
    body: dict[str, Any] = {
        "model": api_model,
        "max_tokens": _MAX_TOKENS,
        "messages": chat_messages or [{"role": "user", "content": ""}],
    }
    if system_parts:
        body["system"] = "\n\n".join(system_parts)
    data = _post_json(url, headers, body)
    try:
        blocks = data["content"]
        return "".join(str(block.get("text", "")) for block in blocks).strip()
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Anthropic response: {data!r}") from exc


def http_chat_complete(
    *,
    provider_id: ProviderId,
    base_url: str,
    api_model: str,
    api_key: str,
    messages: list[dict[str, str]],
) -> str:
    if provider_id == "anthropic":
        return _anthropic_chat(
            base_url=base_url, api_model=api_model, api_key=api_key, messages=messages
        )
    return _openai_chat(
        base_url=base_url, api_model=api_model, api_key=api_key, messages=messages
    )
