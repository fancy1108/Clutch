"""Local image analysis for design spec extraction (no external vision model needed).

When the active LLM does not support vision input, this module extracts:
  1. Dominant color palette via PIL quantization (always available).
  2. Visible UI text via pytesseract OCR (optional — gracefully skipped if absent).

The results are assembled into a structured prompt fragment that lets any text-only
LLM produce an accurate design spec (colors, typography hints, component names) from
a reference screenshot.
"""

from __future__ import annotations

import base64
import colorsys
import io
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Availability flags (set at import time so we warn once, not per call)
# ---------------------------------------------------------------------------

try:
    from PIL import Image as _PILImage

    _PIL_AVAILABLE = True
except ImportError:
    _PILImage = None  # type: ignore[assignment,misc]
    _PIL_AVAILABLE = False
    logger.debug("image_analysis: Pillow not installed — color extraction disabled")

try:
    import pytesseract as _pytesseract

    _OCR_AVAILABLE = True
except ImportError:
    _pytesseract = None  # type: ignore[assignment]
    _OCR_AVAILABLE = False
    logger.debug("image_analysis: pytesseract not installed — OCR disabled")


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hue_name(h: float) -> str:
    """Map hue (0-360) to a human-readable color name."""
    if h < 15 or h >= 345:
        return "red"
    if h < 40:
        return "orange"
    if h < 70:
        return "yellow"
    if h < 160:
        return "green"
    if h < 200:
        return "cyan"
    if h < 260:
        return "blue"
    if h < 290:
        return "violet"
    if h < 345:
        return "pink"
    return "red"


def _classify_color(r: int, g: int, b: int) -> tuple[str, str]:
    """Return (bucket, name) for an RGB color.

    Bucket is one of: primary, neutral, accent.
    Name is a human-readable color description.
    """
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hue_deg = h * 360
    sat_pct = s * 100
    val_pct = v * 100

    # Near-white / near-black / grey → neutral
    if sat_pct < 12:
        if val_pct > 85:
            return "neutral", "white"
        if val_pct < 18:
            return "neutral", "black"
        return "neutral", "grey"

    color_name = _hue_name(hue_deg)

    # High saturation, mid-high brightness → primary candidate
    if sat_pct > 45 and val_pct > 30:
        return "primary", color_name
    # Lower saturation saturated colors → accent
    return "accent", color_name


def _extract_dominant_colors(
    img: Any,
    *,
    n_colors: int = 12,
) -> list[dict[str, Any]]:
    """Return up to n_colors dominant colors sorted by pixel coverage.

    Each entry: {hex, r, g, b, pct, bucket, name}
    """
    # Resize to cap computation cost; 150×150 is plenty for palette extraction.
    thumb = img.convert("RGB").resize((150, 150), _PILImage.LANCZOS)  # type: ignore[attr-defined]
    # Quantize to N representative colors.
    quantized = thumb.quantize(colors=n_colors, method=_PILImage.Quantize.MEDIANCUT, dither=0)  # type: ignore[attr-defined]
    palette_raw = quantized.getpalette()  # [R,G,B, R,G,B, …]
    if not palette_raw:
        return []

    # Count pixels per palette index.
    pixels = quantized.getdata()
    counts: dict[int, int] = {}
    for px in pixels:
        counts[px] = counts.get(px, 0) + 1
    total = sum(counts.values()) or 1

    colors: list[dict[str, Any]] = []
    for idx, cnt in sorted(counts.items(), key=lambda kv: -kv[1]):
        if idx * 3 + 2 >= len(palette_raw):
            continue
        r, g, b = palette_raw[idx * 3], palette_raw[idx * 3 + 1], palette_raw[idx * 3 + 2]
        bucket, name = _classify_color(r, g, b)
        pct = round(cnt / total * 100, 1)
        if pct < 1.0:
            continue
        colors.append(
            {
                "hex": _rgb_to_hex(r, g, b),
                "r": r,
                "g": g,
                "b": b,
                "pct": pct,
                "bucket": bucket,
                "name": name,
            }
        )

    return colors[:n_colors]


