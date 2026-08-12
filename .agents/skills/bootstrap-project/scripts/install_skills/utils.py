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


def without_fenced_code(text: str) -> str:
    """Remove fenced code blocks so example links are not treated as real links."""
    output: list[str] = []
    in_fence = False
    marker = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
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
