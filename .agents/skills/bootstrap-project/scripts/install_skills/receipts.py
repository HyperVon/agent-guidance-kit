"""Receipt handling for install_skills."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import RECEIPTS, SHA256, SKILL_NAME
from .manifest import manifest_digest
from .validation import AdoptionError, validate_relative


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


def receipt_skill_file_paths(target_root: Path) -> dict[str, set[str]]:
    """Return paths previously owned by receipts, conservatively.

    Older receipts may not contain a ``files`` manifest.  In that case the
    skill has no proven file ownership and callers must preserve all existing
    target content during a refresh.  When a manifest is present, malformed
    paths fail closed rather than becoming deletion authority.
    """

    paths_by_skill: dict[str, set[str]] = {}
    untrusted_skills: set[str] = set()
    directory = target_root / RECEIPTS
    if not directory.exists() and not directory.is_symlink():
        return paths_by_skill
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
            if not isinstance(name, str) or not SKILL_NAME.fullmatch(name):
                raise AdoptionError(
                    f"receipt skill identity is malformed: {path.relative_to(target_root)}"
                )
            if name in untrusted_skills:
                continue
            files = entry.get("files")
            if files is None:
                # Pre-manifest receipts cannot prove ownership of any path.
                paths_by_skill.setdefault(name, set())
                continue
            if not isinstance(files, list):
                raise AdoptionError(
                    f"receipt skill files must be a list: {path.relative_to(target_root)}"
                )
            source_digest = entry.get("source_digest")
            if not isinstance(source_digest, str) or not SHA256.fullmatch(
                source_digest
            ):
                raise AdoptionError(
                    f"receipt skill source digest is malformed: "
                    f"{path.relative_to(target_root)}"
                )
            owned = paths_by_skill.setdefault(name, set())
            for file_entry in files:
                if not isinstance(file_entry, dict) or not isinstance(
                    file_entry.get("path"), str
                ):
                    raise AdoptionError(
                        f"receipt skill file entry is malformed: "
                        f"{path.relative_to(target_root)}"
                    )
                relative = Path(file_entry["path"])
                try:
                    validate_relative(relative, "receipt skill file")
                except AdoptionError as error:
                    raise AdoptionError(
                        f"receipt skill file path is unsafe: "
                        f"{path.relative_to(target_root)}"
                    ) from error
                owned.add(relative.as_posix())
            if manifest_digest(files) != source_digest:
                # Historical receipts may have been generated with a broader
                # manifest policy (for example, including evals/). They are
                # still useful for update detection, but they are not safe
                # deletion authority. Preserve all paths for this skill and
                # let the next successful apply write a current receipt.
                untrusted_skills.add(name)
                paths_by_skill[name] = set()
    return paths_by_skill


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
