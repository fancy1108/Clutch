"""Debounced filesystem watcher for workspace changes (M3-04)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path


class DebouncedFsWatcher:
    def __init__(self, debounce_seconds: float = 1.0) -> None:
        self._debounce_seconds = debounce_seconds
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def schedule(self, path: Path, callback: Callable[[Path], None]) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()

            def fire() -> None:
                callback(path)

            self._timer = threading.Timer(self._debounce_seconds, fire)
            self._timer.daemon = True
            self._timer.start()
