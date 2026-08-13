"""Dependency loading and closure for install_skills."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .constants import DEPENDENCIES, MARKDOWN_LINK, SOURCE_SKILLS
from .utils import without_fenced_code
from .validation import AdoptionError

EXTERNAL_RECEIPT = Path(".agents/.agent-runtime-router/receipt.json")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def get_mandatory_skill(kit_root: Path) -> str:
    """Derive the mandatory skill from the dependency catalog.

    The mandatory skill is the one with no dependencies (requires: [])
    that provides the resolve_source.py script for source resolution.
    """
    dependencies = load_dependencies(kit_root)
    providers = [
        name
        for name, entry in dependencies.items()
        if not entry.get("requires")  # empty requires list
        and (kit_root / SOURCE_SKILLS / name / "scripts/resolve_source.py").is_file()
        and not (
            kit_root / SOURCE_SKILLS / name / "scripts/resolve_source.py"
        ).is_symlink()
    ]
    if len(providers) > 1:
        raise AdoptionError(
            "ambiguous mandatory skill: multiple skills without dependencies "
            f"provide resolve_source.py: {', '.join(sorted(providers))}"
        )
    if len(providers) == 1:
        return providers[0]

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
    external_names = _external_skill_names(kit_root)
    catalog_names = set(skills)
    if catalog_names != source_names - external_names:
        missing = sorted((source_names - external_names) - catalog_names)
        extra = sorted(catalog_names - source_names)
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


def _external_skill_names(kit_root: Path) -> set[str]:
    """Return names owned by the ARR receipt, rejecting malformed receipts."""
    path = kit_root / EXTERNAL_RECEIPT
    if not path.exists() and not path.is_symlink():
        return set()
    if path.is_symlink() or not path.is_file():
        raise AdoptionError(f"external skill receipt is unsafe: {EXTERNAL_RECEIPT}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AdoptionError(f"cannot read external skill receipt: {error}") from error
    entries = value.get("skills") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 1
        or not isinstance(entries, list)
        or not entries
    ):
        raise AdoptionError("external skill receipt has an invalid shape")
    names: set[str] = set()
    for entry in entries:
        name = entry.get("name") if isinstance(entry, dict) else None
        if not isinstance(name, str) or not SKILL_NAME.fullmatch(name):
            raise AdoptionError("external skill receipt has an invalid skill name")
        skill = kit_root / SOURCE_SKILLS / name
        if (
            skill.is_symlink()
            or not skill.is_dir()
            or (skill / "SKILL.md").is_symlink()
            or not (skill / "SKILL.md").is_file()
        ):
            raise AdoptionError(
                f"external skill receipt names a missing or unsafe skill: {name}"
            )
        names.add(name)
    return names


def dependency_closure(
    requested: list[str], dependencies: dict[str, dict[str, Any]], kit_root: Path
) -> tuple[list[str], dict[str, list[str]]]:
    mandatory_skill = get_mandatory_skill(kit_root)

    missing = sorted(set(requested) - set(dependencies))
    if missing:
        raise AdoptionError(f"unknown selected skills: {', '.join(missing)}")
    selected = set(requested)
    requested_set = set(requested)
    automatically_added: dict[str, list[str]] = {}
    if mandatory_skill not in selected:
        selected.add(mandatory_skill)
        automatically_added[mandatory_skill] = ["required maintenance entrypoint"]
    pending = sorted(selected)
    while pending:
        name = pending.pop(0)
        for required in dependencies[name]["requires"]:
            if required not in requested_set:
                automatically_added.setdefault(required, []).append(
                    f"required by {name}"
                )
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
        text = path.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(without_fenced_code(text)):
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
