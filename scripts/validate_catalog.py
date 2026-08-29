#!/usr/bin/env python3
"""Validate the portable skill catalog with local Agent Skills checks."""

from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from copy import deepcopy
from pathlib import Path
from urllib.parse import unquote

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised only in an unconfigured environment.
    yaml = None
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None

if yaml is not None:
    class _CatalogLoader(yaml.SafeLoader):
        """Safe PyYAML loader with YAML 1.2 booleans and unique keys."""

        yaml_implicit_resolvers = deepcopy(yaml.SafeLoader.yaml_implicit_resolvers)

    _YAML_BOOL_TAG = "tag:yaml.org,2002:bool"
    for first_character, resolvers in _CatalogLoader.yaml_implicit_resolvers.items():
        _CatalogLoader.yaml_implicit_resolvers[first_character] = [
            (tag, pattern) for tag, pattern in resolvers if tag != _YAML_BOOL_TAG
        ]
    _CatalogLoader.add_implicit_resolver(
        _YAML_BOOL_TAG,
        re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
        list("tTfF"),
    )

    def _construct_unique_mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found unhashable key {key!r}",
                    key_node.start_mark,
                ) from exc
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    _CatalogLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_unique_mapping,
    )
else:
    _CatalogLoader = None


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
CATALOG_LINK = re.compile(r"^\|\s*\[[^\]]+\]\(skills/([^/\s)]+)/SKILL\.md\)\s*\|")
MARKDOWN_LINK = re.compile(r"\]\((?:<([^>]+)>|([^\s)]+))\)")
MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500
ALLOWED_FIELDS = frozenset(
    {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
)


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


def _require_yaml() -> None:
    if yaml is None:
        raise ValueError(
            "PyYAML is required for catalog validation; install the pinned development dependencies "
            "from requirements-dev.txt"
        ) from _YAML_IMPORT_ERROR


def _frontmatter_parts(content: str) -> tuple[str, str]:
    lines = content.split("\n")
    if not lines or lines[0] != "---":
        raise ValueError("frontmatter must start with YAML frontmatter (---)")

    for index, line in enumerate(lines[1:], start=1):
        if line == "---":
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1 :])
        if line.startswith("---"):
            raise ValueError("frontmatter closing marker is invalid")
    raise ValueError("frontmatter closing --- is missing")


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    frontmatter, body = _frontmatter_parts(content)
    _require_yaml()
    try:
        metadata = yaml.load(frontmatter, Loader=_CatalogLoader)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in frontmatter: {exc}") from exc
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return metadata, body


def _validate_metadata(metadata: dict, skill_dir: Path | None = None) -> tuple[str, str]:
    errors: list[str] = []

    unexpected_fields = sorted(str(field) for field in metadata if field not in ALLOWED_FIELDS)
    if unexpected_fields:
        errors.append(f"Unexpected fields in frontmatter: {', '.join(unexpected_fields)}")

    name: str | None = None
    if "name" not in metadata:
        errors.append("Missing required field in frontmatter: name")
    elif not isinstance(metadata["name"], str) or not metadata["name"].strip():
        errors.append("Field 'name' must be a non-empty string")
    else:
        raw_name = metadata["name"]
        name = unicodedata.normalize("NFKC", raw_name)
        if len(raw_name) > MAX_SKILL_NAME_LENGTH or len(name) > MAX_SKILL_NAME_LENGTH:
            errors.append(
                f"Skill name '{name}' exceeds {MAX_SKILL_NAME_LENGTH} character limit ({len(name)} chars)"
            )
        if raw_name != raw_name.lower() or name != name.lower():
            errors.append(f"Skill name '{raw_name}' must be lowercase")
        if raw_name.startswith("-") or raw_name.endswith("-"):
            errors.append("Skill name cannot start or end with a hyphen")
        if "--" in raw_name:
            errors.append("Skill name cannot contain consecutive hyphens")
        if not all(character.isalnum() or character == "-" for character in raw_name):
            errors.append(
                f"Skill name '{raw_name}' contains invalid characters. Only letters, digits, and hyphens are allowed."
            )
        if skill_dir is not None:
            directory_name = unicodedata.normalize("NFKC", skill_dir.name)
            if directory_name != name:
                errors.append(f"Directory name '{skill_dir.name}' must match skill name '{name}'")

    description: str | None = None
    if "description" not in metadata:
        errors.append("Missing required field in frontmatter: description")
    elif not isinstance(metadata["description"], str) or not metadata["description"].strip():
        errors.append("Field 'description' must be a non-empty string")
    else:
        description = metadata["description"].strip()
        if len(metadata["description"]) > MAX_DESCRIPTION_LENGTH:
            errors.append(
                f"Description exceeds {MAX_DESCRIPTION_LENGTH} character limit ({len(metadata['description'])} chars)"
            )

    for field in ("license", "allowed-tools"):
        if field in metadata and not isinstance(metadata[field], str):
            errors.append(f"Field '{field}' must be a string")

    if "compatibility" in metadata:
        compatibility = metadata["compatibility"]
        if not isinstance(compatibility, str):
            errors.append("Field 'compatibility' must be a string")
        elif not compatibility.strip():
            errors.append("Field 'compatibility' must be a non-empty string")
        elif len(compatibility) > MAX_COMPATIBILITY_LENGTH:
            errors.append(
                f"Compatibility exceeds {MAX_COMPATIBILITY_LENGTH} character limit ({len(compatibility)} chars)"
            )

    if "metadata" in metadata:
        additional_metadata = metadata["metadata"]
        if not isinstance(additional_metadata, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in additional_metadata.items()
        ):
            errors.append("Field 'metadata' must be a mapping of strings to strings")

    if errors:
        raise ValueError("; ".join(errors))
    assert name is not None
    assert description is not None
    return name, description


def catalog_names(readme: Path) -> list[str]:
    """Return visible skill links from the README catalog, decoding URI paths."""
    return [
        unicodedata.normalize("NFKC", unquote(match.group(1)))
        for line in readme.read_text(encoding="utf-8").splitlines()
        for match in CATALOG_LINK.finditer(line)
    ]


def parse_frontmatter(path: Path, *, check_directory: bool = False) -> tuple[str, str]:
    """Return validated skill name and description from one SKILL.md file."""
    metadata, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    name, description = _validate_metadata(metadata, path.parent if check_directory else None)
    if not body.strip():
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
        directory_name = unicodedata.normalize("NFKC", skill_dir.name)
        if name != directory_name:
            errors.append(
                f"{skill_file.relative_to(ROOT)}: frontmatter name {name!r} does not match directory {skill_dir.name!r}"
            )
        if name in names:
            errors.append(f"duplicate skill name {name!r}: {names[name]} and {skill_file}")
        names[name] = skill_file

    readme = ROOT / "README.md"
    catalog_entries = catalog_names(readme)
    for name in sorted(names):
        count = catalog_entries.count(name)
        if count != 1:
            errors.append(f"README.md: skill {name!r} appears {count} times; expected exactly once")
    for name in sorted(set(catalog_entries) - set(names)):
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
