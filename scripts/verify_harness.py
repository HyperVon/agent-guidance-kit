#!/usr/bin/env python3
"""Verify harness discovery for the kit (moves BEST_EFFORT toward VERIFIED)."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", default="unknown", help="Harness name to record")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "probe"
        target.mkdir()
        (target / "AGENTS.md").write_text("# Probe\n", encoding="utf-8")
        (target / ".agents/skills/test").mkdir(parents=True)
        (target / ".agents/skills/test/SKILL.md").write_text(
            "---\nname: test\ndescription: A sufficiently long test skill description for validation.\n---\n\n# Test\n",
            encoding="utf-8",
        )
        # Basic checks: guidance hierarchy is readable and not symlinked
        for p in [target / "AGENTS.md", target / ".agents/skills/test/SKILL.md"]:
            if p.is_symlink() or not p.is_file():
                print(f"FAIL {p} missing or symlinked", file=sys.stderr)
                return 1
        # Report harness capability (manual verification still required)
        print(f"Harness probe ({args.harness}): target at {target} is readable.")
        print(
            "Manual step: ask the harness to identify which instruction/skill files it discovered."
        )
        print(
            "Record the result in docs/harness-compatibility.md (DOCUMENTED -> VERIFIED)."
        )
        if args.verbose:
            print(f"Probe files: {list(target.rglob('*'))}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
