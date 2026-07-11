"""Design sessions — Stitch-like two-phase generate (spec → UI) under workspace (D36)."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.workspace import WorkspaceError, require_workspace
from src.design.builtin_presets import normalize_preset_id, resolve_builtin_spec
from src.design.layout_patterns import (
    detect_layout_pattern,
    enrich_fallback_spec,
    fewshot_for_pattern,
    layout_wrapper_hint,
    parse_review_score,
    review_threshold,
)

logger = logging.getLogger(__name__)

DESIGN_ROOT = ".clutch/design/sessions"
MANIFEST = "manifest.json"
DESIGN_MD = "DESIGN.md"
SPEC_JSON = "spec.json"
THUMBNAIL_SVG = "thumbnail.svg"
THUMBNAIL_PNG = "thumbnail.png"
_DEFAULT_FOLDER_TITLES = frozenset(
    {
        "",
        "new design",
        "new-design",
        "design",
        "untitled",
        "新建设计",
    }
)


def _append_design_run_log(run_id: str, message: str, *, reasoning: str | None = None) -> None:
    """Best-effort: mirror Design progress into persisted run terminal_logs (Terminal panel)."""
    if not run_id:
        return
    if reasoning and reasoning.strip():
        _append_design_run_log(
            run_id,
            f"[DESIGN:REASONING] {reasoning.strip().replace(chr(10), ' ↵ ')}",
        )
    if not message:
        return
    try:
        from src.run_state_store import load_run_state, save_run_state
        from src.terminal_logs import TAG_DESIGN, stamp_log_line, tagged

        state = load_run_state(run_id)
        if state is None:
            return
        line = stamp_log_line(tagged(TAG_DESIGN, message))
        logs = list(state.get("terminal_logs") or [])
        if logs and logs[-1] == line:
            return
        logs.append(line)
        state["terminal_logs"] = logs[-200:]
        save_run_state(state)
    except Exception:
        logger.debug("design terminal log skip run_id=%s", run_id, exc_info=True)


_DESIGN_CARD_GAP = 48
_DESIGN_CANVAS_ORIGIN = 40
_DESIGN_AGENT_LOG_W = 272
_DESIGN_SPEC_W = 300
_DESIGN_SOURCE_W = 300
_DESIGN_SPEC_UI_GAP = 56
_DESIGN_ROW_Y = 56
_DESIGN_UI_FRAME = {"web": 720, "app": 300}


def _ui_frame_width(device: str) -> int:
    return _DESIGN_UI_FRAME.get((device or "web").strip().lower(), 720)


def _spec_origin_x(*, has_source: bool = False) -> int:
    """X for the spec card — after Agent Log column (and optional source)."""
    x = _DESIGN_CANVAS_ORIGIN + _DESIGN_AGENT_LOG_W + _DESIGN_CARD_GAP
    if has_source:
        x += _DESIGN_SOURCE_W + _DESIGN_CARD_GAP
    return x


def _default_ui_origin_x(*, has_source: bool = False) -> int:
    """Stitch-like x for the first UI artboard (agentLog → spec → ui)."""
    return _spec_origin_x(has_source=has_source) + _DESIGN_SPEC_W + _DESIGN_SPEC_UI_GAP


def _ui_layout_step(device: str) -> int:
    return _ui_frame_width(device) + _DESIGN_CARD_GAP


_preview_procs: dict[str, dict[str, Any]] = {}
_preview_lock = threading.Lock()
_generate_jobs: dict[str, threading.Thread] = {}
_generate_lock = threading.Lock()
_LLM_TIMEOUT_SEC = 45.0
_LLM_UI_TIMEOUT_SEC = 90.0
_DESIGN_REVIEW_ENABLED = os.environ.get("CLUTCH_DESIGN_REVIEW", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


class DesignError(RuntimeError):
    pass


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _safe_folder_slug(text: str, *, max_len: int = 40) -> str:
    """Filesystem-safe folder label — keeps CJK so users can recognize the session."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", (text or "").strip())
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip(".-")
    if not cleaned:
        return "design"
    return cleaned[:max_len].rstrip(".-") or "design"


def _session_folder_name(run_id: str, *, title: str, device: str = "web") -> str:
    """Human-readable folder: `{slug}-{web|mobile}__{run_id}` (run_id keeps uniqueness)."""
    slug = _safe_folder_slug(title)
    device_tag = "mobile" if (device or "web").strip().lower() == "app" else "web"
    return f"{slug}-{device_tag}__{run_id}"


def _find_existing_session_dir(root: Path, run_id: str) -> Path | None:
    """Resolve session dir: exact `run_id` (legacy) or `*__{run_id}` (readable)."""
    if not run_id:
        return None
    exact = root / run_id
    if exact.is_dir():
        return exact
    suffix = f"__{run_id}"
    if not root.is_dir():
        return None
    matches = [p for p in root.iterdir() if p.is_dir() and p.name.endswith(suffix)]
    if not matches:
        return None
    # Prefer the most recently modified if duplicates somehow exist.
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def _session_dir(run_id: str, workspace: Path | None = None) -> Path:
    root = (workspace or require_workspace()) / DESIGN_ROOT
    root.mkdir(parents=True, exist_ok=True)
    existing = _find_existing_session_dir(root, run_id)
    if existing is not None:
        return existing
    path = root / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def sync_session_folder_name(
    run_id: str,
    *,
    title: str = "",
    device: str = "web",
    workspace: Path | None = None,
) -> Path:
    """Rename Design artifact folder to a readable slug when the session has a real title."""
    root = (workspace or require_workspace()) / DESIGN_ROOT
    root.mkdir(parents=True, exist_ok=True)
    current = _find_existing_session_dir(root, run_id)
    if current is None:
        current = _session_dir(run_id, workspace=workspace)

    label = (title or "").strip()
    is_default = label.lower() in _DEFAULT_FOLDER_TITLES
    has_ui = _first_screen_with_ui(current) is not None
    if is_default and not has_ui:
        desired_name = run_id
    else:
        desired_name = _session_folder_name(
            run_id,
            title=label or "design",
            device=device,
        )

    desired = root / desired_name
    if current.resolve() == desired.resolve():
        return current
    if desired.exists():
        return current
    try:
        current.rename(desired)
        logger.info(
            "design session folder renamed run_id=%s from=%s to=%s",
            run_id,
            current.name,
            desired.name,
        )
        return desired
    except OSError as exc:
        logger.warning("design session folder rename failed run_id=%s err=%s", run_id, exc)
        return current


def delete_session_artifacts(run_id: str) -> None:
    """Remove `.clutch/design/sessions/*__{run_id}` (or legacy `{run_id}`) when a session is deleted."""
    if not run_id:
        return
    try:
        stop_preview(run_id)
    except Exception:
        pass
    try:
        root = require_workspace() / DESIGN_ROOT
    except WorkspaceError:
        return
    path = _find_existing_session_dir(root, run_id)
    if path is None or not path.is_dir():
        return
    try:
        shutil.rmtree(path)
        logger.info("design session artifacts deleted run_id=%s path=%s", run_id, path)
    except OSError as exc:
        logger.warning("design session artifacts delete failed run_id=%s err=%s", run_id, exc)


