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


def _round_timings(rounds: list[dict]) -> tuple[list[int], list[int]]:
  """Return (ttfb_ms list, silence_ms list) from probe or route-c JSON."""
  ttfb: list[int] = []
  silences: list[int] = []
  for r in rounds:
    if r.get("index", 0) <= 0:
      continue
    if r.get("ttfb_ms") is not None:
      ttfb.append(int(r["ttfb_ms"]))
    elif r.get("total_ms") is not None:
      ttfb.append(int(r["total_ms"]))
    if r.get("max_silence_ms") is not None:
      silences.append(int(r["max_silence_ms"]))
    elif r.get("total_ms") is not None:
      silences.append(int(r["total_ms"]))
  return ttfb, silences


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge pty probe run into baseline JSON")
    parser.add_argument("--probe-json", type=Path, required=True, help="runs/*-pty-probe.json")
    parser.add_argument("--provider", required=True)
    parser.add_argument(
        "--mode",
        default=None,
        help="override mode (e.g. hybrid_bash_claude_p); inferred from probe when absent",
    )
    args = parser.parse_args()

    probe = json.loads(args.probe_json.read_text(encoding="utf-8"))
    template = json.loads(SCHEMA.read_text(encoding="utf-8"))

    rounds = probe.get("rounds", [])
    ttfb, silences = _round_timings(rounds)
    mode = args.mode or probe.get("mode") or "interactive_pty"

    template.update(
        {
            "provider": args.provider,
            "binary_path": probe.get("binary", ""),
            "recorded_at": probe.get("recorded_at") or datetime.now(timezone.utc).isoformat(),
            "workspace": probe.get("workspace", ""),
            "mode": mode,
            "pty_drivable": probe.get("pty_drivable"),
            "pty_drivable_notes": probe.get("failure_reason", ""),
            "timing": {
                "first_token_ms": ttfb[0] if ttfb else None,
                "avg_token_gap_ms": int(statistics.mean(silences)) if silences else None,
                "max_silence_ms": max(silences) if silences else None,
                "max_tool_silence_ms": None,
                "round_ttfb_ms": ttfb,
            },
            "notes": f"generated from {args.probe_json.name}; pass_all={probe.get('pass_all')}",
        }
    )

    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    out = BASELINE_DIR / f"{args.provider}.json"
    out.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
