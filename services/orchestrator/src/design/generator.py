"""LLM generation loops and iteration workflows for design canvas sessions."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

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

def _normalize_preset_id(preset_id: str | None) -> str:
    try:
        from src.design import service
        if hasattr(service, "normalize_preset_id"):
            return service.normalize_preset_id(preset_id)
    except ImportError:
        pass
    from src.design.builtin_presets import normalize_preset_id as orig_normalize
    return orig_normalize(preset_id)

logger = logging.getLogger(__name__)

# D38 — stage modules (re-exported for service/tests)
from src.design.gen_spec import (
    _enhance_brief,
    _extract_colors_from_design_md,
    _extract_json_block,
    _extract_json_data,
    _fallback_spec,
    _get_unified_tailwind_config,
    _html_matches_brief_intent,
    _parse_multi_screens,
    _prompt_intent,
    _spec_confirm_enabled,
    _spec_to_design_md,
    _detect_html_intent,
    inject_unified_tailwind_config,
)
from src.design.gen_ui import (
    _DESIGN_REVIEW_ENABLED,
    _LLM_TIMEOUT_SEC,
    _LLM_UI_TIMEOUT_SEC,
    _TASTE_ANTI_PATTERNS,
    _build_shared_layout_context,
    _build_ui_compact_prompt,
    _build_ui_correction_prompt,
    _build_ui_generation_prompt,
    _check_vision_ok,
    _coerce_ui_html,
    _design_review_and_improve,
    _extract_css_tokens,
    _extract_html_from_llm,
    _fallback_login_html,
    _fallback_ui_html,
    _fetch_url_snapshot,
    _first_hex,
    _format_css_tokens_for_prompt,
    _generate_ui_html,
    _html_from_llm_response,
    _html_has_visible_content,
    _llm_complete,
    _llm_complete_vision,
    _looks_like_vision_error,
    _shell_html,
    _try_llm_complete_vision,
)
from src.design.gen_iterate import (
    _html_essentially_same,
    _infer_iterate_mode,
    _merged_design_prompt,
    _next_round_index,
    _next_screen_id,
    _record_screen_round,
    _resolve_screen_html_path,
    _screen_html_rel,
    _screen_layout_x,
    delete_screen,
    iterate_session,
)


_generate_jobs: dict[str, threading.Thread] = {}
_generate_lock = threading.Lock()
_iterate_jobs: dict[str, threading.Thread] = {}
_iterate_lock = threading.Lock()


_DESIGN_ROW_Y = 56


def get_generator_jobs_and_lock() -> tuple[dict[str, threading.Thread], threading.Lock]:
    return _generate_jobs, _generate_lock


def append_design_run_log(run_id: str, message: str, *, reasoning: str | None = None) -> None:
    """Best-effort: mirror Design progress into persisted run terminal_logs (Terminal panel)."""
    if not run_id:
        return
    if reasoning and reasoning.strip():
        append_design_run_log(
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
        "at": now_iso(),
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
    merged = merge_token_usage(usage)
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
        {"role": "assistant", "text": text, "status": status, "at": now_iso()},
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
    merged = merge_token_usage(usage)
    if merged["total_tokens"] <= 0:
        return
    log.append(
        {
            "role": "assistant",
            "kind": "tokens",
            "text": format_token_usage_text(label, merged, estimated=estimated),
            "usage_label": label,
            "usage": merged,
            "usage_estimated": estimated,
            "status": "info",
            "at": now_iso(),
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
        usage, estimated = usage_from_llm_result(
            result,
            prompt=prompt,
            response_text=text,
            reasoning=reasoning_text,
        )
        return text, reasoning_text, usage, estimated
    text = str(result).strip()
    usage, estimated = usage_from_llm_result(result, prompt=prompt, response_text=text)
    return text, None, usage, estimated


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
    resume_ui: bool = False,
) -> dict[str, Any]:
    """Two-phase: design spec first, then UI HTML (optional image / Design.md / URL).

    D40: when Spec soft-confirm is enabled, pauses at `awaiting_spec_confirm` after Spec;
    call with `resume_ui=True` (via confirm_spec) to continue screen generation.
    """
    from src.models_config import get_router, is_model_available

    sdir = session_dir(run_id)
    if not (sdir / MANIFEST).is_file():
        ensure_session(run_id, title=prompt[:40], prompt=prompt)
    manifest = read_manifest(sdir)
    user_prompt = prompt.strip() or str(manifest.get("prompt") or "").strip()
    if resume_ui:
        user_prompt = str(manifest.get("enhanced_prompt") or user_prompt).strip()

    ref_rel = manifest.get("reference_image")
    if reference_image:
        ref_rel = save_reference_image(sdir, reference_image) or ref_rel
    image_data_url = load_reference_data_url(sdir, str(ref_rel) if ref_rel else None)

    md_rel = manifest.get("reference_md")
    if reference_md:
        md_rel = save_reference_md(sdir, reference_md, name=reference_md_name) or md_rel
    md_text, md_name = load_reference_md(sdir, str(md_rel) if md_rel else None)

    url = normalize_reference_url(reference_url) or manifest.get("reference_url")
    url_snapshot = load_url_snapshot(sdir)
    if url and (reference_url or not url_snapshot):
        try:
            from src.design import service
            url_snapshot = service._fetch_url_snapshot(str(url))
            save_url_snapshot(sdir, url_snapshot)
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
                "fetched_at": now_iso(),
            }
            save_url_snapshot(sdir, url_snapshot)

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

    device = device if device in {"web", "app"} else str(manifest.get("device") or "web")
    if device not in {"web", "app"}:
        device = "web"
    if not resume_ui:
        user_prompt = _enhance_brief(user_prompt, device)
        manifest["enhanced_prompt"] = user_prompt
        manifest["raw_prompt"] = prompt.strip() or str(manifest.get("raw_prompt") or manifest.get("prompt") or "")

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
    else:
        _intro_pid = _normalize_preset_id(design_system or manifest.get("design_system"))
        if _intro_pid != "clutch":
            from src.design.builtin_presets import resolve_preset_meta
            _intro_meta = resolve_preset_meta(_intro_pid)
            if _intro_meta:
                intro = (
                    f"I'll apply the {_intro_meta['name']} design system, then craft the interface for your brief."
                )
            else:
                intro = "I'll start with a design specification (colors, type, components), then craft the interface to match."
        else:
            intro = (
                "I'll apply the built-in Clutch design system, then craft the interface for your brief."
            )

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
        "awaiting_spec_confirm",
    }
    skip_spec = bool(resume_ui)
    if skip_spec:
        if str(manifest.get("status") or "") not in {"awaiting_spec_confirm", "generating_ui"}:
            raise DesignError("Spec is not awaiting confirmation")
        process_log = list(manifest.get("process_log") or [])
        manifest["status"] = "generating_ui"
        manifest["phase"] = "ui"
        manifest["error"] = None
        write_manifest(sdir, manifest)
    elif resume and manifest.get("process_log"):
        process_log = list(manifest.get("process_log") or [])
    else:
        process_log = [
            {
                "role": "user",
                "text": user_prompt + attach_note,
                "at": now_iso(),
            },
            {
                "role": "assistant",
                "text": intro,
                "status": "crafting_spec",
                "at": now_iso(),
            },
        ]
    if not skip_spec:
        manifest["prompt"] = user_prompt
        manifest["name"] = (str(manifest.get("raw_prompt") or user_prompt)[:48]) or manifest.get("name") or "New Design"
        manifest["device"] = device if device in {"web", "app"} else "web"
        manifest["phase"] = "spec"
        manifest["status"] = "crafting_spec"
        manifest["process_log"] = process_log
        manifest["error"] = None
    if not resume and not skip_spec:
        manifest["round_history"] = []
        manifest["screens"] = []
        manifest["spec"] = None
        manifest["design_system"] = _normalize_preset_id(design_system or manifest.get("design_system"))
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
    write_manifest(sdir, manifest)

    spec: dict[str, Any] | None = None
    source = "fallback"
    design_md = ""
    router = get_router()
    model_id = router.active_model_id
    process_log = list(manifest.get("process_log") or [])
    model_id, model_name = _stamp_session_model(
        manifest,
        router,
        model_id=model_id,
        process_log=process_log,
        record_in_log=False,
    )
    write_manifest(sdir, manifest)

    if skip_spec:
        spec = manifest.get("spec") if isinstance(manifest.get("spec"), dict) else None
        if not spec and (sdir / SPEC_JSON).is_file():
            try:
                loaded = json.loads((sdir / SPEC_JSON).read_text(encoding="utf-8"))
                spec = loaded if isinstance(loaded, dict) else None
            except (OSError, json.JSONDecodeError):
                spec = None
        if not spec:
            raise DesignError("No Spec available to continue UI generation")
        if (sdir / DESIGN_MD).is_file():
            design_md = (sdir / DESIGN_MD).read_text(encoding="utf-8")
        else:
            design_md = _spec_to_design_md(spec)
        source = str(manifest.get("generate_source") or "resume")
        append_process_status(
            sdir,
            manifest,
            text="Spec confirmed — generating high-fidelity HTML…",
            status="generating_ui",
            model_id=model_id,
            model_name=model_name,
        )
    else:
        preset_id = _normalize_preset_id(manifest.get("design_system"))
        use_builtin_preset = preset_id == "clutch" and not (has_image or has_md or has_url)
        if not use_builtin_preset and not has_image and not has_md and not has_url:
            from src.design.builtin_presets import resolve_preset_spec
            if preset_id != "clutch" and resolve_preset_spec(preset_id):
                use_builtin_preset = True
        spec_usage = empty_token_usage()
        spec_usage_estimated = False

        if use_builtin_preset:
            from src.design.builtin_presets import resolve_preset_meta
            preset_name = (resolve_preset_meta(preset_id) or {}).get("name") or preset_id
            update_process_status(
                sdir,
                manifest,
                text=f"Applying {preset_name} design system…",
                status="crafting_spec",
                model_id=model_id,
                model_name=model_name,
            )
            spec, design_md = resolve_builtin_spec(preset_id, user_prompt, device=device)
            source = "builtin_clutch" if preset_id == "clutch" else "builtin_preset"
        else:
            update_process_status(
                sdir,
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
                            f"\n=== AUTHORITATIVE DESIGN SPECIFICATION: {md_name} ===\n"
                            f"{md_text[:16000]}\n"
                            "=== END OF SPECIFICATION ===\n\n"
                            "CRITICAL: Extract EVERY color, font, spacing value, and component rule from "
                            "the specification above. Use them VERBATIM — do NOT invent or substitute values. "
                            "The JSON output must faithfully reflect the exact tokens defined in this document.\n"
                        )
                    if has_url and url_snapshot:
                        browser_frag = url_snapshot.get("browser_prompt_fragment") or ""
                        context_parts.append(
                            "Reference website:\n"
                            f"URL: {url_snapshot.get('url')}\n"
                            f"Title: {url_snapshot.get('title')}\n"
                            f"Description: {url_snapshot.get('description')}\n"
                        )
                        if browser_frag:
                            context_parts.append(browser_frag + "\n")
                        else:
                            css_tokens = url_snapshot.get("css_tokens") or {}
                            token_desc = _format_css_tokens_for_prompt(
                                css_tokens, host=str(url_snapshot.get("host") or "")
                            )
                            if token_desc:
                                context_parts.append(token_desc + "\n")
                            else:
                                context_parts.append(
                                    f"Excerpt: {(url_snapshot.get('excerpt') or '')[:3000]}\n"
                                    "Infer a polished design system inspired by this site's visual language.\n"
                                )
                        og_analysis = url_snapshot.get("og_image_analysis") or {}
                        og_desc = og_analysis.get("description", "")
                        if og_desc:
                            context_parts.append(og_desc + "\n")
                    if has_image:
                        vision_ok_spec = _check_vision_ok(router, model_id, image_data_url)
                        if vision_ok_spec:
                            context_parts.append(
                                "A reference UI screenshot is attached. Extract colors, typography, and component style from it.\n"
                            )
                        else:
                            try:
                                from src.design.image_analysis import image_analysis_prompt_fragment

                                img_analysis = image_analysis_prompt_fragment(image_data_url or "")
                                if img_analysis:
                                    context_parts.append(img_analysis + "\n")
                                else:
                                    context_parts.append(
                                        "A reference UI screenshot was provided; use the product brief to infer design tokens.\n"
                                    )
                            except Exception:
                                context_parts.append(
                                    "A reference UI screenshot was provided; use the product brief to infer design tokens.\n"
                                )
                    browser_ss = (url_snapshot or {}).get("browser_screenshot") or ""
                    if browser_ss and not image_data_url:
                        vision_ok_browser = _check_vision_ok(router, model_id, browser_ss)
                        if vision_ok_browser:
                            image_data_url = browser_ss
                            context_parts.append(
                                "A browser-rendered screenshot of the reference website is attached. "
                                "Extract exact colors, typography, spacing, and layout from it.\n"
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
                    spec_usage = merge_token_usage(spec_usage, call_usage)
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

        (sdir / SPEC_JSON).write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (sdir / DESIGN_MD).write_text(design_md, encoding="utf-8")

        process_log = list(manifest.get("process_log") or [])
        spec_ready_text = f"Design system «{spec.get('name')}» ready."
        if not is_model_available(router, model_id):
            spec_ready_text += (
                f"\n\n⚠️ Warning: Model '{model_id}' is not available "
                "(API key missing in Settings -> Models). Using offline fallback templates."
            )
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
        write_manifest(sdir, manifest)

        if _spec_confirm_enabled():
            manifest["status"] = "awaiting_spec_confirm"
            write_manifest(sdir, manifest)
            append_process_status(
                sdir,
                manifest,
                text="Spec ready — confirm to generate UI screens.",
                status="awaiting_spec_confirm",
                model_id=model_id,
                model_name=model_name,
            )
            append_design_run_log(
                run_id,
                f"spec ready name={spec.get('name')!s} → awaiting_spec_confirm device={device} model={model_id}",
            )
            return get_session(run_id)

        append_process_status(
            sdir,
            manifest,
            text="Generating high-fidelity HTML with layout patterns and design review…",
            status="generating_ui",
            model_id=model_id,
            model_name=model_name,
        )
        append_design_run_log(
            run_id,
            f"spec ready name={spec.get('name')!s} → generating_ui device={device} model={model_id}",
        )

    sdir = session_dir(run_id)
    screens_to_gen = _parse_multi_screens(user_prompt, model_id, router)
    
    append_design_run_log(
        run_id,
        f"spec ready name={spec.get('name')!s} → generating_ui device={device} model={model_id} screens_count={len(screens_to_gen)}",
    )
    
    ui_origin_x = default_ui_origin_x(has_source=has_image or has_md or has_url)
    screens = []
    for idx, screen_info in enumerate(screens_to_gen):
        sid = screen_info["id"]
        sname = screen_info["name"]
        if idx == 0:
            x_pos = ui_origin_x
        else:
            step = ui_layout_step(device)
            x_pos = ui_origin_x + idx * step
        screens.append({
            "id": sid,
            "name": sname,
            "position": {"x": x_pos, "y": _DESIGN_ROW_Y},
            "html_path": None,
            "active_round_index": 0,
        })
    manifest["screens"] = screens
    write_manifest(sdir, manifest)

    accumulated_usage = empty_token_usage()
    accumulated_estimated = False
    process_log = list(manifest.get("process_log") or [])
    design_md_text = design_md
    
    from concurrent.futures import ThreadPoolExecutor
    manifest_lock = threading.Lock()
    fatal_errors = []
    shared_ctx = _build_shared_layout_context(screens_to_gen)

    def _gen_screen_worker(idx: int, screen_info: dict[str, Any]) -> None:
        nonlocal accumulated_usage, accumulated_estimated
        sid = screen_info["id"]
        sname = screen_info["name"]
        sprompt = screen_info["prompt"]
        spattern = screen_info.get("layout_pattern") or detect_layout_pattern(sprompt, device=device)
        
        # 1. Pre-register round history entry under lock
        with manifest_lock:
            round_index = _next_round_index(manifest, sid)
            rel = f"screens/{sid}_r{round_index}.html"
            
            round_entry = {
                "round_index": round_index,
                "screen_id": sid,
                "html_path": rel,
                "prompt": sprompt,
                "reasoning_content": None,
                "process_log": list(process_log),
                "at": now_iso(),
            }
            history = list(manifest.get("round_history") or [])
            existing_idx = next((i for i, h in enumerate(history) if h.get("screen_id") == sid and h.get("round_index") == round_index), None)
            if existing_idx is not None:
                history[existing_idx] = round_entry
            else:
                history.append(round_entry)
            manifest["round_history"] = history
            
            for screen in screens:
                if screen["id"] == sid:
                    screen["html_path"] = rel
                    screen["active_round_index"] = round_index
            manifest["screens"] = screens
            
            update_process_status(
                sdir,
                manifest,
                text=f"Generating {len(screens_to_gen)} screens concurrently (Screen «{sname}»)...",
                status="generating_ui",
                model_id=model_id,
                model_name=model_name,
            )
            write_manifest(sdir, manifest)
            
        screen_spec = {**spec, "layout_pattern": spattern}
        html = ""
        ui_reasoning = None
        ui_fail_reason = None
        
        if is_model_available(router, model_id):
            try:
                ui_vision_ok = _check_vision_ok(router, model_id, image_data_url)
                use_img = image_data_url if (idx == 0 and ui_vision_ok) else None
                
                from src.design import service
                gen_ui = getattr(service, "_generate_ui_html", _generate_ui_html)
                html, ui_reasoning, ui_usage, ui_usage_estimated, ui_fail_reason = gen_ui(
                    router,
                    user_prompt=sprompt,
                    spec=screen_spec,
                    device=device,
                    model_id=model_id,
                    design_md=design_md_text,
                    md_text=md_text if has_md else None,
                    url_snapshot=url_snapshot if has_url else None,
                    has_image=has_image and (idx == 0),
                    image_data_url=use_img,
                    shared_layout_context=shared_ctx,
                )
                with manifest_lock:
                    accumulated_usage = merge_token_usage(accumulated_usage, ui_usage)
                    accumulated_estimated = accumulated_estimated or ui_usage_estimated
            except Exception as exc:
                logger.warning("design ui LLM failed for screen %s run_id=%s err=%s", sid, run_id, exc)
                ui_fail_reason = str(exc)

        if not _html_has_visible_content(html):
            if is_model_available(router, model_id):
                detail = ui_fail_reason or "the model returned no valid HTML"
                err_msg = f"Generation failed for screen «{sname}» — {detail}. Please try again."
                with manifest_lock:
                    fatal_errors.append(err_msg)
                return
            html = _fallback_ui_html(sprompt, screen_spec, device=device)

        # Inject the unified tailwind config to guarantee style consistency!
        html = inject_unified_tailwind_config(html, spec, design_md_text)

        # 2. Write HTML and update placeholder details under lock
        (sdir / "screens").mkdir(exist_ok=True)
        (sdir / rel).write_text(html, encoding="utf-8")
        
        with manifest_lock:
            history = list(manifest.get("round_history") or [])
            for h in history:
                if h.get("screen_id") == sid and h.get("round_index") == round_index:
                    h["reasoning_content"] = ui_reasoning
                    h["process_log"] = list(process_log)
                    break
            manifest["round_history"] = history
            
            for screen in screens:
                if screen["id"] == sid:
                    screen["html_path"] = rel
                    screen["active_round_index"] = round_index
            manifest["screens"] = screens
            write_manifest(sdir, manifest)

    # Execute all generations concurrently
    max_workers = min(len(screens_to_gen), 8) if len(screens_to_gen) > 0 else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(lambda item: _gen_screen_worker(item[0], item[1]), enumerate(screens_to_gen)))

    # If any fatal error occurred during the parallel runs, report it and exit
    if fatal_errors:
        err_msg = fatal_errors[0]
        _finalize_assistant_step(
            process_log,
            text=err_msg,
            status="error",
            model_id=model_id,
            model_name=model_name,
            usage=accumulated_usage,
            usage_estimated=accumulated_estimated,
            replace_statuses={"generating_ui"},
        )
        manifest["status"] = "error"
        manifest["error"] = err_msg
        manifest["process_log"] = process_log
        manifest["screens"] = screens
        write_manifest(sdir, manifest)
        return public_session_payload(manifest, sdir)

    ui_ready_text = (
        f"Interface draft is ready — generated {len(screens)} screens on the canvas:\n"
        + "\n".join(f"- **{s['name']}** (wrote `{s['html_path']}`)" for s in screens)
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
        usage=accumulated_usage,
        usage_estimated=accumulated_estimated,
        replace_statuses={"generating_ui"},
    )
    if manifest.get("round_history"):
        history = list(manifest["round_history"])
        if history:
            history[-1] = {**history[-1], "process_log": list(process_log)}
            manifest["round_history"] = history
            
    manifest["screens"] = screens
    manifest["phase"] = "canvas"
    manifest["status"] = "ready"
    manifest["process_log"] = process_log
    manifest["prototype_approved"] = False
    manifest["react_ready"] = False
    manifest["react_approved"] = False
    clear_fake_thumbnail(sdir)
    manifest.pop("thumbnail", None)
    write_manifest(sdir, manifest)
    sync_session_folder_name(
        run_id,
        title=str(manifest.get("name") or user_prompt or "design"),
        device=device,
    )
    append_design_run_log(
        run_id,
        f"generate done source={source} screens_count={len(screens)}",
    )
    logger.info("design generate done run_id=%s source=%s count=%d", run_id, source, len(screens))
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
    sdir = session_dir(run_id)
    if not (sdir / MANIFEST).is_file():
        ensure_session(run_id, title=prompt[:40], prompt=prompt)
    with _generate_lock:
        existing = _generate_jobs.get(run_id)
        if existing and existing.is_alive():
            return get_session(run_id)

    user_prompt = (prompt or "").strip()
    url = normalize_reference_url(reference_url)
    md_rel = save_reference_md(sdir, reference_md, name=reference_md_name) if reference_md else None
    md_text, md_name = load_reference_md(sdir, md_rel) if md_rel else (None, None)
    ref_rel = save_reference_image(sdir, reference_image) if reference_image else None

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
            from src.design import service
            url_snapshot = service._fetch_url_snapshot(url)
            save_url_snapshot(sdir, url_snapshot)
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
                "fetched_at": now_iso(),
            }
            save_url_snapshot(sdir, url_snapshot)

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
    elif _normalize_preset_id(design_system) == "clutch":
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

    manifest = read_manifest(sdir)
    manifest["prompt"] = user_prompt
    manifest["name"] = user_prompt[:48] or manifest.get("name") or "New Design"
    manifest["device"] = device if device in {"web", "app"} else "web"
    manifest["phase"] = "spec"
    manifest["status"] = "crafting_spec"
    manifest["error"] = None
    manifest["screens"] = []
    manifest["spec"] = None
    manifest["round_history"] = []
    manifest["design_system"] = _normalize_preset_id(design_system)
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
            "at": now_iso(),
        },
        {
            "role": "assistant",
            "text": intro,
            "status": "crafting_spec",
            "at": now_iso(),
        },
    ]
    clear_fake_thumbnail(sdir)
    manifest.pop("thumbnail", None)
    write_manifest(sdir, manifest)
    sdir = sync_session_folder_name(
        run_id,
        title=str(manifest.get("name") or user_prompt or "design"),
        device=str(manifest.get("device") or device or "web"),
    )
    append_design_run_log(
        run_id,
        f"generate started device={device} prompt={user_prompt[:80]!r}",
    )

    def _worker() -> None:
        try:
            from src.design import service
            service.generate_session(
                run_id,
                prompt=user_prompt,
                device=device,
                reference_image=None,
                reference_md=None,
                reference_url=None,
                design_system=manifest.get("design_system"),
                continue_inflight=True,
            )
        except Exception as exc:
            logger.exception("design generate worker failed run_id=%s", run_id)
            try:
                err_dir = session_dir(run_id)
                m = read_manifest(err_dir)
                m["status"] = "error"
                m["error"] = str(exc)
                log = list(m.get("process_log") or [])
                log.append(
                    {
                        "role": "assistant",
                        "text": f"Generation failed: {exc}",
                        "status": "error",
                        "at": now_iso(),
                    }
                )
                m["process_log"] = log
                write_manifest(err_dir, m)
            except Exception:
                pass
        finally:
            with _generate_lock:
                _generate_jobs.pop(run_id, None)

    thread = threading.Thread(target=_worker, name=f"design-gen-{run_id}", daemon=True)
    with _generate_lock:
        _generate_jobs[run_id] = thread
    thread.start()
    return public_session_payload(manifest, sdir)


def confirm_spec(run_id: str) -> dict[str, Any]:
    """D40: continue UI generation after Spec soft-confirm."""
    return generate_session(run_id, prompt="", resume_ui=True)


def start_confirm_spec(run_id: str) -> dict[str, Any]:
    """Kick off confirm_spec in a background thread for polling."""
    sdir = session_dir(run_id)
    manifest = read_manifest(sdir)
    if str(manifest.get("status") or "") != "awaiting_spec_confirm":
        raise DesignError("Spec is not awaiting confirmation")
    with _generate_lock:
        existing = _generate_jobs.get(run_id)
        if existing and existing.is_alive():
            return get_session(run_id)

    def _worker() -> None:
        try:
            confirm_spec(run_id)
        except Exception as exc:
            logger.exception("design confirm-spec worker failed run_id=%s", run_id)
            try:
                err_dir = session_dir(run_id)
                m = read_manifest(err_dir)
                m["status"] = "error"
                m["error"] = str(exc)
                write_manifest(err_dir, m)
            except Exception:
                pass
        finally:
            with _generate_lock:
                _generate_jobs.pop(run_id, None)

    thread = threading.Thread(target=_worker, name=f"design-confirm-{run_id}", daemon=True)
    with _generate_lock:
        _generate_jobs[run_id] = thread
    thread.start()
    manifest["status"] = "generating_ui"
    write_manifest(sdir, manifest)
    return public_session_payload(manifest, sdir)


def start_iterate_session(
    run_id: str,
    instruction: str,
    *,
    target_kind: str | None = None,
    target_id: str | None = None,
    element_path: str | None = None,
    element_label: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Background iterate (poll until ready) — mirrors start_generate_session."""
    sdir = session_dir(run_id)
    if not (sdir / MANIFEST).is_file():
        raise DesignError("Session not found")
    with _iterate_lock:
        existing = _iterate_jobs.get(run_id)
        if existing and existing.is_alive():
            return get_session(run_id)

    manifest = read_manifest(sdir)
    manifest["status"] = "iterating"
    write_manifest(sdir, manifest)

    def _worker() -> None:
        try:
            iterate_session(
                run_id,
                instruction,
                target_kind=target_kind,
                target_id=target_id,
                element_path=element_path,
                element_label=element_label,
                mode=mode,
            )
        except Exception as exc:
            logger.exception("design iterate worker failed run_id=%s", run_id)
            try:
                err_dir = session_dir(run_id)
                m = read_manifest(err_dir)
                m["status"] = "error"
                m["error"] = str(exc)
                write_manifest(err_dir, m)
            except Exception:
                pass
        finally:
            with _iterate_lock:
                _iterate_jobs.pop(run_id, None)

    thread = threading.Thread(target=_worker, name=f"design-iter-{run_id}", daemon=True)
    with _iterate_lock:
        _iterate_jobs[run_id] = thread
    thread.start()
    return public_session_payload(manifest, sdir)


