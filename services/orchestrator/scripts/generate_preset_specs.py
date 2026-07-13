"""Generate .spec.json for all design presets using code parser (no LLM)."""
from __future__ import annotations

import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.design.preset_parser import preset_to_spec, extract_brand_color
from src.design.builtin_presets import BUILTIN_PRESET_IDS

OUT_DIR = Path(__file__).resolve().parent.parent / "src" / "design" / "presets"


def generate(preset_id: str) -> bool:
    spec_path = OUT_DIR / f"{preset_id}.spec.json"
    try:
        spec = preset_to_spec(preset_id)
        spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
        color = extract_brand_color(spec)
        return True
    except Exception as exc:
        print(f"  ✗ {preset_id}: {exc}")
        return False


def main() -> None:
    ids = [pid for pid in BUILTIN_PRESET_IDS if pid != "clutch"]
    print(f"Generating specs for {len(ids)} presets via parser…")
    ok = sum(1 for pid in ids if generate(pid))
    print(f"Done: {ok}/{len(ids)} succeeded")


if __name__ == "__main__":
    main()
