"""MCP Client: JSON-RPC 2.0 over stdio or Streamable HTTP."""

from __future__ import annotations

import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

_HTTP_401 = "HTTP 401 — add Authorization in Env, or retry Test to open a browser login"


def _is_http_endpoint(endpoint: str) -> bool:
    return endpoint.strip().lower().startswith(("http://", "https://"))


def _oauth_proxy_cmd(url: str) -> str:
    return f"npx -y mcp-remote {url.strip()} --transport http-first --auth-timeout 90"


def oauth_proxy_eligible(endpoint: str, env: dict[str, str] | None = None) -> bool:
    """HTTPS remotes with no API key can fall back to mcp-remote (browser OAuth)."""
    ep = endpoint.strip()
    if not ep.lower().startswith("https://"):
        return False
    host = (urlparse(ep).hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return False
    if not env:
        return True
    for key in env:
        low = key.lower()
        if low in {"authorization", "x-api-key", "figma_api_key"} or low.startswith("header_"):
            return False
    return True


def _is_auth_failure(message: str | None) -> bool:
    blob = (message or "").lower()
    return "401" in blob or "unauthorized" in blob


def _uses_oauth_proxy(args: list[str], endpoint: str) -> bool:
    return "mcp-remote" in f"{' '.join(args)} {endpoint}".lower()


_LOGIN_URL = re.compile(r"https://[^\s<>\"']+", re.I)
_SKIP_HOSTS = (
    "npmjs.",
    "nodejs.org",
    "registry.npmjs",
    "developers.figma.com",
    "github.com",
)
login_url_hook: Callable[[str], None] | None = None
_last_log_line = ""


def extract_login_url(line: str, *, previous: str = "") -> str | None:
    """Pick the OAuth authorize URL; ignore docs / package registry links."""
    follow = "authorize this client by visiting" in (previous or "").lower()
    for match in _LOGIN_URL.finditer(line or ""):
        url = match.group(0).rstrip(".,);")
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        query = (parsed.query or "").lower()
        if parsed.scheme != "https" or any(skip in host for skip in _SKIP_HOSTS):
            continue
        if path.rstrip("/") == "/mcp":
            continue
        oauthish = (
            "client_id=" in query
            or "response_type=" in query
            or "/oauth" in path
            or "/authorize" in path
            or "/login" in path
        )
        if follow or oauthish:
            return url
    return None


def _note_login_url(line: str) -> None:
    global _last_log_line
    url = extract_login_url(line, previous=_last_log_line)
    _last_log_line = line
    if not url:
        return
    hook = login_url_hook
    if hook:
        hook(url)
    _open_in_browser(url)


def _open_in_browser(url: str) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.Popen(
                ["/usr/bin/open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        elif sys.platform == "win32":
            os.startfile(url)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
    except Exception:
        return


def _note_login_url(line: str) -> None:
    url = extract_login_url(line)
    if not url:
        return
    hook = login_url_hook
    if hook:
        hook(url)
    _open_in_browser(url)


def _with_node_path(env: dict[str, str]) -> dict[str, str]:
    home = os.path.expanduser("~")
    extras = ["/opt/homebrew/bin", "/usr/local/bin", os.path.join(home, ".local", "bin")]
    nvm_nodes = os.path.join(home, ".nvm", "versions", "node")
    if os.path.isdir(nvm_nodes):
        extras.extend(
            os.path.join(nvm_nodes, name, "bin")
            for name in os.listdir(nvm_nodes)
            if os.path.isdir(os.path.join(nvm_nodes, name, "bin"))
        )
    env["PATH"] = os.pathsep.join(extras) + os.pathsep + env.get("PATH", "")
    return env


def _stdio_handshake_timeout(args: list[str], endpoint: str) -> float:
    blob = f"{' '.join(args)} {endpoint}".lower()
    if "mcp-remote" in blob:
        return 120.0
    return 5.0


def _http_headers(env: dict[str, str] | None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-03-26",
    }
    if not env:
        return headers
    for key, val in env.items():
        low = key.lower()
        if low in {"authorization", "x-api-key"}:
            headers["Authorization" if low == "authorization" else "X-API-Key"] = val
        elif low == "figma_api_key":
            headers.setdefault("Authorization", f"Bearer {val}")
        elif low.startswith("header_"):
            headers[key[7:].replace("_", "-")] = val
    return headers


def _parse_mcp_http_body(resp: Any) -> dict[str, Any]:
    ctype = (resp.headers.get("content-type") or "").lower()
    if "text/event-stream" in ctype:
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                payload = line[5:].strip()
                if payload and payload != "[DONE]":
                    return json.loads(payload)
        raise RuntimeError("empty SSE body")
    data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError("MCP HTTP response is not a JSON object")
    return data


class McpClient:
    def __init__(self, name: str, endpoint: str, env: dict[str, str] | None = None):
        self.name = name
        self.endpoint = endpoint.strip()
        self.env = env
        self.proc: subprocess.Popen | None = None
        self._http: Any = None
        self._headers: dict[str, str] = {}
        self._next_id = 1
        self._responses: queue.Queue[dict[str, Any]] = queue.Queue()
        self._reader_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._stderr_lines: list[str] = []
        self.last_error: str | None = None

    def start(self, *, oauth_proxy: bool = False) -> bool:
        self.last_error = None
        original = self.endpoint
        if _is_http_endpoint(original):
            if self._start_http():
                return True
            if (
                oauth_proxy
                and oauth_proxy_eligible(original, self.env)
                and _is_auth_failure(self.last_error)
            ):
                self.close()
                self.endpoint = _oauth_proxy_cmd(original)
            else:
                return False
        args = shlex.split(self.endpoint, posix=os.name != "nt")
        if os.name == "nt":
            args = [part.strip('"') for part in args]
        if not args:
            self.last_error = "Empty MCP endpoint / command"
            return False
        env_vars = os.environ.copy()
        env_vars["NPM_CONFIG_UPDATE_NOTIFIER"] = "false"
        env_vars["NPM_CONFIG_AUDIT"] = "false"
        env_vars["NPM_CONFIG_FUND"] = "false"
        env_vars["NO_UPDATE_NOTIFIER"] = "1"
        env_vars = _with_node_path(env_vars)
        if self.env:
            env_vars.update(self.env)
        if args and args[0] == "npx":
            found = shutil.which("npx", path=env_vars.get("PATH"))
            if found:
                args[0] = found
        try:
            oauth = _uses_oauth_proxy(args, self.endpoint)
            self.proc = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE if oauth else subprocess.DEVNULL,
                env=env_vars,
                text=True,
                bufsize=1,
            )
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()
            if oauth:
                self._stderr_thread = threading.Thread(target=self._stderr_loop, daemon=True)
                self._stderr_thread.start()
            self.call(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "clutch-client", "version": "1.0.0"},
                },
                timeout=_stdio_handshake_timeout(args, self.endpoint),
            )
            self.notify("notifications/initialized")
            return True
        except FileNotFoundError as exc:
            self.last_error = f"Command not found: {exc.filename or args[0]}"
            self.close()
            return False
        except Exception as exc:
            msg = str(exc).strip() or exc.__class__.__name__
            mapped = self._proxy_exit_error()
            if mapped:
                msg = mapped
            elif _uses_oauth_proxy(args, self.endpoint) and "timeout" in msg.lower():
                msg = (
                    "Browser login did not finish in time. "
                    "Allow access in the browser, then click Test connection again."
                )
            self.last_error = msg
            self.close()
            return False

    def _start_http(self) -> bool:
        try:
            import httpx
        except ImportError:
            self.last_error = "httpx is required for HTTP MCP"
            return False
        self._headers = _http_headers(self.env)
        self._http = httpx.Client(timeout=30.0, follow_redirects=True)
        try:
            self.call(
                "initialize",
                {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "clutch-client", "version": "1.0.0"},
                },
                timeout=15.0,
            )
            self.notify("notifications/initialized")
            return True
        except Exception as exc:
            self.last_error = str(exc).strip() or exc.__class__.__name__
            self.close()
            return False

    def _proxy_exit_error(self) -> str | None:
        blob = "\n".join(self._stderr_lines[-16:])
        if "403" in blob or "Forbidden" in blob:
            return (
                "Figma blocked OAuth client registration (HTTP 403). "
                "Remote Figma MCP only accepts listed apps (Claude Code, Cursor, VS Code, Codex). "
                "Clutch is not on that list, so no login page opens. "
                "Enable Figma desktop MCP (127.0.0.1:3845) if available, "
                "or use Figma from Claude Code."
            )
        if "Fatal error" in blob:
            return blob.strip()[-400:] or None
        return None

    def _stderr_loop(self) -> None:
        if not self.proc or not self.proc.stderr:
            return
        for line in self.proc.stderr:
            self._stderr_lines.append(line.rstrip())
            if len(self._stderr_lines) > 40:
                self._stderr_lines.pop(0)
            _note_login_url(line)

    def _read_loop(self) -> None:
        if not self.proc or not self.proc.stdout:
            return
        for line in self.proc.stdout:
            _note_login_url(line)
            try:
                self._responses.put(json.loads(line.strip()))
            except (json.JSONDecodeError, TypeError):
                continue

    def _read_response(self, req_id: int, timeout: float = 5.0) -> dict[str, Any]:
        import time
        deadline = time.monotonic() + timeout
        while True:
            if not self.proc:
                raise RuntimeError("Process terminated")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Timeout waiting for MCP response")
            if self.proc.poll() is not None:
                time.sleep(0.2)
                mapped = self._proxy_exit_error()
                raise RuntimeError(mapped or "MCP process exited")
            try:
                data = self._responses.get(timeout=min(remaining, 0.5))
            except queue.Empty:
                continue
            if data.get("id") == req_id:
                return data
            if self.proc.poll() is not None and self._responses.empty():
                raise TimeoutError("Timeout waiting for MCP response")

    def call(
        self, method: str, params: dict[str, Any] | None = None, timeout: float = 5.0
    ) -> dict[str, Any]:
        if self._http is not None:
            return self._http_call(method, params, timeout)
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

    def _http_call(
        self, method: str, params: dict[str, Any] | None, timeout: float
    ) -> dict[str, Any]:
        req_id = self._next_id
        self._next_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        resp = self._http.post(
            self.endpoint, json=payload, headers=self._headers, timeout=timeout
        )
        session = resp.headers.get("mcp-session-id")
        if session:
            self._headers["Mcp-Session-Id"] = session
        if resp.status_code == 401:
            raise RuntimeError(_HTTP_401)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:240]}")
        data = _parse_mcp_http_body(resp)
        if data.get("id") == req_id and "error" in data:
            raise RuntimeError(f"MCP error: {data['error']}")
        result = data.get("result")
        return result if isinstance(result, dict) else {}

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        if self._http is not None:
            payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
            resp = self._http.post(
                self.endpoint, json=payload, headers=self._headers, timeout=10.0
            )
            session = resp.headers.get("mcp-session-id")
            if session:
                self._headers["Mcp-Session-Id"] = session
            return
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

    def list_resources(self) -> list[dict[str, Any]]:
        """D43 — MCP resources/list (empty if server has no resources capability)."""
        try:
            res = self.call("resources/list", timeout=5.0)
            return res.get("resources") or []
        except Exception:
            return []

    def read_resource(self, uri: str) -> dict[str, Any]:
        """D43 — MCP resources/read for a single URI."""
        return self.call("resources/read", {"uri": uri}, timeout=15.0)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.call("tools/call", {"name": name, "arguments": arguments}, timeout=30.0)

    def close(self) -> None:
        if self._http is not None:
            try:
                self._http.close()
            except Exception:
                pass
            self._http = None
            return
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
            self._reader_thread = None
