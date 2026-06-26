"""Lightweight synchronous MCP Client implementing JSON-RPC 2.0 over stdio (P4)."""

from __future__ import annotations

import json
import os
import select
import shlex
import subprocess
from typing import Any


class McpClient:
    def __init__(self, name: str, endpoint: str, env: dict[str, str] | None = None):
        self.name = name
        self.endpoint = endpoint
        self.env = env
        self.proc: subprocess.Popen | None = None
        self._next_id = 1

    def start(self) -> bool:
        args = shlex.split(self.endpoint)
        env_vars = os.environ.copy()
        env_vars["NPM_CONFIG_UPDATE_NOTIFIER"] = "false"
        env_vars["NPM_CONFIG_AUDIT"] = "false"
        env_vars["NPM_CONFIG_FUND"] = "false"
        env_vars["NO_UPDATE_NOTIFIER"] = "1"
        if self.env:
            env_vars.update(self.env)
        try:
            self.proc = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env_vars,
                text=True,
                bufsize=1,
            )
            # Handshake
            self.call(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "clutch-client", "version": "1.0.0"},
                },
                timeout=5.0,
            )
            self.notify("notifications/initialized")
            return True
        except Exception:
            self.close()
            return False

    def _read_response(self, req_id: int, timeout: float = 5.0) -> dict[str, Any]:
        import time
        deadline = time.time() + timeout
        while True:
            if not self.proc or not self.proc.stdout:
                raise RuntimeError("Process terminated")
            remaining = deadline - time.time()
            if remaining <= 0:
                raise TimeoutError("Timeout waiting for MCP response")
            r, _, _ = select.select([self.proc.stdout], [], [], remaining)
            if not r:
                raise TimeoutError("Timeout waiting for MCP response")
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("EOF reached")
            try:
                data = json.loads(line.strip())
                if data.get("id") == req_id:
                    return data
            except Exception:
                continue

    def call(
        self, method: str, params: dict[str, Any] | None = None, timeout: float = 5.0
    ) -> dict[str, Any]:
        if not self.proc or not self.proc.stdin:
            raise RuntimeError("Client not connected")
        req_id = self._next_id
        self._next_id += 1
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        try:
            self.proc.stdin.write(json.dumps(req) + "\n")
            self.proc.stdin.flush()
            res = self._read_response(req_id, timeout=timeout)
            if "error" in res:
                raise RuntimeError(f"MCP error: {res['error']}")
            return res.get("result", {})
        except Exception as e:
            raise RuntimeError(f"MCP call failed: {e}") from e

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        if not self.proc or not self.proc.stdin:
            raise RuntimeError("Client not connected")
        notif = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        self.proc.stdin.write(json.dumps(notif) + "\n")
        self.proc.stdin.flush()

    def list_tools(self) -> list[dict[str, Any]]:
        try:
            res = self.call("tools/list", timeout=5.0)
            return res.get("tools") or []
        except Exception:
            return []

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.call("tools/call", {"name": name, "arguments": arguments}, timeout=30.0)

    def close(self) -> None:
        if self.proc:
            try:
                if self.proc.stdin:
                    req = {"jsonrpc": "2.0", "id": self._next_id, "method": "shutdown"}
                    self.proc.stdin.write(json.dumps(req) + "\n")
                    self.proc.stdin.flush()
                    notif = {"jsonrpc": "2.0", "method": "notifications/exit"}
                    self.proc.stdin.write(json.dumps(notif) + "\n")
                    self.proc.stdin.flush()
            except Exception:
                pass
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
