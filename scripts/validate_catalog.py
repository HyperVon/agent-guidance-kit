#!/usr/bin/env python3
"""Validate the portable skill catalog with local tooling."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
CATALOG_LINK = re.compile(r"\]\(skills/([a-z0-9-]+)/SKILL\.md\)")
MARKDOWN_LINK = re.compile(r"\]\((?:<([^>]+)>|([^\s)]+))\)")
FRONTMATTER_FIELD = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")
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


def _strip_yaml_comment(value: str) -> str:
    """Remove a YAML comment while preserving # characters inside quotes."""
    value = value.lstrip()
    quote = ""
    escaped = False
    index = 0
    while index < len(value):
        character = value[index]
        if quote == '"':
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = ""
        elif quote == "'":
            if character == quote:
                if index + 1 < len(value) and value[index + 1] == quote:
                    index += 1
                else:
                    quote = ""
        elif index == 0 and character in {'"', "'"}:
            quote = character
        elif character == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
        index += 1
    return value.strip()


def _parse_inline_scalar(value: str) -> str:
    """Parse the scalar forms used by required frontmatter fields."""
    value = _strip_yaml_comment(value)
    if not value:
        return ""
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("frontmatter quoted scalar is invalid") from exc
        if not isinstance(parsed, str):
            raise ValueError("frontmatter scalar must be a string")
        return parsed
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise ValueError("frontmatter quoted scalar is invalid")
        return value[1:-1].replace("''", "'")
    return value


def _parse_block_header(value: str) -> tuple[str, int | None, str]:
    header = _strip_yaml_comment(value)
    if not header or header[0] not in {">", "|"}:
        raise ValueError("frontmatter block scalar header is invalid")
    style = header[0]
    indentation: int | None = None
    chomping = ""
    for character in header[1:]:
        if character.isspace():
            continue
        if character in {"+", "-"}:
            if chomping:
                raise ValueError("frontmatter block scalar header is invalid")
            chomping = character
        elif character in "123456789":
            if indentation is not None:
                raise ValueError("frontmatter block scalar header is invalid")
            indentation = int(character)
        else:
            raise ValueError("frontmatter block scalar header is invalid")
    return style, indentation, chomping


def _fold_block_lines(lines: list[str]) -> str:
    """Apply the relevant folded-scalar line-break semantics."""
    result: list[str] = []
    index = 0
    last_was_content = False
    while index < len(lines):
        if lines[index] == "":
            end = index
            while end < len(lines) and lines[end] == "":
                end += 1
            result.append("\n" * (end - index))
            last_was_content = False
            index = end
            continue
        if last_was_content:
            result.append(" ")
        result.append(lines[index])
        last_was_content = True
        index += 1
    return "".join(result)


def _apply_chomping(value: str, chomping: str) -> str:
    if not value:
        return ""
    if chomping == "-":
        return value.rstrip("\n")
    if chomping == "+":
        return value.rstrip("\n") + "\n" * (len(value) - len(value.rstrip("\n")) + 1)
    return value.rstrip("\n") + "\n"


def _parse_block_scalar(lines: list[str], start: int, end: int, header: str) -> tuple[str, int]:
    style, explicit_indent, chomping = _parse_block_header(header)
    raw_lines: list[str] = []
    index = start
    while index < end:
        line = lines[index]
        if not line.strip():
            raw_lines.append("")
            index += 1
            continue
        if not line[:1].isspace():
            if line.startswith("#"):
                index += 1
                continue
            break
        if explicit_indent is not None:
            leading_spaces = len(line) - len(line.lstrip(" "))
            if leading_spaces < explicit_indent:
                break
        raw_lines.append(line)
        index += 1

    if not raw_lines:
        return "", index
    nonblank_indents = [len(line) - len(line.lstrip(" ")) for line in raw_lines if line.strip()]
    indentation = explicit_indent or min(nonblank_indents, default=0)
    values: list[str] = []
    for line in raw_lines:
        if not line.strip():
            values.append("")
            continue
        leading_spaces = len(line) - len(line.lstrip(" "))
        if leading_spaces < indentation:
            raise ValueError("frontmatter block scalar indentation is invalid")
        values.append(line[indentation:])

    value = "\n".join(values) if style == "|" else _fold_block_lines(values)
    return _apply_chomping(value, chomping), index


def parse_frontmatter(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("frontmatter must start with ---")

    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("frontmatter closing --- is missing") from exc

    name = ""
    description = ""
    index = 1
    while index < end:
        match = FRONTMATTER_FIELD.match(lines[index])
        if not match or lines[index][:1].isspace():
            index += 1
            continue
        field, value = match.groups()
        if field == "name":
            name = _parse_inline_scalar(value)
            index += 1
        elif field == "description":
            if value.lstrip().startswith((">", "|")):
                description, index = _parse_block_scalar(lines, index + 1, end, value)
            else:
                description = _parse_inline_scalar(value)
                index += 1
        else:
            index += 1

    if not name:
        raise ValueError("frontmatter name is missing")
    if not description:
        raise ValueError("frontmatter description is empty")

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