def prune_orphan_session_dirs(*, keep_run_ids: set[str]) -> list[str]:
    """Delete Design artifact folders whose run_id is not in the live session history."""
    try:
        root = require_workspace() / DESIGN_ROOT
    except WorkspaceError:
        return []
    if not root.is_dir():
        return []
    keep = {str(x) for x in keep_run_ids if x}
    removed: list[str] = []
    for child in list(root.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        run_id = name.rsplit("__", 1)[-1] if "__" in name else name
        if run_id in keep:
            continue
        with _generate_lock:
            job = _generate_jobs.get(run_id)
            if job is not None and job.is_alive():
                continue
        try:
            shutil.rmtree(child)
            removed.append(name)
            logger.info("design orphan folder pruned path=%s", child)
        except OSError as exc:
            logger.warning("design orphan prune failed path=%s err=%s", child, exc)
    return removed


def _read_manifest(session_dir: Path) -> dict[str, Any]:
    path = session_dir / MANIFEST
    if not path.is_file():
        raise DesignError("Design session not found")
    last_err: Exception | None = None
    for _ in range(12):
        try:
            raw = path.read_text(encoding="utf-8").strip()
            if not raw:
                time.sleep(0.01)
                continue
            return json.loads(raw)
        except (json.JSONDecodeError, OSError) as exc:
            last_err = exc
            time.sleep(0.01)
    raise DesignError(f"Design session manifest unreadable: {last_err}")


def _write_manifest(session_dir: Path, manifest: dict[str, Any]) -> None:
    """Atomic replace so concurrent readers never see a truncated JSON file."""
    manifest["updated_at"] = _now_iso()
    path = session_dir / MANIFEST
    tmp = session_dir / f".{MANIFEST}.{os.getpid()}.{threading.get_ident()}.tmp"
    payload = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(payload, encoding="utf-8")
    last_err: PermissionError | None = None
    for _ in range(12):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as exc:
            if not _is_windows():
                raise
            last_err = exc
            time.sleep(0.01)
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    if last_err is not None:
        raise last_err


def _update_process_status(
    session_dir: Path,
    manifest: dict[str, Any],
    *,
    text: str,
    status: str,
    model_id: str | None = None,
    model_name: str | None = None,
) -> None:
    """Refresh the latest assistant line (in-flight heartbeat for polling UI)."""
    log = list(manifest.get("process_log") or [])
    updated = False
    for i in range(len(log) - 1, -1, -1):
        entry = log[i]
        if entry.get("role") != "assistant" or entry.get("kind") in {"model", "tokens"}:
            continue
        next_entry = {**entry, "text": text, "status": status, "at": _now_iso()}
        # Preserve prior model tags; refresh when caller provides the active model.
        if model_name:
            next_entry["model_id"] = model_id
            next_entry["model_name"] = model_name
        elif manifest.get("model_name") and not next_entry.get("model_name"):
            next_entry["model_id"] = manifest.get("model_id")
            next_entry["model_name"] = manifest.get("model_name")
        log[i] = next_entry
        updated = True
        break
    if not updated:
        entry: dict[str, Any] = {"role": "assistant", "text": text, "status": status, "at": _now_iso()}
        name = model_name or manifest.get("model_name")
        if name:
            entry["model_id"] = model_id or manifest.get("model_id")
            entry["model_name"] = name
        log.append(entry)
    manifest["process_log"] = log
    manifest["status"] = status
    _write_manifest(session_dir, manifest)


def _append_process_status(
    session_dir: Path,
    manifest: dict[str, Any],
    *,
    text: str,
    status: str,
    model_id: str | None = None,
    model_name: str | None = None,
) -> None:
    """Append a new assistant process_log entry (phase transition)."""
    log = list(manifest.get("process_log") or [])
    entry: dict[str, Any] = {"role": "assistant", "text": text, "status": status, "at": _now_iso()}
    name = model_name or manifest.get("model_name")
    if name:
        entry["model_id"] = model_id or manifest.get("model_id")
        entry["model_name"] = name
    log.append(entry)
    manifest["process_log"] = log
    manifest["status"] = status
    _write_manifest(session_dir, manifest)


def _resolve_model_label(router: Any, model_id: str) -> tuple[str, str]:
    try:
        spec, _ = router.resolve_for_model(model_id)
        return model_id, str(spec.name or model_id)
    except Exception:
        return model_id, model_id


def _append_model_process_entry(
    log: list[dict[str, Any]],
    *,
    model_id: str,
    model_name: str,
    insert_after_user: bool = False,
) -> None:
    entry = {
        "role": "assistant",
        "kind": "model",
        "text": f"Model: {model_name}",
        "model_id": model_id,
        "model_name": model_name,
        "status": "info",
        "at": _now_iso(),
    }
    if insert_after_user:
        for i in range(len(log) - 1, -1, -1):
            if log[i].get("role") == "user":
                log.insert(i + 1, entry)
                return
    log.append(entry)


def _round_has_model_entry(log: list[dict[str, Any]]) -> bool:
    """True when the current round (after the latest user line) already has a Model entry."""
    for item in reversed(log):
        if item.get("role") == "user":
            break
        if item.get("kind") == "model":
            return True
    return False


def _stamp_session_model(
    manifest: dict[str, Any],
    router: Any,
    *,
    model_id: str,
    process_log: list[dict[str, Any]] | None = None,
    record_in_log: bool = True,
    insert_after_user: bool = False,
) -> tuple[str, str]:
    """Persist model on the session manifest and optionally append an Agent Log line."""
    model_id, model_name = _resolve_model_label(router, model_id)
    manifest["model_id"] = model_id
    manifest["model_name"] = model_name
    if record_in_log:
        # Mutate the caller's list when provided so generate/iterate stay in sync.
        log = process_log if process_log is not None else list(manifest.get("process_log") or [])
        if not _round_has_model_entry(log):
            _append_model_process_entry(
                log,
                model_id=model_id,
                model_name=model_name,
                insert_after_user=insert_after_user,
            )
        manifest["process_log"] = log
    return model_id, model_name


def _llm_text(result: object) -> str:
    if isinstance(result, dict):
        content = result.get("content")
        return str(content).strip() if content else ""
    return str(result).strip()


def _empty_token_usage() -> dict[str, int]:
    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def _merge_token_usage(*usages: dict[str, int] | None) -> dict[str, int]:
    merged = _empty_token_usage()
    for usage in usages:
        if not usage:
            continue
        merged["input_tokens"] += int(usage.get("input_tokens") or 0)
        merged["output_tokens"] += int(usage.get("output_tokens") or 0)
    merged["total_tokens"] = merged["input_tokens"] + merged["output_tokens"]
    return merged


def _estimate_token_usage(
    *,
    prompt: str = "",
    response_text: str = "",
    reasoning: str | None = None,
) -> dict[str, int]:
    def _count(text: str) -> int:
        return len((text or "").split())

    input_tokens = _count(prompt)
    output_tokens = _count(response_text) + _count(reasoning or "")
    if input_tokens == 0 and output_tokens == 0:
        return _empty_token_usage()
    if output_tokens == 0:
        output_tokens = max(1, input_tokens // 4)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def _normalize_usage_dict(raw: object) -> dict[str, int] | None:
    if not isinstance(raw, dict):
        return None
    if "prompt_tokens" in raw or "completion_tokens" in raw:
        inp = int(raw.get("prompt_tokens") or 0)
        out = int(raw.get("completion_tokens") or 0)
        total = int(raw.get("total_tokens") or (inp + out))
        return {"input_tokens": inp, "output_tokens": out, "total_tokens": total}
    if "input_tokens" in raw or "output_tokens" in raw:
        inp = int(raw.get("input_tokens") or 0)
        out = int(raw.get("output_tokens") or 0)
        return {"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out}
    return None


def _usage_from_llm_result(
    result: object,
    *,
    prompt: str = "",
    response_text: str = "",
    reasoning: str | None = None,
) -> tuple[dict[str, int], bool]:
    if isinstance(result, dict):
        normalized = _normalize_usage_dict(result.get("usage"))
        if normalized and normalized["total_tokens"] > 0:
            return normalized, False
    estimated = _estimate_token_usage(
        prompt=prompt,
        response_text=response_text,
        reasoning=reasoning,
    )
    return estimated, estimated["total_tokens"] > 0


def _format_token_usage_text(label: str, usage: dict[str, int], *, estimated: bool = False) -> str:
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))
    suffix = " (estimated)" if estimated else ""
    return (
        f"Tokens · {label}: {total_tokens:,} total "
        f"({input_tokens:,} in / {output_tokens:,} out){suffix}"
    )


def _attach_step_metadata(
    entry: dict[str, Any],
    *,
    model_id: str | None = None,
    model_name: str | None = None,
    usage: dict[str, int] | None = None,
    usage_estimated: bool = False,
) -> dict[str, Any]:
    out = dict(entry)
    if model_name:
        out["model_id"] = model_id
        out["model_name"] = model_name
    merged = _merge_token_usage(usage)
    if merged["total_tokens"] > 0:
        out["usage"] = merged
        out["usage_estimated"] = usage_estimated
    return out


def _finalize_assistant_step(
    log: list[dict[str, Any]],
    *,
    text: str,
    status: str,
    model_id: str | None = None,
    model_name: str | None = None,
    usage: dict[str, int] | None = None,
    usage_estimated: bool = False,
    replace_statuses: set[str] | None = None,
) -> None:
    """Replace the latest in-flight assistant step, or append if none found."""
    statuses = replace_statuses or {"crafting_spec", "generating_ui", "iterating"}
    entry = _attach_step_metadata(
        {"role": "assistant", "text": text, "status": status, "at": _now_iso()},
        model_id=model_id,
        model_name=model_name,
        usage=usage,
        usage_estimated=usage_estimated,
    )
    for i in range(len(log) - 1, -1, -1):
        item = log[i]
        if item.get("role") != "assistant":
            continue
        if item.get("kind") in {"model", "tokens"}:
            continue
        if item.get("status") in statuses:
            log[i] = entry
            return
    log.append(entry)


def _append_token_usage_entry(
    log: list[dict[str, Any]],
    *,
    label: str,
    usage: dict[str, int] | None,
    estimated: bool = False,
) -> None:
    merged = _merge_token_usage(usage)
    if merged["total_tokens"] <= 0:
        return
    log.append(
        {
            "role": "assistant",
            "kind": "tokens",
            "text": _format_token_usage_text(label, merged, estimated=estimated),
            "usage_label": label,
            "usage": merged,
            "usage_estimated": estimated,
            "status": "info",
            "at": _now_iso(),
        }
    )


def _llm_result(
    result: object,
    *,
    prompt: str = "",
) -> tuple[str, str | None, dict[str, int], bool]:
    if isinstance(result, dict):
        content = result.get("content")
        text = str(content).strip() if content else ""
        reasoning = result.get("reasoning_content") or result.get("reasoning")
        reasoning_text = reasoning.strip() if isinstance(reasoning, str) and reasoning.strip() else None
        usage, estimated = _usage_from_llm_result(
            result,
            prompt=prompt,
            response_text=text,
            reasoning=reasoning_text,
        )
        return text, reasoning_text, usage, estimated
    text = str(result).strip()
    usage, estimated = _usage_from_llm_result(result, prompt=prompt, response_text=text)
    return text, None, usage, estimated


def _extract_json_block(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise DesignError("LLM did not return JSON")
    return json.loads(text[start : end + 1])


def _fallback_spec(prompt: str) -> dict[str, Any]:
    title = (prompt.strip() or "Product").split("\n")[0][:48]
    intent = _prompt_intent(prompt)
    pattern = detect_layout_pattern(prompt)
    components = {
        "login": ["Logo", "Email field", "Password field", "Primary button", "Social login"],
        "shop": ["Navigation", "Search", "Product card", "Cart badge", "Footer"],
        "dashboard": ["Sidebar", "Stat card", "Chart", "Table", "User menu"],
        "music": ["Album art", "Playlist", "Lyrics panel", "Play controls", "Prev/Next"],
        "landing": ["Hero", "Feature grid", "CTA button", "Footer"],
        "generic": ["Header", "Primary button", "Card", "Footer"],
    }.get(intent, ["Header", "Primary button", "Card", "Footer"])
    base = {
        "name": title[:32] or "Neutral Modern",
        "rationale": f"A clean, professional system for: {title}",
        "colors": {
            "primary": ["#2563eb", "#1d4ed8", "#93c5fd"],
            "secondary": ["#0f172a", "#334155", "#64748b"],
            "neutral": ["#ffffff", "#f8fafc", "#e2e8f0", "#94a3b8", "#0f172a"],
            "accent": ["#f59e0b", "#fef3c7"],
        },
        "typography": {
            "fontFamily": "system-ui, Inter, sans-serif",
            "samples": [
                {"label": "Display", "size": "32px", "weight": "700"},
                {"label": "Title", "size": "20px", "weight": "600"},
                {"label": "Body", "size": "14px", "weight": "400"},
            ],
        },
        "components": components,
    }
    return enrich_fallback_spec(base, prompt, pattern)


def _prompt_intent(prompt: str) -> str:
    """Coarse UI intent from the user brief — drives fallback HTML, not LLM."""
    p = (prompt or "").strip().lower()
    if any(
        k in p
        for k in (
            "登录",
            "登陆",
            "注册",
            "signin",
            "sign-in",
            "sign in",
            "log in",
            "login",
            "sign up",
            "signup",
            "auth",
        )
    ):
        return "login"
    if any(
        k in p
        for k in (
            "购物",
            "商城",
            "电商",
            "商品",
            "shop",
            "store",
            "ecommerce",
            "e-commerce",
            "product",
            "cart",
            "marketplace",
        )
    ):
        return "shop"
    if any(k in p for k in ("仪表", "dashboard", "后台", "admin", "analytics", "控制台")):
        return "dashboard"
    if any(
        k in p
        for k in (
            "音乐",
            "播放器",
            "歌词",
            "歌单",
            "切歌",
            "music",
            "player",
            "playlist",
            "lyrics",
            "spotify",
            "song",
            "album",
        )
    ):
        return "music"
    if any(k in p for k in ("落地", "landing", "官网", "首页", "home page", "marketing", "hero")):
        return "landing"
    return "generic"


def _detect_html_intent(html: str) -> str | None:
    """Heuristic screen type from generated HTML (for brief-alignment checks)."""
    lower = (html or "").lower()
    text = re.sub(r"<[^>]+>", " ", lower)
    has_password = 'type="password"' in lower or "password" in text
    has_login_copy = any(
        k in text
        for k in (
            "welcome back",
            "sign in",
            "log in",
            "login",
            "欢迎回来",
            "登录",
            "注册",
        )
    )
    if has_password or (has_login_copy and "email" in text):
        return "login"
    shop_signals = (
        "add to cart",
        "shopping cart",
        "featured product",
        "product card",
        "加入购物车",
        "购物车",
        "商品",
        "featured",
    )
    if any(k in text for k in shop_signals) or (
        "product" in text and ("cart" in text or "shop" in text or "price" in text)
    ):
        return "shop"
    if any(k in text for k in ("dashboard", "analytics", "sidebar", "控制台", "后台")):
        return "dashboard"
    if any(k in text for k in ("playlist", "lyrics", "play", "歌词", "歌单", "切歌")):
        return "music"
    return None


def _html_matches_brief_intent(prompt: str, html: str) -> bool:
    """True when generated HTML aligns with the user brief (guards weak-model drift)."""
    expected = _prompt_intent(prompt)
    if expected == "generic":
        return True
    detected = _detect_html_intent(html)
    if detected is None:
        return True
    return detected == expected


def _first_hex(colors: dict[str, Any] | None, key: str, fallback: str) -> str:
    if not colors:
        return fallback
    values = colors.get(key)
    if isinstance(values, list) and values:
        raw = str(values[0]).strip()
        if re.match(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", raw):
            return raw
    if isinstance(values, str) and re.match(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", values.strip()):
        return values.strip()
    return fallback


def _write_thumbnail_svg(
    session_dir: Path,
    spec: dict[str, Any] | None,
    *,
    device: str = "web",
) -> str:
    """Legacy silhouette SVG — kept for tests; prefer live HTML preview in the sidebar."""
    colors = (spec or {}).get("colors") if isinstance(spec, dict) else None
    if not isinstance(colors, dict):
        colors = {}
    primary = _first_hex(colors, "primary", "#2563eb")
    secondary = _first_hex(colors, "secondary", "#94a3b8")
    surface = _first_hex(colors, "neutral", "#FFFFFF")
    is_app = (device or "web").strip().lower() == "app"

    if is_app:
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160">
  <rect width="160" height="160" rx="20" fill="#EEF2FF"/>
  <rect x="44" y="12" width="72" height="136" rx="14" fill="{surface}" stroke="#1E293B" stroke-width="3"/>
  <rect x="68" y="20" width="24" height="5" rx="2.5" fill="#CBD5E1"/>
  <rect x="54" y="36" width="52" height="8" rx="3" fill="#0F172A" opacity="0.85"/>
  <rect x="54" y="52" width="52" height="40" rx="6" fill="{primary}"/>
  <rect x="54" y="100" width="24" height="20" rx="4" fill="#E2E8F0"/>
  <rect x="82" y="100" width="24" height="20" rx="4" fill="{secondary}" opacity="0.65"/>
  <rect x="54" y="128" width="52" height="10" rx="4" fill="{primary}"/>
  <circle cx="80" cy="142" r="3.5" fill="#CBD5E1"/>
</svg>
"""
    else:
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160">
  <rect width="160" height="160" rx="20" fill="#F1F5F9"/>
  <rect x="10" y="36" width="140" height="96" rx="10" fill="{surface}" stroke="#1E293B" stroke-width="2.5"/>
  <rect x="10" y="36" width="140" height="22" rx="10" fill="#E2E8F0"/>
  <rect x="10" y="52" width="140" height="6" fill="#E2E8F0"/>
  <circle cx="26" cy="47" r="4" fill="#F87171"/>
  <circle cx="40" cy="47" r="4" fill="#FBBF24"/>
  <circle cx="54" cy="47" r="4" fill="#34D399"/>
  <rect x="68" y="43" width="68" height="8" rx="4" fill="#F8FAFC" stroke="#94A3B8"/>
  <rect x="22" y="70" width="116" height="10" rx="3" fill="#0F172A" opacity="0.8"/>
  <rect x="22" y="88" width="54" height="32" rx="5" fill="{primary}"/>
  <rect x="84" y="88" width="54" height="14" rx="3" fill="#E2E8F0"/>
  <rect x="84" y="106" width="54" height="14" rx="3" fill="{secondary}" opacity="0.55"/>
</svg>
"""
    path = session_dir / THUMBNAIL_SVG
    path.write_text(svg, encoding="utf-8")
    return THUMBNAIL_SVG


def _clear_fake_thumbnail(session_dir: Path) -> None:
    """Remove legacy silhouette SVG so empty drafts stay gray in the sidebar."""
    for name in (THUMBNAIL_SVG, THUMBNAIL_PNG):
        path = session_dir / name
        if path.is_file():
            try:
                path.unlink()
            except OSError:
                pass


def _screen_html_rel(screen: dict[str, Any]) -> str:
    sid = str(screen.get("id") or "main")
    return str(screen.get("html_path") or f"screens/{sid}.html")


def _resolve_screen_html_path(session_dir: Path, screen: dict[str, Any]) -> Path:
    return session_dir / _screen_html_rel(screen)


def _next_round_index(manifest: dict[str, Any], screen_id: str) -> int:
    history = list(manifest.get("round_history") or [])
    indices = [
        int(r.get("round_index", 0))
        for r in history
        if str(r.get("screen_id") or "") == screen_id
    ]
    return (max(indices) + 1) if indices else 0


def _record_screen_round(
    session_dir: Path,
    manifest: dict[str, Any],
    *,
    screen_id: str,
    html: str,
    prompt: str,
    reasoning_content: str | None,
    process_log_slice: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write versioned HTML and append round metadata to manifest."""
    round_index = _next_round_index(manifest, screen_id)
    rel = f"screens/{screen_id}_r{round_index}.html"
    (session_dir / "screens").mkdir(exist_ok=True)
    (session_dir / rel).write_text(html, encoding="utf-8")
    entry: dict[str, Any] = {
        "round_index": round_index,
        "screen_id": screen_id,
        "html_path": rel,
        "prompt": prompt,
        "reasoning_content": reasoning_content,
        "process_log": process_log_slice,
        "at": _now_iso(),
    }
    history = list(manifest.get("round_history") or [])
    history.append(entry)
    manifest["round_history"] = history
    for screen in manifest.get("screens") or []:
        if str(screen.get("id")) == screen_id:
            screen["html_path"] = rel
            screen["active_round_index"] = round_index
    return entry


def _first_screen_with_ui(session_dir: Path, manifest: dict[str, Any] | None = None) -> str | None:
    """Return screen id of the first HTML file with visible UI content."""
    try:
        data = manifest if isinstance(manifest, dict) else _read_manifest(session_dir)
    except (OSError, json.JSONDecodeError, DesignError):
        data = {}
    screens = list(data.get("screens") or [])
    candidates: list[str] = []
    for screen in screens:
        sid = str(screen.get("id") or "").strip()
        if sid:
            candidates.append(sid)
    if not candidates:
        # Fallback: any html under screens/
        screens_dir = session_dir / "screens"
        if screens_dir.is_dir():
            candidates = sorted(p.stem for p in screens_dir.glob("*.html"))
    for sid in candidates:
        screen_meta = next((s for s in screens if str(s.get("id")) == sid), {"id": sid})
        path = _resolve_screen_html_path(session_dir, screen_meta)
        if not path.is_file():
            legacy = session_dir / "screens" / f"{sid}.html"
            if legacy.is_file():
                path = legacy
            else:
                continue
        try:
            html = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _html_has_visible_content(html):
            return sid
    return None


def _load_thumbnail_data_url(session_dir: Path) -> str | None:
    """Load a real captured thumbnail only — never invent a silhouette for empty drafts."""
    import base64

    png_path = session_dir / THUMBNAIL_PNG
    if png_path.is_file():
        encoded = base64.b64encode(png_path.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    # Legacy SVG silhouettes are intentionally ignored (they lied about empty sessions).
    return None


def thumbnail_data_url_for_run(run_id: str) -> str | None:
    """Resolve sidebar image thumbnail for a Design session (None → gray placeholder)."""
    try:
        root = require_workspace() / DESIGN_ROOT
    except WorkspaceError:
        return None
    session_dir = _find_existing_session_dir(root, run_id)
    if session_dir is None:
        return None
    return _load_thumbnail_data_url(session_dir)


def design_ui_preview_path_for_run(run_id: str) -> str | None:
    """API path for live HTML preview when the session has real UI (else None)."""
    try:
        root = require_workspace() / DESIGN_ROOT
    except WorkspaceError:
        return None
    session_dir = _find_existing_session_dir(root, run_id)
    if session_dir is None:
        return None
    sid = _first_screen_with_ui(session_dir)
    if not sid:
        return None
    return f"/api/design/sessions/{run_id}/screens/{sid}"


def read_screen_html(run_id: str, screen_id: str) -> str:
    """Return screen HTML for live sidebar / canvas preview."""
    session_dir = _session_dir(run_id)
    manifest = _read_manifest(session_dir)
    raw_id = re.sub(r"[^a-zA-Z0-9_-]", "", (screen_id or "").strip()) or "main"
    versioned = re.match(r"^(?P<base>[a-zA-Z0-9_-]+)_r(?P<round>\d+)$", raw_id)
    if versioned:
        version_path = session_dir / "screens" / f"{raw_id}.html"
        if version_path.is_file():
            return version_path.read_text(encoding="utf-8")
        raw_id = versioned.group("base")
    screen_meta = next(
        (s for s in (manifest.get("screens") or []) if str(s.get("id")) == raw_id),
        {"id": raw_id},
    )
    path = _resolve_screen_html_path(session_dir, screen_meta)
    if not path.is_file():
        legacy = session_dir / "screens" / f"{raw_id}.html"
        if legacy.is_file():
            path = legacy
        else:
            raise DesignError(f"Screen not found: {raw_id}")
    return path.read_text(encoding="utf-8")


def design_device_for_run(run_id: str) -> str:
    """Return design device for a run (`web` | `app`)."""
    try:
        root = require_workspace() / DESIGN_ROOT
    except WorkspaceError:
        return "web"
    session_dir = _find_existing_session_dir(root, run_id)
    if session_dir is None or not (session_dir / MANIFEST).is_file():
        return "web"
    try:
        manifest = _read_manifest(session_dir)
    except (OSError, json.JSONDecodeError, DesignError):
        return "web"
    device = str(manifest.get("device") or "web").strip().lower()
    return device if device in {"web", "app"} else "web"


def session_status_for_run(run_id: str) -> str | None:
    """Return Design manifest status for sidebar history sync (None if missing)."""
    try:
        root = require_workspace() / DESIGN_ROOT
    except WorkspaceError:
        return None
    session_dir = _find_existing_session_dir(root, run_id)
    if session_dir is None or not (session_dir / MANIFEST).is_file():
        return None
    try:
        manifest = _read_manifest(session_dir)
    except (OSError, json.JSONDecodeError, DesignError):
        return None
    status = str(manifest.get("status") or "").strip()
    return status or None


def _shell_html(title: str, body: str, *, device: str = "web") -> str:
    is_app = (device or "web").strip().lower() == "app"
    # Lock the design canvas to the target viewport so previews scale correctly.
    canvas = (
        "width:390px;min-height:844px;margin:0 auto;"
        if is_app
        else "width:1920px;min-height:1080px;margin:0 auto;"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width={'390' if is_app else '1920'}, initial-scale=1"/>
<title>{_esc(title)}</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  html, body {{ margin:0; background:#f8fafc; font-family: system-ui, -apple-system, sans-serif; }}
  .clutch-canvas {{ {canvas} background:#fff; }}
</style>
</head>
<body>
<div class="clutch-canvas">
{body}
</div>
</body>
</html>
"""


def _html_has_visible_content(html: str) -> bool:
    """True when the document body has real UI — not an empty shell after wrap."""
    if not (html or "").strip():
        return False
    lower = html.lower()
    if "<html" in lower and "<body" not in lower:
        return False
    if "<style" in lower and "</style>" not in lower:
        return False
    if "<script" in lower and "</script>" not in lower:
        return False
    m = re.search(
        r'class=["\']clutch-canvas["\'][^>]*>([\s\S]*?)</div>\s*</body>',
        html,
        re.I,
    )
    if not m:
        m = re.search(r"<body[^>]*>([\s\S]*?)</body>", html, re.I)
    chunk = m.group(1) if m else html
    chunk = re.sub(r"<script[\s\S]*?</script>", "", chunk, flags=re.I)
    chunk = re.sub(r"<style[\s\S]*?</style>", "", chunk, flags=re.I)
    chunk = re.sub(r"<!--[\s\S]*?-->", "", chunk)
    compact = re.sub(r">\s+<", "><", chunk.strip())
    if not compact:
        return False
    # Only empty wrapper divs (common LLM failure after _shell_html).
    if re.fullmatch(r"(?:<div\b[^>]*>\s*</div>\s*)+", compact, flags=re.I):
        return False
    text = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", chunk))
    if len(text) >= 2:
        return True
    return bool(
        re.search(
            r"<(?:div|section|main|header|nav|footer|article|aside|h[1-6]|p|button|a|"
            r"img|ul|ol|li|form|input|table|span|svg)\b[^>]*>",
            chunk,
            re.I,
        )
    )


def _coerce_ui_html(
    raw: str,
    *,
    title: str,
    prompt: str,
    spec: dict[str, Any],
    device: str,
    fallback_html: str | None = None,
    allow_template_fallback: bool = True,
) -> str:
    """Wrap fragment if needed; optional offline template when LLM output is blank."""
    html = (raw or "").strip()
    if html and "<html" not in html.lower():
        html = _shell_html(title, html, device=device)
    if _html_has_visible_content(html):
        return html
    if fallback_html is not None and _html_has_visible_content(fallback_html):
        return fallback_html
    if allow_template_fallback:
        return _fallback_ui_html(prompt, spec, device=device)
    return ""


def _fallback_ui_html(prompt: str, spec: dict[str, Any], *, device: str = "web") -> str:
    """Offline-only stub when no model/API key is configured — never used on the LLM path."""
    primary = (spec.get("colors") or {}).get("primary") or ["#2563eb"]
    accent = primary[0] if isinstance(primary, list) else str(primary)
    title = (prompt.strip() or str(spec.get("name") or "Welcome")).split("\n")[0][:48]
    intent = _prompt_intent(prompt)
    is_app = (device or "web").strip().lower() == "app"
    shell = "px-4" if is_app else "px-16"

    if intent == "login":
        body = f"""
<div class="min-h-full flex items-center justify-center p-6 {shell}">
  <div class="w-full {'max-w-sm' if is_app else 'max-w-md'} space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div>
      <h1 class="text-2xl font-bold">Welcome back</h1>
      <p class="text-sm text-slate-500 mt-1">{_esc(title)}</p>
    </div>
    <label class="block text-xs font-semibold text-slate-600">Email
      <input class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm" placeholder="you@company.com"/>
    </label>
    <label class="block text-xs font-semibold text-slate-600">Password
      <input type="password" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm" placeholder="••••••••"/>
    </label>
    <button style="background:{accent}" class="w-full rounded-xl text-white font-semibold py-2.5 text-sm">Log in</button>
  </div>
</div>
"""
    elif intent == "shop":
        cols = "grid-cols-2" if is_app else "grid-cols-4"
        cards = "".join(
            f"""
      <div class="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm">
        <div class="{'h-28' if is_app else 'h-44'}" style="background:{accent};opacity:0.85"></div>
        <div class="p-3 space-y-1">
          <p class="text-sm font-semibold">Product {i}</p>
          <p class="text-xs text-slate-500">¥{(i * 129)}</p>
          <button style="background:{accent}" class="mt-2 w-full rounded-lg text-white text-xs font-semibold py-1.5">Add to cart</button>
        </div>
      </div>"""
            for i in range(1, 5)
        )
        body = f"""
<div class="min-h-full">
  <header class="border-b border-slate-200 bg-white py-4 flex items-center justify-between {shell}">
    <p class="font-bold {'text-sm' if is_app else 'text-lg'}">{_esc(title)}</p>
    <div class="flex gap-6 text-sm text-slate-500"><span>Search</span><span>Cart (0)</span></div>
  </header>
  <main class="py-8 {shell}">
    <h1 class="{'text-xl' if is_app else 'text-3xl'} font-bold mb-1">Featured</h1>
    <p class="text-sm text-slate-500 mb-6">Shop the latest picks</p>
    <div class="grid {cols} gap-4">{cards}
    </div>
  </main>
</div>
"""
    elif intent == "dashboard":
        body = f"""
<div class="min-h-full flex {'flex-col' if is_app else ''}">
  <aside class="{'w-full border-b' if is_app else 'w-64 border-r min-h-[1080px]'} bg-slate-900 text-white p-5 space-y-3">
    <p class="font-bold text-sm">{_esc(title)}</p>
    <p class="text-xs text-slate-400">Overview</p>
    <p class="text-xs text-slate-400">Orders</p>
    <p class="text-xs text-slate-400">Settings</p>
  </aside>
  <main class="flex-1 p-6 space-y-4">
    <h1 class="text-2xl font-bold">Dashboard</h1>
    <div class="grid grid-cols-2 {'md:grid-cols-3' if not is_app else ''} gap-4">
      <div class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-slate-500">Revenue</p><p class="text-lg font-bold">¥128k</p></div>
      <div class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-slate-500">Orders</p><p class="text-lg font-bold">1,284</p></div>
      <div class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-slate-500">Users</p><p class="text-lg font-bold">8.2k</p></div>
    </div>
    <div class="h-56 rounded-xl border border-slate-200 bg-white" style="background:linear-gradient(135deg,{accent}22,transparent)"></div>
  </main>
</div>
"""
    elif intent == "music":
        tracks = "".join(
            f"""
      <button type="button" class="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-left hover:bg-white/10 {'bg-white/15' if i == 1 else ''}">
        <span class="flex h-10 w-10 items-center justify-center rounded-lg text-xs font-bold text-white" style="background:{accent}">{i}</span>
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-semibold text-white">Track {i} · Night Drive</span>
          <span class="block truncate text-xs text-white/50">Artist {i}</span>
        </span>
        <span class="text-[10px] text-white/40">3:2{i}</span>
      </button>"""
            for i in range(1, 6)
        )
        if is_app:
            body = f"""
<div class="min-h-full text-white" style="background:linear-gradient(180deg,#0f172a,#020617)">
  <header class="px-4 pt-6 pb-3 flex items-center justify-between">
    <p class="text-sm font-bold">{_esc(title)}</p>
    <span class="text-xs text-white/50">Library</span>
  </header>
  <main class="px-4 space-y-4 pb-28">
    <div class="rounded-2xl p-4" style="background:linear-gradient(135deg,{accent},#111827)">
      <p class="text-xs text-white/70">Now playing</p>
      <p class="mt-1 text-lg font-bold">Midnight Pulse</p>
      <p class="text-xs text-white/60">SonicFlow · Album</p>
    </div>
    <section>
      <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-white/50">Playlist</p>
      <div class="space-y-1">{tracks}</div>
    </section>
    <section class="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
      <p class="mb-2 text-xs font-semibold text-white/60">Lyrics</p>
      <p class="text-sm leading-relaxed text-white/90">City lights blur past the glass…</p>
      <p class="mt-2 text-sm leading-relaxed text-white/50">Hold the night a little longer…</p>
      <p class="mt-2 text-sm leading-relaxed text-white/35">Pulse under neon rain…</p>
    </section>
  </main>
  <footer class="fixed bottom-0 left-0 right-0 border-t border-white/10 bg-black/80 px-4 py-3 backdrop-blur">
    <div class="flex items-center justify-between gap-3">
      <button type="button" class="rounded-full bg-white/10 px-3 py-2 text-xs">Prev</button>
      <button type="button" class="rounded-full px-5 py-2 text-xs font-bold text-white" style="background:{accent}">Play</button>
      <button type="button" class="rounded-full bg-white/10 px-3 py-2 text-xs">Next</button>
    </div>
  </footer>
</div>
"""
        else:
            body = f"""
<div class="min-h-full flex text-white" style="background:#020617">
  <aside class="w-56 border-r border-white/10 p-5 space-y-3">
    <p class="font-bold">{_esc(str(spec.get("name") or "SonicFlow"))}</p>
    <p class="text-xs text-white/50">Home</p>
    <p class="text-xs text-white/50">Search</p>
    <p class="text-xs text-white/80">Your Library</p>
  </aside>
  <main class="flex-1 flex flex-col min-h-[1080px]">
    <div class="flex-1 grid grid-cols-2 gap-6 p-8">
      <section class="space-y-4">
        <div class="rounded-3xl p-8" style="background:linear-gradient(135deg,{accent},#1e1b4b)">
          <p class="text-sm text-white/70">Featured</p>
          <h1 class="mt-2 text-4xl font-bold">Midnight Pulse</h1>
          <p class="mt-2 text-white/60">A dark immersive player with playlist + lyrics.</p>
        </div>
        <div>
          <p class="mb-3 text-sm font-semibold text-white/70">Playlist</p>
          <div class="space-y-1">{tracks}</div>
        </div>
      </section>
      <section class="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur flex flex-col">
        <p class="text-sm font-semibold text-white/70">Lyrics</p>
        <div class="mt-6 flex-1 space-y-4 text-lg leading-relaxed">
          <p class="text-white">City lights blur past the glass…</p>
          <p class="text-white/70">Hold the night a little longer…</p>
          <p class="text-white/45">Pulse under neon rain…</p>
          <p class="text-white/30">Switch tracks — keep the vibe.</p>
        </div>
      </section>
    </div>
    <footer class="border-t border-white/10 px-8 py-4 flex items-center justify-between bg-black/50">
      <div>
        <p class="text-sm font-semibold">Midnight Pulse</p>
        <p class="text-xs text-white/50">Now playing</p>
      </div>
      <div class="flex items-center gap-3">
        <button type="button" class="rounded-full bg-white/10 px-4 py-2 text-sm">Prev</button>
        <button type="button" class="rounded-full px-6 py-2 text-sm font-bold" style="background:{accent}">Play</button>
        <button type="button" class="rounded-full bg-white/10 px-4 py-2 text-sm">Next</button>
      </div>
    </footer>
  </main>
</div>
"""
    else:
        body = f"""
<div class="min-h-full">
  <header class="py-5 flex items-center justify-between {shell}">
    <p class="font-bold text-sm">{_esc(str(spec.get("name") or "Brand"))}</p>
    <button style="background:{accent}" class="rounded-lg text-white text-xs font-semibold px-4 py-2">Get started</button>
  </header>
  <main class="py-16 {shell} text-center space-y-5">
    <h1 class="{'text-3xl' if is_app else 'text-5xl'} font-bold tracking-tight">{_esc(title)}</h1>
    <p class="text-slate-500 {'text-sm' if is_app else 'text-lg'} max-w-2xl mx-auto">A polished interface draft for your brief. Iterate from the canvas to refine layout and copy.</p>
    <div class="flex justify-center gap-3">
      <button style="background:{accent}" class="rounded-xl text-white font-semibold px-6 py-3 text-sm">Primary action</button>
      <button class="rounded-xl border border-slate-200 px-6 py-3 text-sm font-medium">Learn more</button>
    </div>
    <div class="mt-10 grid grid-cols-1 {'md:grid-cols-3' if not is_app else ''} gap-4 text-left">
      <div class="rounded-2xl border border-slate-200 bg-white p-5"><p class="font-semibold text-sm mb-1">Feature A</p><p class="text-xs text-slate-500">Describe value here.</p></div>
      <div class="rounded-2xl border border-slate-200 bg-white p-5"><p class="font-semibold text-sm mb-1">Feature B</p><p class="text-xs text-slate-500">Describe value here.</p></div>
      <div class="rounded-2xl border border-slate-200 bg-white p-5"><p class="font-semibold text-sm mb-1">Feature C</p><p class="text-xs text-slate-500">Describe value here.</p></div>
    </div>
  </main>
</div>
"""
    return _shell_html(title, body, device=device)


# Back-compat alias used by older call sites / tests
def _fallback_login_html(prompt: str, spec: dict[str, Any]) -> str:
    return _fallback_ui_html(prompt, spec, device="web")


def _spec_to_design_md(spec: dict[str, Any]) -> str:
    """Render a 12-section design specification (P0 Design.md generator)."""
    name = spec.get("name", "Design")
    brand = spec.get("brand") if isinstance(spec.get("brand"), dict) else {}
    grid = spec.get("grid") if isinstance(spec.get("grid"), dict) else {}
    radius = spec.get("radius") if isinstance(spec.get("radius"), dict) else {}
    shadow = spec.get("shadow") if isinstance(spec.get("shadow"), dict) else {}
    motion = spec.get("motion") if isinstance(spec.get("motion"), dict) else {}
    colors = spec.get("colors") or {}
    typo = spec.get("typography") or {}
    lines = [
        f"# DESIGN.md — {name}",
        "",
        "# Brand",
        "",
        f"- **Name**: {brand.get('name', name)}",
        f"- **Voice**: {brand.get('voice', 'Professional, modern')}",
        "",
        "# Visual Style",
        "",
        str(spec.get("visual_style") or spec.get("rationale") or ""),
        "",
        "# Layout System",
        "",
        str(spec.get("layout_system") or layout_wrapper_hint(str(spec.get("layout_pattern") or "landing"))),
        f"- **Pattern**: {spec.get('layout_pattern', 'landing')}",
        "",
        "# Grid",
        "",
        f"- **Columns**: {grid.get('columns', 12)}",
        f"- **Gutter**: {grid.get('gutter', '24px')}",
        f"- **Max width**: {grid.get('max_width', '1280px')}",
        "",
        "# Typography",
        "",
        f"- **Font family**: {typo.get('fontFamily', 'system-ui, Inter, sans-serif')}",
    ]
    for sample in typo.get("samples") or []:
        if isinstance(sample, dict):
            lines.append(
                f"- **{sample.get('label', 'Sample')}**: {sample.get('size', '14px')} / "
                f"weight {sample.get('weight', '400')}"
            )
    lines += ["", "# Color Tokens", ""]
    for group, values in colors.items():
        if isinstance(values, list):
            lines.append(f"- **{group}**: {', '.join(str(v) for v in values)}")
    lines += ["", "# Radius", ""]
    for key, val in radius.items():
        lines.append(f"- **{key}**: {val}")
    if not radius:
        lines.append("- **md**: 12px")
    lines += ["", "# Shadow", ""]
    for key, val in shadow.items():
        lines.append(f"- **{key}**: {val}")
    if not shadow:
        lines.append("- **card**: 0 1px 3px rgba(15,23,42,0.08)")
    lines += ["", "# Components", ""]
    for c in spec.get("components") or []:
        lines.append(f"- {c}")
    lines += ["", "# Motion", ""]
    for key, val in motion.items():
        lines.append(f"- **{key}**: {val}")
    if not motion:
        lines.append("- **duration**: 200ms")
    lines += [
        "",
        "# Responsive Rules",
        "",
        str(spec.get("responsive") or "Mobile-first; stack below md; 44px min touch targets on app."),
        "",
        "# Accessibility Rules",
        "",
        str(spec.get("accessibility") or "WCAG AA contrast; focus rings; semantic headings."),
        "",
    ]
    return "\n".join(lines)


def ensure_session(run_id: str, *, title: str = "", prompt: str = "") -> dict[str, Any]:
    session_dir = _session_dir(run_id)
    manifest_path = session_dir / MANIFEST
    if manifest_path.is_file():
        return get_session(run_id)
    (session_dir / "screens").mkdir(exist_ok=True)
    manifest: dict[str, Any] = {
        "id": run_id,
        "run_id": run_id,
        "name": title.strip() or "New Design",
        "prompt": prompt.strip(),
        "phase": "welcome",
        "status": "draft",
        "device": "web",
        "process_log": [],
        "round_history": [],
        "spec": None,
        "screens": [],
        "prototype_approved": False,
        "react_approved": False,
        "react_ready": False,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _write_manifest(session_dir, manifest)
    return _public(manifest, session_dir)


def get_session(run_id: str) -> dict[str, Any]:
    session_dir = _session_dir(run_id)
    if not (session_dir / MANIFEST).is_file():
        raise DesignError(f"Design session not found: {run_id}")
    manifest = _read_manifest(session_dir)
    # Lazy-migrate legacy `run_*` folders to readable names.
    title = str(manifest.get("name") or manifest.get("prompt") or "")
    device = str(manifest.get("device") or "web")
    if title.strip() and title.strip().lower() not in _DEFAULT_FOLDER_TITLES:
        session_dir = sync_session_folder_name(run_id, title=title, device=device)
        manifest = _read_manifest(session_dir)
    return _public(manifest, session_dir)


def list_sessions() -> list[dict[str, Any]]:
    root = require_workspace() / DESIGN_ROOT
    if not root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for child in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not child.is_dir() or not (child / MANIFEST).is_file():
            continue
        try:
            items.append(_public(_read_manifest(child), child, include_html=False))
        except (OSError, json.JSONDecodeError, DesignError):
            continue
    return items


def _public(manifest: dict[str, Any], session_dir: Path, *, include_html: bool = True) -> dict[str, Any]:
    out = dict(manifest)
    out["path"] = str(session_dir)
    out["design_md"] = (
        (session_dir / DESIGN_MD).read_text(encoding="utf-8")
        if (session_dir / DESIGN_MD).is_file()
        else ""
    )
    if (session_dir / SPEC_JSON).is_file():
        try:
            out["spec"] = json.loads((session_dir / SPEC_JSON).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            out["spec"] = manifest.get("spec")
    ref_rel = manifest.get("reference_image")
    if include_html and ref_rel:
        out["reference_image_url"] = _load_reference_data_url(session_dir, str(ref_rel))
    elif ref_rel:
        out["reference_image_url"] = None
        out["reference_image"] = ref_rel
    md_rel = manifest.get("reference_md")
    if md_rel:
        md_text, md_name = _load_reference_md(session_dir, str(md_rel))
        out["reference_md_name"] = md_name or manifest.get("reference_md_name") or "DESIGN.md"
        out["reference_md_text"] = md_text if include_html else None
    else:
        out["reference_md_name"] = manifest.get("reference_md_name")
        out["reference_md_text"] = None
    out["reference_url"] = manifest.get("reference_url")
    snap = _load_url_snapshot(session_dir) if include_html else None
    if snap:
        out["url_snapshot"] = {
            "url": snap.get("url"),
            "host": snap.get("host"),
            "title": snap.get("title"),
            "description": snap.get("description"),
        }
    else:
        out["url_snapshot"] = manifest.get("url_snapshot")
    # Real capture only; live HTML preview path for sidebar (None → gray placeholder).
    out["thumbnail_url"] = _load_thumbnail_data_url(session_dir)
    sid = _first_screen_with_ui(session_dir, manifest)
    out["ui_preview_url"] = (
        f"/api/design/sessions/{manifest.get('run_id') or manifest.get('id')}/screens/{sid}"
        if sid
        else None
    )
    # Workspace-relative artifact paths for Files / Changes panels.
    try:
        workspace_root = require_workspace()
        artifacts: list[str] = []
        for path in sorted(session_dir.rglob("*")):
            if path.is_file():
                artifacts.append(str(path.relative_to(workspace_root)))
        out["artifact_paths"] = artifacts
    except (WorkspaceError, OSError, ValueError):
        out["artifact_paths"] = []
    history = list(manifest.get("round_history") or [])
    out["round_history"] = history
    out["round_count"] = len(history)
    if include_html:
        screens = []
        for screen in manifest.get("screens") or []:
            item = dict(screen)
            sid = item.get("id")
            if sid:
                screen_meta = next(
                    (s for s in (manifest.get("screens") or []) if str(s.get("id")) == sid),
                    item,
                )
                html_path = _resolve_screen_html_path(session_dir, screen_meta)
                if not html_path.is_file():
                    html_path = session_dir / "screens" / f"{sid}.html"
                item["html"] = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
                item["active_round_index"] = screen_meta.get("active_round_index")
            screens.append(item)
        out["screens"] = screens
    with _preview_lock:
        preview = _preview_procs.get(manifest.get("run_id") or manifest.get("id", ""))
        if preview:
            out["preview_url"] = preview.get("url")
    return out


def _llm_complete(
    router: Any, prompt: str, *, model_id: str, timeout_sec: float = _LLM_TIMEOUT_SEC
) -> tuple[str, str | None, dict[str, int], bool]:
    """Run router.complete with a hard timeout; returns content, reasoning, usage, estimated."""
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(router.complete, prompt, model_id=model_id)
        try:
            return _llm_result(future.result(timeout=timeout_sec), prompt=prompt)
        except FuturesTimeout as exc:
            future.cancel()
            raise DesignError(f"Model timed out after {int(timeout_sec)}s") from exc



def _save_reference_image(session_dir: Path, data_url: str | None) -> str | None:
    """Persist reference image data URL under session dir; return relative path or None."""
    if not data_url or not data_url.startswith("data:image/"):
        return None
    try:
        header, b64 = data_url.split(",", 1)
    except ValueError:
        return None
    ext = "png"
    if "jpeg" in header or "jpg" in header:
        ext = "jpg"
    elif "webp" in header:
        ext = "webp"
    elif "gif" in header:
        ext = "gif"
    import base64

    raw = base64.b64decode(b64)
    if len(raw) > 8_000_000:
        raise DesignError("Reference image too large (max 8MB)")
    rel = f"reference.{ext}"
    (session_dir / rel).write_bytes(raw)
    # Also keep a truncated data-url pointer for UI (prefer file path in public).
    return rel


def _load_reference_data_url(session_dir: Path, rel: str | None) -> str | None:
    if not rel:
        return None
    path = session_dir / rel
    if not path.is_file():
        return None
    import base64

    mime = "image/png"
    if rel.endswith(".jpg") or rel.endswith(".jpeg"):
        mime = "image/jpeg"
    elif rel.endswith(".webp"):
        mime = "image/webp"
    elif rel.endswith(".gif"):
        mime = "image/gif"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


_REF_MD_REL = "reference_design.md"
_URL_SNAPSHOT_REL = "url_snapshot.json"
_MAX_MD_CHARS = 200_000


def _save_reference_md(
    session_dir: Path,
    content: str | None,
    *,
    name: str | None = None,
) -> str | None:
    """Persist uploaded Design.md; return relative path or None."""
    text = (content or "").strip()
    if not text:
        return None
    if len(text) > _MAX_MD_CHARS:
        raise DesignError(f"Design.md too large (max {_MAX_MD_CHARS // 1000}k chars)")
    (session_dir / _REF_MD_REL).write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
    meta = {"name": (name or "DESIGN.md").strip() or "DESIGN.md"}
    (session_dir / "reference_md_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return _REF_MD_REL


def _load_reference_md(session_dir: Path, rel: str | None = None) -> tuple[str | None, str | None]:
    """Return (markdown_text, display_name)."""
    path = session_dir / (rel or _REF_MD_REL)
    if not path.is_file():
        return None, None
    text = path.read_text(encoding="utf-8")
    name = "DESIGN.md"
    meta_path = session_dir / "reference_md_meta.json"
    if meta_path.is_file():
        try:
            name = str(json.loads(meta_path.read_text(encoding="utf-8")).get("name") or name)
        except json.JSONDecodeError:
            pass
    return text, name


def _normalize_reference_url(url: str | None) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return None
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    if len(raw) > 2000:
        raise DesignError("URL too long")
    if not re.match(r"^https?://[^\s]+$", raw, re.I):
        raise DesignError("Invalid URL")
    return raw


def _fetch_url_snapshot(url: str) -> dict[str, Any]:
    """Fetch a lightweight page snapshot (title / description / text excerpt)."""
    import urllib.error
    import urllib.request
    from html import unescape
    from urllib.parse import urlparse

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ClutchDesign/1.0 (+local; design-reference)",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            raw = resp.read(500_000)
            charset = "utf-8"
            ctype = resp.headers.get_content_charset()
            if ctype:
                charset = ctype
            html = raw.decode(charset, errors="replace")
            final_url = resp.geturl() or url
    except urllib.error.HTTPError as exc:
        raise DesignError(f"Could not fetch URL ({exc.code})") from exc
    except Exception as exc:
        raise DesignError(f"Could not fetch URL: {exc}") from exc

    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = unescape(re.sub(r"\s+", " ", title_m.group(1))).strip() if title_m else ""
    desc_m = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        html,
        re.I | re.S,
    ) or re.search(
        r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']',
        html,
        re.I | re.S,
    )
    description = unescape(re.sub(r"\s+", " ", desc_m.group(1))).strip() if desc_m else ""
    # Strip scripts/styles then tags for a short text excerpt.
    cleaned = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = unescape(re.sub(r"\s+", " ", cleaned)).strip()
    excerpt = cleaned[:4000]
    host = urlparse(final_url).netloc or urlparse(url).netloc
    return {
        "url": final_url,
        "host": host,
        "title": title[:200],
        "description": description[:400],
        "excerpt": excerpt,
        "fetched_at": _now_iso(),
    }


def _save_url_snapshot(session_dir: Path, snapshot: dict[str, Any]) -> None:
    (session_dir / _URL_SNAPSHOT_REL).write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _load_url_snapshot(session_dir: Path) -> dict[str, Any] | None:
    path = session_dir / _URL_SNAPSHOT_REL
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _llm_complete_vision(
    router: Any,
    prompt: str,
    *,
    model_id: str,
    image_data_url: str | None = None,
    timeout_sec: float = _LLM_TIMEOUT_SEC,
) -> tuple[str, str | None, dict[str, int], bool]:
    """Complete with optional vision image via router.chat multimodal content."""
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
    from src.adapters.ollama_adapter import model_supports_vision
    from src.chat_content import user_message_content_for_llm

    vision_ok = False
    if image_data_url:
        try:
            spec, _ = router.resolve_for_model(model_id)
            vision_ok = model_supports_vision(spec)
        except Exception:
            vision_ok = False

    if image_data_url and vision_ok:
        content = user_message_content_for_llm(
            f"[image: {image_data_url}]\n{prompt}",
            vision_enabled=True,
        )
        messages = [{"role": "user", "content": content}]

        def _call() -> object:
            return router.chat(messages, model_id=model_id)

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_call)
            try:
                return _llm_result(future.result(timeout=timeout_sec), prompt=prompt)
            except FuturesTimeout as exc:
                future.cancel()
                raise DesignError(f"Model timed out after {int(timeout_sec)}s") from exc

    note = ""
    if image_data_url and not vision_ok:
        note = (
            "A reference screenshot was attached but the active model may not support vision. "
            "Infer a polished UI that matches the product brief alone.\n"
        )
    return _llm_complete(router, note + prompt, model_id=model_id, timeout_sec=timeout_sec)


def _try_llm_complete_vision(
    router: Any,
    prompt: str,
    *,
    model_id: str,
    image_data_url: str | None = None,
    timeout_sec: float = _LLM_UI_TIMEOUT_SEC,
) -> tuple[str, str | None, dict[str, int], bool, str | None]:
    """Best-effort LLM call for UI HTML — never aborts the whole generation pipeline."""
    try:
        text, reasoning, usage, estimated = _llm_complete_vision(
            router,
            prompt,
            model_id=model_id,
            image_data_url=image_data_url,
            timeout_sec=timeout_sec,
        )
        return text, reasoning, usage, estimated, None
    except DesignError as exc:
        logger.warning("design ui llm call failed model=%s err=%s", model_id, exc)
        return "", None, _empty_token_usage(), False, str(exc)
    except Exception as exc:
        logger.warning("design ui llm call error model=%s err=%s", model_id, exc)
        return "", None, _empty_token_usage(), False, str(exc)


def _extract_html_from_llm(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    fence = re.search(r"```(?:html)?\s*([\s\S]*?)```", raw, re.I)
    if fence:
        return fence.group(1).strip()
    # Some models omit fences — grab the first HTML document in the blob.
    doc = re.search(r"(<!DOCTYPE[\s\S]*?</html>)", raw, re.I)
    if doc:
        return doc.group(1).strip()
    html_open = re.search(r"(<html[\s\S]*?</html>)", raw, re.I)
    if html_open:
        return html_open.group(1).strip()
    return raw


def _html_from_llm_response(text: str, reasoning: str | None = None) -> str:
    """Prefer main content; fall back to reasoning when weak models put HTML there."""
    tag_re = re.compile(r"<(?:html|body|div|main|section|header|nav|form|button|h[1-6]|p)\b", re.I)
    for chunk in (text, reasoning or ""):
        if not (chunk or "").strip():
            continue
        extracted = _extract_html_from_llm(chunk)
        if extracted and tag_re.search(extracted):
            return extracted
    return ""


def _build_ui_compact_prompt(
    *,
    user_prompt: str,
    spec: dict[str, Any],
    device: str,
) -> str:
    """Short prompt for weak models that choke on long design briefs."""
    pattern = str(spec.get("layout_pattern") or detect_layout_pattern(user_prompt, device=device))
    primary = _first_hex((spec.get("colors") or {}), "primary", "#171717")
    return (
        "Generate ONE complete HTML page with Tailwind CDN for this brief.\n"
        f"Brief: {user_prompt}\n"
        f"Device: {device}\n"
        f"Layout: {pattern}\n"
        f"Primary color: {primary}\n"
        f"Brand: {spec.get('name') or 'Clutch'}\n"
        "Rules: full <!DOCTYPE html>…</html>, visible UI in body, match the brief intent.\n"
        "Return ONLY ```html ... ```."
    )


def _build_ui_generation_prompt(
    *,
    user_prompt: str,
    spec: dict[str, Any],
    device: str,
    pattern: str,
    design_md: str = "",
    md_text: str | None = None,
    url_snapshot: dict[str, Any] | None = None,
    has_image: bool = False,
    current_html: str = "",
    instruction: str = "",
) -> str:
    """Assemble HTML generation prompt with layout pattern + few-shot reference."""
    fewshot = fewshot_for_pattern(pattern)
    layout_hint = layout_wrapper_hint(pattern)
    ui_parts = [
        "You are an expert web designer. Generate a single, fully-formed, beautiful HTML document "
        "using Tailwind CSS.\n",
        f"Brief: {user_prompt}\n",
    ]
    if instruction:
        ui_parts.append(f"Revision instruction: {instruction}\n")
    ui_parts.append(
        (
            "Device target: mobile app viewport 390×844 CSS pixels (iPhone-class). "
            "Use a single-column stacked layout, large touch targets, no desktop sidebar.\n"
            if device == "app"
            else
            "Device target: desktop web viewport 1920×1080 CSS pixels (16:9). "
            "Use a full-width desktop layout (top nav, multi-column grids, wide hero). "
            "Do NOT produce a narrow phone-only page.\n"
        )
    )
    intent = _prompt_intent(user_prompt)
    if intent == "login":
        intent_rule = (
            "5. Brief intent: login — build a polished sign-in / registration screen.\n"
        )
    else:
        intent_rule = (
            f"5. Brief intent: {intent} — the page MUST match this intent; "
            "do NOT default to a generic login/auth screen unless the brief asks for it.\n"
        )
    ui_parts += [
        f"Layout pattern: {pattern}\n",
        f"Layout constraints: {layout_hint}\n",
        (
            "CRITICAL Rules:\n"
            "1. Use Tailwind CDN: <script src=\"https://cdn.tailwindcss.com\"></script>\n"
            "2. Define design system colors via tailwind.config script — no custom <style> blocks.\n"
            "3. Complete HTML with closed </html>; keep body under 80 lines to avoid truncation.\n"
            "4. Implement the screen in the Brief — match the requested screen type.\n"
        )
        + intent_rule
        + (
            "6. Select 3-5 core components; high-fidelity modern aesthetics (rounded-2xl cards, "
            "subtle gradients, hover transitions, generous spacing py-12–py-20).\n"
        ),
        f"Style reference (match quality & polish only — do NOT copy this layout verbatim):\n{fewshot}\n",
        f"Design system JSON:\n{json.dumps(spec, ensure_ascii=False)}\n",
    ]
    if design_md:
        cap = 2000 if str(spec.get("name") or "").strip().lower() == "clutch" else 6000
        ui_parts.append(f"DESIGN.md rules:\n{design_md[:cap]}\n")
    if md_text:
        ui_parts.append(f"Source Design.md:\n{md_text[:6000]}\n")
    if url_snapshot:
        ui_parts.append(
            f"Visual inspiration from {url_snapshot.get('url')} "
            f"({url_snapshot.get('title') or url_snapshot.get('host')}).\n"
        )
    if has_image:
        ui_parts.append(
            "Match the attached reference screenshot (structure, hierarchy, spacing).\n"
        )
    if current_html:
        ui_parts.append(f"Current HTML to revise:\n{current_html[:14000]}\n")
    ui_parts.append("Return ONLY the HTML document inside ```html ... ```.")
    return "".join(ui_parts)


def _design_review_and_improve(
    router: Any,
    *,
    html: str,
    spec: dict[str, Any],
    user_prompt: str,
    model_id: str,
    device: str,
) -> tuple[str, str | None, int, dict[str, int], bool]:
    """Design Review Pass: score HTML; refine once if below threshold."""
    review_prompt = (
        "You are a senior UI design reviewer. Score this HTML mockup 1-10 on:\n"
        "- Visual hierarchy & modern aesthetics\n"
        "- Spacing & typography consistency\n"
        "- Color consistency & contrast\n"
        "- CTA clarity & accessibility\n"
        "- Responsive layout\n\n"
        f"Brief: {user_prompt}\nDevice: {device}\n"
        f"Design system: {json.dumps(spec, ensure_ascii=False)[:4000]}\n\n"
        f"HTML:\n{html[:12000]}\n\n"
        'Return ONLY JSON: {"score": N, "feedback": "..."}'
    )
    review_text, review_reasoning, review_usage, review_estimated = _llm_complete(
        router, review_prompt, model_id=model_id
    )
    score, feedback = parse_review_score(review_text)
    combined_reasoning = review_reasoning
    usage = review_usage
    estimated = review_estimated
    if score >= review_threshold():
        return html, combined_reasoning, score, usage, estimated
    improve_prompt = (
        "Improve this HTML UI based on the design review feedback. "
        "Apply concrete fixes to spacing, hierarchy, CTAs, and contrast.\n"
        f"Feedback (score {score}/10): {feedback}\n"
        f"Brief: {user_prompt}\n"
        f"HTML:\n{html[:14000]}\n"
        "Use Tailwind CDN + tailwind.config for colors. Return ONLY ```html ... ```."
    )
    improved_text, improve_reasoning, improve_usage, improve_estimated = _llm_complete(
        router, improve_prompt, model_id=model_id
    )
    improved = _extract_html_from_llm(improved_text)
    usage = _merge_token_usage(usage, improve_usage)
    estimated = estimated or improve_estimated
    if improve_reasoning:
        combined_reasoning = "\n---\n".join(filter(None, [combined_reasoning, improve_reasoning]))
    if _html_has_visible_content(improved):
        return improved, combined_reasoning, score, usage, estimated
    return html, combined_reasoning, score, usage, estimated


def _build_ui_correction_prompt(
    *,
    user_prompt: str,
    spec: dict[str, Any],
    device: str,
    reason: str,
) -> str:
    """Second-pass prompt when the first LLM output was blank or misaligned with the brief."""
    layout_hint = layout_wrapper_hint(
        str(spec.get("layout_pattern") or detect_layout_pattern(user_prompt, device=device))
    )
    return (
        "You are an expert web designer. Your previous HTML was rejected.\n"
        f"Rejection reason: {reason}\n"
        f"Brief (follow exactly): {user_prompt}\n"
        f"Layout constraints: {layout_hint}\n"
        f"Design system JSON:\n{json.dumps(spec, ensure_ascii=False)[:6000]}\n"
        "Rules:\n"
        "- Generate a NEW complete HTML document using Tailwind CDN.\n"
        "- Fulfill the brief — do NOT default to login/auth unless explicitly requested.\n"
        "- Use colors and typography from the design system; make it visually distinct.\n"
        "Return ONLY ```html ... ```."
    )


def _generate_ui_html(
    router: Any,
    *,
    user_prompt: str,
    spec: dict[str, Any],
    device: str,
    model_id: str,
    design_md: str = "",
    md_text: str | None = None,
    url_snapshot: dict[str, Any] | None = None,
    has_image: bool = False,
    image_data_url: str | None = None,
    current_html: str = "",
    instruction: str = "",
    fallback_html: str | None = None,
) -> tuple[str, str | None, dict[str, int], bool, str | None]:
    """Generate HTML via LLM; retry once on blank or brief mismatch (no template substitution)."""
    last_fail: str | None = None
    pattern = str(spec.get("layout_pattern") or detect_layout_pattern(user_prompt, device=device))
    meta = _build_ui_generation_prompt(
        user_prompt=user_prompt,
        spec=spec,
        device=device,
        pattern=pattern,
        design_md=design_md,
        md_text=md_text,
        url_snapshot=url_snapshot,
        has_image=has_image,
        current_html=current_html,
        instruction=instruction,
    )
    text, reasoning, usage, estimated, fail = _try_llm_complete_vision(
        router, meta, model_id=model_id, image_data_url=image_data_url
    )
    if fail:
        last_fail = fail
    usage_acc = usage
    estimated_acc = estimated
    raw = _html_from_llm_response(text, reasoning)
    html = _coerce_ui_html(
        raw,
        title=str(spec.get("name") or "UI"),
        prompt=user_prompt,
        spec=spec,
        device=device,
        fallback_html=fallback_html,
        allow_template_fallback=False,
    )
    if _html_has_visible_content(html) and not _html_matches_brief_intent(user_prompt, html):
        detected = _detect_html_intent(html)
        expected = _prompt_intent(user_prompt)
        logger.warning(
            "design ui intent mismatch prompt=%r detected=%s expected=%s — LLM retry",
            user_prompt[:80],
            detected,
            expected,
        )
        correction = _build_ui_correction_prompt(
            user_prompt=user_prompt,
            spec=spec,
            device=device,
            reason=(
                f"Page looks like '{detected}' but brief requires '{expected}'. "
                "Do not output login/auth unless the brief asks for it."
            ),
        )
        retry_text, retry_reasoning, retry_usage, retry_estimated, fail = _try_llm_complete_vision(
            router, correction, model_id=model_id, image_data_url=image_data_url
        )
        if fail:
            last_fail = fail
        usage_acc = _merge_token_usage(usage_acc, retry_usage)
        estimated_acc = estimated_acc or retry_estimated
        retry_raw = _html_from_llm_response(retry_text, retry_reasoning)
        retry_html = _coerce_ui_html(
            retry_raw,
            title=str(spec.get("name") or "UI"),
            prompt=user_prompt,
            spec=spec,
            device=device,
            fallback_html=html,
            allow_template_fallback=False,
        )
        if _html_has_visible_content(retry_html):
            html = retry_html
            reasoning = "\n---\n".join(filter(None, [reasoning, retry_reasoning]))
    elif not _html_has_visible_content(html):
        logger.warning("design ui blank output prompt=%r — compact LLM retry", user_prompt[:80])
        compact = _build_ui_compact_prompt(user_prompt=user_prompt, spec=spec, device=device)
        retry_text, retry_reasoning, retry_usage, retry_estimated, fail = _try_llm_complete_vision(
            router, compact, model_id=model_id, image_data_url=image_data_url
        )
        if fail:
            last_fail = fail
        usage_acc = _merge_token_usage(usage_acc, retry_usage)
        estimated_acc = estimated_acc or retry_estimated
        retry_raw = _html_from_llm_response(retry_text, retry_reasoning)
        retry_html = _coerce_ui_html(
            retry_raw,
            title=str(spec.get("name") or "UI"),
            prompt=user_prompt,
            spec=spec,
            device=device,
            fallback_html=fallback_html,
            allow_template_fallback=False,
        )
        if _html_has_visible_content(retry_html):
            html = retry_html
            reasoning = "\n---\n".join(filter(None, [reasoning, retry_reasoning]))
        else:
            retry_meta = (
                meta
                + "\n\nIMPORTANT: Your previous response was empty or invalid. "
                "Output a complete, visible HTML document that fulfills the brief."
            )
            retry2_text, retry2_reasoning, retry2_usage, retry2_estimated, fail = _try_llm_complete_vision(
                router, retry_meta, model_id=model_id, image_data_url=image_data_url
            )
            if fail:
                last_fail = fail
            usage_acc = _merge_token_usage(usage_acc, retry2_usage)
            estimated_acc = estimated_acc or retry2_estimated
            retry2_raw = _html_from_llm_response(retry2_text, retry2_reasoning)
            retry2_html = _coerce_ui_html(
                retry2_raw,
                title=str(spec.get("name") or "UI"),
                prompt=user_prompt,
                spec=spec,
                device=device,
                fallback_html=fallback_html,
                allow_template_fallback=False,
            )
            if _html_has_visible_content(retry2_html):
                html = retry2_html
                reasoning = "\n---\n".join(
                    filter(None, [reasoning, retry_reasoning, retry2_reasoning])
                )
    if _html_has_visible_content(html) and _DESIGN_REVIEW_ENABLED:
        reviewed, review_reasoning, _score, review_usage, review_estimated = _design_review_and_improve(
            router,
            html=html,
            spec=spec,
            user_prompt=user_prompt,
            model_id=model_id,
            device=device,
        )
        usage_acc = _merge_token_usage(usage_acc, review_usage)
        estimated_acc = estimated_acc or review_estimated
        html = _coerce_ui_html(
            reviewed,
            title=str(spec.get("name") or "UI"),
            prompt=user_prompt,
            spec=spec,
            device=device,
            fallback_html=html,
            allow_template_fallback=False,
        )
        if review_reasoning:
            reasoning = "\n---\n".join(filter(None, [reasoning, review_reasoning]))
    if not _html_has_visible_content(html) and not last_fail:
        last_fail = "the model returned no valid HTML"
    return html, reasoning, usage_acc, estimated_acc, last_fail


def generate_session(
    run_id: str,
    *,
    prompt: str,
    device: str = "web",
    reference_image: str | None = None,
    reference_md: str | None = None,
    reference_md_name: str | None = None,
    reference_url: str | None = None,
    design_system: str | None = None,
    continue_inflight: bool = False,
) -> dict[str, Any]:
    """Two-phase: design spec first, then UI HTML (optional image / Design.md / URL)."""
    from src.models_config import get_router, is_model_available

    session_dir = _session_dir(run_id)
    if not (session_dir / MANIFEST).is_file():
        ensure_session(run_id, title=prompt[:40], prompt=prompt)
    manifest = _read_manifest(session_dir)
    user_prompt = prompt.strip() or str(manifest.get("prompt") or "").strip()

    ref_rel = manifest.get("reference_image")
    if reference_image:
        ref_rel = _save_reference_image(session_dir, reference_image) or ref_rel
    image_data_url = _load_reference_data_url(session_dir, str(ref_rel) if ref_rel else None)

    md_rel = manifest.get("reference_md")
    if reference_md:
        md_rel = _save_reference_md(session_dir, reference_md, name=reference_md_name) or md_rel
    md_text, md_name = _load_reference_md(session_dir, str(md_rel) if md_rel else None)

    url = _normalize_reference_url(reference_url) or manifest.get("reference_url")
    url_snapshot = _load_url_snapshot(session_dir)
    if url and (reference_url or not url_snapshot):
        try:
            url_snapshot = _fetch_url_snapshot(str(url))
            _save_url_snapshot(session_dir, url_snapshot)
            url = url_snapshot.get("url") or url
        except DesignError as exc:
            logger.warning("design url fetch failed run_id=%s err=%s", run_id, exc)
            url_snapshot = {
                "url": url,
                "host": re.sub(r"^https?://", "", str(url)).split("/")[0],
                "title": "",
                "description": "",
                "excerpt": "",
                "error": str(exc),
                "fetched_at": _now_iso(),
            }
            _save_url_snapshot(session_dir, url_snapshot)

    has_image = bool(image_data_url)
    has_md = bool(md_text)
    has_url = bool(url)
    if not user_prompt and not has_image and not has_md and not has_url:
        raise DesignError("Prompt or reference is required")
    if not user_prompt:
        if has_md:
            user_prompt = f"使用 the file [{md_name or 'DESIGN.md'}] 创建设计系统。设计一个登录页面。"
        elif has_url:
            user_prompt = "参考这个网站，生成一个登录页面"
        else:
            user_prompt = "参考图片的设计，生成界面"

    if has_md:
        intro = (
            f"I'll build a design system from «{md_name or 'DESIGN.md'}», then craft an interface that matches your brief."
        )
    elif has_url:
        intro = (
            f"I'll load {url_snapshot.get('host') if url_snapshot else url}, extract a design system, then craft a matching interface."
        )
    elif has_image:
        intro = (
            "I'll use your reference image to extract a design system (colors, type, components), then craft a matching interface."
        )
    elif normalize_preset_id(design_system or manifest.get("design_system")) == "clutch" and not (
        has_md or has_url or has_image
    ):
        intro = (
            "I'll apply the built-in Clutch design system, then craft the interface for your brief."
        )
    else:
        intro = "I'll start with a design specification (colors, type, components), then craft the interface to match."

    attach_bits = []
    if has_image:
        attach_bits.append("reference image")
    if has_md:
        attach_bits.append(f"file {md_name or 'DESIGN.md'}")
    if has_url:
        attach_bits.append(f"url {url}")
    attach_note = f" [{', '.join(attach_bits)}]" if attach_bits else ""

    resume = continue_inflight and str(manifest.get("status") or "") in {
        "crafting_spec",
        "generating_ui",
    }
    if resume and manifest.get("process_log"):
        process_log = list(manifest.get("process_log") or [])
    else:
        process_log = [
            {
                "role": "user",
                "text": user_prompt + attach_note,
                "at": _now_iso(),
            },
            {
                "role": "assistant",
                "text": intro,
                "status": "crafting_spec",
                "at": _now_iso(),
            },
        ]
    manifest["prompt"] = user_prompt
    manifest["name"] = user_prompt[:48] or manifest.get("name") or "New Design"
    manifest["device"] = device if device in {"web", "app"} else "web"
    manifest["phase"] = "spec"
    manifest["status"] = "crafting_spec"
    manifest["process_log"] = process_log
    manifest["error"] = None
    if not resume:
        manifest["round_history"] = []
        manifest["screens"] = []
        manifest["spec"] = None
        manifest["design_system"] = normalize_preset_id(design_system or manifest.get("design_system"))
    if ref_rel:
        manifest["reference_image"] = ref_rel
    if md_rel:
        manifest["reference_md"] = md_rel
        manifest["reference_md_name"] = md_name or reference_md_name or "DESIGN.md"
    if url:
        manifest["reference_url"] = url
        if url_snapshot:
            manifest["url_snapshot"] = {
                "url": url_snapshot.get("url"),
                "host": url_snapshot.get("host"),
                "title": url_snapshot.get("title"),
                "description": url_snapshot.get("description"),
            }
    _write_manifest(session_dir, manifest)

    # Phase 1 — spec
    spec: dict[str, Any] | None = None
    source = "fallback"
    router = get_router()
    model_id = router.active_model_id
    # Persist active model on the session; tags live on each step via metadata
    # (not as standalone Agent Log lines — users may switch models mid-session).
    process_log = list(manifest.get("process_log") or [])
    model_id, model_name = _stamp_session_model(
        manifest,
        router,
        model_id=model_id,
        process_log=process_log,
        record_in_log=False,
    )
    _write_manifest(session_dir, manifest)
    preset_id = normalize_preset_id(manifest.get("design_system"))
    use_builtin_preset = preset_id == "clutch" and not (has_image or has_md or has_url)
    spec_usage = _empty_token_usage()
    spec_usage_estimated = False

    if use_builtin_preset:
        _update_process_status(
            session_dir,
            manifest,
            text="Applying built-in Clutch design system…",
            status="crafting_spec",
            model_id=model_id,
            model_name=model_name,
        )
        spec, design_md = resolve_builtin_spec(preset_id, user_prompt, device=device)
        source = "builtin_clutch"
    else:
        _update_process_status(
            session_dir,
            manifest,
            text="Extracting colors, typography, and layout tokens from your brief…",
            status="crafting_spec",
            model_id=model_id,
            model_name=model_name,
        )
        design_md = ""
        if is_model_available(router, model_id):
            try:
                context_parts = [
                    "You are a product design system generator.\n",
                    f"Brief: {user_prompt}\nDevice: {device}\n",
                ]
                if has_md and md_text:
                    context_parts.append(
                        f"Source design markdown «{md_name}» (authoritative tokens & rules):\n"
                        f"---\n{md_text[:12000]}\n---\n"
                        "Extract and structure a design system from this document.\n"
                    )
                if has_url and url_snapshot:
                    context_parts.append(
                        "Reference website snapshot:\n"
                        f"URL: {url_snapshot.get('url')}\n"
                        f"Title: {url_snapshot.get('title')}\n"
                        f"Description: {url_snapshot.get('description')}\n"
                        f"Excerpt: {(url_snapshot.get('excerpt') or '')[:3000]}\n"
                        "Infer a polished design system inspired by this site's visual language.\n"
                    )
                if has_image:
                    context_parts.append(
                        "A reference UI screenshot is attached. Extract colors, typography, and component style from it.\n"
                    )
                context_parts.append(
                    "Return ONLY JSON with keys: name, rationale, brand (name, voice), visual_style, "
                    "layout_system, layout_pattern, grid (columns, gutter, max_width), colors "
                    "(object of arrays of hex), typography (fontFamily, samples[{label,size,weight}]), "
                    "radius (sm, md, lg, xl), shadow (card, elevated), components (string array), "
                    "motion (duration, easing, hover_lift), responsive (string), accessibility (string). "
                    "No markdown fences."
                )
                meta = "".join(context_parts)
                spec_raw, _spec_reasoning, call_usage, call_estimated = _llm_complete_vision(
                    router, meta, model_id=model_id, image_data_url=image_data_url
                )
                spec_usage = _merge_token_usage(spec_usage, call_usage)
                spec_usage_estimated = spec_usage_estimated or call_estimated
                spec = _extract_json_block(spec_raw)
                pattern = detect_layout_pattern(user_prompt, device=device)
                spec = enrich_fallback_spec(spec, user_prompt, pattern)
                if has_image:
                    source = "llm_vision"
                elif has_md:
                    source = "llm_md"
                elif has_url:
                    source = "llm_url"
                else:
                    source = "llm"
            except Exception as exc:
                logger.warning("design spec LLM failed run_id=%s err=%s", run_id, exc)

        if not spec:
            seed = user_prompt
            if has_md and md_text:
                seed = f"{user_prompt}\n{md_text[:2000]}"
            elif has_url and url_snapshot:
                seed = f"{user_prompt}\n{url_snapshot.get('title')}\n{url_snapshot.get('description')}"
            pattern = detect_layout_pattern(seed, device=device)
            spec = enrich_fallback_spec(_fallback_spec(seed), seed, pattern)

        if has_md and md_text:
            design_md = md_text if md_text.endswith("\n") else md_text + "\n"
        else:
            design_md = _spec_to_design_md(spec)

    (session_dir / SPEC_JSON).write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (session_dir / DESIGN_MD).write_text(design_md, encoding="utf-8")

    process_log = list(manifest.get("process_log") or [])
    spec_ready_text = f"Design system «{spec.get('name')}» ready."
    if not is_model_available(router, model_id):
        spec_ready_text += f"\n\n⚠️ Warning: Model '{model_id}' is not available (API key missing in Settings -> Models). Using offline fallback templates."
    _finalize_assistant_step(
        process_log,
        text=spec_ready_text,
        status="spec_ready",
        model_id=model_id,
        model_name=model_name,
        usage=spec_usage if not use_builtin_preset else None,
        usage_estimated=spec_usage_estimated,
        replace_statuses={"crafting_spec"},
    )
    manifest["spec"] = spec
    manifest["phase"] = "ui"
    manifest["generate_source"] = source
    manifest["process_log"] = process_log
    _write_manifest(session_dir, manifest)
    _append_process_status(
        session_dir,
        manifest,
        text="Generating high-fidelity HTML with layout patterns and design review…",
        status="generating_ui",
        model_id=model_id,
        model_name=model_name,
    )
    _append_design_run_log(
        run_id,
        f"spec ready name={spec.get('name')!s} → generating_ui device={device} model={model_id}",
    )

    # Phase 2 — UI from spec (layout pattern + few-shot + review pass)
    session_dir = _session_dir(run_id)
    html = ""
    ui_reasoning: str | None = None
    ui_usage = _empty_token_usage()
    ui_usage_estimated = False
    ui_fail_reason: str | None = None
    design_md_text = design_md
    if is_model_available(router, model_id):
        try:
            html, ui_reasoning, ui_usage, ui_usage_estimated, ui_fail_reason = _generate_ui_html(
                router,
                user_prompt=user_prompt,
                spec=spec,
                device=device,
                model_id=model_id,
                design_md=design_md_text,
                md_text=md_text if has_md else None,
                url_snapshot=url_snapshot if has_url else None,
                has_image=has_image,
                image_data_url=image_data_url,
            )
        except Exception as exc:
            logger.warning("design ui LLM failed run_id=%s err=%s", run_id, exc)
            ui_fail_reason = str(exc)

    llm_available = is_model_available(router, model_id)
    if not _html_has_visible_content(html):
        if llm_available:
            detail = ui_fail_reason or "the model returned no valid HTML"
            err_msg = f"Generation failed — {detail}. Please try again."
            process_log = list(manifest.get("process_log") or [])
            _finalize_assistant_step(
                process_log,
                text=err_msg,
                status="error",
                model_id=model_id,
                model_name=model_name,
                usage=ui_usage,
                usage_estimated=ui_usage_estimated,
                replace_statuses={"generating_ui"},
            )
            manifest["status"] = "error"
            manifest["error"] = err_msg
            manifest["process_log"] = process_log
            manifest["screens"] = []
            _write_manifest(session_dir, manifest)
            return _public(manifest, session_dir)
        html = _fallback_ui_html(user_prompt, spec, device=device)

    screen_id = "main"
    session_dir = _session_dir(run_id)
    (session_dir / "screens").mkdir(exist_ok=True)
    process_log = list(manifest.get("process_log") or [])
    round_index = _next_round_index(manifest, screen_id)
    ui_ready_text = (
        f"Interface draft is ready — wrote screens/{screen_id}_r{round_index}.html "
        f"({len(html)} bytes)."
    )
    manifest["generate_source"] = source
    if not is_model_available(router, model_id):
        ui_ready_text += f"\n\n⚠️ Warning: Model '{model_id}' is not available (API key missing in Settings -> Models). Using offline fallback templates."
    _finalize_assistant_step(
        process_log,
        text=ui_ready_text,
        status="ready",
        model_id=model_id,
        model_name=model_name,
        usage=ui_usage,
        usage_estimated=ui_usage_estimated,
        replace_statuses={"generating_ui"},
    )
    round_entry = _record_screen_round(
        session_dir,
        manifest,
        screen_id=screen_id,
        html=html,
        prompt=user_prompt,
        reasoning_content=ui_reasoning,
        process_log_slice=list(process_log),
    )
    if manifest.get("round_history"):
        history = list(manifest["round_history"])
        if history:
            history[-1] = {**history[-1], "process_log": list(process_log)}
            manifest["round_history"] = history
    ui_origin_x = _default_ui_origin_x(has_source=has_image or has_md or has_url)
    screens = [
        {
            "id": screen_id,
            "name": str(spec.get("name") or "Interface"),
            "position": {"x": ui_origin_x, "y": _DESIGN_ROW_Y},
            "html_path": round_entry["html_path"],
            "active_round_index": round_entry["round_index"],
        }
    ]
    manifest["screens"] = screens
    manifest["phase"] = "canvas"
    manifest["status"] = "ready"
    manifest["process_log"] = process_log
    manifest["prototype_approved"] = False
    manifest["react_ready"] = False
    manifest["react_approved"] = False
    # Sidebar uses live HTML preview — drop legacy silhouette SVG.
    _clear_fake_thumbnail(session_dir)
    manifest.pop("thumbnail", None)
    _write_manifest(session_dir, manifest)
    sync_session_folder_name(
        run_id,
        title=str(manifest.get("name") or user_prompt or "design"),
        device=device,
    )
    _append_design_run_log(
        run_id,
        f"generate done source={source} screen={screen_id} html_bytes={len(html)} round={round_entry['round_index']}",
        reasoning=ui_reasoning,
    )
    logger.info("design generate done run_id=%s source=%s", run_id, source)
    return get_session(run_id)


def start_generate_session(
    run_id: str,
    *,
    prompt: str,
    device: str = "web",
    reference_image: str | None = None,
    reference_md: str | None = None,
    reference_md_name: str | None = None,
    reference_url: str | None = None,
    design_system: str | None = None,
) -> dict[str, Any]:
    """Kick off two-phase generate in a background thread; return immediately for polling."""
    session_dir = _session_dir(run_id)
    if not (session_dir / MANIFEST).is_file():
        ensure_session(run_id, title=prompt[:40], prompt=prompt)
    with _generate_lock:
        existing = _generate_jobs.get(run_id)
        if existing and existing.is_alive():
            return get_session(run_id)

    user_prompt = (prompt or "").strip()
    url = _normalize_reference_url(reference_url)
    md_rel = _save_reference_md(session_dir, reference_md, name=reference_md_name) if reference_md else None
    md_text, md_name = _load_reference_md(session_dir, md_rel) if md_rel else (None, None)
    ref_rel = _save_reference_image(session_dir, reference_image) if reference_image else None

    if not user_prompt and not ref_rel and not md_rel and not url:
        raise DesignError("Prompt or reference is required")
    if not user_prompt:
        if md_rel:
            user_prompt = f"使用 the file [{md_name or 'DESIGN.md'}] 创建设计系统。设计一个登录页面。"
        elif url:
            user_prompt = "参考这个网站，生成一个登录页面"
        else:
            user_prompt = "参考图片的设计，生成界面"

    url_snapshot: dict[str, Any] | None = None
    if url:
        try:
            url_snapshot = _fetch_url_snapshot(url)
            _save_url_snapshot(session_dir, url_snapshot)
            url = str(url_snapshot.get("url") or url)
        except DesignError as exc:
            logger.warning("design url fetch (start) failed run_id=%s err=%s", run_id, exc)
            url_snapshot = {
                "url": url,
                "host": re.sub(r"^https?://", "", url).split("/")[0],
                "title": "",
                "description": "",
                "excerpt": "",
                "error": str(exc),
                "fetched_at": _now_iso(),
            }
            _save_url_snapshot(session_dir, url_snapshot)

    has_image = bool(ref_rel)
    has_md = bool(md_rel)
    has_url = bool(url)
    if has_md:
        intro = f"I'll build a design system from «{md_name or 'DESIGN.md'}», then craft a matching interface."
    elif has_url:
        host = (url_snapshot or {}).get("host") or url
        intro = f"I'll load {host} on the canvas, extract a design system, then craft a matching interface."
    elif has_image:
        intro = "I'll use your reference image to extract a design system, then craft a matching interface."
    elif normalize_preset_id(design_system) == "clutch":
        intro = (
            "I'll apply the built-in Clutch design system, then craft the interface for your brief."
        )
    else:
        intro = "I'll start with a design specification (colors, type, components), then craft the interface to match."

    attach_bits = []
    if has_image:
        attach_bits.append("reference image")
    if has_md:
        attach_bits.append(f"file {md_name or 'DESIGN.md'}")
    if has_url:
        attach_bits.append(f"url {url}")
    attach_note = f" [{', '.join(attach_bits)}]" if attach_bits else ""

    manifest = _read_manifest(session_dir)
    manifest["prompt"] = user_prompt
    manifest["name"] = user_prompt[:48] or manifest.get("name") or "New Design"
    manifest["device"] = device if device in {"web", "app"} else "web"
    manifest["phase"] = "spec"
    manifest["status"] = "crafting_spec"
    manifest["error"] = None
    manifest["screens"] = []
    manifest["spec"] = None
    manifest["round_history"] = []
    manifest["design_system"] = normalize_preset_id(design_system)
    if ref_rel:
        manifest["reference_image"] = ref_rel
    if md_rel:
        manifest["reference_md"] = md_rel
        manifest["reference_md_name"] = md_name or reference_md_name or "DESIGN.md"
    if url:
        manifest["reference_url"] = url
        if url_snapshot:
            manifest["url_snapshot"] = {
                "url": url_snapshot.get("url"),
                "host": url_snapshot.get("host"),
                "title": url_snapshot.get("title"),
                "description": url_snapshot.get("description"),
            }
    manifest["process_log"] = [
        {
            "role": "user",
            "text": user_prompt + attach_note,
            "at": _now_iso(),
        },
        {
            "role": "assistant",
            "text": intro,
            "status": "crafting_spec",
            "at": _now_iso(),
        },
    ]
    # No silhouette thumbnail while crafting — sidebar stays gray until real UI exists.
    _clear_fake_thumbnail(session_dir)
    manifest.pop("thumbnail", None)
    _write_manifest(session_dir, manifest)
    session_dir = sync_session_folder_name(
        run_id,
        title=str(manifest.get("name") or user_prompt or "design"),
        device=str(manifest.get("device") or device or "web"),
    )
    _append_design_run_log(
        run_id,
        f"generate started device={device} prompt={user_prompt[:80]!r}",
    )

    def _worker() -> None:
        try:
            generate_session(
                run_id,
                prompt=user_prompt,
                device=device,
                reference_image=None,
                reference_md=None,
                reference_url=None,  # already saved / snapshotted
                design_system=manifest.get("design_system"),
                continue_inflight=True,
            )
        except Exception as exc:
            logger.exception("design generate worker failed run_id=%s", run_id)
            try:
                err_dir = _session_dir(run_id)
                m = _read_manifest(err_dir)
                m["status"] = "error"
                m["error"] = str(exc)
                log = list(m.get("process_log") or [])
                log.append(
                    {
                        "role": "assistant",
                        "text": f"Generation failed: {exc}",
                        "status": "error",
                        "at": _now_iso(),
                    }
                )
                m["process_log"] = log
                _write_manifest(err_dir, m)
            except Exception:
                pass
        finally:
            with _generate_lock:
                _generate_jobs.pop(run_id, None)

    thread = threading.Thread(target=_worker, name=f"design-gen-{run_id}", daemon=True)
    with _generate_lock:
        _generate_jobs[run_id] = thread
    thread.start()
    # Return in-memory snapshot — do not re-read disk (worker may be rewriting).
    return _public(manifest, session_dir)


def _html_essentially_same(a: str, b: str) -> bool:
    """True when two HTML docs are visually the same (ignore whitespace / data-note)."""

    def norm(s: str) -> str:
        out = re.sub(r"\s+", "", s or "")
        out = re.sub(r'data-note="[^"]*"', "", out, flags=re.I)
        return out

    return bool(a) and bool(b) and norm(a) == norm(b)


def _merged_design_prompt(manifest: dict[str, Any], instruction: str) -> str:
    base = str(manifest.get("prompt") or manifest.get("name") or "").strip()
    note = (instruction or "").strip()
    if base and note:
        return f"{base}\n{note}"
    return note or base or "Interface"


def _infer_iterate_mode(instruction: str, *, mode: str | None, target_kind: str | None) -> str:
    """Decide modify vs add. Selected UI defaults to modify; explicit add language → add."""
    raw = (mode or "auto").strip().lower()
    if raw in {"modify", "add"}:
        return raw
    text = instruction.lower()
    add_keys = (
        "新增",
        "添加一",
        "再做",
        "另一个",
        "新页面",
        "新画板",
        "再来一",
        "add ",
        "new page",
        "another ",
        "create a new",
        "also create",
        "new screen",
        "new artboard",
    )
    mod_keys = (
        "改成",
        "修改",
        "优化",
        "调整",
        "换成",
        "改一下",
        "要体现",
        "需要",
        "显示",
        "加上",
        "增加",
        "完善",
        "深色",
        "fix",
        "change ",
        "update ",
        "make it",
        "dark mode",
        "improve",
        "tweak",
        "refine",
        "add lyrics",
        "show ",
    )
    has_add = any(k in text for k in add_keys)
    has_mod = any(k in text for k in mod_keys)
    if has_add and not has_mod:
        return "add"
    if has_mod and not has_add:
        return "modify"
    if has_mod and has_add and target_kind == "ui":
        return "modify"
    # Selected artboard → refine in place (Stitch-like). Unknown without UI → add.
    if target_kind == "ui":
        return "modify"
    return "add"


def _next_screen_id(screens: list[dict[str, Any]]) -> str:
    used = {str(s.get("id") or "") for s in screens}
    if "main" not in used:
        return "main"
    i = 2
    while f"screen-{i}" in used:
        i += 1
    return f"screen-{i}"


def _screen_layout_x(
    screens: list[dict[str, Any]], *, device: str = "web", has_source: bool = False
) -> int:
    xs = []
    for s in screens:
        pos = s.get("position") or {}
        if isinstance(pos, dict) and isinstance(pos.get("x"), (int, float)):
            xs.append(int(pos["x"]))
    step = _ui_layout_step(device)
    return (max(xs) + step) if xs else _default_ui_origin_x(has_source=has_source)


def iterate_session(
    run_id: str,
    instruction: str,
    *,
    target_kind: str | None = None,
    target_id: str | None = None,
    element_path: str | None = None,
    element_label: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    from src.models_config import get_router, is_model_available

    session_dir = _session_dir(run_id)
    manifest = _read_manifest(session_dir)
    instruction = instruction.strip()
    if not instruction:
        raise DesignError("Instruction is required")
    screens = list(manifest.get("screens") or [])
    if not screens and (target_kind or "ui") == "ui":
        raise DesignError("Generate a design before iterating")

    kind = (target_kind or "ui").strip().lower()
    if kind not in {"ui", "spec", "md", "image", "url", "process"}:
        kind = "ui"
    action = _infer_iterate_mode(instruction, mode=mode, target_kind=kind)
    design_md = (session_dir / DESIGN_MD).read_text(encoding="utf-8") if (session_dir / DESIGN_MD).is_file() else ""
    spec = manifest.get("spec")
    if not isinstance(spec, dict) and (session_dir / SPEC_JSON).is_file():
        try:
            spec = json.loads((session_dir / SPEC_JSON).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            spec = None

    selection_note = f"Selected: {kind}"
    if target_id:
        selection_note += f"/{target_id}"
    if element_label or element_path:
        selection_note += f"; element={element_label or element_path}"

    log = list(manifest.get("process_log") or [])
    # Capture round boundary before appending this turn's user/assistant lines
    # (and before Model is inserted after the user entry).
    log_start = len(log)
    log.append(
        {
            "role": "user",
            "text": f"{instruction} [{selection_note}; mode={action}]",
            "at": _now_iso(),
        }
    )
    log.append(
        {
            "role": "assistant",
            "text": (
                "Creating a new version…"
                if action == "add" and kind == "ui"
                else "Thinking… applying your changes to the selected design."
            ),
            "status": "iterating",
            "at": _now_iso(),
        }
    )
    manifest["status"] = "iterating"
    manifest["process_log"] = log
    _write_manifest(session_dir, manifest)

    router = get_router()
    model_id = router.active_model_id
    model_id, model_name = _stamp_session_model(
        manifest,
        router,
        model_id=model_id,
        process_log=log,
        record_in_log=False,
    )
    # Tag the in-flight "Thinking…" step with the model used for this round.
    for i in range(len(log) - 1, -1, -1):
        if log[i].get("role") == "assistant" and log[i].get("status") == "iterating":
            log[i] = {
                **log[i],
                "model_id": model_id,
                "model_name": model_name,
            }
            break
    manifest["process_log"] = log
    _write_manifest(session_dir, manifest)

    # --- Spec / Design.md edits ---
    if kind in {"spec", "md"}:
        if action == "add":
            # New variant: keep existing DESIGN.md, append a short note screen instead of wiping.
            pass
        updated_spec = spec if isinstance(spec, dict) else _fallback_spec(instruction)
        spec_usage = _empty_token_usage()
        spec_usage_estimated = False
        if is_model_available(router, model_id):
            try:
                meta = (
                    "You revise a product design system JSON.\n"
                    f"Instruction: {instruction}\n"
                    f"Current design system JSON:\n{json.dumps(updated_spec, ensure_ascii=False)}\n"
                    f"Source DESIGN.md (excerpt):\n{design_md[:8000]}\n"
                    "Return ONLY updated JSON with keys: name, rationale, colors, typography, components."
                )
                spec_raw, _, spec_usage, spec_usage_estimated = _llm_complete(
                    router, meta, model_id=model_id
                )
                parsed = _extract_json_block(spec_raw)
                if isinstance(parsed, dict):
                    updated_spec = enrich_fallback_spec(
                        parsed,
                        instruction,
                        str(parsed.get("layout_pattern") or detect_layout_pattern(instruction)),
                    )
            except Exception as exc:
                logger.warning("design iterate spec failed: %s", exc)
        (session_dir / SPEC_JSON).write_text(
            json.dumps(updated_spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if kind == "md" or not design_md:
            (session_dir / DESIGN_MD).write_text(_spec_to_design_md(updated_spec), encoding="utf-8")
        else:
            # Keep uploaded Design.md; still refresh structured spec.
            pass
        manifest["spec"] = updated_spec
        _clear_fake_thumbnail(session_dir)
        manifest.pop("thumbnail", None)
        spec_updated_text = "Design system updated."
        if not is_model_available(router, model_id):
            spec_updated_text += f"\n\n⚠️ Warning: Model '{model_id}' is not available (API key missing in Settings -> Models). Using offline fallback templates."
        _finalize_assistant_step(
            log,
            text=spec_updated_text,
            status="ready",
            model_id=model_id,
            model_name=model_name,
            usage=spec_usage,
            usage_estimated=spec_usage_estimated,
            replace_statuses={"iterating"},
        )
        manifest["process_log"] = log
        manifest["status"] = "ready"
        _write_manifest(session_dir, manifest)
        return _public(manifest, session_dir)

    # --- UI iterate (modify existing or add new screen) ---
    if not screens:
        raise DesignError("Generate a design before iterating")

    if action == "add":
        base_id = str(target_id or screens[0].get("id") or "main")
        base = next((s for s in screens if str(s.get("id")) == base_id), screens[0])
        base_html_path = _resolve_screen_html_path(session_dir, base)
        if not base_html_path.is_file():
            base_html_path = session_dir / "screens" / f"{base['id']}.html"
        base_html = base_html_path.read_text(encoding="utf-8") if base_html_path.is_file() else ""
        new_id = _next_screen_id(screens)
        html = ""
        ui_reasoning: str | None = None
        ui_usage = _empty_token_usage()
        ui_usage_estimated = False
        device = str(manifest.get("device") or "web")
        spec_dict = spec if isinstance(spec, dict) else _fallback_spec(instruction)
        if is_model_available(router, model_id):
            try:
                html, ui_reasoning, ui_usage, ui_usage_estimated, _ui_fail = _generate_ui_html(
                    router,
                    user_prompt=instruction,
                    spec=spec_dict,
                    device=device,
                    model_id=model_id,
                    design_md=design_md,
                    current_html=base_html,
                    instruction=instruction,
                )
            except Exception as exc:
                logger.warning("design iterate add failed: %s", exc)
        if not _html_has_visible_content(html):
            if is_model_available(router, model_id):
                raise DesignError(
                    "Could not generate the new screen — model returned empty HTML. "
                    "Please try again."
                )
            html = _fallback_ui_html(instruction, spec_dict, device=device)
        round_entry = _record_screen_round(
            session_dir,
            manifest,
            screen_id=new_id,
            html=html,
            prompt=instruction,
            reasoning_content=ui_reasoning,
            process_log_slice=log[log_start:],
        )
        new_screen = {
            "id": new_id,
            "name": instruction.strip()[:40] or f"Screen {new_id}",
            "position": {
                "x": _screen_layout_x(
                    screens,
                    device=device,
                    has_source=bool(
                        manifest.get("reference_image")
                        or manifest.get("reference_md")
                        or manifest.get("reference_url")
                    ),
                ),
                "y": _DESIGN_ROW_Y,
            },
            "html_path": round_entry["html_path"],
            "active_round_index": round_entry["round_index"],
        }
        screens.append(new_screen)
        manifest["screens"] = screens
        _finalize_assistant_step(
            log,
            text=(
                f"Added «{new_screen['name']}» — wrote {round_entry['html_path']}. "
                "Select it to refine further."
            ),
            status="ready",
            model_id=model_id,
            model_name=model_name,
            usage=ui_usage,
            usage_estimated=ui_usage_estimated,
            replace_statuses={"iterating"},
        )
        history = list(manifest.get("round_history") or [])
        if history:
            history[-1] = {**history[-1], "process_log": list(log[log_start:])}
            manifest["round_history"] = history
        manifest["last_iterate_action"] = "add"
        manifest["last_iterate_screen_id"] = new_id
    else:
        screen_id = str(target_id or screens[0].get("id") or "main")
        screen = next((s for s in screens if str(s.get("id")) == screen_id), screens[0])
        screen_id = str(screen["id"])
        html_path = _resolve_screen_html_path(session_dir, screen)
        if not html_path.is_file():
            html_path = session_dir / "screens" / f"{screen_id}.html"
        current = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
        html = current
        element_hint = ""
        if element_path or element_label:
            element_hint = (
                f"Focus ONLY on this element/region: {element_label or ''} "
                f"({element_path or ''}). Keep the rest of the page intact when possible.\n"
            )
        merged_prompt = _merged_design_prompt(manifest, instruction)
        device = str(manifest.get("device") or "web")
        spec_dict = spec if isinstance(spec, dict) else _fallback_spec(merged_prompt)
        ui_reasoning: str | None = None
        ui_usage = _empty_token_usage()
        ui_usage_estimated = False
        if is_model_available(router, model_id):
            try:
                candidate, ui_reasoning, ui_usage, ui_usage_estimated, _ui_fail = _generate_ui_html(
                    router,
                    user_prompt=merged_prompt,
                    spec=spec_dict,
                    device=device,
                    model_id=model_id,
                    design_md=design_md,
                    current_html=current,
                    instruction=f"{instruction}\n{element_hint}",
                    fallback_html=current,
                )
                if _html_has_visible_content(candidate) and not _html_essentially_same(
                    candidate, current
                ):
                    html = candidate
                elif not is_model_available(router, model_id):
                    html = _fallback_ui_html(merged_prompt, spec_dict, device=device)
                else:
                    logger.warning(
                        "design iterate modify unchanged/blank run_id=%s — keeping current HTML",
                        run_id,
                    )
            except Exception as exc:
                logger.warning("design iterate modify failed: %s", exc)
                if not is_model_available(router, model_id):
                    html = _fallback_ui_html(merged_prompt, spec_dict, device=device)
        else:
            html = _fallback_ui_html(merged_prompt, spec_dict, device=device)
        if not is_model_available(router, model_id) and (
            not _html_has_visible_content(html) or _html_essentially_same(html, current)
        ):
            html = _fallback_ui_html(merged_prompt, spec_dict, device=device)
        round_entry = _record_screen_round(
            session_dir,
            manifest,
            screen_id=screen_id,
            html=html,
            prompt=instruction,
            reasoning_content=ui_reasoning,
            process_log_slice=log[log_start:],
        )
        iterate_ready_text = (
            f"Updated the artboard — wrote {round_entry['html_path']}. What else?"
        )
        if not is_model_available(router, model_id):
            iterate_ready_text += f"\n\n⚠️ Warning: Model '{model_id}' is not available (API key missing in Settings -> Models). Using offline fallback templates."
        _finalize_assistant_step(
            log,
            text=iterate_ready_text,
            status="ready",
            model_id=model_id,
            model_name=model_name,
            usage=ui_usage,
            usage_estimated=ui_usage_estimated,
            replace_statuses={"iterating"},
        )
        history = list(manifest.get("round_history") or [])
        if history:
            history[-1] = {**history[-1], "process_log": list(log[log_start:])}
            manifest["round_history"] = history
        manifest["last_iterate_action"] = "modify"
        manifest["last_iterate_screen_id"] = screen_id

    _clear_fake_thumbnail(session_dir)
    manifest.pop("thumbnail", None)
    manifest["process_log"] = log
    manifest["status"] = "ready"
    _write_manifest(session_dir, manifest)
    return _public(manifest, session_dir)


def approve_prototype(run_id: str) -> dict[str, Any]:
    session_dir = _session_dir(run_id)
    manifest = _read_manifest(session_dir)
    if not manifest.get("screens"):
        raise DesignError("Generate UI before approving")
    manifest["prototype_approved"] = True
    manifest["status"] = "prototype_approved"
    _write_manifest(session_dir, manifest)
    return _public(manifest, session_dir)


def _component_name(screen_id: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", screen_id)
    name = "".join(p[:1].upper() + p[1:] for p in parts if p)
    return name or "Screen"


def _html_to_react_component(
    router: Any,
    *,
    html: str,
    component_name: str,
    screen_id: str,
    all_screen_ids: list[str],
    design_md: str,
    model_id: str,
) -> str:
    """LLM translation chain: static HTML → React 19 + Tailwind component."""
    nav_ids = [sid for sid in all_screen_ids if sid != screen_id]
    nav_hint = ""
    if nav_ids:
        nav_hint = (
            "Wire navigation: convert href links to react-router-dom <Link to=\"/{id}\"> "
            f"for screen ids: {', '.join(nav_ids)}.\n"
        )
    prompt = (
        "Convert this HTML UI into a React 19 functional component.\n"
        f"Component name: {component_name}\n"
        f"Screen route id: {screen_id}\n"
        f"{nav_hint}"
        "Rules:\n"
        "- Use Tailwind utility classes from the HTML (no CDN script tags).\n"
        "- Convert class → className, for → htmlFor, inline styles stay as style objects where needed.\n"
        "- For modals, drawers, dropdowns, mobile menus: add useState hooks and toggle handlers.\n"
        "- Export named function component; include `import { useState } from 'react'` when needed.\n"
        "- Include `import { Link } from 'react-router-dom'` for internal navigation.\n"
        "- Preserve visual fidelity — do NOT replace with placeholder skeleton UI.\n"
        f"Design system excerpt:\n{design_md[:4000]}\n\n"
        f"HTML:\n{html[:16000]}\n\n"
        f"Return ONLY the TSX file content for `{component_name}.tsx` inside ```tsx ... ```."
    )
    text, _reasoning, _usage, _estimated = _llm_complete(router, prompt, model_id=model_id)
    fence = re.search(r"```(?:tsx|typescript|jsx)?\s*([\s\S]*?)```", text)
    tsx = fence.group(1).strip() if fence else text.strip()
    if tsx and f"export function {component_name}" in tsx:
        return tsx + ("\n" if not tsx.endswith("\n") else "")
    # Minimal fallback preserving HTML body content
    body_match = re.search(r"<body[^>]*>([\s\S]*?)</body>", html, re.I)
    inner = body_match.group(1).strip() if body_match else html[:8000]
    inner = re.sub(r"\sclass=", " className=", inner)
    escaped_inner = inner.replace("`", "\\`")[:12000]
    return f"""import {{ useState }} from 'react';
import {{ Link }} from 'react-router-dom';

export function {component_name}() {{
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div dangerouslySetInnerHTML={{{{ __html: `{escaped_inner}` }}}} />
    </div>
  );
}}
"""


def _react_scaffold(
    app_name: str,
    screens: list[dict[str, Any]],
    design_md: str,
    *,
    screen_components: dict[str, str] | None = None,
) -> dict[str, str]:
    first = screens[0]["id"] if screens else "main"
    imports = "\n".join(
        f"import {{ {_component_name(s['id'])} }} from './screens/{_component_name(s['id'])}';"
        for s in screens
    )
    routes = "\n".join(
        f'        <Route path="/{s["id"]}" element={{<{_component_name(s["id"])} />}} />'
        for s in screens
    )
    files: dict[str, str] = {
        "package.json": json.dumps(
            {
                "name": re.sub(r"[^a-z0-9-]+", "-", app_name.lower()).strip("-") or "clutch-design-app",
                "private": True,
                "version": "0.0.1",
                "type": "module",
                "scripts": {"dev": "vite --host 127.0.0.1", "build": "vite build"},
                "dependencies": {
                    "react": "^19.0.0",
                    "react-dom": "^19.0.0",
                    "react-router-dom": "^7.0.0",
                },
                "devDependencies": {
                    "@tailwindcss/vite": "^4.0.0",
                    "@vitejs/plugin-react": "^4.3.0",
                    "tailwindcss": "^4.0.0",
                    "typescript": "^5.6.0",
                    "vite": "^6.0.0",
                },
            },
            indent=2,
        )
        + "\n",
        "vite.config.ts": "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\nimport tailwindcss from '@tailwindcss/vite';\nexport default defineConfig({ plugins: [react(), tailwindcss()], server: { host: '127.0.0.1', strictPort: false } });\n",
        "index.html": "<!doctype html><html><head><meta charset=\"UTF-8\"/><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"/><title>Clutch Design</title></head><body><div id=\"root\"></div><script type=\"module\" src=\"/src/main.tsx\"></script></body></html>\n",
        "src/index.css": '@import "tailwindcss";\n',
        "src/main.tsx": "import { StrictMode } from 'react';\nimport { createRoot } from 'react-dom/client';\nimport { BrowserRouter } from 'react-router-dom';\nimport App from './App';\nimport './index.css';\ncreateRoot(document.getElementById('root')!).render(<StrictMode><BrowserRouter><App /></BrowserRouter></StrictMode>);\n",
        "src/App.tsx": f"import {{ Navigate, Route, Routes }} from 'react-router-dom';\n{imports}\nexport default function App() {{\n  return (\n    <Routes>\n      <Route path=\"/\" element={{<Navigate to=\"/{first}\" replace />}} />\n{routes}\n    </Routes>\n  );\n}}\n",
        "DESIGN.md": design_md,
    }
    screen_components = screen_components or {}
    all_ids = [str(s["id"]) for s in screens]
    for s in screens:
        cname = _component_name(s["id"])
        files[f"src/screens/{cname}.tsx"] = screen_components.get(
            s["id"],
            f"""export function {cname}() {{
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-8">
      <h1 className="text-2xl font-bold mb-2">{s.get("name", s["id"])}</h1>
      <p className="text-slate-500 text-sm">Generated by Clutch Design</p>
    </div>
  );
}}
""",
        )
    return files


def generate_react(run_id: str) -> dict[str, Any]:
    from src.models_config import get_router, is_model_available

    session_dir = _session_dir(run_id)
    manifest = _read_manifest(session_dir)
    if not manifest.get("prototype_approved"):
        raise DesignError("Approve the prototype before generating UI code")
    screens = manifest.get("screens") or []
    if not screens:
        raise DesignError("No screens to codegen")
    design_md = (session_dir / DESIGN_MD).read_text(encoding="utf-8") if (session_dir / DESIGN_MD).is_file() else ""
    router = get_router()
    model_id = router.active_model_id
    all_ids = [str(s["id"]) for s in screens]
    screen_components: dict[str, str] = {}
    for s in screens:
        sid = str(s["id"])
        html_path = _resolve_screen_html_path(session_dir, s)
        if not html_path.is_file():
            html_path = session_dir / "screens" / f"{sid}.html"
        html = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
        cname = _component_name(sid)
        if html and is_model_available(router, model_id):
            try:
                screen_components[sid] = _html_to_react_component(
                    router,
                    html=html,
                    component_name=cname,
                    screen_id=sid,
                    all_screen_ids=all_ids,
                    design_md=design_md,
                    model_id=model_id,
                )
            except Exception as exc:
                logger.warning("design react LLM failed screen=%s err=%s", sid, exc)
    files = _react_scaffold(
        str(manifest.get("name") or "App"),
        screens,
        design_md,
        screen_components=screen_components,
    )
    react_dir = session_dir / "react"
    if react_dir.exists():
        stop_preview(run_id)
        shutil.rmtree(react_dir)
    for rel, content in files.items():
        path = react_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    manifest["react_ready"] = True
    manifest["react_path"] = str(react_dir)
    manifest["status"] = "react_generated"
    _write_manifest(session_dir, manifest)
    return _public(manifest, session_dir)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _resolve_command(name: str) -> str | None:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    if _is_windows() and not name.lower().endswith(".cmd"):
        return shutil.which(f"{name}.cmd") or shutil.which(f"{name}.CMD")
    return None


def _is_windows() -> bool:
    return os.name == "nt"


def _install_react_dependencies(react_dir: Path) -> None:
    attempts: list[str] = []
    found_command = False
    for name in ("pnpm", "npm"):
        command = _resolve_command(name)
        if not command:
            attempts.append(f"{name}: not found")
            continue
        found_command = True
        args = [command, "install"]
        if name == "pnpm":
            args.append("--config.dangerously-allow-all-builds=true")
        try:
            result = subprocess.run(
                args,
                cwd=react_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise DesignError(f"{name} install timed out after {int(exc.timeout)}s") from exc
        except OSError as exc:
            attempts.append(f"{name}: {exc}")
            continue
        if result.returncode == 0:
            return
        detail = (result.stderr or result.stdout or f"exit code {result.returncode}")[:400]
        attempts.append(f"{name}: {detail}")
    if not found_command:
        raise DesignError("pnpm or npm was not found on PATH")
    raise DesignError(f"Failed to install deps: {'; '.join(attempts)}")


def _local_bin_command(react_dir: Path, name: str) -> str | None:
    bin_dir = react_dir / "node_modules" / ".bin"
    suffixes = (".cmd", ".exe", "") if _is_windows() else ("",)
    for suffix in suffixes:
        candidate = bin_dir / f"{name}{suffix}"
        if candidate.is_file():
            return str(candidate)
    return None


def _preview_command(react_dir: Path, port: int) -> list[str]:
    vite = _local_bin_command(react_dir, "vite")
    if vite:
        return [vite, "--host", "127.0.0.1", "--port", str(port), "--strictPort"]
    npx = _resolve_command("npx")
    if not npx:
        raise DesignError("npx was not found on PATH")
    return [npx, "vite", "--host", "127.0.0.1", "--port", str(port), "--strictPort"]


def _stop_preview_process(proc: subprocess.Popen[Any], *, timeout: float = 5.0) -> None:
    if proc.poll() is not None:
        return
    if _is_windows() and getattr(proc, "pid", None):
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.warning("preview process did not exit after taskkill pid=%s", proc.pid)
            proc.kill()
            proc.wait(timeout=timeout)
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout)


def start_preview(run_id: str) -> dict[str, Any]:
    session_dir = _session_dir(run_id)
    manifest = _read_manifest(session_dir)
    react_dir = session_dir / "react"
    if not react_dir.is_dir():
        raise DesignError("Generate UI code before starting preview")
    with _preview_lock:
        existing = _preview_procs.get(run_id)
        if existing and existing.get("proc") and existing["proc"].poll() is None:
            return {"run_id": run_id, "url": existing["url"], "port": existing["port"], "status": "running"}
    if not (react_dir / "node_modules").is_dir():
        _install_react_dependencies(react_dir)
    port = _free_port()
    command = _preview_command(react_dir, port)
    try:
        proc = subprocess.Popen(
            command,
            cwd=react_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise DesignError(f"Failed to start preview: {exc}") from exc
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        if proc.poll() is not None:
            raise DesignError("Preview process exited early")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.3)
    else:
        _stop_preview_process(proc)
        raise DesignError("Preview server did not become ready")
    with _preview_lock:
        _preview_procs[run_id] = {"proc": proc, "port": port, "url": url}
    manifest["preview_url"] = url
    _write_manifest(session_dir, manifest)
    return {"run_id": run_id, "url": url, "port": port, "status": "running"}


def stop_preview(run_id: str) -> dict[str, Any]:
    with _preview_lock:
        entry = _preview_procs.pop(run_id, None)
    if entry and entry.get("proc") and entry["proc"].poll() is None:
        _stop_preview_process(entry["proc"])
    try:
        session_dir = _session_dir(run_id)
        manifest = _read_manifest(session_dir)
        manifest["preview_url"] = None
        _write_manifest(session_dir, manifest)
    except DesignError:
        pass
    return {"run_id": run_id, "status": "stopped"}


def approve_react(run_id: str) -> dict[str, Any]:
    session_dir = _session_dir(run_id)
    manifest = _read_manifest(session_dir)
    if not manifest.get("react_ready"):
        raise DesignError("Generate UI code before approving")
    manifest["react_approved"] = True
    manifest["status"] = "react_approved"
    _write_manifest(session_dir, manifest)
    return _public(manifest, session_dir)


def coding_handoff_payload(run_id: str) -> dict[str, Any]:
    session_dir = _session_dir(run_id)
    manifest = _read_manifest(session_dir)
    if not manifest.get("react_approved"):
        raise DesignError("Approve UI code before sending to Coding")
    design_md_path = session_dir / DESIGN_MD
    react_path = session_dir / "react"
    instruction = (
        f"Implement business logic for approved Clutch Design «{manifest.get('name')}».\n"
        f"Design system: {design_md_path}\n"
        f"React scaffold: {react_path}\n"
        f"Brief: {manifest.get('prompt') or '(none)'}\n"
        "Respect DESIGN.md. Wire real data; do not redesign unless asked."
    )
    return {
        "run_id": run_id,
        "project_id": run_id,
        "name": manifest.get("name"),
        "instruction": instruction,
        "design_md_path": str(design_md_path),
        "react_path": str(react_path),
        "workspace_relative": str(session_dir.relative_to(require_workspace())),
    }


# --- Back-compat aliases used by older tests (map project_id → run_id) ---

def create_project(*, name: str, prompt: str = "", template_id: str = "neutral") -> dict[str, Any]:
    run_id = f"design-{uuid.uuid4().hex[:10]}"
    return ensure_session(run_id, title=name, prompt=prompt)


def list_projects() -> list[dict[str, Any]]:
    return list_sessions()


def get_project(project_id: str) -> dict[str, Any]:
    return get_session(project_id)


def delete_project(project_id: str) -> None:
    delete_session_artifacts(project_id)


def generate_prototype(project_id: str, *, prompt: str | None = None, template_id: str | None = None, vision_note: str | None = None) -> dict[str, Any]:
    ensure_session(project_id, prompt=prompt or "")
    text = (prompt or "") + (f"\n{vision_note}" if vision_note else "")
    return generate_session(project_id, prompt=text or "Design a screen")


def iterate_screen(project_id: str, screen_id: str, instruction: str) -> dict[str, Any]:
    return iterate_session(project_id, instruction)


def list_templates() -> list[dict[str, str]]:
    return [
        {"id": "neutral", "name": "Neutral Product"},
        {"id": "linear", "name": "Linear-inspired"},
        {"id": "stripe", "name": "Stripe-inspired"},
    ]


def update_graph(project_id: str, *, screens=None, edges=None) -> dict[str, Any]:
    return get_session(project_id)


def apply_vision_note(project_id: str, note: str, image_data_url: str | None = None) -> dict[str, Any]:
    ensure_session(project_id)
    return generate_session(project_id, prompt=note or "Match the reference UI")
