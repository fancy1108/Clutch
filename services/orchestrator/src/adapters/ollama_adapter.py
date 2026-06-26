"""Ollama adapter for local model API execution (M4-04)."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from collections.abc import Callable
from typing import Any

from src.llm.router import ModelSpec


def _fetch_ollama_tags() -> list[dict[str, Any]]:
    url = "http://localhost:11434/api/tags"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    models = data.get("models", [])
    return models if isinstance(models, list) else []


def get_ollama_models() -> list[str]:
    try:
        return [str(m["name"]) for m in _fetch_ollama_tags() if m.get("name")]
    except Exception as exc:
        raise RuntimeError(f"Failed to query Ollama models from http://localhost:11434/api/tags: {exc}") from exc


def ollama_model_supports_tools(model_tag: str) -> bool:
    """Return whether the local Ollama tag advertises tool-calling support."""
    try:
        for entry in _fetch_ollama_tags():
            if str(entry.get("name", "")) == model_tag:
                capabilities = entry.get("capabilities")
                if isinstance(capabilities, list):
                    return "tools" in capabilities
                return False
    except Exception:
        return False
    return False


def ollama_model_supports_vision(model_tag: str) -> bool:
    """Return whether the local Ollama tag advertises vision input."""
    try:
        for entry in _fetch_ollama_tags():
            if str(entry.get("name", "")) == model_tag:
                capabilities = entry.get("capabilities")
                if isinstance(capabilities, list):
                    return "vision" in capabilities
                return False
    except Exception:
        return False
    return False


def model_supports_vision(spec: ModelSpec) -> bool:
    if getattr(spec, "provider_id", None) == "ollama":
        return ollama_model_supports_vision(spec.api_model)
    return True


def model_supports_tool_calling(spec: ModelSpec) -> bool:
    if getattr(spec, "provider_id", None) == "ollama":
        return ollama_model_supports_tools(spec.api_model)
    return True

def pick_best_ollama_model(models: list[str]) -> str:
    if not models:
        raise RuntimeError("No models found in Ollama. Please run `ollama pull <model>` first.")
    
    # Score each model based on prioritization rules
    scored_models = []
    for model in models:
        lower_model = model.lower()
        if "qwen3.6" in lower_model:
            score = 100
        elif "qwen2.5-coder" in lower_model:
            score = 90
        elif "llama3" in lower_model:
            score = 80
        elif "qwen" in lower_model:
            score = 50
        else:
            score = 10
        scored_models.append((score, model))
    
    # Sort descending by score, pick the highest scoring model. Preserve list order as fallback.
    scored_models.sort(key=lambda x: x[0], reverse=True)
    return scored_models[0][1]

def chat_ollama(
    prompt: str,
    *,
    model: str | None = None,
    system_prompt: str | None = None,
    history: list[dict[str, str]] | None = None,
    on_log: Callable[[str], None] | None = None,
) -> tuple[str, str]:
    """
    Sends chat request to local Ollama instance.
    Returns: (selected_model_name, response_text)
    """
    if model:
        selected_model = model
        if on_log:
            on_log(f"[OLLAMA] Using agent-configured model: {selected_model}")
    else:
        if on_log:
            on_log("[OLLAMA] Discovering local Ollama models...")
        models = get_ollama_models()
        selected_model = pick_best_ollama_model(models)
        if on_log:
            on_log(f"[OLLAMA] Selected best Ollama model: {selected_model}")
    
    # Build messages
    formatted_messages = []
    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_messages.append({"role": role, "content": content})
    else:
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.append({"role": "user", "content": prompt})

    url = "http://localhost:11434/v1/chat/completions"
    body = {
        "model": selected_model,
        "messages": formatted_messages,
    }
    
    if on_log:
        on_log("[OLLAMA] Sending request to Ollama chat completions endpoint...")
        
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            output = data["choices"][0]["message"]["content"]
            return selected_model, output
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Ollama API error {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to communicate with Ollama: {exc}") from exc
