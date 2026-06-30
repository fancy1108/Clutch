#!/usr/bin/env python3
"""Offline demo for critical trajectory preservation during context compaction."""

import asyncio
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

ORCH_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ORCH_ROOT not in sys.path:
    sys.path.insert(0, ORCH_ROOT)

from src.compaction import _build_critical_context, _generate_llm_digest  # noqa: E402
from src.state import initial_state  # noqa: E402


async def main() -> int:
    state = initial_state("run_compaction_demo")
    state.update(status="awaiting_human", active_node_id="validate", changed_files=["src/app.py"])
    messages = [
        {"agent": "Supervisor", "text": "Human approval: Approved, continuing workflow."},
        {"agent": "Builder", "text": "Updated.",
         "outputEvents": [{"type": "tool", "content": "write src/app.py"}]},
    ]
    critical_context = _build_critical_context(state, messages)
    chat = lambda messages, model_id=None: {"content": "The model returned a general summary."}
    with patch("src.models_config.get_router", return_value=SimpleNamespace(chat=chat)):
        digest = await _generate_llm_digest(messages, critical_context=critical_context)
    required = ("[files_changed] src/app.py", "Human approval: Approved", "tool=write src/app.py")
    assert all(item in digest for item in required), "critical context was lost"
    print(digest)
    print("\nPASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
