"""Receipt handling for install_skills."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import RECEIPTS, SHA256, SKILL_NAME
from .validation import AdoptionError


def receipt_skill_digests(target_root: Path) -> dict[str, set[str]]:
    digests: dict[str, set[str]] = {}
    directory = target_root / RECEIPTS
    if not directory.exists() and not directory.is_symlink():
        return digests
    if directory.is_symlink() or not directory.is_dir():
        raise AdoptionError(f"receipt directory is unsafe: {RECEIPTS}")
    for path in sorted(directory.glob("*.json")):
        if path.is_symlink() or not path.is_file():
            raise AdoptionError(f"receipt is unsafe: {path.relative_to(target_root)}")
        receipt = read_json(path)
        entries = receipt.get("skills")
        if not isinstance(entries, list):
            raise AdoptionError(
                f"receipt skills must be a list: {path.relative_to(target_root)}"
            )
        for entry in entries:
            if not isinstance(entry, dict):
                raise AdoptionError(
                    f"receipt skill entry is malformed: {path.relative_to(target_root)}"
                )
            name = entry.get("name")
            digest = entry.get("source_digest")
            if (
                not isinstance(name, str)
                or not SKILL_NAME.fullmatch(name)
                or not isinstance(digest, str)
                or not SHA256.fullmatch(digest)
            ):
                raise AdoptionError(
                    f"receipt skill identity or digest is malformed: "
                    f"{path.relative_to(target_root)}"
                )
            digests.setdefault(name, set()).add(digest)
    return digests


def receipt_route_block_digests(target_root: Path) -> set[str]:
    digests: set[str] = set()
    directory = target_root / RECEIPTS
    if not directory.exists() and not directory.is_symlink():
        return digests
    if directory.is_symlink() or not directory.is_dir():
        raise AdoptionError(f"receipt directory is unsafe: {RECEIPTS}")
    for path in sorted(directory.glob("*.json")):
        receipt = read_json(path)
        routing = receipt.get("routing")
        digest = routing.get("block_digest") if isinstance(routing, dict) else None
        if isinstance(digest, str):
            digests.add(digest)
    return digests


def read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise AdoptionError(f"plan must be a real file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AdoptionError(f"cannot read plan: {error}") from error
    if not isinstance(value, dict):
        raise AdoptionError("plan root must be a JSON object")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise AdoptionError(f"refusing to overwrite existing file: {path}")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise AdoptionError(
            f"output parent must be an existing real directory: {path.parent}"
        )
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def receipt_for(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": plan.get("schema_version", 2),
        "plan_id": plan["plan_id"],
        "source": plan["source"],
        "source_resolution": plan["source_resolution"],
        "selection": plan["selection"],
        "result": "COMPLETED",
        "routing": {
            "path": plan["routing"]["path"],
            "skills": plan["routing"]["skills"],
            "after_digest": plan["routing"]["after_digest"],
            "block_digest": plan["routing"]["block_digest"],
        },
        "skills": [
            {
                "name": item["name"],
                "destination": item["destination"],
                "status": item["status"],
                "source_digest": item["source_digest"],
                "files": item["files"],
            }
            for item in plan["skills"]
        ],
    }
