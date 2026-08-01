from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from src.workspace import WorkspaceError, require_workspace
from src.design.session_store import (
    DESIGN_MD,
    DESIGN_ROOT,
    MANIFEST,
    SPEC_JSON,
    DesignError,
    append_process_status,
    ensure_session,
    esc,
    find_existing_session_dir,
    first_screen_with_ui,
    get_session,
    load_reference_data_url,
    load_reference_md,
    load_url_snapshot,
    normalize_reference_url,
    now_iso,
    public_session_payload,
    read_manifest,
    save_reference_image,
    save_reference_md,
    save_url_snapshot,
    session_dir,
    sync_session_folder_name,
    update_process_status,
    write_manifest,
)
from src.design.layout import (
    default_ui_origin_x,
    ui_frame_width,
    ui_layout_step,
)
from src.design.thumbnail import (
    clear_fake_thumbnail,
    write_thumbnail_svg,
)
from src.design.token_usage import (
    empty_token_usage,
    format_token_usage_text,
    merge_token_usage,
    usage_from_llm_result,
)
from src.design.builtin_presets import resolve_builtin_spec
from src.design.layout_patterns import (
    detect_layout_pattern,
    enrich_fallback_spec,
    fewshot_for_pattern,
    layout_wrapper_hint,
    parse_review_score,
    review_threshold,
)

logger = logging.getLogger(__name__)

from src.design.gen_spec import (
    _detect_html_intent,
    _extract_json_block,
    _extract_json_data,
    _fallback_spec,
    _parse_multi_screens,
    _prompt_intent,
    _spec_to_design_md,
    inject_unified_tailwind_config,
)
from src.design.gen_ui import (
    _build_shared_layout_context,
    _check_vision_ok,
    _coerce_ui_html,
    _fallback_ui_html,
    _generate_ui_html,
    _html_from_llm_response,
    _html_has_visible_content,
    _llm_complete,
)

_DESIGN_ROW_Y = 56


def _finalize_assistant_step(*args: Any, **kwargs: Any) -> Any:
    from src.design.generator import _finalize_assistant_step as _impl

    return _impl(*args, **kwargs)


def _stamp_session_model(*args: Any, **kwargs: Any) -> Any:
    from src.design.generator import _stamp_session_model as _impl

    return _impl(*args, **kwargs)

def _infer_iterate_mode(instruction: str, *, mode: str | None, target_kind: str | None) -> str:
    raw = (mode or "auto").strip().lower()
    if raw in {"modify", "add", "duplicate", "variant", "revise_spec"}:
        return raw
    text = instruction.lower()
    if any(k in text for k in ("variant", "变体", "换个布局", "another version", "explore layout")):
        return "variant"
    if any(k in text for k in ("revise spec", "改规范", "更新设计系统", "update design system")):
        return "revise_spec"
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
    if target_kind == "ui":
        return "modify"
    return "add"


def _merged_design_prompt(manifest: dict[str, Any], instruction: str) -> str:
    base = str(manifest.get("prompt") or manifest.get("name") or "").strip()
    note = (instruction or "").strip()
    if base and note:
        return f"{base}\n{note}"
    return note or base or "Interface"


def _html_essentially_same(a: str, b: str) -> bool:
    def norm(s: str) -> str:
        out = re.sub(r"\s+", "", s or "")
        out = re.sub(r'data-note="[^"]*"', "", out, flags=re.I)
        return out
    return bool(a) and bool(b) and norm(a) == norm(b)


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
    step = ui_layout_step(device)
    return (max(xs) + step) if xs else default_ui_origin_x(has_source=has_source)


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
        "at": now_iso(),
    }
    history = list(manifest.get("round_history") or [])
    history.append(entry)
    manifest["round_history"] = history
    for screen in manifest.get("screens") or []:
        if str(screen.get("id")) == screen_id:
            screen["html_path"] = rel
            screen["active_round_index"] = round_index
    return entry


def _screen_html_rel(screen: dict[str, Any]) -> str:
    sid = str(screen.get("id") or "main")
    return str(screen.get("html_path") or f"screens/{sid}.html")


