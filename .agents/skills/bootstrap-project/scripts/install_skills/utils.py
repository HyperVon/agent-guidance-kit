"""Shared utilities for install_skills."""

from __future__ import annotations

from pathlib import Path


def read_text_exact(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as error:
        from .validation import AdoptionError

        raise AdoptionError(
            f"cannot read UTF-8 routing file: {path}: {error}"
        ) from error
