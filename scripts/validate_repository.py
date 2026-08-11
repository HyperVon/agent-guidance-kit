#!/usr/bin/env python3
"""Validate the guidance hierarchy, skills, links, metadata, and Python syntax."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / ".agents/skills"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
INDEX_RE = re.compile(r"\]\(skills/([^/]+)/SKILL\.md\)")
IMPORT_RE = re.compile(r"(?m)^@(?P<path>\S+)\s*$")


def simple_frontmatter(text: str) -> tuple[dict[str, str], str | None]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, "missing or malformed YAML frontmatter"
    try:
        values = yaml.safe_load(match.group("body"))
    except yaml.YAMLError as error:
        return {}, f"invalid YAML frontmatter: {error}"
    if not isinstance(values, dict):
        return {}, "frontmatter must be a YAML mapping"
    for key, value in values.items():
        if not isinstance(key, str) or not isinstance(value, str):
            return {}, f"frontmatter {key!r} must be a string value"
    return values, None


def without_fenced_code(text: str) -> str:
    output: list[str] = []
    in_fence = False
    marker = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            current = stripped[:3]
            if not in_fence:
                in_fence = True
                marker = current
            elif current == marker:
                in_fence = False
                marker = ""
            continue
        if not in_fence:
            output.append(line)
    return "\n".join(output)


def validate_links(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.suffix not in {".md", ".mdc"}:
            continue
        if ".git" in path.parts:
            continue
        text = without_fenced_code(path.read_text(encoding="utf-8"))
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            split = urlsplit(target)
            if split.scheme or target.startswith("#"):
                continue
            relative = unquote(split.path)
            if not relative:
                continue
            if Path(relative).is_absolute():
                errors.append(f"{path.relative_to(ROOT)}: absolute local link is not portable: {target}")
                continue
            resolved = (path.parent / relative).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(f"{path.relative_to(ROOT)}: link escapes repository: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}: broken relative link: {target}")


def validate_harness_imports(errors: list[str]) -> None:
    for relative_path in (Path("CLAUDE.md"), Path("GEMINI.md")):
        path = ROOT / relative_path
        if not path.is_file() or path.is_symlink():
            errors.append(f"{relative_path}: missing real harness entrypoint")
            continue
        imports = IMPORT_RE.findall(without_fenced_code(path.read_text(encoding="utf-8")))
        if not imports:
            errors.append(f"{relative_path}: expected at least one canonical-file import")
            continue
        for raw_target in imports:
            target = Path(raw_target)
            if target.is_absolute():
                errors.append(f"{relative_path}: absolute import is not portable: {raw_target}")
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(f"{relative_path}: import escapes repository: {raw_target}")
                continue
            if not resolved.is_file() or resolved.is_symlink():
                errors.append(f"{relative_path}: broken or unsafe import: {raw_target}")


def validate_skills(errors: list[str]) -> set[str]:
    names: set[str] = set()
    for directory in sorted(SKILLS_ROOT.iterdir()):
        if directory.name.startswith("."):
            continue
        if directory.is_symlink() or not directory.is_dir():
            errors.append(f".agents/skills/{directory.name}: skill entry must be a real directory")
            continue
        skill_md = directory / "SKILL.md"
        if skill_md.is_symlink() or not skill_md.is_file():
            errors.append(f".agents/skills/{directory.name}: missing real SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        values, error = simple_frontmatter(text)
        if error:
            errors.append(f"{skill_md.relative_to(ROOT)}: {error}")
            continue
        if set(values) != {"name", "description"}:
            errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter keys must be exactly name and description")
        name = values.get("name", "")
        description = values.get("description", "")
        if not NAME_RE.fullmatch(name):
            errors.append(f"{skill_md.relative_to(ROOT)}: invalid skill name {name!r}")
        if name != directory.name:
            errors.append(f"{skill_md.relative_to(ROOT)}: name must match directory {directory.name!r}")
        if not (40 <= len(description) <= 1024):
            errors.append(f"{skill_md.relative_to(ROOT)}: description must be 40-1024 characters")
        if "[TODO" in text or "TODO:" in text:
            errors.append(f"{skill_md.relative_to(ROOT)}: unfinished TODO marker")
        names.add(name)

        metadata = directory / "agents/openai.yaml"
        if metadata.is_symlink() or not metadata.is_file():
            errors.append(f"{metadata.relative_to(ROOT)}: missing real metadata file")
            continue
        metadata_text = metadata.read_text(encoding="utf-8")
        try:
            metadata_value = yaml.safe_load(metadata_text)
        except yaml.YAMLError as error:
            errors.append(f"{metadata.relative_to(ROOT)}: invalid YAML: {error}")
            continue
        interface = metadata_value.get("interface", {}) if isinstance(metadata_value, dict) else {}
        display = interface.get("display_name") if isinstance(interface, dict) else None
        short = interface.get("short_description") if isinstance(interface, dict) else None
        prompt = interface.get("default_prompt") if isinstance(interface, dict) else None
        if not display:
            errors.append(f"{metadata.relative_to(ROOT)}: missing quoted display_name")
        if not short or not (25 <= len(short) <= 64):
            errors.append(f"{metadata.relative_to(ROOT)}: short_description must be 25-64 characters")
        if not prompt or f"${name}" not in prompt:
            errors.append(f"{metadata.relative_to(ROOT)}: default_prompt must mention ${name}")
    return names


def validate_index(skill_names: set[str], errors: list[str]) -> None:
    index_path = ROOT / ".agents/AGENTS.md"
    indexed = set(INDEX_RE.findall(index_path.read_text(encoding="utf-8")))
    missing = sorted(skill_names - indexed)
    extra = sorted(indexed - skill_names)
    if missing:
        errors.append(f".agents/AGENTS.md: missing skills from index: {', '.join(missing)}")
    if extra:
        errors.append(f".agents/AGENTS.md: index references unknown skills: {', '.join(extra)}")


def validate_python(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*.py")):
        if path.is_symlink() or ".git" in path.parts:
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (SyntaxError, UnicodeDecodeError) as error:
            errors.append(f"{path.relative_to(ROOT)}: Python syntax error: {error}")


def main() -> int:
    errors: list[str] = []
    if not SKILLS_ROOT.is_dir() or SKILLS_ROOT.is_symlink():
        print("error: .agents/skills must be a real directory", file=sys.stderr)
        return 2
    skills = validate_skills(errors)
    validate_index(skills, errors)
    validate_links(errors)
    validate_harness_imports(errors)
    validate_python(errors)
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        print(f"Validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1
    print(f"Validated {len(skills)} skills, relative links, metadata, and Python syntax.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
