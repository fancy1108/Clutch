"""Built-in Clutch tools (virtual MCP server, no external MCP subprocess)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import difflib
from pathlib import Path
from typing import Any

from src.builtin_tools_workspace import _MAX_CMD_OUTPUT_CHARS


def _tool_generate_image(arguments: dict[str, Any]) -> str:
    from src.image_router import (
        format_image_reply,
        generate_image_for_model,
        persist_generated_image,
        resolve_configured_image_model,
    )

    prompt = str(arguments.get("prompt") or "").strip()
    if not prompt:
        return "Error executing tool: generate_image requires `prompt`"
    resolved = resolve_configured_image_model()
    if resolved is None:
        return (
            "Error executing tool: no image model API key configured. "
            "Add an image model key in Settings → Models (e.g. Agnes Image), "
            "then retry generate_image. Do NOT write an HTML page as a substitute."
        )
    spec, api_key = resolved
    stem = str(arguments.get("filename_stem") or "").strip() or None
    try:
        result = generate_image_for_model(spec, prompt, api_key=api_key)
        result = persist_generated_image(result, filename_stem=stem)
    except Exception as exc:
        return (
            f"Error executing tool: image generation failed ({exc}). "
            "Do NOT write an HTML page as a substitute."
        )
    local = str(result.get("local_media_path") or "").strip()
    # Keep tool payload small (no multi‑MB base64 in the ReAct transcript).
    payload = {
        "ok": True,
        "model_id": spec.id,
        "local_media_path": local,
        "message": (
            f"Image generated with {spec.name} and saved to `{local}`. "
            "Include that path in your final reply; do not invent an HTML substitute."
            if local
            else f"Image generated with {spec.name}."
        ),
        # Optional short preview for Chat UI if the runner surfaces tool markdown later.
        "preview_markdown": format_image_reply(result) if local else "",
    }
    return json.dumps(payload, ensure_ascii=False)


def _tool_generate_video(arguments: dict[str, Any]) -> str:
    from src.video_router import (
        format_video_reply,
        generate_video_for_model,
        persist_generated_video,
        resolve_configured_video_model,
    )

    prompt = str(arguments.get("prompt") or "").strip()
    if not prompt:
        return "Error executing tool: generate_video requires `prompt`"
    resolved = resolve_configured_video_model()
    if resolved is None:
        return (
            "Error executing tool: no video model API key configured. "
            "Add a video model key in Settings → Models (e.g. Agnes Video), "
            "then retry generate_video. Do NOT write an HTML page as a substitute."
        )
    spec, api_key = resolved
    try:
        result = generate_video_for_model(spec, prompt, api_key=api_key)
        result = persist_generated_video(result)
    except Exception as exc:
        return (
            f"Error executing tool: video generation failed ({exc}). "
            "Do NOT write an HTML page as a substitute."
        )
    local = str(result.get("local_media_path") or "").strip()
    payload = {
        "ok": True,
        "model_id": spec.id,
        "local_media_path": local,
        "message": (
            f"Video generated with {spec.name} and saved to `{local}`."
            if local
            else f"Video generated with {spec.name}."
        ),
        "preview_markdown": format_video_reply(result) if local else "",
    }
    return json.dumps(payload, ensure_ascii=False)


def _tool_git_status(arguments: dict[str, Any]) -> str:
    del arguments
    from src.workspace import WorkspaceError, require_workspace

    try:
        root = require_workspace()
    except WorkspaceError as exc:
        return f"Error executing tool: {exc}"
    proc = _run_git(["status", "--short", "--branch"], cwd=root)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "git status failed").strip()
        return f"Error executing tool: {err}"
    out = (proc.stdout or "").strip()
    return out or "(clean)"


def _tool_git_diff(arguments: dict[str, Any]) -> str:
    from src.workspace import WorkspaceError, require_workspace

    try:
        root = require_workspace()
    except WorkspaceError as exc:
        return f"Error executing tool: {exc}"
    staged = bool(arguments.get("staged"))
    paths = [
        str(p).strip()
        for p in (arguments.get("paths") or [])
        if str(p).strip()
    ]
    args = ["diff", "--staged"] if staged else ["diff"]
    if paths:
        args.extend(["--", *paths])
    proc = _run_git(args, cwd=root)
    if proc.returncode not in (0, 1):
        err = (proc.stderr or proc.stdout or "git diff failed").strip()
        return f"Error executing tool: {err}"
    out = proc.stdout or ""
    if len(out) > _MAX_CMD_OUTPUT_CHARS:
        out = out[:_MAX_CMD_OUTPUT_CHARS] + "\n…[truncated]"
    return out.strip() or "(no diff)"


def _tool_git_commit(arguments: dict[str, Any]) -> str:
    from src.workspace import WorkspaceError, require_workspace

    message = str(arguments.get("message") or "").strip()
    if not message:
        return "Error executing tool: git_commit requires `message`"
    try:
        root = require_workspace()
    except WorkspaceError as exc:
        return f"Error executing tool: {exc}"
    paths = [
        str(p).strip()
        for p in (arguments.get("paths") or [])
        if str(p).strip()
    ]
    if paths:
        add = _run_git(["add", "--", *paths], cwd=root)
    else:
        add = _run_git(["add", "-A"], cwd=root)
    if add.returncode != 0:
        err = (add.stderr or add.stdout or "git add failed").strip()
        return f"Error executing tool: {err}"
    commit = _run_git(["commit", "-m", message], cwd=root)
    if commit.returncode != 0:
        err = (commit.stderr or commit.stdout or "git commit failed").strip()
        return f"Error executing tool: {err}"
    head = _run_git(["rev-parse", "--short", "HEAD"], cwd=root)
    sha = (head.stdout or "").strip() if head.returncode == 0 else ""
    return json.dumps(
        {
            "ok": True,
            "message": message,
            "sha": sha,
            "stdout": (commit.stdout or "").strip(),
        },
        ensure_ascii=False,
    )


def _tool_web_fetch(arguments: dict[str, Any]) -> str:
    from src.web_fetch_util import (
        extract_serp_query,
        fetch_url_text,
        is_search_engine_serp_url,
        serp_redirect_error_message,
    )

    url = str(arguments.get("url") or "").strip()
    if not url:
        return "Error executing tool: web_fetch requires `url`"
    try:
        timeout = int(arguments.get("timeout_sec") or 20)
    except (TypeError, ValueError):
        timeout = 20

    # Flash models often web_fetch google.com/search — rewrite to web_search so
    # the turn can continue (and loop fuse is not burned on policy rejects).
    if is_search_engine_serp_url(url):
        from src.preferences_storage import load_allow_network
        from src.web_search_util import search_web

        query = extract_serp_query(url)
        if load_allow_network() and query:
            try:
                payload = search_web(query, max_results=5)
            except Exception as exc:
                return f"Error executing tool: {serp_redirect_error_message(url)} ({exc})"
            payload = {
                **payload,
                "redirected_from_web_fetch": True,
                "original_url": url,
                "note": (
                    "You called web_fetch on a search-engine results URL. "
                    "Clutch ran web_search instead. Next: web_fetch at most 1–2 "
                    "concrete article URLs from results[], then answer or write the HTML — "
                    "do not fetch google.com/search / bing.com/search again."
                ),
            }
            return json.dumps(payload, ensure_ascii=False)
        return f"Error executing tool: {serp_redirect_error_message(url)}"

    try:
        payload = fetch_url_text(url, timeout_sec=timeout)
    except ValueError as exc:
        return f"Error executing tool: {exc}"
    return json.dumps(payload, ensure_ascii=False)


def _tool_web_search(arguments: dict[str, Any]) -> str:
    from src.preferences_storage import load_allow_network
    from src.web_search_util import search_web

    if not load_allow_network():
        return (
            "Error executing tool: web_search is disabled. "
            "Enable Settings → General → Allow network to search the web."
        )
    query = str(arguments.get("query") or "").strip()
    if not query:
        return "Error executing tool: web_search requires `query`"
    try:
        max_results = int(arguments.get("max_results") or 5)
    except (TypeError, ValueError):
        max_results = 5
    try:
        payload = search_web(query, max_results=max_results)
    except ValueError as exc:
        return f"Error executing tool: {exc}"
    except Exception as exc:
        from src.web_fetch_util import _friendly_network_error

        return f"Error executing tool: web search failed: {_friendly_network_error(exc)}"
    return json.dumps(payload, ensure_ascii=False)


def _run_git(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

