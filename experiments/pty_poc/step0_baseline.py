#!/usr/bin/env python3
"""Step 0.5 — Output behavior baseline recorder (extends probe JSON into baseline_schema)."""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent / "baseline_schema.json"
BASELINE_DIR = Path(__file__).resolve().parent / "baseline"


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge pty probe run into baseline JSON")
    parser.add_argument("--probe-json", type=Path, required=True, help="runs/*-pty-probe.json")
    parser.add_argument("--provider", required=True)
    args = parser.parse_args()

    probe = json.loads(args.probe_json.read_text(encoding="utf-8"))
    template = json.loads(SCHEMA.read_text(encoding="utf-8"))

    rounds = [r for r in probe.get("rounds", []) if r.get("index", 0) > 0]
    ttfb = [r["ttfb_ms"] for r in rounds if r.get("ttfb_ms") is not None]
    silences = [r["max_silence_ms"] for r in rounds if r.get("max_silence_ms")]

    template.update(
        {
            "provider": args.provider,
            "binary_path": probe.get("binary", ""),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "workspace": probe.get("workspace", ""),
            "mode": "interactive_pty",
            "pty_drivable": probe.get("pty_drivable"),
            "pty_drivable_notes": probe.get("failure_reason", ""),
            "timing": {
                "first_token_ms": ttfb[0] if ttfb else None,
                "avg_token_gap_ms": int(statistics.mean(silences)) if silences else None,
                "max_silence_ms": max(silences) if silences else None,
                "max_tool_silence_ms": None,
                "round_ttfb_ms": ttfb,
            },
            "notes": f"generated from {args.probe_json.name}",
        }
    )

    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    out = BASELINE_DIR / f"{args.provider}.json"
    out.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
