"""B-48: eval ablation gate + JSONL trajectory (no Chat UI)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent_eval import (
    ABLATION_ALL,
    assemble_eval_prompt,
    parse_ablation,
    persist_trajectory,
    snapshot_fingerprint,
    snapshot_layers,
)


def _isolate_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    workspace_mod.add_workspace(str(tmp_path))


def test_parse_ablation_all_named_and_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLUTCH_AGENT_EVAL_ABLATION", raising=False)
    assert parse_ablation() == frozenset()
    assert parse_ablation("") == frozenset()
    assert parse_ablation("all") == ABLATION_ALL
    assert parse_ablation("skills, memory") == frozenset({"skills", "memory"})
    monkeypatch.setenv("CLUTCH_AGENT_EVAL_ABLATION", "tools")
    assert parse_ablation() == frozenset({"tools"})
    with pytest.raises(ValueError, match="unknown"):
        parse_ablation("nope")


def test_ablation_drops_tools_and_changes_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_workspace(tmp_path, monkeypatch)
    full = assemble_eval_prompt()
    ablated = assemble_eval_prompt(ablation="tools")
    names_full = {layer.name for layer in full.layers}
    names_off = {layer.name for layer in ablated.layers}
    assert "tools" in names_full
    assert "tools" not in names_off
    assert "system" in names_off
    assert snapshot_fingerprint(snapshot_layers(full)) != snapshot_fingerprint(
        snapshot_layers(ablated)
    )


def test_persist_trajectory_jsonl_strips_secrets(tmp_path: Path) -> None:
    dest = tmp_path / "eval" / "trajectory.jsonl"
    persist_trajectory(
        {
            "name": "fingerprint",
            "ablation": ["tools"],
            "fingerprint": "abc",
            "passed": True,
            "api_key": "sk-secret",
        },
        path=dest,
    )
    persist_trajectory({"name": "second", "passed": False}, path=dest)
    lines = dest.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["name"] == "fingerprint"
    assert first["ablation"] == ["tools"]
    assert first["fingerprint"] == "abc"
    assert "api_key" not in first
    assert "ts" in first
    assert json.loads(lines[1])["name"] == "second"
