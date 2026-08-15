"""Routing (AGENTS.md route block) handling for install_skills."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from .constants import ROUTE_END, ROUTE_START, TARGET_SKILLS
from .manifest import digest_bytes
from .utils import read_text_exact
from .validation import AdoptionError


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
    from .receipts import receipt_route_block_digests, receipt_skill_digests

    receipt_names = set(receipt_skill_digests(target_root))
    selected_names = {entry["name"] for entry in entries}
    names = (existing_names | receipt_names | selected_names) & set(dependencies)
    block = route_block(
        target_root, path, names, dependencies, newline_sequence(current)
    )
    from .manifest import digest_bytes

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


def write_routing(
    target_root: Path, routing: dict[str, Any], plan_id: str
) -> bytes | None:
    relative = Path(str(routing.get("path", "")))
    from .validation import validate_relative

    validate_relative(relative, "routing path")
    from .validation import ensure_safe_ancestors

    # Ensure ancestor chain contains no symlinks before creating parents.
    if relative.parent != Path("."):
        ensure_safe_ancestors(target_root, relative.parent, create=True)
    else:
        # For root-level routing file (AGENTS.md) the parent is the target root
        # itself; validation of the root was already done via validate_root.
        pass
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
    if temporary.exists() or temporary.is_symlink():
        # The rollback temp is always a path we created ourselves; a stale
        # regular file OR a leftover symlink (including a dangling one) must
        # be cleared so the exclusive create below does not fail and mask the
        # original exception being rolled back for.
        os.unlink(temporary)
    with temporary.open("xb") as handle:
        handle.write(before)
    os.replace(temporary, path)
