"""Loopback sidecar session token (OSR-08).

When CLUTCH_SIDECAR_TOKEN is set (Tauri spawn), HTTP and WebSocket clients must
present the token. E2E sandboxes and plain pytest omit the env var.
"""

from __future__ import annotations

import os
import secrets


def auth_required() -> bool:
    """True when requests must carry the session token."""
    if os.environ.get("CLUTCH_E2E_SANDBOX"):
        return False
    return bool(os.environ.get("CLUTCH_SIDECAR_TOKEN", "").strip())


def expected_token() -> str | None:
    token = os.environ.get("CLUTCH_SIDECAR_TOKEN", "").strip()
    return token or None


def validate_token(token: str | None) -> bool:
    if not auth_required():
        return True
    expected = expected_token()
    if not expected or not token:
        return False
    return secrets.compare_digest(token, expected)


def validate_bearer(authorization: str | None) -> bool:
    if not auth_required():
        return True
    if not authorization or not authorization.startswith("Bearer "):
        return False
    return validate_token(authorization[7:].strip())


def public_http_paths() -> frozenset[str]:
    from src.release_hardening import api_docs_enabled

    paths = {"/health"}
    if api_docs_enabled():
        paths.update({"/openapi.json", "/docs", "/redoc"})
    return frozenset(paths)
