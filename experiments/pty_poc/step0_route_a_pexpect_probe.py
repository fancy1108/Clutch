#!/usr/bin/env python3
"""Step 0 Route A — expect-style PTY drive of Claude interactive TUI.

Pass criteria: 5/5 rounds after boot trust gate.

  pexpect.spawn("claude")
  expect trust menu -> send "1\\r"  (BOOT_TRUST; skip if workspace already trusted)
  expect prompt ready -> send prompt -> expect output

Requires: pip install pexpect  (or: uv run --with pexpect python ...)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import pexpect
except ImportError:
    print("pexpect not installed. Run: uv run --with pexpect python step0_route_a_pexpect_probe.py", file=sys.stderr)
    raise SystemExit(1)

RUNS_DIR = Path(__file__).resolve().parent / "runs"
DEFAULT_WORKSPACE = Path("/tmp/clutch-pty-poc")


@dataclass
class RoundResult:
    index: int
    prompt: str
    ok: bool
    elapsed_s: float
    output_preview: str
    notes: str = ""


@dataclass
class RouteAReport:
    route: str
    provider: str
    binary: str
    workspace: str
    started_at: str
    boot_trust_handled: bool
    boot_trust_skipped: bool
    bypass_permissions_handled: bool
    rounds: list[RoundResult]
    success_count: int
    pass_5_of_5: bool
    failure_reason: str = ""


def _round_prompts(n: int) -> list[str]:
    base = [
        "Reply with exactly the word OK and nothing else.",
        "What is 2+2? One short line only.",
        "Name one color. One word only.",
        "Say hello in one word.",
        "Reply DONE only.",
    ]
    return base[:n]


TRUST_PATTERNS = [
    re.compile(r"trust.*folder", re.I),
    re.compile(r"I trust this folder", re.I),
    re.compile(r"Quick safety check", re.I),
]

READY_PATTERNS = [
    re.compile(r"❯"),
    re.compile(r"How can I help", re.I),
    re.compile(r"Claude Code", re.I),
    re.compile(r"Tip:", re.I),
    re.compile(r"type your message", re.I),
]


BYPASS_PATTERNS = [
    re.compile(r"Bypass Permissions", re.I),
    re.compile(r"Yes, I accept", re.I),
    re.compile(r"dangerously-skip", re.I),
]


def _handle_boot_trust(child: pexpect.spawn, *, timeout_s: int) -> tuple[bool, bool]:
    """Returns (handled, skipped). skipped=True when menu never appeared (already trusted)."""
    idx = child.expect(TRUST_PATTERNS + [pexpect.TIMEOUT], timeout=timeout_s)
    if idx == len(TRUST_PATTERNS):
        return False, True
    child.send("1\r")
    return True, False


def _handle_bypass_permissions(child: pexpect.spawn, *, timeout_s: int) -> bool:
    """`--dangerously-skip-permissions` shows a second boot gate; accept with option 2."""
    idx = child.expect(BYPASS_PATTERNS + [pexpect.TIMEOUT], timeout=timeout_s)
    if idx == len(BYPASS_PATTERNS):
        return False
    # Default selection is "1. No exit" — move to "2. Yes, I accept" then confirm
    child.send("\x1b[B\r")
    child.expect(
        [re.compile(r"How can I help", re.I), re.compile(r"❯\\s*$"), pexpect.TIMEOUT],
        timeout=45,
    )
    return True


def run_route_a(*, rounds: int, workspace: Path, timeout_s: int) -> RouteAReport:
    binary = shutil.which("claude")
    if not binary:
        raise SystemExit("claude not on PATH")

    workspace.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()

    cmd = f"{binary} --dangerously-skip-permissions"
    child = pexpect.spawn(cmd, cwd=str(workspace), encoding="utf-8", timeout=timeout_s)
    child.setwinsize(24, 120)

    report = RouteAReport(
        route="A",
        provider="claude",
        binary=binary,
        workspace=str(workspace),
        started_at=started_at,
        boot_trust_handled=False,
        boot_trust_skipped=False,
        bypass_permissions_handled=False,
        rounds=[],
        success_count=0,
        pass_5_of_5=False,
    )

    try:
        handled, skipped = _handle_boot_trust(child, timeout_s=45)
        report.boot_trust_handled = handled
        report.boot_trust_skipped = skipped

        if skipped:
            # Already trusted workspace — wait for TUI ready without sending "1"
            idx = child.expect(
                READY_PATTERNS + BYPASS_PATTERNS + [pexpect.TIMEOUT, pexpect.EOF],
                timeout=60,
            )
            if idx >= len(READY_PATTERNS) + len(BYPASS_PATTERNS):
                report.failure_reason = "timeout/EOF waiting for prompt after skipped BOOT_TRUST"
                return report
            if idx >= len(READY_PATTERNS):
                report.bypass_permissions_handled = _handle_bypass_permissions(child, timeout_s=30)
        else:
            report.bypass_permissions_handled = _handle_bypass_permissions(child, timeout_s=15)

        # Ensure main prompt ready
        child.expect(READY_PATTERNS + [pexpect.TIMEOUT], timeout=30)

        # Settle Ink render
        time.sleep(1.5)

        prompts = _round_prompts(rounds)
        for i, prompt in enumerate(prompts, start=1):
            t0 = time.monotonic()
            child.send(prompt + "\r")
            try:
                if i == 1:
                    # Must see model reply, not just echoed prompt containing "OK"
                    child.expect(
                        re.compile(r"(?<!word )(?<!the )\bOK\b(?!\s+and)", re.I),
                        timeout=timeout_s,
                    )
                elif i == 2:
                    child.expect(re.compile(r"\b4\b"), timeout=timeout_s)
                elif i == 5:
                    child.expect(re.compile(r"\bDONE\b", re.I), timeout=timeout_s)
                else:
                    child.expect(re.compile(r".{8,}", re.S), timeout=timeout_s)
                out = ((child.before or "") + str(child.after or ""))[-800:]
                elapsed = time.monotonic() - t0
                ok = elapsed >= 1.0 and len(out.strip()) > 10
                if i == 1:
                    ok = ok and bool(re.search(r"(?<!word )(?<!the )\bOK\b(?!\s+and)", out, re.I))
                elif i == 2:
                    ok = ok and bool(re.search(r"\b4\b", out))
                elif i == 5:
                    ok = ok and bool(re.search(r"\bDONE\b", out, re.I))
            except pexpect.TIMEOUT:
                out = (child.before or "")[-800:]
                ok = False
                report.failure_reason = f"round {i} timeout"
            except pexpect.EOF:
                out = (child.before or "")[-800:]
                ok = False
                report.failure_reason = f"round {i} EOF (claude exited)"
            elapsed = time.monotonic() - t0
            report.rounds.append(
                RoundResult(
                    index=i,
                    prompt=prompt,
                    ok=ok,
                    elapsed_s=round(elapsed, 2),
                    output_preview=out,
                )
            )
            if not ok:
                break
            time.sleep(0.5)

        report.success_count = sum(1 for r in report.rounds if r.ok)
        report.pass_5_of_5 = report.success_count == rounds
        if report.pass_5_of_5:
            report.failure_reason = ""
        elif not report.failure_reason:
            report.failure_reason = f"only {report.success_count}/{rounds} rounds ok"

    finally:
        try:
            child.close(force=True)
        except Exception:
            pass

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 0 Route A — pexpect PTY probe")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="fresh dir recommended; default creates /tmp/clutch-pty-poc-<uuid>",
    )
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    workspace = args.workspace or (DEFAULT_WORKSPACE.parent / f"{DEFAULT_WORKSPACE.name}-{uuid.uuid4().hex[:8]}")

    report = run_route_a(rounds=args.rounds, workspace=workspace, timeout_s=args.timeout)

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RUNS_DIR / f"{stamp}-route-a-pexpect.json"
    payload = {**asdict(report), "rounds": [asdict(r) for r in report.rounds]}
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "pass_5_of_5": report.pass_5_of_5,
                "success": f"{report.success_count}/{args.rounds}",
                "boot_trust_skipped": report.boot_trust_skipped,
                "workspace": str(workspace),
                "out": str(out_path),
                "failure": report.failure_reason,
            },
            indent=2,
        )
    )
    sys.exit(0 if report.pass_5_of_5 else 1)


if __name__ == "__main__":
    main()
