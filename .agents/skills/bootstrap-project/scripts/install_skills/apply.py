"""Plan application for install_skills."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from .constants import (
    RECEIPTS,
    SCHEMA_VERSION,
    SOURCE_SKILLS,
    TARGET_SKILLS,
)
from .dependencies import dependency_closure, load_dependencies, normalize_skills
from .inspect import inspect_skill
from .manifest import (
    canonical_json,
    copy_manifest,
    digest_bytes,
    manifest_digest,
    tree_manifest,
)
from .receipts import read_json, receipt_for, receipt_skill_digests, write_new_json
from .routing import inspect_routing, restore_routing, write_routing
from .source import (
    configure_source_locator,
    restore_source_locator,
    source_resolution_plan,
)
from .utils import read_text_exact
from .validation import (
    AdoptionError,
    ensure_safe_ancestors,
    validate_relative,
    validate_root,
)


def verify_plan_id(plan: dict[str, Any]) -> None:
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise AdoptionError(f"unsupported plan schema: {plan.get('schema_version')!r}")
    expected = plan.get("plan_id")
    unsigned = dict(plan)
    unsigned.pop("plan_id", None)
    actual = digest_bytes(canonical_json(unsigned))
    if not isinstance(expected, str) or expected != actual:
        raise AdoptionError("plan digest is missing or does not match the plan content")


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
    from .routing import managed_route_block

    route_block_text = managed_route_block(read_text_exact(route_path))
    from .manifest import digest_bytes

    route_digest = (
        digest_bytes(route_block_text.encode("utf-8"))
        if route_block_text is not None
        else None
    )
    if route_digest != routing.get("block_digest"):
        raise AdoptionError("managed AGENTS route changed after adoption")


# Module-level reference to allow monkey-patching in tests
validate_installed_impl = validate_installed


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
    expected_skills, _ = dependency_closure(requested, dependencies, kit_root)
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
        validate_installed_impl(target_root, plan)
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
        validate_installed_impl(target_root, plan)
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


def build_plan(kit_root: Path, target_root: Path, skills: list[str]) -> dict[str, Any]:
    kit_root = validate_root(kit_root, "kit root")
    target_root = validate_root(target_root, "target root")
    dependencies = load_dependencies(kit_root)
    selected, automatically_added = dependency_closure(skills, dependencies, kit_root)
    adopted_digests = receipt_skill_digests(target_root)
    entries = [
        inspect_skill(kit_root, target_root, name, dependencies, adopted_digests)
        for name in selected
    ]
    source_summary = [
        {"name": item["name"], "source_digest": item["source_digest"]}
        for item in entries
    ]
    from .manifest import git_revision

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


def _is_text_file(path: Path) -> bool:
    try:
        path.read_text(encoding="utf-8")
        return True
    except UnicodeDecodeError:
        return False
    except OSError:
        return False


def generate_diff(plan: dict[str, Any], kit_root: Path, target_root: Path) -> str:
    lines: list[str] = []
    # Skill file diffs
    for item in plan["skills"]:
        status = item["status"]
        if status == "UNCHANGED":
            continue
        name = item["name"]
        source_base = kit_root / Path(item["source"])
        dest_base = target_root / Path(item["destination"])
        if status == "CONFLICT":
            lines.append(
                f"--- CONFLICT {name}: {item['conflict']['reason'] if item['conflict'] else 'unknown'}"
            )
            continue
        if status == "CREATE":
            lines.append(
                f"--- CREATE {name} -> {item['destination']} ({len(item['files'])} files)"
            )
            for f in item["files"]:
                lines.append(f"+++ {f['path']}")
            continue
        if status == "UPDATE":
            lines.append(f"--- UPDATE {name} -> {item['destination']}")
            for manifest_item in item["files"]:
                rel = Path(manifest_item["path"])
                src = source_base / rel
                dst = dest_base / rel
                if not dst.exists():
                    lines.append(f"+++ new file {rel}")
                    continue
                # Only diff text files
                if not _is_text_file(src) or not _is_text_file(dst):
                    lines.append(
                        f"*** binary or unreadable {rel} (sha {manifest_item['sha256'][:8]})"
                    )
                    continue
                try:
                    src_text = src.read_text(encoding="utf-8").splitlines(keepends=True)
                    dst_text = dst.read_text(encoding="utf-8").splitlines(keepends=True)
                except OSError:
                    continue
                if src_text == dst_text:
                    continue
                diff = difflib.unified_diff(
                    dst_text,
                    src_text,
                    fromfile=f"a/{rel}",
                    tofile=f"b/{rel}",
                    lineterm="",
                )
                diff_text = "\n".join(diff)
                if diff_text:
                    lines.append(diff_text)
    # Routing diff
    routing = plan.get("routing", {})
    rstatus = routing.get("status")
    if rstatus and rstatus not in {"UNCHANGED", "CONFLICT"}:
        try:
            rel = Path(str(routing.get("path", "")))
            current_path = target_root / rel
            current = (
                current_path.read_text(encoding="utf-8")
                if current_path.exists()
                else ""
            )
            # Render desired routing content
            from .routing import render_routing

            desired = render_routing(current, routing.get("block", ""))
            if current != desired:
                lines.append(f"--- ROUTING {rel} ({rstatus})")
                diff = difflib.unified_diff(
                    current.splitlines(keepends=True),
                    desired.splitlines(keepends=True),
                    fromfile=f"a/{rel}",
                    tofile=f"b/{rel}",
                    lineterm="",
                )
                diff_text = "\n".join(diff)
                if diff_text:
                    lines.append(diff_text)
        except Exception:
            pass
    elif rstatus == "CONFLICT":
        lines.append(
            f"--- ROUTING CONFLICT {routing.get('path')}: {routing.get('conflict', {}).get('reason', 'unknown')}"
        )
    # Harness & AGENTS.md recommendations are deterministic diagnostics. The
    # recommender is kit-owned code executed from the selected kit_root; failures
    # are surfaced rather than silently masked as successful advisory output.
    try:
        import importlib.util
        import sys as _sys

        harness_script = kit_root / "scripts" / "harness_recommendations.py"
        if not harness_script.is_file():
            harness_script = (
                Path(__file__).resolve().parents[0]
                / "scripts"
                / "harness_recommendations.py"
            )
        if not harness_script.is_file():
            raise FileNotFoundError(
                f"harness_recommendations.py not found under {kit_root}"
            )
        spec = importlib.util.spec_from_file_location(
            "harness_recommendations", harness_script
        )
        hr = importlib.util.module_from_spec(spec)
        _sys.modules["harness_recommendations"] = hr
        spec.loader.exec_module(hr)
        hr_recs = hr.collect_harness_recommendations(kit_root, target_root)
    except (FileNotFoundError, ImportError, OSError, ValueError) as error:
        lines.append(
            "--- HARNESS & AGENTS.md RECOMMENDATIONS (informational, no auto-apply) ---"
        )
        lines.append(f"*** recommender unavailable: {error}")
        return "\n".join(lines) + ("\n" if lines else "")

    if hr_recs:
        lines.append(
            "--- HARNESS & AGENTS.md RECOMMENDATIONS (informational, no auto-apply) ---"
        )
        for rec in hr_recs:
            lines.append(f"*** {rec['file']} [{rec['status']}]: {rec['reason']}")
            lines.append(f"    -> {rec['action']}")
            if rec.get("current") is not None and rec.get("desired") is not None:
                diff = difflib.unified_diff(
                    rec["current"].splitlines(keepends=True),
                    rec["desired"].splitlines(keepends=True),
                    fromfile=f"a/{rec['file']}",
                    tofile=f"b/{rec['file']}",
                    lineterm="",
                )
                dtext = "\n".join(diff)
                if dtext.strip():
                    lines.append(dtext)
        lines.append(
            "*** Run: python scripts/harness_recommendations.py --kit-root <kit> --target <target> --diff"
        )
        lines.append(
            "*** Then apply via harness-adaptation / skill-authoring with approval gate."
        )
    return "\n".join(lines) + ("\n" if lines else "")


def print_diff(plan: dict[str, Any], kit_root: Path, target_root: Path) -> None:
    diff = generate_diff(plan, kit_root, target_root)
    if diff:
        sys.stdout.write(diff)
        if not diff.endswith("\n"):
            sys.stdout.write("\n")
    else:
        print("(no diff: plan is unchanged)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan and apply receipt-aware skill adoption from Agent Guidance Kit."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Create a read-only adoption plan")
    plan_parser.add_argument("--kit-root", required=True)
    plan_parser.add_argument("--target", required=True)
    plan_parser.add_argument("--skill", action="append", required=True)
    plan_parser.add_argument(
        "--output", help="Write plan JSON to a new file; defaults to stdout"
    )
    plan_parser.add_argument(
        "--diff",
        action="store_true",
        help="Show unified diff of planned skill and routing changes",
    )
    plan_parser.add_argument(
        "--check",
        action="store_true",
        help="Conflict-only check: do not write plan file, exit 1 if conflicts exist",
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
            has_conflict = (
                any(item["status"] == "CONFLICT" for item in plan["skills"])
                or plan["routing"]["status"] == "CONFLICT"
                or plan["source_resolution"]["status"] in {"CONFLICT", "ASK"}
            )
            # --check is conflict-only: no file write, no JSON to stdout, just summary
            if getattr(args, "check", False):
                if getattr(args, "diff", False):
                    print_diff(plan, kit_root, target_root)
                else:
                    print_summary(plan)
                if has_conflict:
                    print("CHECK: conflicts detected", file=sys.stderr)
                else:
                    print("CHECK: no conflicts")
                return 1 if has_conflict else 0
            if getattr(args, "diff", False):
                print_diff(plan, kit_root, target_root)
                # Still emit plan JSON / file after diff unless --check
            if args.output:
                write_new_json(Path(args.output).expanduser(), plan)
                print_summary(plan)
                print(f"Plan file: {Path(args.output).expanduser()}")
            else:
                if getattr(args, "diff", False):
                    # Separate diff from JSON with a marker when both go to stdout
                    print("--- PLAN JSON ---")
                json.dump(plan, sys.stdout, indent=2, sort_keys=True)
                sys.stdout.write("\n")
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
