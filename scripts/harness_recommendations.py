#!/usr/bin/env python3
"""Generate paste-ready recommendations for AGENTS.md and harness entrypoints.

Compares a target repository's AGENTS.md hierarchy and harness adapters
(CLAUDE.md, GEMINI.md, .github/copilot-instructions.md, .cursor/rules, etc.)
against the kit's canonical guidance, without overwriting local divergence.

Deterministic, standard-library only, network-free.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT_AGENTS = ROOT / ".agents/AGENTS.md"
KIT_OPERATING = ROOT / ".agents/OPERATING.md"
KIT_ROOT_AGENTS = ROOT / "AGENTS.md"
KIT_CLAUDE = ROOT / "CLAUDE.md"
KIT_GEMINI = ROOT / "GEMINI.md"
KIT_COPILOT = ROOT / ".github/copilot-instructions.md"

HARNESS_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
    ".cursor/rules",
    ".cursorrules",
    ".clinerules",
    ".claude/settings.json",
    ".claude/settings.local.json",
]


def read_text_safe(path: Path) -> str | None:
    try:
        if path.is_symlink() or not path.is_file():
            return None
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def is_thin_root_agents(text: str) -> bool:
    # Thin root AGENTS.md should reference .agents/AGENTS.md and be short
    has_ref = ".agents/AGENTS.md" in text
    # Thick file contains canonical invariants duplicated
    thick_markers = ["Product boundary", "Repository invariants", "Skill index"]
    thick_count = sum(1 for m in thick_markers if m in text)
    # Thin if has ref and not thick, and < 40 lines
    lines = text.splitlines()
    return has_ref and thick_count == 0 and len(lines) < 40


def expected_root_agents() -> str:
    try:
        return KIT_ROOT_AGENTS.read_text(encoding="utf-8")
    except OSError:
        return "# Agent instructions\n\nThis file is the thin universal entrypoint.\n"


def expected_claude() -> str:
    try:
        return KIT_CLAUDE.read_text(encoding="utf-8")
    except OSError:
        return "@AGENTS.md\n@.agents/AGENTS.md\n@.agents/OPERATING.md\n"


def expected_gemini() -> str:
    try:
        return KIT_GEMINI.read_text(encoding="utf-8")
    except OSError:
        return "@./AGENTS.md\n@./.agents/AGENTS.md\n@./.agents/OPERATING.md\n"


def expected_copilot() -> str:
    try:
        return KIT_COPILOT.read_text(encoding="utf-8")
    except OSError:
        return "# GitHub Copilot instructions\n\nSee AGENTS.md\n"


def recommendation_for_file(
    target_root: Path, kit_root: Path, relative: str
) -> dict | None:
    target_path = target_root / relative
    kit_path = kit_root / relative if (kit_root / relative).exists() else None

    # Only recommend if file exists in target or is expected as thin adapter
    text = read_text_safe(target_path)

    # Special handling per file
    if relative == "AGENTS.md":
        if text is None:
            return {
                "file": relative,
                "status": "CREATE",
                "reason": "Missing thin root AGENTS.md entrypoint",
                "current": "",
                "desired": expected_root_agents(),
                "action": "Create thin pointer to .agents/AGENTS.md (keep canonical policy in .agents/AGENTS.md only)",
            }
        if is_thin_root_agents(text):
            return None  # OK
        # Thick or missing reference
        if ".agents/AGENTS.md" not in text:
            return {
                "file": relative,
                "status": "RECOMMEND",
                "reason": "Root AGENTS.md does not reference canonical .agents/AGENTS.md",
                "current": text,
                "desired": expected_root_agents(),
                "action": "Replace with thin pointer; move project-specific invariants to .agents/AGENTS.md via harness-adaptation",
            }
        # Has reference but also thick
        if any(m in text for m in ["Product boundary", "Repository invariants"]):
            return {
                "file": relative,
                "status": "RECOMMEND",
                "reason": "Root AGENTS.md duplicates canonical policy (should be thin)",
                "current": text,
                "desired": expected_root_agents(),
                "action": "Keep thin pointer at root; use skill-authoring to update .agents/AGENTS.md for project invariants",
            }
        return None

    if relative == "CLAUDE.md":
        if text is None:
            return None  # Not all targets need Claude adapter; skip unless harness marker present
        expected = expected_claude()
        if text.strip() == expected.strip():
            return None
        # Check for at least one canonical import
        has_import = "@AGENTS.md" in text or "@.agents/AGENTS.md" in text
        if not has_import:
            return {
                "file": relative,
                "status": "RECOMMEND",
                "reason": "CLAUDE.md missing canonical @ import",
                "current": text,
                "desired": expected,
                "action": "Update to thin adapter with @AGENTS.md / @.agents/AGENTS.md / @.agents/OPERATING.md",
            }
        # If imports present but file is thick (contains duplicated policy)
        if len(text.splitlines()) > 30 and "Skill index" in text:
            return {
                "file": relative,
                "status": "RECOMMEND",
                "reason": "CLAUDE.md duplicates canonical content; should be thin adapter",
                "current": text,
                "desired": expected,
                "action": "Keep CLAUDE.md thin; canonical policy stays in .agents/AGENTS.md",
            }
        return None

    if relative == "GEMINI.md":
        if text is None:
            return None
        expected = expected_gemini()
        if text.strip() == expected.strip():
            return None
        has_import = "AGENTS.md" in text
        if not has_import:
            return {
                "file": relative,
                "status": "RECOMMEND",
                "reason": "GEMINI.md missing canonical reference",
                "current": text,
                "desired": expected,
                "action": "Update to thin GEMINI.md adapter referencing AGENTS.md hierarchy",
            }
        return None

    if relative == ".github/copilot-instructions.md":
        if text is None:
            return None
        has_ref = ".agents/AGENTS.md" in text or "AGENTS.md" in text
        if has_ref and "canonical" in text.lower():
            return None
        return {
            "file": relative,
            "status": "RECOMMEND",
            "reason": "Copilot instructions should reference canonical AGENTS.md",
            "current": text,
            "desired": expected_copilot(),
            "action": "Align with thin Copilot entrypoint referencing AGENTS.md / .agents/AGENTS.md",
        }

    if relative in {".cursor/rules", ".cursorrules", ".clinerules"}:
        # These are often directories or legacy files
        p = target_root / relative
        if not p.exists():
            return None
        # If it's a directory, check if it contains duplicated rules
        if p.is_dir():
            # If AGENTS.md already covers it, recommend to keep thin
            return None
        if text and len(text) > 500 and "AGENTS.md" not in text:
            return {
                "file": relative,
                "status": "RECOMMEND",
                "reason": f"{relative} contains duplicated guidance without canonical reference",
                "current": text,
                "desired": "# See AGENTS.md and .agents/AGENTS.md\n",
                "action": "Remove duplication; keep harnesses thin and canonical",
            }
        return None

    # Generic file: if exists in kit and differs, suggest review
    if kit_path and kit_path.is_file() and text is not None:
        try:
            kit_text = kit_path.read_text(encoding="utf-8")
            if text.strip() != kit_text.strip():
                # Only for .agents files that are canonical
                if relative.startswith(".agents/"):
                    return {
                        "file": relative,
                        "status": "REVIEW",
                        "reason": f"{relative} differs from kit canonical",
                        "current": text,
                        "desired": kit_text,
                        "action": "Review via skill-authoring; keep target-local invariants, merge upstream improvements if generic",
                    }
        except OSError:
            pass
    return None


def collect_harness_recommendations(kit_root: Path, target_root: Path) -> list[dict]:
    recs: list[dict] = []
    # Always check core files
    for rel in [
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
    ]:
        r = recommendation_for_file(target_root, kit_root, rel)
        if r:
            recs.append(r)
    # Check .agents hierarchy
    for rel in [".agents/AGENTS.md", ".agents/OPERATING.md"]:
        tp = target_root / rel
        kp = kit_root / rel
        if tp.exists() and kp.exists():
            try:
                t_text = tp.read_text(encoding="utf-8")
                k_text = kp.read_text(encoding="utf-8")
                if t_text.strip() != k_text.strip():
                    # Do not auto-recommend overwrite; flag for ADAPT review
                    recs.append(
                        {
                            "file": rel,
                            "status": "REVIEW",
                            "reason": f"{rel} local content differs from kit; may need ADAPT merge",
                            "current": t_text[:2000],
                            "desired": k_text[:2000],
                            "action": "Compare via harness-adaptation + skill-authoring; preserve local invariants",
                        }
                    )
            except OSError:
                pass
        elif not tp.exists() and kp.exists():
            recs.append(
                {
                    "file": rel,
                    "status": "CREATE",
                    "reason": f"Missing canonical {rel}",
                    "current": "",
                    "desired": kp.read_text(encoding="utf-8")[:2000]
                    if kp.exists()
                    else "",
                    "action": "Adopt via bootstrap-project (approval-gated)",
                }
            )
    # Check optional harness dirs
    for rel in [".cursor/rules", ".cursorrules", ".clinerules"]:
        r = recommendation_for_file(target_root, kit_root, rel)
        if r:
            recs.append(r)
    return recs


def render_diff(current: str, desired: str, rel: str) -> str:
    a = current.splitlines(keepends=True) if current else []
    b = desired.splitlines(keepends=True) if desired else []
    diff = difflib.unified_diff(
        a, b, fromfile=f"a/{rel}", tofile=f"b/{rel}", lineterm=""
    )
    return "".join(diff)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kit-root", default=str(ROOT), help="Kit root (defaults to repo root)"
    )
    parser.add_argument("--target", default=".", help="Target repository root")
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument(
        "--check", action="store_true", help="Exit 1 if any recommendations exist"
    )
    parser.add_argument(
        "--diff", action="store_true", help="Include unified diffs in markdown"
    )
    parser.add_argument(
        "--json", action="store_true", help="Shortcut for --format json"
    )
    args = parser.parse_args()

    if args.json:
        args.format = "json"

    kit_root = Path(args.kit_root).expanduser().resolve()
    target_root = Path(args.target).expanduser().resolve()

    if kit_root.is_symlink() or not kit_root.is_dir():
        print(f"error: kit-root must be a real directory: {kit_root}", file=sys.stderr)
        return 2
    if target_root.is_symlink() or not target_root.is_dir():
        print(f"error: target must be a real directory: {target_root}", file=sys.stderr)
        return 2

    recs = collect_harness_recommendations(kit_root, target_root)

    if args.format == "json":
        payload = {
            "kit_root": str(kit_root),
            "target": str(target_root),
            "recommendations": recs,
            "count": len(recs),
        }
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 1 if args.check and recs else 0

    # Markdown
    out: list[str] = []
    out.append("# Harness & AGENTS.md recommendations")
    out.append("")
    out.append(f"- Kit: `{kit_root}`")
    out.append(f"- Target: `{target_root}`")
    out.append(f"- Findings: **{len(recs)}**")
    out.append("")
    if not recs:
        out.append("No recommendations — harness entrypoints are thin and canonical.")
        out.append("")
    else:
        out.append("| File | Status | Reason | Action |")
        out.append("| :--- | :--- | :--- | :--- |")
        for r in recs:
            out.append(
                f"| `{r['file']}` | {r['status']} | {r['reason']} | {r['action']} |"
            )
        out.append("")
        if args.diff:
            for r in recs:
                if r.get("current") is not None and r.get("desired") is not None:
                    diff = render_diff(r["current"], r["desired"], r["file"])
                    if diff:
                        out.append(f"### `{r['file']}` ({r['status']})")
                        out.append("")
                        out.append("```diff")
                        out.append(diff.rstrip())
                        out.append("```")
                        out.append("")
        else:
            out.append("_Run with `--diff` for paste-ready unified diffs._")
            out.append("")
        out.append(
            "Apply via `harness-adaptation` / `skill-authoring` with approval gate; never overwrite local divergence without `ADAPT` review."
        )
        out.append("")
    sys.stdout.write("\n".join(out))
    return 1 if args.check and recs else 0


if __name__ == "__main__":
    raise SystemExit(main())
