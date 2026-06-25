"""Tests for agent skill resolution (P2-14)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent_skills import compose_skills_section
from src.skills_storage import save_registry


@pytest.fixture
def skills_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "skills"
    monkeypatch.setenv("CLUTCH_SKILLS_DIR", str(target))
    return target


def test_compose_skills_section_includes_linked_skill_md(
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

    section = compose_skills_section(["my-skills/secure-review"])
    assert "## Attached Skills" in section
    assert "Always check for secrets" in section


def test_compose_skills_section_ignores_unknown_keys(skills_data_dir: Path) -> None:
    save_registry(mounted_directories=[], skills=[])
    assert compose_skills_section(["missing/key"]) == ""
