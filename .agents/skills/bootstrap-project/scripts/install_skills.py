#!/usr/bin/env python3
"""Plan and apply create-only skill adoption from Agent Guidance Kit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SOURCE_SKILLS = Path(".agents/skills")
TARGET_SKILLS = Path(".agents/skills")
RECEIPTS = Path(".agents/.agent-guidance-kit/receipts")
TRANSIENT_DIRS = {"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
TRANSIENT_FILES = {".DS_Store"}
TRANSIENT_SUFFIXES = {".pyc", ".pyo", ".swp"}


class AdoptionError(RuntimeError):
    """Raised when a safety or plan invariant is not satisfied."""


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


def validate_root(path: Path, label: str) -> Path:
    expanded = path.expanduser()
    if not expanded.exists():
        raise AdoptionError(f"{label} does not exist: {expanded}")
    if expanded.is_symlink() or not expanded.is_dir():
        raise AdoptionError(
            f"{label} must be a real directory, not a symlink: {expanded}"
        )
    return expanded.resolve()


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


def tree_manifest(root: Path) -> list[dict[str, Any]]:
    ensure_no_symlink_tree(root)
    records: list[dict[str, Any]] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if name not in TRANSIENT_DIRS)
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


def normalize_skills(raw_skills: list[str]) -> list[str]:
    skills: set[str] = set()
    for raw in raw_skills:
        for name in raw.split(","):
            candidate = name.strip()
            if not SKILL_NAME.fullmatch(candidate):
                raise AdoptionError(f"invalid skill name: {candidate!r}")
            skills.add(candidate)
    if not skills:
        raise AdoptionError("at least one --skill is required")
    return sorted(skills)


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


def inspect_skill(kit_root: Path, target_root: Path, name: str) -> dict[str, Any]:
    ensure_safe_ancestors(kit_root, SOURCE_SKILLS / name)
    source_dir = kit_root / SOURCE_SKILLS / name
    if source_dir.is_symlink() or not source_dir.is_dir():
        raise AdoptionError(f"source skill does not exist as a real directory: {name}")
    if (
        not (source_dir / "SKILL.md").is_file()
        or (source_dir / "SKILL.md").is_symlink()
    ):
        raise AdoptionError(f"source skill is missing a real SKILL.md: {name}")

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
                else:
                    status_value = "CONFLICT"
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
    }


def build_plan(kit_root: Path, target_root: Path, skills: list[str]) -> dict[str, Any]:
    entries = [inspect_skill(kit_root, target_root, name) for name in skills]
    source_summary = [
        {"name": item["name"], "source_digest": item["source_digest"]}
        for item in entries
    ]
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "name": "agent-guidance-kit",
            "revision": git_revision(kit_root),
            "selected_digest": digest_bytes(canonical_json(source_summary)),
        },
        "target": {"skill_root": TARGET_SKILLS.as_posix()},
        "skills": entries,
    }
    payload["plan_id"] = digest_bytes(canonical_json(payload))
    return payload


def verify_plan_id(plan: dict[str, Any]) -> None:
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise AdoptionError(f"unsupported plan schema: {plan.get('schema_version')!r}")
    expected = plan.get("plan_id")
    unsigned = dict(plan)
    unsigned.pop("plan_id", None)
    actual = digest_bytes(canonical_json(unsigned))
    if not isinstance(expected, str) or expected != actual:
        raise AdoptionError("plan digest is missing or does not match the plan content")


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
        "schema_version": SCHEMA_VERSION,
        "plan_id": plan["plan_id"],
        "source": plan["source"],
        "result": "COMPLETED",
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


def validate_installed(target_root: Path, plan: dict[str, Any]) -> None:
    for item in plan["skills"]:
        destination = Path(item["destination"])
        validate_relative(destination, "receipt destination")
        path = target_root / destination
        if path.is_symlink() or not path.is_dir():
            raise AdoptionError(f"installed skill is missing or unsafe: {item['name']}")
        if manifest_digest(tree_manifest(path)) != item["source_digest"]:
            raise AdoptionError(
                f"installed skill no longer matches its receipt: {item['name']}"
            )


def apply_plan(kit_root: Path, target_root: Path, plan: dict[str, Any]) -> Path:
    verify_plan_id(plan)
    plan_skills = plan.get("skills")
    if not isinstance(plan_skills, list) or not plan_skills:
        raise AdoptionError("plan contains no skills")
    if any(not isinstance(item, dict) for item in plan_skills):
        raise AdoptionError("every plan skill entry must be a JSON object")
    skills = normalize_skills([str(item.get("name", "")) for item in plan_skills])
    if len(skills) != len(plan_skills):
        raise AdoptionError("plan skill names must be unique")
    for item in plan_skills:
        name = item["name"]
        if item.get("source") != (SOURCE_SKILLS / name).as_posix():
            raise AdoptionError(f"unexpected source path for skill: {name}")
        if item.get("destination") != (TARGET_SKILLS / name).as_posix():
            raise AdoptionError(f"unexpected destination path for skill: {name}")

    receipt_relative = RECEIPTS / f"{plan['plan_id']}.json"
    receipt_path = target_root / receipt_relative
    if receipt_path.exists() or receipt_path.is_symlink():
        if receipt_path.is_symlink() or not receipt_path.is_file():
            raise AdoptionError(f"receipt path is unsafe: {receipt_relative}")
        existing = read_json(receipt_path)
        if existing != receipt_for(plan):
            raise AdoptionError(f"existing receipt differs: {receipt_relative}")
        validate_installed(target_root, plan)
        return receipt_path

    current = build_plan(kit_root, target_root, skills)
    if current != plan:
        raise AdoptionError(
            "source or target state changed after planning; generate and approve a new plan"
        )
    conflicts = [
        item["name"] for item in plan_skills if item.get("status") == "CONFLICT"
    ]
    if conflicts:
        raise AdoptionError(f"plan contains conflicts: {', '.join(conflicts)}")
    unexpected = [
        item["name"]
        for item in plan_skills
        if item.get("status") not in {"CREATE", "UNCHANGED"}
    ]
    if unexpected:
        raise AdoptionError(
            f"plan contains unsupported statuses for: {', '.join(unexpected)}"
        )

    ensure_safe_ancestors(target_root, Path(".agents"), create=True)
    ensure_safe_ancestors(target_root, TARGET_SKILLS, create=True)
    ensure_safe_ancestors(target_root, RECEIPTS, create=True)
    if receipt_path.exists() or receipt_path.is_symlink():
        raise AdoptionError(f"receipt appeared during preflight: {receipt_relative}")

    staging_relative = (
        Path(".agents") / f".agent-guidance-kit-staging-{plan['plan_id'][:12]}"
    )
    staging = target_root / staging_relative
    if staging.exists() or staging.is_symlink():
        raise AdoptionError(f"staging path already exists: {staging_relative}")
    staging.mkdir()
    moved: list[tuple[Path, Path]] = []
    try:
        for item in plan_skills:
            if item["status"] != "CREATE":
                continue
            source = kit_root / Path(item["source"])
            staged = staging / item["name"]
            copy_manifest(source, staged, item["files"])
            if manifest_digest(tree_manifest(staged)) != item["source_digest"]:
                raise AdoptionError(f"staged copy digest mismatch: {item['name']}")

        for item in plan_skills:
            if item["status"] != "CREATE":
                continue
            staged = staging / item["name"]
            destination = target_root / Path(item["destination"])
            if destination.exists() or destination.is_symlink():
                raise AdoptionError(
                    f"destination appeared during apply: {item['destination']}"
                )
            os.replace(staged, destination)
            moved.append((destination, staged))

        validate_installed(target_root, plan)
        receipt = receipt_for(plan)
        with receipt_path.open("x", encoding="utf-8") as handle:
            json.dump(receipt, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except Exception:
        for destination, staged in reversed(moved):
            if (
                destination.exists()
                and not destination.is_symlink()
                and not staged.exists()
            ):
                os.replace(destination, staged)
        raise
    finally:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)

    return receipt_path


def print_summary(plan: dict[str, Any]) -> None:
    print(f"Plan: {plan['plan_id']}")
    print(f"Source revision: {plan['source']['revision']}")
    print(f"Selected digest: {plan['source']['selected_digest']}")
    for item in plan["skills"]:
        detail = f" ({item['conflict']['reason']})" if item["conflict"] else ""
        print(f"{item['status']:9} {item['name']} -> {item['destination']}{detail}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Create a read-only adoption plan")
    plan_parser.add_argument("--kit-root", required=True)
    plan_parser.add_argument("--target", required=True)
    plan_parser.add_argument("--skill", action="append", required=True)
    plan_parser.add_argument(
        "--output", help="Write plan JSON to a new file; defaults to stdout"
    )

    apply_parser = subparsers.add_parser(
        "apply", help="Apply an unchanged approved plan"
    )
    apply_parser.add_argument("--kit-root", required=True)
    apply_parser.add_argument("--target", required=True)
    apply_parser.add_argument("--plan", required=True)
    apply_parser.add_argument(
        "--approve", action="store_true", help="Required explicit apply acknowledgement"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        kit_root = validate_root(Path(args.kit_root), "kit root")
        target_root = validate_root(Path(args.target), "target root")
        if args.command == "plan":
            skills = normalize_skills(args.skill)
            plan = build_plan(kit_root, target_root, skills)
            if args.output:
                write_new_json(Path(args.output).expanduser(), plan)
                print_summary(plan)
                print(f"Plan file: {Path(args.output).expanduser()}")
            else:
                json.dump(plan, sys.stdout, indent=2, sort_keys=True)
                sys.stdout.write("\n")
            return (
                1 if any(item["status"] == "CONFLICT" for item in plan["skills"]) else 0
            )

        if not args.approve:
            raise AdoptionError(
                "apply requires --approve after review of the exact plan"
            )
        plan = read_json(Path(args.plan).expanduser())
        receipt = apply_plan(kit_root, target_root, plan)
        print(f"Applied plan {plan['plan_id']}")
        print(f"Receipt: {receipt.relative_to(target_root)}")
        return 0
    except AdoptionError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
