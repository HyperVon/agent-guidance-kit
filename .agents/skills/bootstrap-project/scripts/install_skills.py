#!/usr/bin/env python3
"""Plan and apply receipt-aware skill adoption from Agent Guidance Kit."""

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
from urllib.parse import unquote, urlsplit

SCHEMA_VERSION = 2
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
SOURCE_SKILLS = Path(".agents/skills")
TARGET_SKILLS = Path(".agents/skills")
DEPENDENCIES = Path(".agents/skill-dependencies.json")
RECEIPTS = Path(".agents/.agent-guidance-kit/receipts")
SOURCE_LOCATOR = Path(".agents/.agent-guidance-kit/source.json")
SOURCE_ENVIRONMENT = "AGENT_GUIDANCE_KIT_ROOT"
MANDATORY_SKILL = "agent-guidance-maintenance"
ROUTE_START = "<!-- agent-guidance-kit:routes:start -->"
ROUTE_END = "<!-- agent-guidance-kit:routes:end -->"
TRANSIENT_DIRS = {"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
TRANSIENT_FILES = {".DS_Store"}
TRANSIENT_SUFFIXES = {".pyc", ".pyo", ".swp"}
# Evaluation cases validate the kit and are not runtime guidance for targets.
SOURCE_ONLY_DIRS = {"evals"}


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


def load_dependencies(kit_root: Path) -> dict[str, dict[str, Any]]:
    path = kit_root / DEPENDENCIES
    if path.is_symlink() or not path.is_file():
        raise AdoptionError(f"missing real skill dependency catalog: {DEPENDENCIES}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AdoptionError(f"cannot read skill dependency catalog: {error}") from error
    skills = value.get("skills") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 1
        or not isinstance(skills, dict)
    ):
        raise AdoptionError("unsupported or malformed skill dependency catalog")
    source_names = {
        path.name
        for path in (kit_root / SOURCE_SKILLS).iterdir()
        if path.is_dir() and not path.is_symlink() and not path.name.startswith(".")
    }
    if set(skills) != source_names:
        missing = sorted(source_names - set(skills))
        extra = sorted(set(skills) - source_names)
        raise AdoptionError(
            "skill dependency catalog does not match source skills; "
            f"missing={missing}, extra={extra}"
        )
    for name, entry in skills.items():
        if not isinstance(entry, dict):
            raise AdoptionError(f"dependency entry must be an object: {name}")
        requires = entry.get("requires")
        related = entry.get("related")
        route = entry.get("route")
        if not isinstance(requires, list) or not isinstance(related, list):
            raise AdoptionError(f"dependency lists are required for skill: {name}")
        if any(
            not isinstance(item, str) or item not in source_names
            for item in requires + related
        ):
            raise AdoptionError(f"dependency entry references an unknown skill: {name}")
        if name in requires or name in related or set(requires) & set(related):
            raise AdoptionError(
                f"dependency entry is self-referential or overlapping: {name}"
            )
        if (
            not isinstance(route, str)
            or not route.strip()
            or "|" in route
            or "\n" in route
        ):
            raise AdoptionError(
                f"dependency entry has an invalid route description: {name}"
            )
    return skills


def dependency_closure(
    requested: list[str], dependencies: dict[str, dict[str, Any]]
) -> tuple[list[str], dict[str, list[str]]]:
    missing = sorted(set(requested) - set(dependencies))
    if missing:
        raise AdoptionError(f"unknown selected skills: {', '.join(missing)}")
    selected = set(requested)
    automatically_added: dict[str, list[str]] = {}
    if MANDATORY_SKILL not in selected:
        selected.add(MANDATORY_SKILL)
        automatically_added[MANDATORY_SKILL] = ["required maintenance entrypoint"]
    pending = sorted(selected)
    while pending:
        name = pending.pop(0)
        for required in dependencies[name]["requires"]:
            automatically_added.setdefault(required, []).append(f"required by {name}")
            if required not in selected:
                selected.add(required)
                pending.append(required)
    return sorted(selected), {
        name: sorted(set(reasons))
        for name, reasons in sorted(automatically_added.items())
    }


def validate_declared_links(
    source_dir: Path, name: str, dependencies: dict[str, dict[str, Any]]
) -> None:
    linked: set[str] = set()
    source_root = source_dir.resolve()
    skills_root = source_dir.parent.resolve()
    for path in sorted(source_dir.rglob("*.md")):
        if path.is_symlink():
            raise AdoptionError(f"symlinked Markdown is not allowed: {path}")
        for raw_target in MARKDOWN_LINK.findall(path.read_text(encoding="utf-8")):
            target = raw_target.strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            split = urlsplit(target)
            if split.scheme or target.startswith("#") or not split.path:
                continue
            candidate = (path.parent / unquote(split.path)).resolve()
            try:
                candidate.relative_to(source_root)
                continue
            except ValueError:
                pass
            try:
                relative_to_skills = candidate.relative_to(skills_root)
            except ValueError as error:
                raise AdoptionError(
                    f"skill {name} has a relative link outside the portable catalog: {target}"
                ) from error
            dependency = relative_to_skills.parts[0]
            if dependency != name:
                linked.add(dependency)
    requires = set(dependencies[name]["requires"])
    undeclared = sorted(linked - requires)
    if undeclared:
        raise AdoptionError(
            f"skill {name} has relative links to non-required skills: {', '.join(undeclared)}"
        )


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
    resolver = kit_root / SOURCE_SKILLS / MANDATORY_SKILL / "scripts/resolve_source.py"
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


def managed_route_names(text: str) -> set[str]:
    if text.count(ROUTE_START) != 1 or text.count(ROUTE_END) != 1:
        return set()
    block = text.split(ROUTE_START, 1)[1].split(ROUTE_END, 1)[0]
    return set(re.findall(r"skills/([a-z0-9-]+)/SKILL\.md", block))


def managed_route_block(text: str) -> str | None:
    if text.count(ROUTE_START) != 1 or text.count(ROUTE_END) != 1:
        return None
    body = text.split(ROUTE_START, 1)[1].split(ROUTE_END, 1)[0]
    return f"{ROUTE_START}{body}{ROUTE_END}"


def read_text_exact(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as error:
        raise AdoptionError(
            f"cannot read UTF-8 routing file: {path}: {error}"
        ) from error


def newline_sequence(text: str) -> str:
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    cr = text.count("\r") - crlf
    if crlf and crlf >= lf and crlf >= cr:
        return "\r\n"
    if lf and lf >= cr:
        return "\n"
    if cr:
        return "\r"
    return os.linesep


def routing_path(target_root: Path) -> Path:
    nested = target_root / ".agents/AGENTS.md"
    root = target_root / "AGENTS.md"
    managed: list[Path] = []
    for path in (nested, root):
        if path.exists() or path.is_symlink():
            if path.is_symlink() or not path.is_file():
                raise AdoptionError(
                    f"routing owner must be a real file: {path.relative_to(target_root)}"
                )
            if ROUTE_START in read_text_exact(path):
                managed.append(path)
    if len(managed) > 1:
        raise AdoptionError("multiple managed Agent Guidance Kit route blocks exist")
    if managed:
        return managed[0]
    for path in (nested, root):
        if path.is_file() and not path.is_symlink():
            return path
    return root


def route_block(
    target_root: Path,
    path: Path,
    names: set[str],
    dependencies: dict[str, dict[str, Any]],
    newline: str,
) -> str:
    if path.parent == target_root / ".agents":
        prefix = "skills"
    else:
        prefix = ".agents/skills"
    lines = [
        ROUTE_START,
        "## Agent Guidance Kit skills",
        "",
        "These receipt-managed skills were adopted from Agent Guidance Kit.",
        "",
        "| Task | Skill |",
        "| :--- | :--- |",
    ]
    for name in sorted(names):
        route = dependencies[name]["route"]
        lines.append(f"| {route} | [{name}]({prefix}/{name}/SKILL.md) |")
    lines.extend([ROUTE_END, ""])
    return newline.join(lines)


def render_routing(current: str, block: str) -> str:
    start_count = current.count(ROUTE_START)
    end_count = current.count(ROUTE_END)
    if start_count == 0 and end_count == 0:
        newline = newline_sequence(current or block)
        separator = (
            ""
            if not current or current.endswith(newline * 2)
            else newline
            if current.endswith(newline)
            else newline * 2
        )
        return f"{current}{separator}{block}"
    if start_count != 1 or end_count != 1:
        raise AdoptionError("managed Agent Guidance Kit route block is malformed")
    before, remainder = current.split(ROUTE_START, 1)
    _, after = remainder.split(ROUTE_END, 1)
    return f"{before}{block.rstrip()}{after}"


def inspect_routing(
    target_root: Path,
    entries: list[dict[str, Any]],
    dependencies: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    path = routing_path(target_root)
    relative = path.relative_to(target_root)
    current = read_text_exact(path) if path.exists() else ""
    existing_names = managed_route_names(current)
    receipt_names = set(receipt_skill_digests(target_root))
    selected_names = {entry["name"] for entry in entries}
    names = (existing_names | receipt_names | selected_names) & set(dependencies)
    block = route_block(
        target_root, path, names, dependencies, newline_sequence(current)
    )
    block_digest = digest_bytes(block.rstrip().encode("utf-8"))
    conflict = None
    missing_receipt_skills = sorted(
        name
        for name in receipt_names
        if not (target_root / TARGET_SKILLS / name / "SKILL.md").is_file()
        or (target_root / TARGET_SKILLS / name / "SKILL.md").is_symlink()
    )
    if missing_receipt_skills:
        desired = current
        status_value = "CONFLICT"
        conflict = {
            "reason": "receipt-owned skills are missing or unsafe: "
            + ", ".join(missing_receipt_skills)
        }
    else:
        try:
            desired = render_routing(current, block)
        except AdoptionError as error:
            desired = current
            status_value = "CONFLICT"
            conflict = {"reason": str(error)}
        else:
            if not path.exists():
                status_value = "CREATE"
            elif desired == current:
                status_value = "UNCHANGED"
            elif ROUTE_START in current:
                existing_block = managed_route_block(current)
                existing_digest = (
                    digest_bytes(existing_block.encode("utf-8"))
                    if existing_block is not None
                    else None
                )
                if existing_digest not in receipt_route_block_digests(target_root):
                    status_value = "CONFLICT"
                    conflict = {
                        "reason": "managed route block differs from receipt-owned content"
                    }
                else:
                    status_value = "UPDATE"
            else:
                status_value = "APPEND"
    return {
        "path": relative.as_posix(),
        "status": status_value,
        "before_digest": digest_bytes(current.encode("utf-8"))
        if path.exists()
        else None,
        "after_digest": digest_bytes(desired.encode("utf-8")),
        "skills": sorted(names),
        "block": block,
        "block_digest": block_digest,
        "conflict": conflict,
    }


def build_plan(kit_root: Path, target_root: Path, skills: list[str]) -> dict[str, Any]:
    kit_root = validate_root(kit_root, "kit root")
    target_root = validate_root(target_root, "target root")
    dependencies = load_dependencies(kit_root)
    selected, automatically_added = dependency_closure(skills, dependencies)
    adopted_digests = receipt_skill_digests(target_root)
    entries = [
        inspect_skill(kit_root, target_root, name, dependencies, adopted_digests)
        for name in selected
    ]
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
        "source_resolution": source_resolution_plan(kit_root, target_root),
        "selection": {
            "requested": sorted(skills),
            "automatically_added": automatically_added,
        },
        "target": {"skill_root": TARGET_SKILLS.as_posix()},
        "skills": entries,
    }
    payload["routing"] = inspect_routing(target_root, entries, dependencies)
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
    routing = plan.get("routing")
    if not isinstance(routing, dict):
        raise AdoptionError("plan routing entry is missing")
    route_path = target_root / Path(str(routing.get("path", "")))
    if route_path.is_symlink() or not route_path.is_file():
        raise AdoptionError("managed AGENTS route file is missing or unsafe")
    route_block_text = managed_route_block(read_text_exact(route_path))
    route_digest = (
        digest_bytes(route_block_text.encode("utf-8"))
        if route_block_text is not None
        else None
    )
    if route_digest != routing.get("block_digest"):
        raise AdoptionError("managed AGENTS route changed after adoption")


def write_routing(
    target_root: Path, routing: dict[str, Any], plan_id: str
) -> bytes | None:
    relative = Path(str(routing.get("path", "")))
    validate_relative(relative, "routing path")
    path = target_root / relative
    before = path.read_bytes() if path.exists() else None
    before_digest = digest_bytes(before) if before is not None else None
    if before_digest != routing.get("before_digest"):
        raise AdoptionError("managed AGENTS route changed after planning")
    try:
        current = before.decode("utf-8") if before is not None else ""
    except UnicodeDecodeError as error:
        raise AdoptionError(f"managed AGENTS route is not UTF-8: {relative}") from error
    desired = render_routing(current, str(routing.get("block", "")))
    if digest_bytes(desired.encode("utf-8")) != routing.get("after_digest"):
        raise AdoptionError("managed AGENTS route does not match the approved plan")
    path.parent.mkdir(parents=True, exist_ok=True)
    if before is None:
        with path.open("xb") as handle:
            handle.write(desired.encode("utf-8"))
        return None
    temporary = path.parent / f".{path.name}.agent-guidance-kit-{plan_id[:12]}"
    if temporary.exists() or temporary.is_symlink():
        raise AdoptionError(f"temporary routing path already exists: {temporary}")
    with temporary.open("xb") as handle:
        handle.write(desired.encode("utf-8"))
    os.replace(temporary, path)
    return before


def restore_routing(
    target_root: Path, routing: dict[str, Any], before: bytes | None
) -> None:
    path = target_root / Path(routing["path"])
    if before is None:
        if path.exists() and not path.is_symlink():
            path.unlink()
        return
    temporary = path.parent / f".{path.name}.agent-guidance-kit-rollback"
    if temporary.exists() and not temporary.is_symlink():
        temporary.unlink()
    with temporary.open("xb") as handle:
        handle.write(before)
    os.replace(temporary, path)


def apply_plan(kit_root: Path, target_root: Path, plan: dict[str, Any]) -> Path:
    kit_root = validate_root(kit_root, "kit root")
    target_root = validate_root(target_root, "target root")
    verify_plan_id(plan)
    plan_skills = plan.get("skills")
    if not isinstance(plan_skills, list) or not plan_skills:
        raise AdoptionError("plan contains no skills")
    if any(not isinstance(item, dict) for item in plan_skills):
        raise AdoptionError("every plan skill entry must be a JSON object")
    planned_skills = normalize_skills(
        [str(item.get("name", "")) for item in plan_skills]
    )
    if len(planned_skills) != len(plan_skills):
        raise AdoptionError("plan skill names must be unique")
    selection = plan.get("selection")
    requested_value = (
        selection.get("requested") if isinstance(selection, dict) else None
    )
    if not isinstance(requested_value, list):
        raise AdoptionError("plan selection is missing requested skills")
    requested = normalize_skills([str(name) for name in requested_value])
    dependencies = load_dependencies(kit_root)
    expected_skills, _ = dependency_closure(requested, dependencies)
    if expected_skills != planned_skills:
        raise AdoptionError("plan skills do not match the declared dependency closure")
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

    current = build_plan(kit_root, target_root, requested)
    if current != plan:
        raise AdoptionError(
            "source or target state changed after planning; generate and approve a new plan"
        )
    conflicts = [
        item["name"] for item in plan_skills if item.get("status") == "CONFLICT"
    ]
    if conflicts:
        raise AdoptionError(f"plan contains conflicts: {', '.join(conflicts)}")
    routing = plan.get("routing")
    if not isinstance(routing, dict):
        raise AdoptionError("plan routing entry is missing")
    if routing.get("status") == "CONFLICT":
        reason = routing.get("conflict", {}).get("reason", "unknown conflict")
        raise AdoptionError(f"managed AGENTS routing conflict: {reason}")
    source_resolution = plan.get("source_resolution")
    if not isinstance(source_resolution, dict):
        raise AdoptionError("plan source resolution entry is missing")
    if source_resolution.get("status") in {"CONFLICT", "ASK"}:
        reason = source_resolution.get("reason", "future source is unresolved")
        raise AdoptionError(f"persistent source resolution requires input: {reason}")
    unexpected = [
        item["name"]
        for item in plan_skills
        if item.get("status") not in {"CREATE", "UPDATE", "UNCHANGED"}
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
    moved: list[tuple[str, Path, Path, Path | None]] = []
    route_applied = False
    route_before: bytes | None = None
    source_locator_state: tuple[dict[str, Any], dict[str, Any]] | None = None
    try:
        for item in plan_skills:
            if item["status"] not in {"CREATE", "UPDATE"}:
                continue
            source = kit_root / Path(item["source"])
            staged = staging / f"new-{item['name']}"
            copy_manifest(source, staged, item["files"])
            if manifest_digest(tree_manifest(staged)) != item["source_digest"]:
                raise AdoptionError(f"staged copy digest mismatch: {item['name']}")

        for item in plan_skills:
            if item["status"] not in {"CREATE", "UPDATE"}:
                continue
            staged = staging / f"new-{item['name']}"
            destination = target_root / Path(item["destination"])
            previous: Path | None = None
            if item["status"] == "CREATE":
                if destination.exists() or destination.is_symlink():
                    raise AdoptionError(
                        f"destination appeared during apply: {item['destination']}"
                    )
            else:
                if destination.is_symlink() or not destination.is_dir():
                    raise AdoptionError(
                        f"update destination is missing or unsafe: {item['destination']}"
                    )
                if manifest_digest(tree_manifest(destination)) != item["target_digest"]:
                    raise AdoptionError(
                        f"update destination changed during apply: {item['destination']}"
                    )
                previous = staging / f"previous-{item['name']}"
                os.replace(destination, previous)
            os.replace(staged, destination)
            moved.append((item["status"], destination, staged, previous))

        if routing.get("status") != "UNCHANGED":
            route_before = write_routing(target_root, routing, plan["plan_id"])
            route_applied = True
        if source_resolution.get("status") == "CONFIGURE":
            source_locator_state = configure_source_locator(
                kit_root, target_root, plan["plan_id"][:12]
            )
        validate_installed(target_root, plan)
        receipt = receipt_for(plan)
        with receipt_path.open("x", encoding="utf-8") as handle:
            json.dump(receipt, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except Exception:
        if source_locator_state is not None:
            restore_source_locator(
                source_locator_state[0],
                source_locator_state[1],
                f"{plan['plan_id'][:12]}-rollback",
            )
        if route_applied:
            restore_routing(target_root, routing, route_before)
        for status_value, destination, staged, previous in reversed(moved):
            if (
                destination.exists()
                and not destination.is_symlink()
                and not staged.exists()
            ):
                os.replace(destination, staged)
            if status_value == "UPDATE" and previous is not None and previous.exists():
                os.replace(previous, destination)
        raise
    finally:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)

    return receipt_path


def print_summary(plan: dict[str, Any]) -> None:
    print(f"Plan: {plan['plan_id']}")
    print(f"Source revision: {plan['source']['revision']}")
    print(f"Selected digest: {plan['source']['selected_digest']}")
    source_resolution = plan["source_resolution"]
    print(
        f"Future source: {source_resolution['method']} ({source_resolution['status']})"
    )
    print(f"Requested skills: {', '.join(plan['selection']['requested'])}")
    for name, reasons in plan["selection"]["automatically_added"].items():
        print(f"AUTO-ADD  {name}: {', '.join(reasons)}")
    for item in plan["skills"]:
        detail = f" ({item['conflict']['reason']})" if item["conflict"] else ""
        print(f"{item['status']:9} {item['name']} -> {item['destination']}{detail}")
    route = plan["routing"]
    detail = f" ({route['conflict']['reason']})" if route["conflict"] else ""
    print(f"{route['status']:9} managed routes -> {route['path']}{detail}")


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
            has_conflict = (
                any(item["status"] == "CONFLICT" for item in plan["skills"])
                or plan["routing"]["status"] == "CONFLICT"
                or plan["source_resolution"]["status"] in {"CONFLICT", "ASK"}
            )
            return 1 if has_conflict else 0

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
