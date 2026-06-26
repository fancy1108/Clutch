#!/usr/bin/env python3
"""Step 0 Route C — Hybrid Runtime: long-lived bash PTY + repeated `claude -p`.

Validates Plan B without driving Claude Ink TUI:
  Session -> bash PTY -> many `claude -p` invocations in same shell.

Preserves: cwd, env, background processes (e.g. dev server).
"""

from __future__ import annotations

import argparse
import json
import os
import pty
import re
import select
import shutil
import signal
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

RUNS_DIR = Path(__file__).resolve().parent / "runs"
DEFAULT_WORKSPACE = Path("/tmp/clutch-pty-poc-hybrid")


@dataclass
class RoundResult:
    index: int
    prompt: str
    exit_hint: str
    total_ms: int
    output_preview: str
    claude_output_preview: str
    ok: bool


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", text)


def _read_available(master_fd: int, *, wait_s: float) -> str:
    chunks: list[str] = []
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        r, _, _ = select.select([master_fd], [], [], min(0.2, remaining))
        if not r:
            continue
        try:
            data = os.read(master_fd, 65536)
        except OSError:
            break
        if not data:
            break
        chunks.append(data.decode(errors="replace"))
    return "".join(chunks)


def _read_until_marker(master_fd: int, marker: str, *, max_wait_s: float) -> str:
    chunks: list[str] = []
    deadline = time.monotonic() + max_wait_s
    while time.monotonic() < deadline:
        chunk = _read_available(master_fd, wait_s=min(2.0, deadline - time.monotonic()))
        if chunk:
            chunks.append(chunk)
            if marker in _strip_ansi("".join(chunks)):
                break
        elif chunks:
            # brief pause when child is thinking
            time.sleep(0.1)
        else:
            time.sleep(0.05)
    return "".join(chunks)


def _write_line(master_fd: int, line: str) -> None:
    os.write(master_fd, (line if line.endswith("\n") else line + "\n").encode())


def _extract_claude_output(plain: str, *, marker: str, cmd_echo: str) -> str:
    """Strip shell echo and marker; return Claude stdout-ish region."""
    text = plain
    if marker in text:
        text = text.split(marker, 1)[0]
    for noise in (cmd_echo, "\r"):
        text = text.replace(noise, "")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Drop lines that look like our shell command
    kept = [ln for ln in lines if "claude -p" not in ln and "__CLUTCH_" not in ln]
    return "\n".join(kept).strip()


def run_hybrid(*, rounds: int, workspace: Path, claude_binary: str, round_timeout_s: float) -> dict:
    workspace.mkdir(parents=True, exist_ok=True)
    shell = shutil.which("bash") or "/bin/bash"
    pid, master_fd = pty.fork()
    if pid == 0:
        os.chdir(workspace)
        # Avoid login/rc noise and readline bracketed-paste quirks in long lines
        os.execvp(shell, [shell, "--norc", "--noprofile", "-i"])
        raise SystemExit(1)

    results: list[RoundResult] = []
    try:
        boot = _read_until_marker(master_fd, "$", max_wait_s=8.0)
        _write_line(master_fd, f"export COLUMNS=200 PS1='clutch$ '")
        _read_until_marker(master_fd, "clutch$", max_wait_s=3.0)
        _write_line(master_fd, f"cd {workspace}")
        _read_until_marker(master_fd, "clutch$", max_wait_s=3.0)

        _write_line(master_fd, "mkdir -p sub && cd sub && pwd")
        pwd_out = _strip_ansi(_read_until_marker(master_fd, "clutch$", max_wait_s=5.0))

        prompts = [
            "Reply with exactly: OK",
            "What is 2+2? One short line.",
            "Say hi in one word.",
            "Reply: DONE",
            "One word: blue",
        ][:rounds]

        for i, prompt in enumerate(prompts, start=1):
            marker = f"__CLUTCH_HYBRID_DONE_{i}__"
            # Short on-wire line: prompt via env avoids readline wrap on long paths
            safe = prompt.replace("'", "'\"'\"'")
            cmd = (
                f"CLUTCH_P='{safe}'; "
                f"{claude_binary} -p \"$CLUTCH_P\" --dangerously-skip-permissions; "
                f"echo {marker}"
            )
            t0 = time.monotonic()
            _write_line(master_fd, cmd)
            out = _read_until_marker(master_fd, marker, max_wait_s=round_timeout_s)
            total_ms = int((time.monotonic() - t0) * 1000)
            plain = _strip_ansi(out)
            claude_out = _extract_claude_output(plain, marker=marker, cmd_echo=cmd[:80])
            has_marker = marker in plain
            has_model_text = len(claude_out) >= 2
            ok = has_marker and has_model_text
            results.append(
                RoundResult(
                    index=i,
                    prompt=prompt,
                    exit_hint=marker if has_marker else "missing marker",
                    total_ms=total_ms,
                    output_preview=plain[-700:],
                    claude_output_preview=claude_out[:300],
                    ok=ok,
                )
            )

        cwd_ok = "sub" in pwd_out
        success = sum(1 for r in results if r.ok)
        pass_all = success == rounds and cwd_ok

        return {
            "route": "C",
            "mode": "hybrid_bash_claude_p",
            "workspace": str(workspace),
            "cwd_inheritance_ok": cwd_ok,
            "pwd_output": pwd_out[-200:],
            "rounds": [asdict(r) for r in results],
            "success_count": success,
            "pass_all": pass_all,
            "boot_preview": _strip_ansi(boot)[:200],
        }
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass
        try:
            os.kill(pid, signal.SIGTERM)
            os.waitpid(pid, 0)
        except (ChildProcessError, ProcessLookupError):
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="defaults to /tmp/clutch-pty-poc-hybrid-<uuid>",
    )
    parser.add_argument("--round-timeout", type=float, default=180.0)
    args = parser.parse_args()

    claude = shutil.which("claude")
    if not claude:
        raise SystemExit("claude not on PATH")

    workspace = args.workspace or (DEFAULT_WORKSPACE.parent / f"{DEFAULT_WORKSPACE.name}-{uuid.uuid4().hex[:8]}")

    report = run_hybrid(
        rounds=args.rounds,
        workspace=workspace,
        claude_binary=claude,
        round_timeout_s=args.round_timeout,
    )
    report["recorded_at"] = datetime.now(timezone.utc).isoformat()
    report["binary"] = claude

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RUNS_DIR / f"{stamp}-route-c-hybrid.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "pass_all": report["pass_all"],
                "success": f"{report['success_count']}/{args.rounds}",
                "out": str(out),
            },
            indent=2,
        )
    )
    sys.exit(0 if report["pass_all"] else 1)


if __name__ == "__main__":
    main()
