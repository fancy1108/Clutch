"""B-37: force test-suite + mechanical artifact review before claiming passed."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

HARNESS_STEP_IDS = frozenset({"harness_tests", "harness_artifacts"})
_TEST_TIMEOUT_S = 45


def _timeout_s() -> int:
    raw = os.environ.get("CLUTCH_VERIFY_TEST_TIMEOUT", str(_TEST_TIMEOUT_S))
    try:
        return max(5, int(raw))
    except ValueError:
        return _TEST_TIMEOUT_S


def detect_test_command(root: Path) -> list[str] | None:
    """Return a command if this workspace looks like it has a test suite."""
    if (root / "pytest.ini").exists() or (root / "tests").is_dir():
        pytest_bin = shutil.which("pytest")
        if pytest_bin:
            return [pytest_bin, "-q", "--tb=line", "-x"]
        return ["python", "-m", "pytest", "-q", "--tb=line", "-x"]
    pkg = root / "package.json"
    if pkg.is_file():
        text = pkg.read_text(encoding="utf-8", errors="replace")
        if '"test"' in text:
            npm = shutil.which("pnpm") or shutil.which("npm")
            if npm:
                return [npm, "test", "--silent"]
    return None


def review_artifacts(root: Path, rel_paths: list[str]) -> tuple[bool, str]:
    """Isolated check: files exist on disk. No LLM, no scoring the agent's prose."""
    if not rel_paths:
        return True, "No changed files listed."
    missing: list[str] = []
    for rel in rel_paths:
        clean = rel.strip().lstrip("/")
        if not clean or clean.startswith(".."):
            continue
        target = (root / clean).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            missing.append(rel)
            continue
        if not target.exists():
            missing.append(rel)
    if missing:
        return False, "Missing: " + ", ".join(missing[:8])
    return True, f"{len(rel_paths)} path(s) present."


def run_test_suite(root: Path, command: list[str]) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=_timeout_s(),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)[:400]
    blob = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    preview = " ".join(blob.split())[:400]
    ok = proc.returncode == 0
    return ok, preview or ("exit 0" if ok else f"exit {proc.returncode}")


def apply_verify_harness(report: dict[str, Any]) -> dict[str, Any]:
    """When claiming passed: run suite if present, then check artifacts exist."""
    steps = list(report.get("steps") or [])
    if any(str(s.get("id") or "") in HARNESS_STEP_IDS for s in steps if isinstance(s, dict)):
        return report
    if str(report.get("conclusion") or "") != "passed":
        return report
    from src.workspace import get_workspace

    entry = get_workspace()
    if not entry or not entry.get("workspace_path"):
        return report
    root = Path(str(entry["workspace_path"]))
    if not root.is_dir():
        return report

    next_actions = list(report.get("nextActions") or [])
    files = [str(p) for p in (report.get("changedFiles") or []) if str(p).strip()]

    command = detect_test_command(root)
    if command:
        ok, detail = run_test_suite(root, command)
        steps.insert(
            0,
            {
                "id": "harness_tests",
                "name": "Harness test suite",
                "status": "passed" if ok else "failed",
                "detail": detail,
            },
        )
        if not ok:
            report["conclusion"] = "failed"
            tip = "Fix the test suite; cannot claim passed while tests fail."
            if tip not in next_actions:
                next_actions.insert(0, tip)
            report["summary"] = "Verification forced to failed because the test suite failed."

    if str(report.get("conclusion") or "") == "passed" and files:
        ok, detail = review_artifacts(root, files)
        steps.insert(
            0 if not command else 1,
            {
                "id": "harness_artifacts",
                "name": "Harness artifact review",
                "status": "passed" if ok else "failed",
                "detail": detail,
            },
        )
        if not ok:
            report["conclusion"] = "failed"
            tip = "Changed files are missing on disk; cannot claim passed."
            if tip not in next_actions:
                next_actions.insert(0, tip)
            report["summary"] = "Verification forced to failed because listed files are missing on disk."

    report["steps"] = steps
    report["nextActions"] = next_actions
    return report
