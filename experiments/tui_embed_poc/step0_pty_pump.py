#!/usr/bin/env python3
"""Phase 0 — PTY byte pump + optional WebSocket bridge for xterm harness."""

from __future__ import annotations

import argparse
import asyncio
import codecs
import json
import os
import shutil
import struct
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

if os.name != "nt":
    import fcntl
    import pty
    import termios

RUNS_DIR = Path(__file__).resolve().parent / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

CLI_MAP = {"claude": "claude", "opencode": "opencode"}


@dataclass
class SmokeResult:
    ok: bool
    rounds: int
    output_preview: str
    notes: str = ""


def _read_available(master_fd: int, wait_s: float) -> bytes:
    if os.name == "nt":
        return b""
    import select

    chunks: list[bytes] = []
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        remaining = max(0.0, deadline - time.monotonic())
        if remaining <= 0:
            break
        ready, _, _ = select.select([master_fd], [], [], min(0.1, remaining))
        if not ready:
            if chunks:
                break
            continue
        try:
            data = os.read(master_fd, 4096)
        except OSError:
            break
        if not data:
            break
        chunks.append(data)
    return b"".join(chunks)


def run_bash_smoke(*, rounds: int = 3) -> SmokeResult:
    if os.name == "nt":
        return SmokeResult(ok=False, rounds=0, output_preview="", notes="PTY smoke skipped on Windows")
    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        [shutil.which("bash") or "/bin/bash", "--norc", "--noprofile", "-i"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        start_new_session=True,
    )
    os.close(slave_fd)
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    captured: list[str] = []
    try:
        time.sleep(0.3)
        for idx in range(rounds):
            os.write(master_fd, f"echo CLUTCH_SMOKE_{idx}\n".encode())
            chunk = _read_available(master_fd, 1.5)
            if chunk:
                captured.append(decoder.decode(chunk))
        decoder.decode(b"", final=True)
        joined = "".join(captured)
        ok = all(f"CLUTCH_SMOKE_{i}" in joined for i in range(rounds))
        return SmokeResult(ok=ok, rounds=rounds, output_preview=joined[:400], notes="bash echo smoke")
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except (ProcessLookupError, subprocess.TimeoutExpired, OSError):
            try:
                proc.kill()
            except OSError:
                pass
        os.close(master_fd)


def spawn_cli(binary: str, workspace: Path) -> tuple[int, subprocess.Popen[bytes]]:
    master_fd, slave_fd = pty.openpty()
    winsize = struct.pack("HHHH", 24, 80, 0, 0)
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
    proc = subprocess.Popen(
        [binary],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        cwd=str(workspace),
        close_fds=True,
        start_new_session=True,
    )
    os.close(slave_fd)
    return master_fd, proc


async def ws_bridge(master_fd: int, proc: subprocess.Popen[bytes], port: int) -> None:
    import websockets

    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    clients: set = set()
    stop = threading.Event()

    def reader() -> None:
        while not stop.is_set() and proc.poll() is None:
            chunk = _read_available(master_fd, 0.2)
            if not chunk:
                continue
            text = decoder.decode(chunk)
            if not text:
                continue
            for ws in list(clients):
                asyncio.run_coroutine_threadsafe(ws.send(text), loop)

    loop = asyncio.get_running_loop()
    thread = threading.Thread(target=reader, name="pty-reader", daemon=True)
    thread.start()

    async def handler(websocket):  # type: ignore[no-untyped-def]
        clients.add(websocket)
        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    os.write(master_fd, message)
                else:
                    os.write(master_fd, message.encode("utf-8", errors="replace"))
        finally:
            clients.discard(websocket)

    async with websockets.serve(handler, "127.0.0.1", port):
        print(f"xterm harness: ws://127.0.0.1:{port} (open step0_xterm_harness.html)")
        while proc.poll() is None:
            await asyncio.sleep(0.5)
    stop.set()
    thread.join(timeout=1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="bash PTY smoke only")
    parser.add_argument("--cli", choices=sorted(CLI_MAP), default="claude")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workspace", type=Path, default=Path(f"/tmp/clutch-tui-poc-{uuid.uuid4().hex[:8]}"))
    args = parser.parse_args()

    started = datetime.now(timezone.utc).isoformat()
    if args.smoke:
        result = run_bash_smoke()
        out = RUNS_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-bash-smoke.json"
        out.write_text(json.dumps({"started_at": started, **asdict(result)}, indent=2), encoding="utf-8")
        print(json.dumps(asdict(result), indent=2))
        return 0 if result.ok else 1

    if os.name == "nt":
        print("Interactive CLI bridge requires Unix PTY", file=sys.stderr)
        return 1

    binary_name = CLI_MAP[args.cli]
    binary = shutil.which(binary_name)
    if not binary:
        print(f"{binary_name} not found on PATH", file=sys.stderr)
        return 1

    args.workspace.mkdir(parents=True, exist_ok=True)
    master_fd, proc = spawn_cli(binary, args.workspace)
    try:
        asyncio.run(ws_bridge(master_fd, proc, args.port))
    except KeyboardInterrupt:
        pass
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except (ProcessLookupError, subprocess.TimeoutExpired, OSError):
            try:
                proc.kill()
            except OSError:
                pass
        os.close(master_fd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
