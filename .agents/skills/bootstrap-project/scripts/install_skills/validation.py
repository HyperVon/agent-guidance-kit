"""Shared validation utilities for install_skills."""

from __future__ import annotations

import os
from pathlib import Path


class AdoptionError(RuntimeError):
    """Raised when a safety or plan invariant is not satisfied."""


def validate_root(path: Path, label: str) -> Path:
    expanded = path.expanduser()
    if not expanded.exists():
        raise AdoptionError(f"{label} does not exist: {expanded}")
    if expanded.is_symlink() or not expanded.is_dir():
        raise AdoptionError(
            f"{label} must be a real directory, not a symlink: {expanded}"
        )
    return expanded.resolve()


def validate_directory(path: Path, label: str) -> Path:
    return validate_root(path, label)


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
