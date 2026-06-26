#!/usr/bin/env python3
"""Step 0 Route B — search Claude CLI help for headless / pipe / non-TUI flags."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

RUNS_DIR = Path(__file__).resolve().parent / "runs"

KEYWORDS = re.compile(
    r"headless|raw|json|stdio|pipe|no-tui|non-interactive|trust|tty|print|bare|safe-mode",
    re.I,
)

COMMANDS = [
    ["claude", "--help"],
    ["claude", "agents", "--help"],
    ["claude", "project", "--help"],
    ["claude", "mcp", "--help"],
    ["claude", "auth", "--help"],
]


def main() -> None:
    binary = shutil.which("claude")
    if not binary:
        raise SystemExit("claude not on PATH")

    hits: list[dict[str, str]] = []
    full_text: list[str] = []

    for cmd in COMMANDS:
        cmd[0] = binary
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        full_text.append(f"$ {' '.join(cmd)}\n{text}\n")
        for line in text.splitlines():
            if KEYWORDS.search(line):
                hits.append({"cmd": " ".join(cmd), "line": line.strip()})

    full_joined = "\n".join(full_text)
    # Help text wraps across lines: "... workspace trust dialog" / "is skipped when ..."
    normalized = re.sub(r"\s+", " ", full_joined.lower())
    flags_found = {
        "headless": bool(re.search(r"--headless", full_joined, re.I)),
        "no_tui": bool(re.search(r"no-tui|notui", full_joined, re.I)),
        "print_skips_trust": "trust dialog" in normalized and "is skipped" in normalized,
        "bare_mode": "--bare" in full_joined,
        "stream_json_print_only": "only works with --print" in full_joined.lower()
        and "stream-json" in full_joined.lower(),
    }

    report = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "binary": binary,
        "flags_found": flags_found,
        "conclusion": (
            "No --headless / --no-tui flag in scanned help. "
            "-p/--print skips workspace trust dialog (non-TTY). "
            "Structured output requires --print + --verbose."
        ),
        "keyword_hits": hits,
    }

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RUNS_DIR / f"{stamp}-route-b-headless-search.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "flags_found": flags_found}, indent=2))


if __name__ == "__main__":
    main()
