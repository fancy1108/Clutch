"""D7 — project rules discovery + Skills on-demand + workspace mount hygiene."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent_prompt import compose_agent_prompt_assembly, compose_agent_system_prompt
from src.agent_skills import compose_skills_section, load_skill_body
from src.builtin_tools import execute_builtin_tool
from src.mcp_risk import is_risky_mcp_tool
from src.skills_storage import load_registry, save_registry, sync_workspace_skill_mounts


@pytest.fixture
def skills_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "skills-reg"
    monkeypatch.setenv("CLUTCH_SKILLS_DIR", str(target))
    return target


def _clutch_agent(**extra: object) -> dict:
    base = {
        "id": "clutch-agent",
        "name": "Clutch Agent",
        "agentType": "clutch",
        "markdownDoc": "## Protocol\n- Prefer tools.\n",
        "skills": [],
    }
    base.update(extra)
    return base


def _reset_workspaces(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None


def test_no_rules_workspace_omits_rules_layer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _reset_workspaces(tmp_path, monkeypatch)
    from src import workspace as workspace_mod

    bare = tmp_path / "bare"
    bare.mkdir()
    workspace_mod.add_workspace(str(bare))

    assembly = compose_agent_prompt_assembly(
        _clutch_agent(),
        model_name="A",
        model_api="a",
        mcp_servers_bound=True,
        permission_mode="ask",
    )
    assert not any(layer.name == "rules" for layer in assembly.layers)
    assert "Project rules" not in assembly.as_system_prompt()


def test_cursor_rules_injected_as_separate_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _reset_workspaces(tmp_path, monkeypatch)
    from src import workspace as workspace_mod

    ws = tmp_path / "ruled"
    rules = ws / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (ws / "AGENTS.md").write_text("ROOT_AGENTS_MARKER\n", encoding="utf-8")
    (rules / "no-secrets.mdc").write_text(
        "CURSOR_RULE_NO_SECRETS\nNever commit .env files.\n",
        encoding="utf-8",
    )
    workspace_mod.add_workspace(str(ws))

    prompt = compose_agent_system_prompt(
        _clutch_agent(),
        model_name="A",
        model_api="a",
        mcp_servers_bound=True,
    )
    assert "ROOT_AGENTS_MARKER" in prompt
    assert "CURSOR_RULE_NO_SECRETS" in prompt
    assert ".cursor/rules/no-secrets.mdc" in prompt


def test_read_skill_loads_body_on_demand(skills_data_dir: Path, tmp_path: Path) -> None:
    mount = tmp_path / "pack"
    skill_dir = mount / "secure-review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "# Secure Review\n\nAlways check for secrets before commit.\n",
        encoding="utf-8",
    )
    save_registry(
        mounted_directories=[str(mount.resolve())],
        skills=[
            {
                "key": "pack/secure-review",
                "label": "Secure Review",
                "source": str(mount.resolve()),
                "desc": "Security checklist",
                "isActiveGlobally": True,
            }
        ],
    )

    catalog = compose_skills_section(["pack/secure-review"])
    assert "Always check for secrets" not in catalog
    assert "read_skill" in catalog

    body = load_skill_body("pack/secure-review")
    assert "Always check for secrets" in body

    tool_out = execute_builtin_tool("read_skill", {"key": "pack/secure-review"})
    assert "Always check for secrets" in tool_out
    assert not is_risky_mcp_tool("read_skill")

    missing = execute_builtin_tool("read_skill", {"key": "pack/missing"})
    assert missing.startswith("Error executing tool:")


def test_sync_prunes_other_workspace_skill_mounts(
    skills_data_dir: Path, tmp_path: Path
) -> None:
    ws_a = tmp_path / "proj-a"
    ws_b = tmp_path / "proj-b"
    skill_a = ws_a / "skills" / "alpha"
    skill_b = ws_b / "skills" / "beta"
    skill_a.mkdir(parents=True)
    skill_b.mkdir(parents=True)
    (skill_a / "SKILL.md").write_text("# Alpha\n\nALPHA_BODY\n", encoding="utf-8")
    (skill_b / "SKILL.md").write_text("# Beta\n\nBETA_BODY\n", encoding="utf-8")

    mount_a = str((ws_a / "skills").resolve())
    mount_b = str((ws_b / "skills").resolve())
    save_registry(
        mounted_directories=[mount_a, mount_b],
        skills=[
            {
                "key": "skills/alpha",
                "label": "Alpha",
                "source": mount_a,
                "desc": "A",
                "isActiveGlobally": False,
            },
            {
                "key": "skills/beta",
                "label": "Beta",
                "source": mount_b,
                "desc": "B",
                "isActiveGlobally": False,
            },
        ],
        auto_workspace_mounts=[mount_a, mount_b],
    )

    result = sync_workspace_skill_mounts(workspace_path=str(ws_b))
    stored = load_registry()
    assert mount_b in stored["mounted_directories"]
    assert mount_a not in stored["mounted_directories"]
    assert mount_a in result["removed"]
    assert all(s.get("source") != mount_a for s in stored["skills"])
    assert mount_b in stored["auto_workspace_mounts"]


def test_sync_preserves_manual_search_paths(
    skills_data_dir: Path, tmp_path: Path
) -> None:
    """Skills Registry Mount Root paths must survive workspace switch (D7)."""
    ws_a = tmp_path / "proj-a"
    ws_b = tmp_path / "proj-b"
    (ws_a / "skills" / "a").mkdir(parents=True)
    (ws_b / "skills" / "b").mkdir(parents=True)
    ((ws_a / "skills" / "a") / "SKILL.md").write_text("# A\n", encoding="utf-8")
    ((ws_b / "skills" / "b") / "SKILL.md").write_text("# B\n", encoding="utf-8")

    custom = tmp_path / "bundled_skills" / "pack"
    custom.mkdir(parents=True)
    (custom / "SKILL.md").write_text("# Pack\n\nCUSTOM_PACK\n", encoding="utf-8")
    # Also a *skills*-named folder the user explicitly mounted (not auto).
    foreign = tmp_path / "other-repo" / "skills" / "x"
    foreign.mkdir(parents=True)
    (foreign / "SKILL.md").write_text("# X\n", encoding="utf-8")

    mount_a = str((ws_a / "skills").resolve())
    mount_b = str((ws_b / "skills").resolve())
    custom_root = str((tmp_path / "bundled_skills").resolve())
    foreign_root = str((tmp_path / "other-repo" / "skills").resolve())

    save_registry(
        mounted_directories=[mount_a, custom_root, foreign_root],
        skills=[],
        auto_workspace_mounts=[mount_a],
    )

    sync_workspace_skill_mounts(workspace_path=str(ws_b))
    stored = load_registry()
    assert custom_root in stored["mounted_directories"]
    assert foreign_root in stored["mounted_directories"]
    assert mount_a not in stored["mounted_directories"]
    assert mount_b in stored["mounted_directories"]
    assert mount_b in stored["auto_workspace_mounts"]
    assert custom_root not in stored["auto_workspace_mounts"]
    assert foreign_root not in stored["auto_workspace_mounts"]


def test_nested_agents_md_chain_deeper_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Grok-style: authorize a package path → root→cwd chain; deeper last."""
    _reset_workspaces(tmp_path, monkeypatch)
    from src import workspace as workspace_mod

    repo = tmp_path / "mono"
    pkg = repo / "packages" / "frontend"
    pkg.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "AGENTS.md").write_text("ROOT_RULE\n", encoding="utf-8")
    (pkg / "AGENTS.md").write_text("PKG_RULE_DEEPER\n", encoding="utf-8")
    (pkg / ".claude" / "rules").mkdir(parents=True)
    (pkg / ".claude" / "rules" / "ui.md").write_text("CLAUDE_RULES_UI\n", encoding="utf-8")

    workspace_mod.add_workspace(str(pkg))
    prompt = compose_agent_system_prompt(
        _clutch_agent(),
        model_name="A",
        model_api="a",
        mcp_servers_bound=True,
    )
    assert "ROOT_RULE" in prompt
    assert "PKG_RULE_DEEPER" in prompt
    assert "CLAUDE_RULES_UI" in prompt
    # Deeper file appears after root in the assembled rules layer
    assert prompt.index("ROOT_RULE") < prompt.index("PKG_RULE_DEEPER")


