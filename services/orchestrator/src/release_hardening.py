"""Release hardening gates (OSR-16)."""

from __future__ import annotations

import os
import sys


def is_frozen_release() -> bool:
    return bool(getattr(sys, "frozen", False))


def _debug_opt_in() -> bool:
    return os.environ.get("CLUTCH_DEBUG_API", "").strip() == "1"


def debug_api_enabled() -> bool:
    if _debug_opt_in():
        return True
    return not is_frozen_release()


def api_docs_enabled() -> bool:
    return debug_api_enabled()
