"""Vite React preview dev server process management."""

from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from src.design.session_store import (
    DesignError,
    read_manifest,
    session_dir,
    write_manifest,
)

logger = logging.getLogger(__name__)

# Global preview process register
preview_procs: dict[str, dict[str, Any]] = {}
preview_lock = threading.Lock()


def is_windows() -> bool:
    try:
        from src.design import service
        if hasattr(service, "_is_windows"):
            return service._is_windows()
    except ImportError:
        pass
    from src.design.session_store import is_windows as store_is_windows
    return store_is_windows()


# Resolve dependencies dynamically for test monkeypatching
try:
    from src.design import service
    sub = getattr(service, "subprocess", subprocess)
except (ImportError, AttributeError):
    sub = subprocess

try:
    from src.design import service
    sh = getattr(service, "shutil", shutil)
except (ImportError, AttributeError):
    sh = shutil

try:
    from src.design import service
    sock_mod = getattr(service, "socket", socket)
except (ImportError, AttributeError):
    sock_mod = socket


def free_port() -> int:
    try:
        from src.design import service
        if hasattr(service, "_free_port"):
            return service._free_port()
    except ImportError:
        pass
    with sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def resolve_command(name: str) -> str | None:
    resolved = sh.which(name)
    if resolved:
        return resolved
    if is_windows() and not name.lower().endswith(".cmd"):
        return sh.which(f"{name}.cmd") or sh.which(f"{name}.CMD")
    return None


def install_react_dependencies(react_dir: Path) -> None:
    attempts: list[str] = []
    found_command = False
    for name in ("pnpm", "npm"):
        command = resolve_command(name)
        if not command:
            attempts.append(f"{name}: not found")
            continue
        found_command = True
        args = [command, "install"]
        if name == "pnpm":
            args.append("--config.dangerously-allow-all-builds=true")
        try:
            result = sub.run(
                args,
                cwd=react_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                check=False,
            )
        except sub.TimeoutExpired as exc:
            raise DesignError(f"{name} install timed out after {int(exc.timeout)}s") from exc
        except OSError as exc:
            attempts.append(f"{name}: {exc}")
            continue
        if result.returncode == 0:
            return
        detail = (result.stderr or result.stdout or f"exit code {result.returncode}")[:400]
        attempts.append(f"{name}: {detail}")
    if not found_command:
        raise DesignError("pnpm or npm was not found on PATH")
    raise DesignError(f"Failed to install deps: {'; '.join(attempts)}")


def local_bin_command(react_dir: Path, name: str) -> str | None:
    bin_dir = react_dir / "node_modules" / ".bin"
    suffixes = (".cmd", ".exe", "") if is_windows() else ("",)
    for suffix in suffixes:
        candidate = bin_dir / f"{name}{suffix}"
        if candidate.is_file():
            return str(candidate)
    return None


def preview_command(react_dir: Path, port: int) -> list[str]:
    vite = local_bin_command(react_dir, "vite")
    if vite:
        return [vite, "--host", "127.0.0.1", "--port", str(port), "--strictPort"]
    npx = resolve_command("npx")
    if not npx:
        raise DesignError("npx was not found on PATH")
    return [npx, "vite", "--host", "127.0.0.1", "--port", str(port), "--strictPort"]


def stop_preview_process(proc: sub.Popen[Any], *, timeout: float = 5.0) -> None:
    if proc.poll() is not None:
        return
    if is_windows() and getattr(proc, "pid", None):
        sub.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
        try:
            proc.wait(timeout=timeout)
        except sub.TimeoutExpired:
            logger.warning("preview process did not exit after taskkill pid=%s", proc.pid)
            proc.kill()
            proc.wait(timeout=timeout)
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except sub.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout)


def start_preview(run_id: str) -> dict[str, Any]:
    sdir = session_dir(run_id)
    manifest = read_manifest(sdir)
    react_dir = sdir / "react"
    if not react_dir.is_dir():
        raise DesignError("Generate UI code before starting preview")
    with preview_lock:
        existing = preview_procs.get(run_id)
        if existing and existing.get("proc") and existing["proc"].poll() is None:
            return {"run_id": run_id, "url": existing["url"], "port": existing["port"], "status": "running"}
    if not (react_dir / "node_modules").is_dir():
        install_react_dependencies(react_dir)
    port = free_port()
    cmd = preview_command(react_dir, port)
    try:
        proc = sub.Popen(
            cmd,
            cwd=react_dir,
            stdout=sub.DEVNULL,
            stderr=sub.DEVNULL,
        )
    except OSError as exc:
        raise DesignError(f"Failed to start preview: {exc}") from exc
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        if proc.poll() is not None:
            raise DesignError("Preview process exited early")
        try:
            with sock_mod.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.3)
    else:
        stop_preview_process(proc)
        raise DesignError("Preview server did not become ready")
    with preview_lock:
        preview_procs[run_id] = {"proc": proc, "port": port, "url": url}
    manifest["preview_url"] = url
    write_manifest(sdir, manifest)
    return {"run_id": run_id, "url": url, "port": port, "status": "running"}


def stop_preview(run_id: str) -> dict[str, Any]:
    with preview_lock:
        entry = preview_procs.pop(run_id, None)
    if entry and entry.get("proc") and entry["proc"].poll() is None:
        stop_preview_process(entry["proc"])
    try:
        sdir = session_dir(run_id)
        manifest = read_manifest(sdir)
        manifest["preview_url"] = None
        write_manifest(sdir, manifest)
    except DesignError:
        pass
    return {"run_id": run_id, "status": "stopped"}
