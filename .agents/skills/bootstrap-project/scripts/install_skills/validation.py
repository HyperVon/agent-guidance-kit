"""Shared validation utilities for install_skills."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

# Fallback matcher only. The authoritative SOURCE_ONLY signal is the frontmatter
# `source_only: true` flag, which assert_not_source_only reads from the skill's
# frontmatter below. This regex is a backstop for skills whose prose says
# "is `SOURCE_ONLY`" but predate the structured flag; it must not be the sole
# gate. The audit shares an equivalent backstop.
SOURCE_ONLY_RE = re.compile(r"(?:is|this skill) `SOURCE_ONLY`")


def frontmatter_source_only(text: str) -> bool:
    """Return True when the SKILL.md frontmatter declares `source_only: true`."""
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return False
    for line in match.group(1).splitlines():
        if line.startswith("source_only:"):
            value = line.split(":", 1)[1].strip().lower()
            return value in {"true", "yes", "1", "on"}
    return False


class AdoptionError(RuntimeError):
    """Raised when a safety or plan invariant is not satisfied."""


def assert_not_source_only(kit_root: Path, skill_names: Iterable[str]) -> None:
    """Refuse to adopt SOURCE_ONLY skills into a target.

    SOURCE_ONLY skills (for example catalog-discovery) are kit-maintainer tools
    and must never be shipped to a target. This is the hard gate that enforces
    the documented "never shipped to targets" invariant; the audit omits them
    for visibility, but the installer must refuse regardless.
    """
    blocked = []
    for name in skill_names:
        skill_md = kit_root / ".agents/skills" / name / "SKILL.md"
        if skill_md.is_symlink() or not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if frontmatter_source_only(text) or SOURCE_ONLY_RE.search(text):
            blocked.append(name)
    if blocked:
        raise AdoptionError(
            "SOURCE_ONLY skills cannot be adopted into a target: "
            + ", ".join(sorted(blocked))
        )


def validate_root(path: Path, label: str) -> Path:
    expanded = path.expanduser()
    if not expanded.exists():
        raise AdoptionError(f"{label} does not exist: {expanded}")
    if expanded.is_symlink() or not expanded.is_dir():
        raise AdoptionError(
            f"{label} must be a real directory, not a symlink: {expanded}"
        )
    return expanded.resolve()


def validate_relative(path: Path, label: str) -> None:
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise AdoptionError(f"{label} must be a normalized relative path: {path}")


def ensure_no_symlink_tree(root: Path) -> None:
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        for name in sorted(dirnames + filenames):
            path = current / name
            if path.is_symlink():
                raise AdoptionError(
                    f"symlinks are not allowed in skill content: {path.relative_to(root)}"
                )


def ensure_safe_ancestors(root: Path, relative: Path, create: bool = False) -> Path:
    validate_relative(relative, "destination")
    current = root
    for part in relative.parts:
        current = current / part
        if current.exists() or current.is_symlink():
            if current.is_symlink():
                raise AdoptionError(
                    f"symlinked destination component is not allowed: {current.relative_to(root)}"
                )
            if not current.is_dir():
                raise AdoptionError(
                    f"destination component is not a directory: {current.relative_to(root)}"
                )
        elif create:
            current.mkdir()
        else:
            break
    return current