def _resolve_screen_html_path(session_dir: Path, screen: dict[str, Any]) -> Path:
    return session_dir / _screen_html_rel(screen)


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

    sdir = session_dir(run_id)
    manifest = read_manifest(sdir)
    instruction = instruction.strip()
    if not instruction:
        raise DesignError("Instruction is required")
    screens = [s for s in (manifest.get("screens") or []) if not s.get("deleted")]
    if not screens and (target_kind or "ui") == "ui":
        raise DesignError("Generate a design before iterating")

    kind = (target_kind or "ui").strip().lower()
    if kind not in {"ui", "spec", "md", "image", "url", "process"}:
        kind = "ui"
    action = _infer_iterate_mode(instruction, mode=mode, target_kind=kind)
    if action == "revise_spec":
        kind = "spec"
        action = "modify"
    elif action == "variant":
        kind = "ui"
        action = "add"
        instruction = (
            "Generate a design variant exploring layout / color / content aspects. "
            f"Direction: {instruction}"
        )
    design_md = (sdir / DESIGN_MD).read_text(encoding="utf-8") if (sdir / DESIGN_MD).is_file() else ""
    spec = manifest.get("spec")
    if not isinstance(spec, dict) and (sdir / SPEC_JSON).is_file():
        try:
            spec = json.loads((sdir / SPEC_JSON).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            spec = None

    selection_note = f"Selected: {kind}"
    if target_id:
        selection_note += f"/{target_id}"
    if element_label or element_path:
        selection_note += f"; element={element_label or element_path}"

    log = list(manifest.get("process_log") or [])
    log_start = len(log)
    log.append(
        {
            "role": "user",
            "text": f"{instruction} [{selection_note}; mode={action}]",
            "at": now_iso(),
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
            "at": now_iso(),
        }
    )
    manifest["status"] = "iterating"
    manifest["process_log"] = log
    write_manifest(sdir, manifest)

    router = get_router()
    model_id = router.active_model_id
    model_id, model_name = _stamp_session_model(
        manifest,
        router,
        model_id=model_id,
        process_log=log,
        record_in_log=False,
    )
    for i in range(len(log) - 1, -1, -1):
        if log[i].get("role") == "assistant" and log[i].get("status") == "iterating":
            log[i] = {
                **log[i],
                "model_id": model_id,
                "model_name": model_name,
            }
            break
    manifest["process_log"] = log
    write_manifest(sdir, manifest)

    if kind in {"spec", "md"}:
        updated_spec = spec if isinstance(spec, dict) else _fallback_spec(instruction)
        spec_usage = empty_token_usage()
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
        (sdir / SPEC_JSON).write_text(
            json.dumps(updated_spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if kind == "md" or not design_md:
            (sdir / DESIGN_MD).write_text(_spec_to_design_md(updated_spec), encoding="utf-8")
        manifest["spec"] = updated_spec
        clear_fake_thumbnail(sdir)
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
        write_manifest(sdir, manifest)
        return public_session_payload(manifest, sdir)

    if not screens:
        raise DesignError("Generate a design before iterating")

    ref_rel = manifest.get("reference_image")
    image_data_url = load_reference_data_url(sdir, str(ref_rel) if ref_rel else None)
    has_image = bool(image_data_url)

    md_rel = manifest.get("reference_md")
    md_text, md_name = load_reference_md(sdir, str(md_rel) if md_rel else None)
    has_md = bool(md_text)

    url = manifest.get("reference_url")
    url_snapshot = load_url_snapshot(sdir) if url else None
    has_url = bool(url_snapshot)

    ui_vision_ok = _check_vision_ok(router, model_id, image_data_url)

    device = str(manifest.get("device") or "web")

    if action == "add":
        spec_dict = spec if isinstance(spec, dict) else _fallback_spec(instruction)
        screens_to_gen = _parse_multi_screens(instruction, model_id, router)
        
        new_screens = []
        ui_origin_x = _screen_layout_x(screens, device=device, has_source=has_md or has_image or has_url)
        for idx, screen_info in enumerate(screens_to_gen):
            sid = _next_screen_id(screens + new_screens)
            sname = screen_info["name"]
            step = ui_layout_step(device)
            x_pos = ui_origin_x + idx * step
            new_screens.append({
                "id": sid,
                "name": sname,
                "position": {"x": x_pos, "y": _DESIGN_ROW_Y},
                "html_path": None,
                "active_round_index": 0,
                "original_info": screen_info,
            })
            
        # Append new screens to manifest immediately as placeholders
        manifest["screens"] = screens + [{k: v for k, v in ns.items() if k != "original_info"} for ns in new_screens]
        write_manifest(sdir, manifest)
        
        accumulated_usage = empty_token_usage()
        accumulated_estimated = False
        
        from concurrent.futures import ThreadPoolExecutor
        manifest_lock = threading.Lock()
        fatal_errors: list[str] = []
        new_screens_info = [{"id": ns["id"], "name": ns["name"], "prompt": ns["original_info"]["prompt"]} for ns in new_screens]
        shared_ctx = _build_shared_layout_context(new_screens_info)
        
        def _gen_iter_screen_worker(idx: int, ns: dict[str, Any]) -> None:
            nonlocal accumulated_usage, accumulated_estimated
            sid = ns["id"]
            sname = ns["name"]
            sprompt = ns["original_info"]["prompt"]
            spattern = ns["original_info"].get("layout_pattern") or detect_layout_pattern(sprompt, device=device)
            
            # Pre-register round history entry under lock
            with manifest_lock:
                round_index = _next_round_index(manifest, sid)
                rel = f"screens/{sid}_r{round_index}.html"
                
                round_entry = {
                    "round_index": round_index,
                    "screen_id": sid,
                    "html_path": rel,
                    "prompt": sprompt,
                    "reasoning_content": None,
                    "process_log": list(log[log_start:]),
                    "at": now_iso(),
                }
                history_local = list(manifest.get("round_history") or [])
                existing_idx = next((i for i, h in enumerate(history_local) if h.get("screen_id") == sid and h.get("round_index") == round_index), None)
                if existing_idx is not None:
                    history_local[existing_idx] = round_entry
                else:
                    history_local.append(round_entry)
                manifest["round_history"] = history_local
                
                for s in manifest.get("screens") or []:
                    if str(s.get("id")) == sid:
                        s["html_path"] = rel
                        s["active_round_index"] = round_index
                
                update_process_status(
                    sdir,
                    manifest,
                    text=f"Generating {len(new_screens)} screens concurrently (Screen «{sname}»)...",
                    status="generating_ui",
                    model_id=model_id,
                    model_name=model_name,
                )
                write_manifest(sdir, manifest)
            
            screen_spec = {**spec_dict, "layout_pattern": spattern}
            html = ""
            ui_reasoning = None
            ui_fail_reason = None
            
            if is_model_available(router, model_id):
                try:
                    from src.design import service
                    gen_ui = getattr(service, "_generate_ui_html", _generate_ui_html)
                    html, ui_reasoning, ui_usage, ui_usage_estimated, ui_fail_reason = gen_ui(
                        router,
                        user_prompt=sprompt,
                        spec=screen_spec,
                        device=device,
                        model_id=model_id,
                        design_md=design_md,
                        md_text=md_text if has_md else None,
                        url_snapshot=url_snapshot if has_url else None,
                        has_image=has_image,
                        image_data_url=image_data_url if ui_vision_ok else None,
                        current_html="",
                        instruction="",
                        shared_layout_context=shared_ctx,
                    )
                    with manifest_lock:
                        accumulated_usage = merge_token_usage(accumulated_usage, ui_usage)
                        accumulated_estimated = accumulated_estimated or ui_usage_estimated
                except Exception as exc:
                    logger.warning("design ui LLM failed for iterated screen %s run_id=%s err=%s", sid, run_id, exc)
                    ui_fail_reason = str(exc)
            
            llm_available = is_model_available(router, model_id)
            if not _html_has_visible_content(html):
                if llm_available:
                    detail = ui_fail_reason or "the model returned no valid HTML"
                    err_msg = f"Generation failed for screen «{sname}» — {detail}. Please try again."
                    with manifest_lock:
                        fatal_errors.append(err_msg)
                    return
                html = _fallback_ui_html(sprompt, screen_spec, device=device)
            
            # Inject unified tailwind config for cross-screen style consistency
            html = inject_unified_tailwind_config(html, spec_dict, design_md)
            
            # Write html and update round entry under lock
            (sdir / "screens").mkdir(exist_ok=True)
            (sdir / rel).write_text(html, encoding="utf-8")
            
            with manifest_lock:
                history_local = list(manifest.get("round_history") or [])
                for h in history_local:
                    if h.get("screen_id") == sid and h.get("round_index") == round_index:
                        h["reasoning_content"] = ui_reasoning
                        h["process_log"] = list(log[log_start:])
                        break
                manifest["round_history"] = history_local
                
                for s in manifest.get("screens") or []:
                    if str(s.get("id")) == sid:
                        s["html_path"] = rel
                        s["active_round_index"] = round_index
                write_manifest(sdir, manifest)
        
        # Execute all generations concurrently
        max_workers = min(len(new_screens), 8) if len(new_screens) > 0 else 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(lambda item: _gen_iter_screen_worker(item[0], item[1]), enumerate(new_screens)))
        
        # If any fatal error occurred during the parallel runs, report it and exit
        if fatal_errors:
            err_msg = fatal_errors[0]
            _finalize_assistant_step(
                log,
                text=err_msg,
                status="error",
                model_id=model_id,
                model_name=model_name,
                usage=accumulated_usage,
                usage_estimated=accumulated_estimated,
                replace_statuses={"generating_ui", "iterating"},
            )
            manifest["status"] = "error"
            manifest["error"] = err_msg
            manifest["process_log"] = log
            write_manifest(sdir, manifest)
            return public_session_payload(manifest, sdir)
        
        added_names = ", ".join(f"«{ns['name']}»" for ns in new_screens)
        _finalize_assistant_step(
            log,
            text=f"Added {added_names} successfully. Select any screen to refine further.",
            status="ready",
            model_id=model_id,
            model_name=model_name,
            usage=accumulated_usage,
            usage_estimated=accumulated_estimated,
            replace_statuses={"generating_ui", "iterating"},
        )
        
        # Ensure the final history entry has the full process log
        history = list(manifest.get("round_history") or [])
        if history:
            history[-1] = {**history[-1], "process_log": list(log[log_start:])}
            manifest["round_history"] = history
            
        manifest["last_iterate_action"] = action
        manifest["last_iterate_screen_id"] = new_screens[-1]["id"]
        manifest["status"] = "ready"
        write_manifest(sdir, manifest)

    elif action == "duplicate":
        base_id = str(target_id or screens[0].get("id") or "main")
        base = next((s for s in screens if str(s.get("id")) == base_id), screens[0])
        base_html_path = _resolve_screen_html_path(sdir, base)
        if not base_html_path.is_file():
            base_html_path = sdir / "screens" / f"{base['id']}.html"
        base_html = base_html_path.read_text(encoding="utf-8") if base_html_path.is_file() else ""
        new_id = _next_screen_id(screens)
        
        round_index = _next_round_index(manifest, new_id)
        rel = f"screens/{new_id}_r{round_index}.html"
        
        (sdir / "screens").mkdir(exist_ok=True)
        (sdir / rel).write_text(base_html, encoding="utf-8")
        
        round_entry = {
            "round_index": round_index,
            "screen_id": new_id,
            "html_path": rel,
            "prompt": f"Duplicate of {base.get('name') or 'Screen'}",
            "reasoning_content": None,
            "process_log": list(log[log_start:]),
            "at": now_iso(),
        }
        history = list(manifest.get("round_history") or [])
        history.append(round_entry)
        manifest["round_history"] = history
        
        new_screen = {
            "id": new_id,
            "name": f"Copy of {base.get('name') or 'Screen'}",
            "position": {
                "x": _screen_layout_x(
                    screens,
                    device=device,
                    has_source=has_md or has_image or has_url,
                ),
                "y": _DESIGN_ROW_Y,
            },
            "html_path": rel,
            "active_round_index": round_index,
        }
        screens.append(new_screen)
        manifest["screens"] = screens
        
        _finalize_assistant_step(
            log,
            text=f"Duplicated screen as «{new_screen['name']}».",
            status="ready",
            model_id=model_id,
            model_name=model_name,
            usage=empty_token_usage(),
            usage_estimated=False,
            replace_statuses={"iterating"},
        )
        manifest["last_iterate_action"] = "duplicate"
        manifest["last_iterate_screen_id"] = new_id
        manifest["status"] = "ready"
        write_manifest(sdir, manifest)
    else:
        screen_id = str(target_id or screens[0].get("id") or "main")
        screen = next((s for s in screens if str(s.get("id")) == screen_id), screens[0])
        screen_id = str(screen["id"])
        html_path = _resolve_screen_html_path(sdir, screen)
        if not html_path.is_file():
            html_path = sdir / "screens" / f"{screen_id}.html"
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
        ui_usage = empty_token_usage()
        ui_usage_estimated = False
        if is_model_available(router, model_id):
            try:
                from src.design import service
                gen_ui = getattr(service, "_generate_ui_html", _generate_ui_html)
                candidate, ui_reasoning, ui_usage, ui_usage_estimated, _ui_fail = gen_ui(
                    router,
                    user_prompt=merged_prompt,
                    spec=spec_dict,
                    device=device,
                    model_id=model_id,
                    design_md=design_md,
                    md_text=md_text if has_md else None,
                    url_snapshot=url_snapshot if has_url else None,
                    has_image=False,
                    image_data_url=None,
                    current_html=current,
                    instruction=f"{instruction}\n{element_hint}",
                    fallback_html=current,
                )
                if _html_has_visible_content(candidate) and not _html_essentially_same(
                    candidate, current
                ):
                    # Guard: reject if page type completely changed (dashboard→login etc.)
                    if current and _detect_html_intent(candidate) != _detect_html_intent(current):
                        logger.warning(
                            "design iterate modify type-changed run_id=%s — keeping current HTML",
                            run_id,
                        )
                    else:
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
        rel = screen.get("html_path") or f"screens/{screen_id}_r0.html"
        (sdir / "screens").mkdir(exist_ok=True)
        # Inject unified tailwind config to maintain style consistency after modification
        html = inject_unified_tailwind_config(html, spec, design_md)
        (sdir / rel).write_text(html, encoding="utf-8")
        screen["html_path"] = rel
        iterate_ready_text = (
            f"Updated the artboard — wrote {rel}. What else?"
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
        manifest["last_iterate_action"] = "modify"
        manifest["last_iterate_screen_id"] = screen_id

    clear_fake_thumbnail(sdir)
    manifest.pop("thumbnail", None)
    manifest["process_log"] = log
    manifest["status"] = "ready"
    write_manifest(sdir, manifest)
    return public_session_payload(manifest, sdir)


def delete_screen(
    run_id: str,
    screen_id: str,
) -> dict[str, Any]:
    sdir = session_dir(run_id)
    manifest = read_manifest(sdir)
    screens = list(manifest.get("screens") or [])
    target = next((s for s in screens if str(s.get("id")) == screen_id), None)
    if not target:
        raise DesignError(f"Screen {screen_id} not found")
    if target.get("deleted"):
        raise DesignError(f"Screen {screen_id} is already deleted")
    removed_name = str(target.get("name") or screen_id)
    round_index = _next_round_index(manifest, screen_id)
    for s in screens:
        if str(s.get("id")) == screen_id:
            s["deleted"] = True
            s["deleted_at_round"] = round_index
            break

    instruction = f"Delete screen: {removed_name}"
    log = list(manifest.get("process_log") or [])
    log_start = len(log)
    log.append({"role": "user", "text": instruction, "at": now_iso()})
    log.append({"role": "assistant", "text": f"Removed «{removed_name}» from the canvas.", "status": "ready", "at": now_iso()})
    history = list(manifest.get("round_history") or [])
    history.append({
        "round_index": round_index,
        "screen_id": screen_id,
        "html_path": f"screens/{screen_id}_r{round_index}.html",
        "prompt": instruction,
        "reasoning_content": None,
        "process_log": list(log[log_start:]),
        "at": now_iso(),
        "action": "delete",
    })
    manifest["round_history"] = history
    manifest["process_log"] = log
    manifest["status"] = "ready"
    manifest["last_iterate_action"] = "delete"
    manifest["last_iterate_screen_id"] = None
    write_manifest(sdir, manifest)
    return public_session_payload(manifest, sdir)