def test_open_catalog_includes_enabled_without_agent_bind(
    skills_data_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.agent_skills import resolve_effective_skill_keys

    _reset_workspaces(tmp_path, monkeypatch)
    from src import workspace as workspace_mod

    ws = tmp_path / "proj"
    skill = ws / ".grok" / "skills" / "commit"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Commit\n\nMake commits.\n", encoding="utf-8")
    workspace_mod.add_workspace(str(ws))

    mount = str((ws / ".grok" / "skills").resolve())
    save_registry(
        mounted_directories=[mount],
        skills=[
            {
                "key": "skills/commit",
                "label": "Commit",
                "source": mount,
                "desc": "Make commits",
                "isActiveGlobally": True,
            }
        ],
        auto_workspace_mounts=[mount],
    )
    keys = resolve_effective_skill_keys(_clutch_agent(skills=[]))
    assert "skills/commit" in keys

    assembly = compose_agent_prompt_assembly(
        _clutch_agent(skills=[]),
        model_name="A",
        model_api="a",
        mcp_servers_bound=True,
        permission_mode="ask",
    )
    skills_layer = next(layer for layer in assembly.layers if layer.name == "skills")
    assert "skills/commit" in skills_layer.content


def test_skill_name_dedupe_project_beats_global(
    skills_data_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.agent_skills import resolve_effective_skill_keys

    _reset_workspaces(tmp_path, monkeypatch)
    from src import workspace as workspace_mod

    ws = tmp_path / "proj"
    ws.mkdir()
    workspace_mod.add_workspace(str(ws))

    global_mount = tmp_path / "global-skills"
    (global_mount / "commit").mkdir(parents=True)
    (global_mount / "commit" / "SKILL.md").write_text("# G\n", encoding="utf-8")
    proj_mount = ws / ".claude" / "skills"
    (proj_mount / "commit").mkdir(parents=True)
    (proj_mount / "commit" / "SKILL.md").write_text("# P\n", encoding="utf-8")

    g_src = str(global_mount.resolve())
    p_src = str(proj_mount.resolve())
    save_registry(
        mounted_directories=[g_src, p_src],
        skills=[
            {
                "key": "global-skills/commit",
                "label": "G",
                "source": g_src,
                "desc": "global",
                "isActiveGlobally": True,
            },
            {
                "key": "skills/commit",
                "label": "P",
                "source": p_src,
                "desc": "project",
                "isActiveGlobally": True,
            },
        ],
        auto_workspace_mounts=[p_src],
    )
    monkeypatch.setattr(
        "src.agent_skills.discover_user_skill_directories",
        lambda: [g_src],
    )
    keys = resolve_effective_skill_keys(_clutch_agent())
    assert keys == ["skills/commit"]
