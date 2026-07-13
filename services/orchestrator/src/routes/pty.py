"""HTTP API for PTY/terminal-related diagnostics."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter

router = APIRouter(tags=["pty"])


@router.get("/api/pty/status")
async def get_pty_status() -> dict[str, Any]:
    """Return status of live PTY channels."""
    from src.interactive_pty_runtime import interactive_pty_manager
    return {"status": "ok", "active_sessions_count": len(interactive_pty_manager._sessions)}
