#!/usr/bin/env python3
"""Cross-platform Tauri dev launcher.

Starts Vite when needed, waits for it on :3000, then runs Tauri without the
dev-server wait because this script owns the readiness check.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
import time
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DESKTOP = REPO_ROOT / "apps" / "desktop"
VITE_URL = "http://127.0.0.1:3000/"
VITE_LOG = REPO_ROOT / ".clutch-vite-dev.log"
VITE_PID_FILE = REPO_ROOT / ".clutch-vite.pid"


def candidate_uv_paths() -> list[Path | None]:
    home = Path.home()
    user_scripts = sysconfig.get_path("scripts", scheme="nt_user") if os.name == "nt" else None
    current_scripts = sysconfig.get_path("scripts")
    return [
        Path(os.environ["CLUTCH_UV_BIN"]) if os.environ.get("CLUTCH_UV_BIN") else None,
        Path(os.environ["UV_EXE"]) if os.environ.get("UV_EXE") else None,
        Path(os.environ["UV"]) if os.environ.get("UV") else None,
        Path(user_scripts) / "uv.exe" if user_scripts else None,
        Path(current_scripts) / "uv.exe" if current_scripts else None,
        home / ".local" / "bin" / "uv.exe",
        home / ".cargo" / "bin" / "uv.exe",
        home / "AppData" / "Roaming" / "uv" / "uv.exe",
    ]


def command(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        found = shutil.which(f"{name}.cmd")
        if found:
            return found
    return name


def resolve_uv() -> str:
    found = command("uv")
    if found != "uv":
        return found
    if os.name == "nt":
        for path in candidate_uv_paths():
            if path and path.is_file():
                return str(path)
    return found


def vite_ready() -> bool:
    try:
        with urllib.request.urlopen(VITE_URL, timeout=1.0) as response:
            return 200 <= response.status < 500
    except (OSError, urllib.error.URLError):
        return False


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_pid() -> int | None:
    try:
        return int(VITE_PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def start_vite() -> subprocess.Popen[bytes]:
    VITE_LOG.parent.mkdir(parents=True, exist_ok=True)
    log = VITE_LOG.open("ab")
    creationflags = 0
    start_new_session = True
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        start_new_session = False
    proc = subprocess.Popen(
        [command("corepack"), "pnpm", "--filter", "@clutch/desktop", "dev"],
        cwd=REPO_ROOT,
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        start_new_session=start_new_session,
    )
    VITE_PID_FILE.write_text(f"{proc.pid}\n", encoding="utf-8")
    return proc


def wait_for_vite(proc: subprocess.Popen[bytes] | None) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if vite_ready():
            return
        if proc is not None and proc.poll() is not None:
            tail = ""
            try:
                tail = "".join(VITE_LOG.read_text(encoding="utf-8", errors="replace").splitlines(True)[-30:])
            except OSError:
                pass
            raise RuntimeError(f"Vite exited before {VITE_URL} became ready.\n{tail}")
        time.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for Vite on {VITE_URL}. See {VITE_LOG}.")


def main() -> int:
    proc: subprocess.Popen[bytes] | None = None
    if vite_ready():
        print(f"[tauri-dev] Reusing existing Vite on {VITE_URL}")
    else:
        existing_pid = read_pid()
        if existing_pid and process_alive(existing_pid):
            print(f"[tauri-dev] Waiting for existing Vite process {existing_pid}")
        else:
            proc = start_vite()
        wait_for_vite(proc)
        pid = read_pid()
        print(f"[tauri-dev] Vite ready at {VITE_URL} (pid {pid}, log {VITE_LOG})")

    env = os.environ.copy()
    env.setdefault("CLUTCH_RUNTIME_MODE", "hybrid")
    env["CLUTCH_UV_BIN"] = resolve_uv()
    return subprocess.call(
        [command("corepack"), "pnpm", "tauri", "dev", "--no-dev-server-wait"],
        cwd=DESKTOP,
        env=env,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
