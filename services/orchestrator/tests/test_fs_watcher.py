"""FS watcher debounce tests — M3-04."""

from __future__ import annotations

import time
from pathlib import Path

from src.fs_watcher import DebouncedFsWatcher


def test_debounced_callback_fires_once(tmp_path: Path) -> None:
    fired: list[Path] = []
    watcher = DebouncedFsWatcher(debounce_seconds=0.15)

    target = tmp_path / "docs" / "verify.md"
    watcher.schedule(target, lambda path: fired.append(path))
    watcher.schedule(target, lambda path: fired.append(path))

    time.sleep(0.35)
    assert len(fired) == 1
    assert fired[0] == target
