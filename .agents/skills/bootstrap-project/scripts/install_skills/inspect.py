"""Skill inspection for install_skills."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import SOURCE_SKILLS, TARGET_SKILLS
from .dependencies import validate_declared_links
from .manifest import manifest_digest, tree_manifest
from .validation import AdoptionError, ensure_safe_ancestors


def inspect_skill(
    kit_root: Path,
    target_root: Path,
    name: str,
    dependencies: dict[str, dict[str, Any]],
    adopted_digests: dict[str, set[str]],
) -> dict[str, Any]:
    ensure_safe_ancestors(kit_root, SOURCE_SKILLS / name)
    source_dir = kit_root / SOURCE_SKILLS / name
    if source_dir.is_symlink() or not source_dir.is_dir():
        raise AdoptionError(f"source skill does not exist as a real directory: {name}")
    if (
        not (source_dir / "SKILL.md").is_file()
        or (source_dir / "SKILL.md").is_symlink()
    ):
        raise AdoptionError(f"source skill is missing a real SKILL.md: {name}")
    validate_declared_links(source_dir, name, dependencies)

    source_manifest = tree_manifest(source_dir)
    destination = TARGET_SKILLS / name
    destination_dir = target_root / destination
    status_value = "CREATE"
    target_digest = None
    conflict = None

    ensure_safe_ancestors(target_root, TARGET_SKILLS)
    if destination_dir.exists() or destination_dir.is_symlink():
        if destination_dir.is_symlink() or not destination_dir.is_dir():
            status_value = "CONFLICT"
            conflict = {"reason": "destination is not a real directory"}
        else:
            try:
                target_manifest = tree_manifest(destination_dir)
            except AdoptionError as error:
                status_value = "CONFLICT"
                conflict = {"reason": str(error)}
            else:
                target_digest = manifest_digest(target_manifest)
                if target_manifest == source_manifest:
                    status_value = "UNCHANGED"
                elif target_digest in adopted_digests.get(name, set()):
                    status_value = "UPDATE"
                else:
                    status_value = "CONFLICT"
                    from .manifest import difference_summary

                    conflict = {
                        "reason": "destination differs from the selected source skill",
                        **difference_summary(source_manifest, target_manifest),
                    }

    return {
        "name": name,
        "status": status_value,
        "source": (SOURCE_SKILLS / name).as_posix(),
        "destination": destination.as_posix(),
        "source_digest": manifest_digest(source_manifest),
        "target_digest": target_digest,
        "files": source_manifest,
        "conflict": conflict,
        "requires": dependencies[name]["requires"],
        "related": dependencies[name]["related"],
    }
