#!/usr/bin/env python3
"""Run all repository checks with the current Python interpreter."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from skill_ownership import OwnershipError, external_skill_names

ROOT = Path(__file__).resolve().parents[1]


def markdownlint_command(
    root: Path = ROOT, node: str | None = None
) -> list[str] | None:
    node_executable = node or shutil.which("node")
    cli = root / "node_modules/markdownlint-cli2/markdownlint-cli2-bin.mjs"
    if node_executable is None or not cli.is_file():
        return None
    return [node_executable, str(cli)]


def agent_skills_commands(
    root: Path = ROOT, python: str | None = None
) -> list[list[str]] | None:
    python_path = Path(python or sys.executable)
    executable_dirs = [python_path.parent]
    if python_path.name.lower().endswith(".exe"):
        executable_dirs.append(python_path.parent / "Scripts")
    validator = None
    for executable_dir in executable_dirs:
        for name in ("agentskills", "skills-ref"):
            for suffix in ("", ".exe"):
                candidate = executable_dir / f"{name}{suffix}"
                if candidate.is_file():
                    validator = candidate
                    break
            if validator is not None:
                break
        if validator is not None:
            break
    if validator is None:
        return None

    skills_root = root / ".agents/skills"
    try:
        external = external_skill_names(root)
    except OwnershipError:
        # validate_repository.py reports the structured ownership failure later.
        external = set()
    skills = sorted(
        directory
        for directory in skills_root.iterdir()
        if directory.is_dir()
        and not directory.name.startswith(".")
        and directory.name not in external
    )
    return [[str(validator), "validate", str(skill)] for skill in skills]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run repository checks")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip markdownlint and agentskills for faster inner loop",
    )
    args = parser.parse_args()
    markdownlint = markdownlint_command()
    if markdownlint is None and not args.quick:
        print(
            "ERROR Markdown lint is required; run python scripts/setup_dev.py first.",
            file=sys.stderr,
        )
        return 2
    agent_skills = agent_skills_commands()
    if agent_skills is None and not args.quick:
        print(
            "ERROR Agent Skills reference validation is required; "
            "run python scripts/setup_dev.py first.",
            file=sys.stderr,
        )
        return 2
    commands: list[list[str]] = []
    if not args.quick:
        if markdownlint is not None:
            commands.append(markdownlint)
        if agent_skills is not None:
            commands.extend(agent_skills)
    commands.extend(
        [
            [sys.executable, "-m", "ruff", "check", "."],
            [sys.executable, "-m", "ruff", "format", "--check", "."],
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            [sys.executable, "scripts/validate_repository.py"],
            [sys.executable, "scripts/public_hygiene_check.py"],
        ]
    )
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
