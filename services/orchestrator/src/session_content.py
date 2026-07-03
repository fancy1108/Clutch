"""Whether a run has user-visible history worth persisting in session list."""

from __future__ import annotations

from typing import Any


def session_has_persistable_content(state: dict[str, Any] | None) -> bool:
    """True when the session has chat messages or terminal dispatch records."""
    if not state:
        return False
    messages = state.get("messages")
    if isinstance(messages, list) and len(messages) > 0:
        return True
    dispatch_log = state.get("dispatch_log")
    if isinstance(dispatch_log, list) and len(dispatch_log) > 0:
        return True
    return False
