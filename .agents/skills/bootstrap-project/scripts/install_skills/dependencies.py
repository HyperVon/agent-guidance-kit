"""Dependency loading and closure for install_skills."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .constants import DEPENDENCIES, MARKDOWN_LINK, SOURCE_SKILLS
from .validation import AdoptionError

_MANDATORY_SKILL_CACHE: str | None = None


def get_mandatory_skill(kit_root: Path) -> str:
    """Derive the mandatory skill from the dependency catalog.

    The mandatory skill is the one with no dependencies (requires: [])
    that provides the resolve_source.py script for source resolution.
    """
    global _MANDATORY_SKILL_CACHE
    if _MANDATORY_SKILL_CACHE is not None:
        return _MANDATORY_SKILL_CACHE

    dependencies = load_dependencies(kit_root)
    candidates = [
        name
        for name, entry in dependencies.items()
        if not entry.get("requires")  # empty requires list
    ]

    for name in candidates:
        resolver = kit_root / SOURCE_SKILLS / name / "scripts/resolve_source.py"
        if resolver.is_file() and not resolver.is_symlink():
            _MANDATORY_SKILL_CACHE = name
            return name

    raise AdoptionError(
        "no skill provides resolve_source.py; cannot determine mandatory skill"
    )


def normalize_skills(raw_skills: list[str]) -> list[str]:
    from .constants import SKILL_NAME

    skills: set[str] = set()
    for raw in raw_skills:
        for name in raw.split(","):
            candidate = name.strip()
            if not SKILL_NAME.fullmatch(candidate):
                raise AdoptionError(f"invalid skill name: {candidate!r}")
            skills.add(candidate)
    if not skills:
        raise AdoptionError("at least one --skill is required")
    return sorted(skills)


def load_dependencies(kit_root: Path) -> dict[str, dict[str, Any]]:
    path = kit_root / DEPENDENCIES
    if path.is_symlink() or not path.is_file():
        raise AdoptionError(f"missing real skill dependency catalog: {DEPENDENCIES}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AdoptionError(f"cannot read skill dependency catalog: {error}") from error
    skills = value.get("skills") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 1
        or not isinstance(skills, dict)
    ):
        raise AdoptionError("unsupported or malformed skill dependency catalog")
    source_names = {
        path.name
        for path in (kit_root / SOURCE_SKILLS).iterdir()
        if path.is_dir() and not path.is_symlink() and not path.name.startswith(".")
    }
    if set(skills) != source_names:
        missing = sorted(source_names - set(skills))
        extra = sorted(set(skills) - source_names)
        raise AdoptionError(
            "skill dependency catalog does not match source skills; "
            f"missing={missing}, extra={extra}"
        )
    for name, entry in skills.items():
        if not isinstance(entry, dict):
            raise AdoptionError(f"dependency entry must be an object: {name}")
        requires = entry.get("requires")
        related = entry.get("related")
        route = entry.get("route")
        if not isinstance(requires, list) or not isinstance(related, list):
            raise AdoptionError(f"dependency lists are required for skill: {name}")
        if any(
            not isinstance(item, str) or item not in source_names
            for item in requires + related
        ):
            raise AdoptionError(f"dependency entry references an unknown skill: {name}")
        if name in requires or name in related or set(requires) & set(related):
            raise AdoptionError(
                f"dependency entry is self-referential or overlapping: {name}"
            )
        if (
            not isinstance(route, str)
            or not route.strip()
            or "|" in route
            or "\n" in route
        ):
            raise AdoptionError(
                f"dependency entry has an invalid route description: {name}"
            )
    return skills


def dependency_closure(
    requested: list[str], dependencies: dict[str, dict[str, Any]], kit_root: Path
) -> tuple[list[str], dict[str, list[str]]]:
    mandatory_skill = get_mandatory_skill(kit_root)

    missing = sorted(set(requested) - set(dependencies))
    if missing:
        raise AdoptionError(f"unknown selected skills: {', '.join(missing)}")
    selected = set(requested)
    automatically_added: dict[str, list[str]] = {}
    if mandatory_skill not in selected:
        selected.add(mandatory_skill)
        automatically_added[mandatory_skill] = ["required maintenance entrypoint"]
    pending = sorted(selected)
    while pending:
        name = pending.pop(0)
        for required in dependencies[name]["requires"]:
            automatically_added.setdefault(required, []).append(f"required by {name}")
            if required not in selected:
                selected.add(required)
                pending.append(required)
    return sorted(selected), {
        name: sorted(set(reasons))
        for name, reasons in sorted(automatically_added.items())
    }


def validate_declared_links(
    source_dir: Path, name: str, dependencies: dict[str, dict[str, Any]]
) -> None:
    linked: set[str] = set()
    source_root = source_dir.resolve()
    skills_root = source_dir.parent.resolve()
    for path in sorted(source_dir.rglob("*.md")):
        if path.is_symlink():
            raise AdoptionError(f"symlinked Markdown is not allowed: {path}")
        for raw_target in MARKDOWN_LINK.findall(path.read_text(encoding="utf-8")):
            target = raw_target.strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            split = urlsplit(target)
            if split.scheme or target.startswith("#") or not split.path:
                continue
            candidate = (path.parent / unquote(split.path)).resolve()
            try:
                candidate.relative_to(source_root)
                continue
            except ValueError:
                pass
            try:
                relative_to_skills = candidate.relative_to(skills_root)
            except ValueError as error:
                raise AdoptionError(
                    f"skill {name} has a relative link outside the portable catalog: {target}"
                ) from error
            dependency = relative_to_skills.parts[0]
            if dependency != name:
                linked.add(dependency)
    requires = set(dependencies[name]["requires"])
    undeclared = sorted(linked - requires)
    if undeclared:
        raise AdoptionError(
            f"skill {name} has relative links to non-required skills: {', '.join(undeclared)}"
        )
