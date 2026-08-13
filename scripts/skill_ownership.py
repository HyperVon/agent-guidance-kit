"""Identify skills owned by receipt-managed integrations.

Agent Guidance Kit validates its own catalog. Optional integrations such as
Agent Runtime Router install skills under the same harness-visible directory,
but their receipt and validator remain owned by the integration. This module
keeps that boundary explicit for repository checks.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXTERNAL_RECEIPTS = (Path(".agents/.agent-runtime-router/receipt.json"),)


class OwnershipError(ValueError):
    """Raised when an external ownership receipt is malformed or unsafe."""


def external_skill_names(root: Path) -> set[str]:
    names: set[str] = set()
    for relative in EXTERNAL_RECEIPTS:
        path = root / relative
        if not path.exists() and not path.is_symlink():
            continue
        if path.is_symlink() or not path.is_file():
            raise OwnershipError(f"external skill receipt is unsafe: {relative}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise OwnershipError(
                f"cannot read external skill receipt: {error}"
            ) from error
        entries = value.get("skills") if isinstance(value, dict) else None
        if (
            not isinstance(value, dict)
            or value.get("schema_version") != 1
            or not isinstance(entries, list)
            or not entries
        ):
            raise OwnershipError(
                f"external skill receipt has an invalid shape: {relative}"
            )
        for entry in entries:
            name = entry.get("name") if isinstance(entry, dict) else None
            if not isinstance(name, str) or not SKILL_NAME.fullmatch(name):
                raise OwnershipError(
                    f"external skill receipt has an invalid skill: {relative}"
                )
            skill = root / ".agents/skills" / name
            if (
                skill.is_symlink()
                or not skill.is_dir()
                or (skill / "SKILL.md").is_symlink()
                or not (skill / "SKILL.md").is_file()
            ):
                raise OwnershipError(
                    f"external skill receipt names a missing or unsafe skill: {name}"
                )
            names.add(name)
    return names
