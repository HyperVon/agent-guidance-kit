#!/usr/bin/env python3
"""Validate the portable skill catalog with local tooling."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
CATALOG_LINK = re.compile(r"\]\(skills/([a-z0-9-]+)/SKILL\.md\)")
MARKDOWN_LINK = re.compile(r"\]\((?:<([^>]+)>|([^\s)]+))\)")
MIN_DESCRIPTION_CHARS = 40
MAX_DESCRIPTION_CHARS = 1024


def tracked_markdown_files() -> list[Path]:
    """Use tracked files so local experiments do not affect the product gate."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", "*.md"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return sorted(path for path in ROOT.rglob("*.md") if ".git" not in path.parts)
    return [ROOT / line for line in result.stdout.splitlines() if line]


def parse_frontmatter(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("frontmatter must start with ---")

    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("frontmatter closing --- is missing") from exc

    name = ""
    description_parts: list[str] = []
    in_description = False
    for line in lines[1:end]:
        if line.startswith("name:"):
            name = line.partition(":")[2].strip()
            in_description = False
        elif line.startswith("description:"):
            value = line.partition(":")[2].strip()
            in_description = True
            if value not in {"", ">-", ">", "|-", "|"}:
                description_parts.append(value)
        elif in_description and line.strip() and line[:1].isspace():
            description_parts.append(line.strip())
        elif in_description:
            # A non-indented frontmatter key ends a folded description. Ignore
            # optional fields such as compatibility or metadata instead of
            # counting them toward the description limit.
            in_description = False

    if not name:
        raise ValueError("frontmatter name is missing")
    if not description_parts:
        raise ValueError("frontmatter description is empty")

    description = " ".join(description_parts)
    if not MIN_DESCRIPTION_CHARS <= len(description) <= MAX_DESCRIPTION_CHARS:
        raise ValueError(
            "frontmatter description length "
            f"{len(description)} is outside "
            f"{MIN_DESCRIPTION_CHARS}-{MAX_DESCRIPTION_CHARS} characters"
        )

    if not any(line.strip() for line in lines[end + 1 :]):
        raise ValueError("skill body is empty")

    return name, description


def local_link_errors(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for match in MARKDOWN_LINK.finditer(text):
        target = (match.group(1) or match.group(2) or "").strip()
        if not target or target.startswith(("#", "http://", "https://", "mailto:", "//")):
            continue
        target = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not target:
            continue
        candidate = (path.parent / target).resolve()
        try:
            candidate.relative_to(ROOT)
        except ValueError:
            errors.append(f"{path.relative_to(ROOT)}: link escapes repository: {target}")
            continue
        if not candidate.exists():
            errors.append(f"{path.relative_to(ROOT)}: missing link target: {target}")
    return errors


def validate() -> list[str]:
    errors: list[str] = []
    if not SKILLS_ROOT.is_dir():
        return ["skills/ directory is missing"]

    skills = sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir())
    names: dict[str, Path] = {}
    for skill_dir in skills:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{skill_dir.relative_to(ROOT)}: SKILL.md is missing")
            continue
        try:
            name, _description = parse_frontmatter(skill_file)
        except ValueError as exc:
            errors.append(f"{skill_file.relative_to(ROOT)}: {exc}")
            continue
        if name != skill_dir.name:
            errors.append(
                f"{skill_file.relative_to(ROOT)}: frontmatter name {name!r} does not match directory {skill_dir.name!r}"
            )
        if name in names:
            errors.append(f"duplicate skill name {name!r}: {names[name]} and {skill_file}")
        names[name] = skill_file

    readme = ROOT / "README.md"
    catalog_names = CATALOG_LINK.findall(readme.read_text(encoding="utf-8"))
    for name in sorted(names):
        count = catalog_names.count(name)
        if count != 1:
            errors.append(f"README.md: skill {name!r} appears {count} times; expected exactly once")
    for name in sorted(set(catalog_names) - set(names)):
        errors.append(f"README.md: catalog lists removed or unknown skill {name!r}")

    for markdown in tracked_markdown_files():
        if markdown.exists():
            errors.extend(local_link_errors(markdown))
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Catalog validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    count = sum(1 for path in SKILLS_ROOT.iterdir() if path.is_dir())
    print(f"Catalog validation passed: {count} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
