#!/usr/bin/env python3
"""Validate the portable skill catalog with the Agent Skills reference validator."""

from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
CATALOG_LINK = re.compile(r"\]\(skills/([a-z0-9-]+)/SKILL\.md\)")
MARKDOWN_LINK = re.compile(r"\]\((?:<([^>]+)>|([^\s)]+))\)")

try:
    from skills_ref.parser import parse_frontmatter as _reference_parse_frontmatter
    from skills_ref.validator import validate_metadata as _reference_validate_metadata
except ImportError as exc:  # pragma: no cover - exercised only in an unconfigured environment.
    _REFERENCE_IMPORT_ERROR = exc
    _reference_parse_frontmatter = None
    _reference_validate_metadata = None
else:
    _REFERENCE_IMPORT_ERROR = None


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


def _require_reference_validator() -> None:
    if _REFERENCE_IMPORT_ERROR is not None:
        raise ValueError(
            "skills-ref is required for catalog validation; install the pinned development dependencies "
            "from requirements-dev.txt"
        ) from _REFERENCE_IMPORT_ERROR


def _validate_frontmatter_fence(content: str) -> None:
    """Keep the repository's closing fence exact before skills-ref parses YAML."""
    lines = content.splitlines()
    for line in lines[1:]:
        if line == "---":
            return
        if line.startswith("---"):
            raise ValueError("frontmatter closing marker is invalid")
    raise ValueError("frontmatter closing --- is missing")


def _reference_properties(path: Path, *, check_directory: bool) -> tuple[str, str, str]:
    """Parse and validate one skill through skills-ref, then apply local body checks."""
    _require_reference_validator()
    content = path.read_text(encoding="utf-8")
    _validate_frontmatter_fence(content)
    try:
        metadata, body = _reference_parse_frontmatter(content)
    except Exception as exc:  # skills-ref wraps parser-specific YAML exceptions inconsistently across releases.
        raise ValueError(str(exc)) from exc

    skill_dir = path.parent if check_directory else None
    errors = _reference_validate_metadata(metadata, skill_dir)
    if errors:
        raise ValueError("; ".join(errors))
    if not body.strip():
        raise ValueError("skill body is empty")

    name = unicodedata.normalize("NFKC", str(metadata["name"]).strip())
    description = str(metadata["description"]).strip()
    return name, description, body


def parse_frontmatter(path: Path) -> tuple[str, str]:
    """Return validated skill name and description using the reference implementation."""
    name, description, _body = _reference_properties(path, check_directory=False)
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
            name, _description, _body = _reference_properties(skill_file, check_directory=True)
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
