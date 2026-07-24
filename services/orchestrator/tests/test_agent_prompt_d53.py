"""Tests for D53 layered agent prompt assembly + progressive skills disclosure."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent_prompt import (
    compose_agent_prompt_assembly,
    compose_agent_system_prompt,
)
from src.agent_skills import compose_skills_section
from src.skills_storage import save_registry


@pytest.fixture
def skills_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "skills"
    monkeypatch.setenv("CLUTCH_SKILLS_DIR", str(target))
    return target


def _clutch_agent(**extra: object) -> dict:
    base = {
        "id": "clutch-agent",
        "name": "Clutch Agent",
        "agentType": "clutch",
        "markdownDoc": "## Protocol\n- Prefer tools for file work.\n",
        "skills": [],
    }
    base.update(extra)
    return base


def test_assembly_layers_and_short_system_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    workspace_mod.add_workspace(str(tmp_path))

    assembly = compose_agent_prompt_assembly(
        _clutch_agent(),
        model_name="Agnes 2.0 Flash",
        model_api="agnes-2.0-flash",
        mcp_servers_bound=True,
        permission_mode="ask",
    )
    names = [layer.name for layer in assembly.layers]
    assert "system" in names
    assert "env" in names
    assert "protocol" in names
    system = next(layer for layer in assembly.layers if layer.name == "system")
    assert "Clutch Agent" in system.content
    assert len(system.content) < 1200
    summary = assembly.summary()
    assert summary["layers"]
    assert all("chars" in item for item in summary["layers"])


def test_workspace_rules_injected_and_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    ws_a = tmp_path / "a"
    ws_b = tmp_path / "b"
    ws_a.mkdir()
    ws_b.mkdir()
    (ws_a / "AGENTS.md").write_text("RULE_ALPHA_ONLY\n", encoding="utf-8")
    (ws_b / "AGENTS.md").write_text("RULE_BETA_ONLY\n", encoding="utf-8")

    workspace_mod.add_workspace(str(ws_a))
    prompt_a = compose_agent_system_prompt(
        _clutch_agent(),
        model_name="A",
        model_api="a",
        mcp_servers_bound=True,
    )
    assert "RULE_ALPHA_ONLY" in prompt_a
    assert "RULE_BETA_ONLY" not in prompt_a

    workspace_mod.add_workspace(str(ws_b))
    prompt_b = compose_agent_system_prompt(
        _clutch_agent(),
        model_name="A",
        model_api="a",
        mcp_servers_bound=True,
    )
    assert "RULE_BETA_ONLY" in prompt_b
    assert "RULE_ALPHA_ONLY" not in prompt_b


def test_skills_default_to_catalog_not_full_body(
    skills_data_dir: Path, tmp_path: Path
) -> None:
    mount = tmp_path / "my-skills"
    skill_dir = mount / "secure-review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "# Secure Review\n\nAlways check for secrets before commit.\n",
        encoding="utf-8",
    )
    save_registry(
        mounted_directories=[str(mount)],
        skills=[
            {
                "key": "my-skills/secure-review",
                "label": "Secure Review",
                "source": str(mount.resolve()),
                "desc": "Security checklist",
                "isActiveGlobally": True,
            }
        ],
    )

    catalog = compose_skills_section(["my-skills/secure-review"])
    assert "## Skills catalog" in catalog
    assert "Security checklist" in catalog
    assert "Always check for secrets" not in catalog

    full = compose_skills_section(
        ["my-skills/secure-review"], include_bodies=True
    )
    assert "Always check for secrets" in full


def test_plan_mode_reminder_is_ephemeral() -> None:
    ask = compose_agent_prompt_assembly(
        _clutch_agent(),
        model_name="A",
        model_api="a",
        mcp_servers_bound=False,
        permission_mode="ask",
        clutch_mcp_path=True,
    )
    plan = compose_agent_prompt_assembly(
        _clutch_agent(),
        model_name="A",
        model_api="a",
        mcp_servers_bound=False,
        permission_mode="plan",
        clutch_mcp_path=True,
    )
    assert not any(layer.name == "mode" for layer in ask.layers)
    mode = next(layer for layer in plan.layers if layer.name == "mode")
    assert "Plan mode" in mode.content or "read-only" in mode.content.lower()
    assert "Plan mode" not in ask.as_system_prompt()
