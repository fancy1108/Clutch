"""D35 — capability pack import and uninstall."""

from __future__ import annotations

import json
from pathlib import Path

from src.capability_pack import import_pack, list_installed_packs, uninstall_pack
from src.skills_storage import load_registry


def test_import_dir_registers_skills_and_uninstall(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "storage"))
    pack_src = tmp_path / "demo-pack"
    skill_root = pack_src / "skills" / "demo-skill"
    skill_root.mkdir(parents=True)
    (skill_root / "SKILL.md").write_text("# Demo\nA demo skill.", encoding="utf-8")
    (pack_src / "hooks.json").write_text(
        json.dumps({"PreToolUse": [{"tool": "grep", "action": "deny", "reason": "no grep"}]}),
        encoding="utf-8",
    )
    (pack_src / "pack.json").write_text(json.dumps({"name": "Demo Pack"}), encoding="utf-8")

    record = import_pack(str(pack_src))
    pack_id = record["id"]
    assert pack_id.startswith("pack_")
    assert list_installed_packs()
    assert record.get("skills_mount")
    assert Path(str(record["skills_mount"])).is_dir()

    uninstall_pack(pack_id)
    assert not any(p.get("id") == pack_id for p in list_installed_packs())
