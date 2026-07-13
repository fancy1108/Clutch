"""Canvas grid and position offsets for design mode artboards."""

from __future__ import annotations

_DESIGN_CARD_GAP = 48
_DESIGN_CANVAS_ORIGIN = 40
_DESIGN_AGENT_LOG_W = 272
_DESIGN_SPEC_W = 300
_DESIGN_SOURCE_W = 300
_DESIGN_SPEC_UI_GAP = 56
_DESIGN_ROW_Y = 56
_DESIGN_UI_FRAME = {"web": 720, "app": 300}


def ui_frame_width(device: str) -> int:
    return _DESIGN_UI_FRAME.get((device or "web").strip().lower(), 720)


def spec_origin_x(*, has_source: bool = False) -> int:
    """X for the spec card — after Agent Log column (and optional source)."""
    x = _DESIGN_CANVAS_ORIGIN + _DESIGN_AGENT_LOG_W + _DESIGN_CARD_GAP
    if has_source:
        x += _DESIGN_SOURCE_W + _DESIGN_CARD_GAP
    return x


def default_ui_origin_x(*, has_source: bool = False) -> int:
    """Stitch-like x for the first UI artboard (agentLog → spec → ui)."""
    return spec_origin_x(has_source=has_source) + _DESIGN_SPEC_W + _DESIGN_SPEC_UI_GAP


def ui_layout_step(device: str) -> int:
    return ui_frame_width(device) + _DESIGN_CARD_GAP
