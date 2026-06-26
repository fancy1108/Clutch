#!/usr/bin/env python3
"""Step 0.1 — PTY interactive drivability probe for Claude / agy CLIs.

Spawns a long-lived PTY session, writes N prompts via stdin (not print mode),
and records whether each round returns to an interactive-ready state.

Usage:
  uv run python step0_pty_probe.py --provider claude --rounds 5
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
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_WORKSPACE = Path("/tmp/clutch-pty-poc")
RUNS_DIR = Path(__file__).resolve().parent / "runs"

PROVIDER_BINARIES = {
    "claude": "claude",
    "agy": "agy",
}


@dataclass
class RoundResult:
    index: int
    prompt: str
    write_ok: bool
    ttfb_ms: int | None
    total_ms: int
    max_silence_ms: int
    output_chars: int
    output_preview: str
    likely_ready: bool
    notes: str = ""


@dataclass
class ProbeReport:
    provider: str
    binary: str
    workspace: str
    started_at: str
    rounds: list[RoundResult] = field(default_factory=list)
    pty_drivable: bool = False
    failure_reason: str = ""
    sigint_note: str = "not tested in this script"


def _resolve_binary(provider: str) -> str:
    binary = PROVIDER_BINARIES[provider]
    path = shutil.which(binary)
    if not path:
        raise SystemExit(f"Binary not found on PATH: {binary}")
    return path


def _build_argv(provider: str, binary: str, workspace: Path) -> list[str]:
    if provider == "claude":
        return [
            binary,
            "--dangerously-skip-permissions",
            "--add-dir",
            str(workspace),
        ]
    if provider == "agy":
        return [
            binary,
            "--dangerously-skip-permissions",
        ]
    raise ValueError(provider)


def _spawn_pty(argv: list[str], *, cwd: Path) -> tuple[int, int]:
    pid, master_fd = pty.fork()
    if pid == 0:
        os.chdir(cwd)
        os.execvp(argv[0], argv)
    return pid, master_fd


def _set_master_nonblocking(master_fd: int) -> None:
    flags = fcntl_get(master_fd)
    import fcntl

    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)


def fcntl_get(fd: int) -> int:
    import fcntl

    return fcntl.fcntl(fd, fcntl.F_GETFL)


def _read_available(master_fd: int, *, idle_ms: int, max_wait_s: float) -> tuple[str, int]:
    """Read until idle_ms silence or max_wait_s elapsed."""
    chunks: list[str] = []
    deadline = time.monotonic() + max_wait_s
    last_data = time.monotonic()
    max_silence = 0

    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        wait_s = min(0.2, remaining)
        if wait_s <= 0:
            break
        r, _, _ = select.select([master_fd], [], [], wait_s)
        if r:
            try:
                data = os.read(master_fd, 65536)
            except OSError:
                break
            if not data:
                break
            text = data.decode(errors="replace")
            chunks.append(text)
            last_data = time.monotonic()
        else:
            silence = int((time.monotonic() - last_data) * 1000)
            max_silence = max(max_silence, silence)
            if chunks and silence >= idle_ms:
                break

    return "".join(chunks), max_silence


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", text)


def _needs_trust_ack(output: str) -> bool:
    plain = _strip_ansi(output).lower()
    return ("trust" in plain and "folder" in plain) or "safety" in plain


def _trust_ack_line(output: str) -> str:
    plain = _strip_ansi(output).lower()
    if "1." in plain and "trust" in plain:
        return "1"
    return "y"


def _write_line(master_fd: int, line: str) -> None:
    payload = line if line.endswith("\n") else f"{line}\n"
    os.write(master_fd, payload.encode())


def _likely_interactive_ready(output: str, provider: str) -> bool:
    """Heuristic: CLI finished a turn and waits for next input."""
    plain = _strip_ansi(output)
    if not plain.strip():
        return False
    lower = plain.lower()
    if provider == "claude":
        if re.search(r"allow tool|\(y/n\)|press enter|>", lower):
            return True
        return len(plain) > 20 and not re.search(r"\.\.\.|thinking", lower)
    if provider == "agy":
        return ">" in plain or "?" in plain[-80:]
    return False


def _round_prompts(n: int) -> list[str]:
    base = [
        "Reply with exactly the word OK and nothing else.",
        "What is 2+2? One short line only.",
        "Name one color. One word only.",
        "Say hello in one word.",
        "Reply DONE only.",
    ]
    return base[:n]


def run_probe(
    *,
    provider: str,
    rounds: int,
    workspace: Path,
    round_timeout_s: float,
    idle_ms: int,
) -> ProbeReport:
    workspace.mkdir(parents=True, exist_ok=True)
    binary = _resolve_binary(provider)
    argv = _build_argv(provider, binary, workspace)
    started_at = datetime.now(timezone.utc).isoformat()

    pid, master_fd = _spawn_pty(argv, cwd=workspace)
    _set_master_nonblocking(master_fd)

    report = ProbeReport(
        provider=provider,
        binary=binary,
        workspace=str(workspace),
        started_at=started_at,
    )

    try:
        # Initial boot output
        boot_out, _ = _read_available(master_fd, idle_ms=idle_ms, max_wait_s=min(30.0, round_timeout_s))
        if boot_out:
            report.rounds.append(
                RoundResult(
                    index=0,
                    prompt="(boot)",
                    write_ok=True,
                    ttfb_ms=None,
                    total_ms=0,
                    max_silence_ms=0,
                    output_chars=len(boot_out),
                    output_preview=_strip_ansi(boot_out)[:500],
                    likely_ready=False,
                    notes="startup banner",
                )
            )
            if _needs_trust_ack(boot_out):
                ack = _trust_ack_line(boot_out)
                _write_line(master_fd, ack)
                ack_out, _ = _read_available(master_fd, idle_ms=idle_ms, max_wait_s=25.0)
                report.rounds.append(
                    RoundResult(
                        index=0,
                        prompt=f"(trust_ack {ack!r})",
                        write_ok=True,
                        ttfb_ms=None,
                        total_ms=0,
                        max_silence_ms=0,
                        output_chars=len(ack_out),
                        output_preview=_strip_ansi(ack_out)[:500],
                        likely_ready=False,
                        notes="auto-ack workspace trust gate",
                    )
                )

        prompts = _round_prompts(rounds)
        all_ok = True

        for i, prompt in enumerate(prompts, start=1):
            t0 = time.monotonic()
            payload = prompt if prompt.endswith("\n") else f"{prompt}\n"
            try:
                os.write(master_fd, payload.encode())
                write_ok = True
            except OSError as exc:
                write_ok = False
                report.rounds.append(
                    RoundResult(
                        index=i,
                        prompt=prompt,
                        write_ok=False,
                        ttfb_ms=None,
                        total_ms=int((time.monotonic() - t0) * 1000),
                        max_silence_ms=0,
                        output_chars=0,
                        output_preview="",
                        likely_ready=False,
                        notes=str(exc),
                    )
                )
                all_ok = False
                report.failure_reason = f"stdin write failed round {i}: {exc}"
                break

            first_byte_at: float | None = None
            chunks: list[str] = []
            deadline = t0 + round_timeout_s
            last_data = t0
            max_silence = 0

            while time.monotonic() < deadline:
                wait_s = min(0.2, deadline - time.monotonic())
                if wait_s <= 0:
                    break
                r, _, _ = select.select([master_fd], [], [], wait_s)
                if r:
                    try:
                        data = os.read(master_fd, 65536)
                    except OSError:
                        break
                    if not data:
                        break
                    if first_byte_at is None:
                        first_byte_at = time.monotonic()
                    chunks.append(data.decode(errors="replace"))
                    last_data = time.monotonic()
                else:
                    silence = int((time.monotonic() - last_data) * 1000)
                    max_silence = max(max_silence, silence)
                    if chunks and silence >= idle_ms:
                        break

            output = "".join(chunks)
            ttfb_ms = int((first_byte_at - t0) * 1000) if first_byte_at else None
            total_ms = int((time.monotonic() - t0) * 1000)
            ready = _likely_interactive_ready(output, provider)

            report.rounds.append(
                RoundResult(
                    index=i,
                    prompt=prompt,
                    write_ok=write_ok,
                    ttfb_ms=ttfb_ms,
                    total_ms=total_ms,
                    max_silence_ms=max_silence,
                    output_chars=len(output),
                    output_preview=output[:800],
                    likely_ready=ready,
                )
            )

            if not ready:
                all_ok = False
                report.failure_reason = f"round {i} did not reach interactive-ready heuristic"
                # Continue probing to collect more data unless output empty + timeout
                if not output.strip() and total_ms >= int(round_timeout_s * 1000) - 100:
                    break

        report.pty_drivable = all_ok and len([r for r in report.rounds if r.index > 0]) == rounds

    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass
        try:
            os.kill(pid, signal.SIGTERM)
            os.waitpid(pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 0.1 PTY drivability probe")
    parser.add_argument("--provider", choices=sorted(PROVIDER_BINARIES), default="claude")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--round-timeout", type=float, default=120.0)
    parser.add_argument("--idle-ms", type=int, default=2500)
    args = parser.parse_args()

    report = run_probe(
        provider=args.provider,
        rounds=args.rounds,
        workspace=args.workspace,
        round_timeout_s=args.round_timeout,
        idle_ms=args.idle_ms,
    )

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RUNS_DIR / f"{stamp}-{args.provider}-pty-probe.json"
    payload = {
        **asdict(report),
        "rounds": [asdict(r) for r in report.rounds],
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"ok": report.pty_drivable, "out": str(out_path), "failure": report.failure_reason}, indent=2))
    sys.exit(0 if report.pty_drivable else 1)


if __name__ == "__main__":
    main()
