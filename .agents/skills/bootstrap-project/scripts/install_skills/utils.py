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


def extract_markdown_link_targets(text: str) -> list[str]:
    """Extract raw markdown link targets handling nested parentheses."""
    targets: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        idx = text.find("](", i)
        if idx == -1:
            break
        lb = text.rfind("[", 0, idx + 1)
        if lb == -1:
            i = idx + 2
            continue
        if lb > 0 and text[lb - 1] == "!":
            i = idx + 2
            continue
        start = idx + 2
        if start < n and text[start] == "<":
            end_angle = text.find(">", start + 1)
            if end_angle != -1:
                pos = end_angle + 1
                remaining = text[pos:].find(")")
                if remaining != -1:
                    raw_end = pos + remaining
                    targets.append(text[start:raw_end])
                    i = raw_end + 1
                    continue
            i = start + 1
            continue
        depth = 1
        pos = start
        raw_end = -1
        while pos < n:
            ch = text[pos]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    raw_end = pos
                    break
            pos += 1
        if raw_end == -1:
            i = start + 1
            continue
        targets.append(text[start:raw_end])
        i = raw_end + 1
    return targets
