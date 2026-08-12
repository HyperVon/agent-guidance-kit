"""Manifest and digest utilities for install_skills."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

from .constants import (
    SOURCE_ONLY_DIRS,
    TRANSIENT_DIRS,
    TRANSIENT_FILES,
    TRANSIENT_SUFFIXES,
)
from .validation import AdoptionError, ensure_no_symlink_tree, validate_relative


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_manifest(root: Path) -> list[dict[str, Any]]:
    ensure_no_symlink_tree(root)
    records: list[dict[str, Any]] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in TRANSIENT_DIRS and name not in SOURCE_ONLY_DIRS
        )
        current = Path(directory)
        for filename in sorted(filenames):
            if (
                filename in TRANSIENT_FILES
                or Path(filename).suffix in TRANSIENT_SUFFIXES
                or filename.endswith("~")
            ):
                continue
            path = current / filename
            if not path.is_file():
                raise AdoptionError(
                    f"unsupported non-file entry: {path.relative_to(root)}"
                )
            relative = path.relative_to(root)
            validate_relative(relative, "skill file")
            records.append(
                {
                    "path": relative.as_posix(),
                    "sha256": digest_file(path),
                    "size": path.stat().st_size,
                    "mode": stat.S_IMODE(path.stat().st_mode),
                }
            )
    records.sort(key=lambda item: item["path"])
    return records


def copy_manifest(
    source: Path, destination: Path, manifest: list[dict[str, Any]]
) -> None:
    destination.mkdir()
    for item in manifest:
        relative = Path(item["path"])
        validate_relative(relative, "manifest file")
        source_file = source / relative
        if source_file.is_symlink() or not source_file.is_file():
            raise AdoptionError(f"planned source file is missing or unsafe: {relative}")
        if digest_file(source_file) != item["sha256"]:
            raise AdoptionError(f"planned source file changed during apply: {relative}")
        destination_file = destination / relative
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copy2(source_file, destination_file)


def manifest_digest(manifest: list[dict[str, Any]]) -> str:
    return digest_bytes(canonical_json(manifest))


def git_revision(root: Path) -> str:
    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        status_result = subprocess.run(
            ["git", "-C", str(root), "status", "--short"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"
    if commit.returncode != 0:
        return "uncommitted"
    revision = commit.stdout.strip()
    if status_result.returncode == 0 and status_result.stdout.strip():
        revision += "+dirty"
    return revision


def difference_summary(
    source: list[dict[str, Any]], target: list[dict[str, Any]]
) -> dict[str, list[str]]:
    source_map = {item["path"]: item for item in source}
    target_map = {item["path"]: item for item in target}
    return {
        "source_only": sorted(set(source_map) - set(target_map)),
        "target_only": sorted(set(target_map) - set(source_map)),
        "different": sorted(
            path
            for path in set(source_map) & set(target_map)
            if source_map[path] != target_map[path]
        ),
    }