def _build_palette(colors: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Group extracted colors into primary / accent / neutral / secondary buckets."""
    primary: list[dict] = []
    accent: list[dict] = []
    neutral: list[dict] = []

    for c in colors:
        if c["bucket"] == "primary":
            primary.append(c)
        elif c["bucket"] == "accent":
            accent.append(c)
        else:
            neutral.append(c)

    # If no primary colors found, promote the top accent colors.
    if not primary and accent:
        primary = accent[:3]
        accent = accent[3:]

    # Build secondary from remaining primary colors.
    secondary = primary[2:4] if len(primary) > 2 else []
    if not secondary:
        secondary = accent[:2]

    return {
        "primary": [c["hex"] for c in primary[:3]],
        "secondary": [c["hex"] for c in secondary[:3]],
        "accent": [c["hex"] for c in accent[:3]],
        "neutral": [c["hex"] for c in neutral[:5]],
    }


# ---------------------------------------------------------------------------
# OCR helper
# ---------------------------------------------------------------------------

def _extract_ocr_text(img: Any) -> str:
    """Extract visible text from the image using pytesseract.

    Returns empty string if pytesseract is not available or fails.
    """
    if not _OCR_AVAILABLE or _pytesseract is None:
        return ""
    try:
        # Convert to grayscale for better OCR accuracy.
        gray = img.convert("L")
        text = _pytesseract.image_to_string(gray, config="--oem 3 --psm 6")  # type: ignore[union-attr]
        # Clean up: strip blank lines, truncate to a reasonable length.
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return " | ".join(lines[:40])[:800]
    except Exception as exc:
        logger.debug("image_analysis: OCR failed: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_image_for_spec(image_data_url: str) -> dict[str, Any]:
    """Analyse a base64 image data URL and return a structured description dict.

    Returns::
        {
            "colors": [{hex, pct, name, bucket}, …],
            "palette": {primary: [hex,…], secondary: […], accent: […], neutral: […]},
            "ocr_text": "Welcome | Projects | Timeline | …",
            "description": "<multiline text for LLM prompt injection>",
            "available": True | False,  # False if Pillow not installed
        }
    """
    if not _PIL_AVAILABLE or _PILImage is None:
        return {
            "colors": [],
            "palette": {},
            "ocr_text": "",
            "description": "",
            "available": False,
        }

    try:
        # Decode data URL → bytes → PIL Image.
        if "," in image_data_url:
            _, b64 = image_data_url.split(",", 1)
        else:
            b64 = image_data_url
        raw_bytes = base64.b64decode(b64)
        img = _PILImage.open(io.BytesIO(raw_bytes))
    except Exception as exc:
        logger.warning("image_analysis: failed to decode image: %s", exc)
        return {
            "colors": [],
            "palette": {},
            "ocr_text": "",
            "description": "",
            "available": False,
        }

    colors = _extract_dominant_colors(img, n_colors=12)
    palette = _build_palette(colors)
    ocr_text = _extract_ocr_text(img)

    # ---- Build structured description ----------------------------------------
    lines: list[str] = ["[Reference Image Analysis]"]

    if colors:
        color_lines = [
            f"  {c['hex']} ({c['name']}, {c['pct']}%)" for c in colors[:8]
        ]
        lines.append("Dominant colors (by pixel coverage):")
        lines.extend(color_lines)

    if palette.get("primary"):
        lines.append(f"Primary color(s): {', '.join(palette['primary'])}")
    if palette.get("secondary"):
        lines.append(f"Secondary color(s): {', '.join(palette['secondary'])}")
    if palette.get("accent"):
        lines.append(f"Accent color(s): {', '.join(palette['accent'])}")
    if palette.get("neutral"):
        lines.append(f"Neutral/background color(s): {', '.join(palette['neutral'])}")

    if ocr_text:
        lines.append(f"Visible UI text detected: {ocr_text}")
    else:
        lines.append(
            "(OCR not available — use the color palette above to infer typography and UI elements.)"
        )

    lines.append(
        "\nIMPORTANT: You MUST use the exact hex colors listed above as your primary, "
        "secondary, accent, and neutral palette in the JSON spec. Do NOT substitute or invent colors."
    )

    description = "\n".join(lines)

    return {
        "colors": colors,
        "palette": palette,
        "ocr_text": ocr_text,
        "description": description,
        "available": True,
    }


def image_analysis_prompt_fragment(image_data_url: str) -> str:
    """Return a ready-to-inject prompt string describing the reference image.

    Returns an empty string if analysis is unavailable (Pillow not installed,
    or decoding fails), so callers can safely concatenate without checking.
    """
    result = analyze_image_for_spec(image_data_url)
    return result.get("description", "")


def image_analysis_prompt_fragment_for_chat(image_data_url: str) -> str:
    """Coding-chat variant: OCR/text first; no Design-spec color mandates.

    Design's fragment tells the LLM to lock hex palettes into a JSON spec — that
    poisons Coding answers when the user only asks what text is in the image.
    """
    result = analyze_image_for_spec(image_data_url)
    if not result.get("available"):
        return ""

    lines: list[str] = ["[Attached image — local analysis]"]
    ocr_text = (result.get("ocr_text") or "").strip()
    colors = result.get("colors") or []
    ocr_status = ocr_runtime_status()

    if ocr_text:
        lines.append(f"Visible text (OCR): {ocr_text}")
        lines.append(
            "Answer using the OCR text above when the user asks what the image says "
            "or contains. Do not claim OCR is unavailable."
        )
    else:
        if not ocr_status.get("ready"):
            reason = ocr_status.get("detail") or "OCR runtime unavailable"
            lines.append(f"Visible text (OCR): unavailable — {reason}")
        else:
            lines.append("Visible text (OCR): no text detected in the image.")
        lines.append(
            "You CANNOT reliably read writing from this image via local OCR. "
            "Do not invent text from colors. Tell the user the vision model could not "
            "process the image and local OCR did not extract text."
        )

    if colors:
        top = ", ".join(f"{c['hex']} ({c.get('name', '?')})" for c in colors[:5])
        lines.append(f"Dominant colors (secondary context only): {top}")

    return "\n".join(lines)


def ocr_runtime_status() -> dict[str, Any]:
    """Report whether local OCR can run (pytesseract + tesseract binary)."""
    import shutil

    if not _OCR_AVAILABLE or _pytesseract is None:
        return {
            "ready": False,
            "pytesseract": False,
            "tesseract_bin": None,
            "detail": "Python package pytesseract is not installed",
        }
    bin_path = shutil.which("tesseract")
    if not bin_path:
        return {
            "ready": False,
            "pytesseract": True,
            "tesseract_bin": None,
            "detail": "tesseract binary not found on PATH (e.g. brew install tesseract)",
        }
    try:
        version = str(_pytesseract.get_tesseract_version())
    except Exception as exc:  # noqa: BLE001
        return {
            "ready": False,
            "pytesseract": True,
            "tesseract_bin": bin_path,
            "detail": f"tesseract found but not usable: {exc}",
        }
    return {
        "ready": True,
        "pytesseract": True,
        "tesseract_bin": bin_path,
        "version": version,
        "detail": "ok",
    }
