"""DEV vs PROD storage directory isolation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from src import storage_helper


def test_dev_uses_clutch_dev_subdir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLUTCH_STORAGE_DIR", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    path = storage_helper.get_storage_dir()
    assert path.name == "clutch_dev"


def test_prod_uses_clutch_subdir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLUTCH_STORAGE_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    path = storage_helper.get_storage_dir()
    assert path.name == "clutch"


def test_storage_dir_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "custom-store"))
    path = storage_helper.get_storage_dir()
    assert path == (tmp_path / "custom-store").resolve()
