#!/usr/bin/env python3
"""Audit a target repository's Agent Guidance Kit adoption against the catalog.

Read-only, deterministic, network-free. Diffs the kit catalog (each skill's name
and description) against the skills the target has actually adopted (recorded in
receipts) and the target's own repository characteristics (via the bundled
project inventory) to surface catalog skills the target has not yet adopted but
that match its stack or activity.

This is the target-facing mirror of ``catalog-discovery``: that skill expands
the kit's own catalog and is ``SOURCE_ONLY``, while this audit helps an adopted
target discover net-new guidance it should consider. It proposes only; adoption
still requires the normal plan/approval gate via bootstrap-project.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

_HERE = Path(__file__).resolve().parent
_BOOTSTRAP = _HERE.parents[1] / "bootstrap-project" / "scripts"
for _p in (_HERE, _BOOTSTRAP):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

import inventory_project  # noqa: E402
import resolve_source  # noqa: E402

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - PyYAML is a declared dev dependency
    yaml = None  # type: ignore


CATALOG_SKILLS = Path(".agents/skills")
RECEIPTS = Path(".agents/.agent-guidance-kit/receipts")

# A skill is SOURCE_ONLY when it describes itself that way (catalog-discovery),
# not merely when it mentions the term while referring to another skill.
SOURCE_ONLY_RE = re.compile(r"(?:is|this skill) `SOURCE_ONLY`")


DEPENDENCY_MANIFESTS = {
    "Cargo.toml",
    "Gemfile",
    "Makefile",
    "Package.swift",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "go.mod",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "requirements.txt",
    "settings.gradle",
    "settings.gradle.kts",
}
FRONTEND_LANGUAGES = {"TypeScript", "JavaScript", "Vue"}


# --------------------------------------------------------------------------- #
# Catalog and receipt reading
# --------------------------------------------------------------------------- #
def _parse_frontmatter(text: str) -> tuple[Optional[dict], Optional[str]]:
    if not text.startswith("---"):
        return None, "missing frontmatter delimiters"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "unterminated frontmatter"
    body = text[3:end]
    if yaml is not None:
        try:
            values = yaml.safe_load(body)
        except yaml.YAMLError as error:  # type: ignore[attr-defined]
            return None, f"invalid YAML: {error}"
        if not isinstance(values, dict):
            return None, "frontmatter must be a mapping"
        return values, None
    values: dict[str, str] = {}
    for line in body.splitlines():
        if line.startswith("name:"):
            values["name"] = line.split(":", 1)[1].strip()
        elif line.startswith("description:"):
            values["description"] = line.split(":", 1)[1].strip()
    return values, None


def read_catalog(kit_root: Path) -> list[dict]:
    skills_root = Path(kit_root) / CATALOG_SKILLS
    catalog: list[dict] = []
    if not skills_root.is_dir() or skills_root.is_symlink():
        return catalog
    for directory in sorted(skills_root.iterdir()):
        if directory.name.startswith(".") or directory.is_symlink():
            continue
        if not directory.is_dir():
            continue
        skill_md = directory / "SKILL.md"
        if skill_md.is_symlink() or not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        values, error = _parse_frontmatter(text)
        if values is None:
            continue
        name = values.get("name", "")
        description = values.get("description", "")
        if not isinstance(name, str) or not isinstance(description, str):
            continue
        catalog.append(
            {
                "name": name,
                "description": description,
                "source_only": bool(SOURCE_ONLY_RE.search(text)),
            }
        )
    catalog.sort(key=lambda item: item["name"])
    return catalog


def read_adopted(target: Path) -> set[str]:
    names: set[str] = set()
    directory = Path(target) / RECEIPTS
    if not directory.is_dir() or directory.is_symlink():
        return names
    for path in sorted(directory.glob("*.json")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        skills = value.get("skills") if isinstance(value, dict) else None
        if not isinstance(skills, list):
            continue
        for item in skills:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str) and name:
                names.add(name)
    return names


# --------------------------------------------------------------------------- #
# Repository-characteristic signals
# --------------------------------------------------------------------------- #
def _has_dep_manifest(inv: dict) -> Optional[str]:
    build = set(inv.get("build_files") or [])
    present = sorted(build & DEPENDENCY_MANIFESTS)
    if present:
        return f"repo pins dependencies ({', '.join(present)})"
    return None


def _has_ci(inv: dict) -> Optional[str]:
    ci = inv.get("ci_files") or []
    if ci:
        shown = ", ".join(sorted(ci)[:3])
        suffix = "…" if len(ci) > 3 else ""
        return f"repo has CI configuration ({shown}{suffix})"
    return None


def _has_tests(inv: dict) -> Optional[str]:
    roots = inv.get("test_roots") or []
    if roots:
        return f"repo has test roots ({', '.join(sorted(roots))})"
    return None


def _has_frontend(inv: dict) -> Optional[str]:
    langs = set(inv.get("languages_by_file_count") or {})
    build = set(inv.get("build_files") or [])
    matched = sorted(langs & FRONTEND_LANGUAGES)
    if matched or "package.json" in build or "Vue" in langs:
        label = ", ".join(matched) or "package.json"
        return f"repo has a frontend/browser stack ({label})"
    return None


def _multi_harness(inv: dict) -> Optional[str]:
    markers = inv.get("harness_markers") or []
    if len(markers) >= 2:
        shown = ", ".join(sorted(markers)[:3])
        return f"target already integrates multiple harnesses ({shown})"
    return None


def _local_skills(inv: dict) -> Optional[str]:
    guidance = inv.get("guidance_files") or []
    local = [
        g
        for g in guidance
        if g.endswith("SKILL.md") and not g.startswith(".agents/skills/")
    ]
    if local:
        return f"target maintains local skills ({', '.join(local[:3])})"
    return None


def _git_repo(inv: dict) -> Optional[str]:
    git = inv.get("git") or {}
    if git.get("repository"):
        return "target is a Git repository that could contribute improvements upstream"
    return None


def _deployed(inv: dict) -> Optional[str]:
    if _has_dep_manifest(inv) and _has_ci(inv):
        return (
            "repo is a deployed service (dependencies + CI); a design-time "
            "threat model applies"
        )
    return None


def _git_with_ci(inv: dict) -> Optional[str]:
    if _git_repo(inv) and _has_ci(inv):
        return "repo uses Git with CI; branch/commit/PR hygiene applies"
    return None


def _authoring_or_upstream(inv: dict) -> Optional[str]:
    return _local_skills(inv) or _git_repo(inv)


SIGNALS: dict[str, list[Callable[[dict], Optional[str]]]] = {
    "dependency-upgrade": [_has_dep_manifest],
    "security-review": [_has_dep_manifest],
    "threat-modeling": [_deployed],
    "git-github-workflow": [_git_with_ci],
    "quality-hardening": [_has_tests],
    "frontend-quality-review": [_has_frontend],
    "harness-adaptation": [_multi_harness],
    "skill-authoring": [_local_skills],
    "skill-reviewer": [_local_skills],
    "rules-and-skills-audit": [_local_skills],
    "skill-evaluation": [_local_skills],
    "skill-optimizer": [_local_skills],
    "upstream-contribution": [_authoring_or_upstream],
}


def match_signals(name: str, inv: dict) -> list[str]:
    reasons: list[str] = []
    for predicate in SIGNALS.get(name, []):
        reason = predicate(inv)
        if reason:
            reasons.append(reason)
    return reasons


# --------------------------------------------------------------------------- #
# Report assembly
# --------------------------------------------------------------------------- #
def git_revision(root: Path) -> str:
    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        status = subprocess.run(
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
    if status.returncode == 0 and status.stdout.strip():
        revision += "+dirty"
    return revision


def run_audit(kit_root: Path, target: Path) -> dict:
    kit_root = resolve_source.validate_kit_root(Path(kit_root))
    target_path = Path(target).expanduser().resolve()
    if target_path.is_symlink() or not target_path.is_dir():
        raise ValueError(f"target must be a real directory: {target_path}")
    catalog = read_catalog(kit_root)
    adopted = read_adopted(target_path)
    inventory = inventory_project.inventory(target_path, 50_000)

    suggestions: list[dict] = []
    available: list[dict] = []
    excluded: list[str] = []
    for skill in catalog:
        if skill["source_only"]:
            excluded.append(skill["name"])
            continue
        if skill["name"] in adopted:
            continue
        entry = {
            "name": skill["name"],
            "description": skill["description"],
        }
        reasons = match_signals(skill["name"], inventory)
        if reasons:
            entry["reasons"] = reasons
            suggestions.append(entry)
        else:
            available.append(entry)
    suggestions.sort(key=lambda item: item["name"])
    available.sort(key=lambda item: item["name"])

    return {
        "schema_version": 1,
        "kit_root": str(kit_root),
        "kit_revision": git_revision(kit_root),
        "target": str(target_path),
        "catalog_total": len(catalog),
        "adopted": sorted(adopted),
        "adopted_count": len(adopted),
        "source_only_excluded": sorted(excluded),
        "suggestions": suggestions,
        "available": available,
        "repo_signals": {
            "languages": inventory.get("languages_by_file_count", {}),
            "build_files": inventory.get("build_files", []),
            "test_roots": inventory.get("test_roots", []),
            "ci_files": inventory.get("ci_files", []),
            "harness_markers": inventory.get("harness_markers", []),
        },
    }


def _first_sentence(description: str) -> str:
    trimmed = description.strip()
    index = trimmed.find(". ")
    if index != -1:
        return trimmed[: index + 1]
    return trimmed


def markdown_report(report: dict) -> str:
    lines = [
        "# Agent Guidance Kit adoption audit",
        "",
        f"- Target: `{report['target']}`",
        f"- Kit: `{report['kit_root']}` @ `{report['kit_revision']}`",
        f"- Adopted: **{report['adopted_count']}** of "
        f"**{report['catalog_total']}** catalog skills",
    ]
    if report["source_only_excluded"]:
        lines.append(
            f"- Maintainer-only (excluded): {', '.join(report['source_only_excluded'])}"
        )
    lines.extend(
        [
            "",
            f"## Suggested by target characteristics ({len(report['suggestions'])})",
            "",
        ]
    )
    if report["suggestions"]:
        for skill in report["suggestions"]:
            lines.append(
                f"- **{skill['name']}** — {_first_sentence(skill['description'])}"
            )
            for reason in skill.get("reasons", []):
                lines.append(f"  - {reason}")
    else:
        lines.append("None — every applicable catalog skill appears adopted.")
    lines.extend(
        [
            "",
            f"## Other catalog skills available ({len(report['available'])})",
            "",
        ]
    )
    if report["available"]:
        for skill in report["available"]:
            lines.append(
                f"- **{skill['name']}** — {_first_sentence(skill['description'])}"
            )
    else:
        lines.append("None.")
    lines.extend(
        [
            "",
            "## Canonical guidance to review",
            "",
            "Compare source-owned `.agents/AGENTS.md` and `.agents/OPERATING.md` "
            "against the target (agent-guidance-maintenance step 4) and decide "
            "ADAPT / KEEP_LOCAL / DEFER for any changed section.",
            "",
            "Adoption of any suggested skill still requires the normal "
            "plan/approval gate via bootstrap-project.",
            "",
        ]
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Target repository root")
    parser.add_argument(
        "--kit-root",
        default=None,
        help="Kit checkout root (resolved automatically when omitted)",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    target = Path(args.target).expanduser()
    if target.is_symlink() or not target.is_dir():
        print(f"error: target must be a real directory: {target}", file=sys.stderr)
        return 2
    try:
        if args.kit_root:
            kit_root = resolve_source.validate_kit_root(
                Path(args.kit_root).expanduser()
            )
        else:
            kit_root, _method = resolve_source.resolve_source(target)
    except resolve_source.SourceResolutionError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    try:
        report = run_audit(kit_root, target)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.format == "markdown":
        sys.stdout.write(markdown_report(report))
    else:
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
