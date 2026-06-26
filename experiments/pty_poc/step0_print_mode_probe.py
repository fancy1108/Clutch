#!/usr/bin/env python3
"""Step 0.2 — Sample claude/agy --print --output-format stream-json (non-PTY).

Documents event shapes for CliBoundaryDetector design. Does not prove PTY viability.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RUNS_DIR = Path(__file__).resolve().parent / "runs"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["claude", "agy"], default="claude")
    parser.add_argument("--prompt", default="Reply with exactly: OK")
    args = parser.parse_args()

    binary = shutil.which("claude" if args.provider == "claude" else "agy")
    if not binary:
        raise SystemExit("CLI not on PATH")

    if args.provider == "claude":
        cmd = [
            binary,
            "-p",
            args.prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--dangerously-skip-permissions",
        ]
    else:
        cmd = [binary, "-p", args.prompt, "--dangerously-skip-permissions"]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out = RUNS_DIR / f"{stamp}-{args.provider}-print-probe.txt"
    body = {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout": proc.stdout[:20000],
        "stderr": proc.stderr[:5000],
    }
    out.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"exit_code": proc.returncode, "out": str(out)}, indent=2))
    sys.exit(0 if proc.returncode == 0 else 1)


if __name__ == "__main__":
    main()
