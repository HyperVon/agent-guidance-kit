"""Source resolution and locator handling for install_skills."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .constants import (
    SOURCE_ENVIRONMENT,
    SOURCE_LOCATOR,
    SOURCE_SKILLS,
)
from .dependencies import get_mandatory_skill
from .validation import AdoptionError, validate_root


def is_git_worktree(target_root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(target_root), "rev-parse", "--is-inside-work-tree"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def run_source_resolver(
    kit_root: Path, arguments: list[str]
) -> subprocess.CompletedProcess[str]:
    mandatory_skill = get_mandatory_skill(kit_root)
    resolver = kit_root / SOURCE_SKILLS / mandatory_skill / "scripts/resolve_source.py"
    if resolver.is_symlink() or not resolver.is_file():
        raise AdoptionError("maintenance source resolver is missing or unsafe")
    try:
        return subprocess.run(
            [sys.executable, str(resolver), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AdoptionError(
            f"cannot run maintenance source resolver: {error}"
        ) from error


def source_resolution_plan(kit_root: Path, target_root: Path) -> dict[str, Any]:
    result = run_source_resolver(kit_root, ["resolve", "--target", str(target_root)])
    if result.returncode == 0:
        try:
            value = json.loads(result.stdout)
            resolved_root = validate_root(
                Path(value["kit_root"]), "resolved future kit root"
            )
            method = value["method"]
            if not isinstance(method, str) or not method:
                raise AdoptionError("source resolver returned an invalid method")
        except (
            KeyError,
            TypeError,
            json.JSONDecodeError,
            AdoptionError,
        ) as error:
            return {
                "status": "CONFLICT",
                "method": "maintenance resolver",
                "reason": f"source resolver returned invalid output: {error}",
            }
        if resolved_root != kit_root:
            return {
                "status": "CONFLICT",
                "method": method,
                "reason": "future source resolves to a different checkout",
            }
        return {"status": "UNCHANGED", "method": method}

    detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
    if os.environ.get(SOURCE_ENVIRONMENT) or (
        (target_root / SOURCE_LOCATOR).exists()
        or (target_root / SOURCE_LOCATOR).is_symlink()
    ):
        return {
            "status": "CONFLICT",
            "method": "maintenance resolver",
            "reason": detail,
        }
    if is_git_worktree(target_root):
        return {"status": "CONFIGURE", "method": "target-local locator"}
    return {
        "status": "ASK",
        "method": "explicit or environment",
        "reason": detail,
    }


def read_optional_bytes(path: Path, label: str) -> bytes | None:
    if path.is_symlink():
        raise AdoptionError(f"{label} must not be a symlink: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        raise AdoptionError(f"{label} must be a file: {path}")
    try:
        return path.read_bytes()
    except OSError as error:
        raise AdoptionError(f"cannot read {label}: {path}: {error}") from error


def git_exclude_path(target_root: Path) -> Path:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(target_root),
                "rev-parse",
                "--path-format=absolute",
                "--git-path",
                "info/exclude",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise AdoptionError("Git is unavailable for source locator rollback") from error
    if result.returncode != 0 or not result.stdout.strip():
        raise AdoptionError("cannot resolve the target Git exclude file")
    path = Path(result.stdout.strip())
    read_optional_bytes(path, "Git exclude file")
    return path


def source_locator_snapshot(target_root: Path) -> dict[str, Any]:
    locator = target_root / SOURCE_LOCATOR
    exclude = git_exclude_path(target_root)
    return {
        "locator_path": locator,
        "locator_bytes": read_optional_bytes(locator, "source locator"),
        "exclude_path": exclude,
        "exclude_bytes": read_optional_bytes(exclude, "Git exclude file"),
    }


def restore_source_locator(
    before: dict[str, Any], after: dict[str, Any], token: str
) -> None:
    for path_key, bytes_key, label in (
        ("locator_path", "locator_bytes", "source locator"),
        ("exclude_path", "exclude_bytes", "Git exclude file"),
    ):
        path = before[path_key]
        current = read_optional_bytes(path, label)
        if current != after[bytes_key]:
            raise AdoptionError(f"{label} changed during rollback: {path}")
        previous = before[bytes_key]
        if previous is None:
            if current is not None:
                path.unlink()
            continue
        temporary = path.parent / f".{path.name}.agent-guidance-kit-{token}"
        if temporary.exists() or temporary.is_symlink():
            raise AdoptionError(f"rollback path already exists: {temporary}")
        with temporary.open("xb") as handle:
            handle.write(previous)
        os.replace(temporary, path)


def configure_source_locator(
    kit_root: Path, target_root: Path, token: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    before = source_locator_snapshot(target_root)
    result = run_source_resolver(
        kit_root,
        [
            "configure",
            "--target",
            str(target_root),
            "--kit-root",
            str(kit_root),
        ],
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        after = source_locator_snapshot(target_root)
        restore_source_locator(before, after, token)
        raise AdoptionError(f"cannot configure persistent source locator: {detail}")
    after = source_locator_snapshot(target_root)
    return before, after
