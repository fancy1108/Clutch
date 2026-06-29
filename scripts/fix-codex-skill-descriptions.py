#!/usr/bin/env python3
"""Add missing `description` frontmatter to Codex-compatible SKILL.md files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NAME_RE = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
_SCENARIO_RE = re.compile(
    r"###\s*🎯\s*适用场景.*?\n\*+\s*(.+?)(?:\n\*|\n#|\Z)",
    re.DOTALL,
)
_WHEN_TO_USE_RE = re.compile(
    r"##\s+When to Use.*?\n+(.+?)(?:\n##|\Z)",
    re.DOTALL | re.IGNORECASE,
)


def _has_description(frontmatter: str) -> bool:
    return bool(re.search(r"^description:\s*.+", frontmatter, re.MULTILINE))


def _derive_description(name: str, body: str) -> str:
    scenario = _SCENARIO_RE.search(body)
    if scenario:
        text = re.sub(r"\s+", " ", scenario.group(1).strip())
        if text:
            return text[:240]

    when = _WHEN_TO_USE_RE.search(body)
    if when:
        lines = [
            re.sub(r"^[-*]\s*", "", ln.strip())
            for ln in when.group(1).splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if lines:
            return lines[0][:240]

    for block in body.split("\n\n"):
        clean = block.strip()
        if not clean or clean.startswith("#") or clean.startswith("```"):
            continue
        text = re.sub(r"[*`#\[\]]", "", clean)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) >= 24:
            return text[:240]

    slug = name.replace(":", " ").replace("-", " ").strip()
    return f"Use the {slug} agent skill for related tasks in this workspace."


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def patch_skill(path: Path, *, dry_run: bool) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return False
    frontmatter = match.group(1)
    if _has_description(frontmatter):
        return False

    name_match = _NAME_RE.search(frontmatter)
    name = name_match.group(1).strip().strip("'\"") if name_match else path.parent.name
    body = text[match.end() :]
    description = _derive_description(name, body)
    desc_line = f"description: {_yaml_quote(description)}"

    if name_match:
        insert_at = name_match.end()
        new_frontmatter = frontmatter[:insert_at] + f"\n{desc_line}" + frontmatter[insert_at:]
    else:
        new_frontmatter = f"name: {_yaml_quote(name)}\n{desc_line}\n{frontmatter}"

    new_text = f"---\n{new_frontmatter}\n---\n{body}"
    if dry_run:
        print(f"would patch: {path}")
        return True
    path.write_text(new_text, encoding="utf-8")
    print(f"patched: {path}")
    return True


def resolve_default_root() -> Path:
    link = Path.home() / ".claude" / "skills"
    if link.is_symlink():
        return link.resolve()
    return Path("/Users/fancy/obsidian/PARA/3_Resources/Skills/Sources")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=str(resolve_default_root()),
        help="Skills root directory (default: ~/.claude/skills target)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"skills root not found: {root}", file=sys.stderr)
        return 1

    patched = 0
    for skill in sorted(root.rglob("SKILL.md")):
        if patch_skill(skill, dry_run=args.dry_run):
            patched += 1

    print(f"{'would patch' if args.dry_run else 'patched'} {patched} skill(s) under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
