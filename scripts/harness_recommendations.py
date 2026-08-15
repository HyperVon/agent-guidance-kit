#!/usr/bin/env python3
"""Generate deterministic, non-destructive diagnostics for AGENTS.md and harness entrypoints.

Compares a target repository's AGENTS.md hierarchy and harness adapters
(CLAUDE.md, GEMINI.md, .github/copilot-instructions.md, etc.) against the kit's
canonical guidance and the kit-assumed thin-adapter shape. This script is a
*diagnostic detector*: it surfaces gaps and divergence, but it never authors
policy for the target. In particular it never recommends undoing configuration
the installer owns (the managed routing block) and it never offers the kit
repository's own `.agents/AGENTS.md` / `.agents/OPERATING.md` body as paste-ready
target content. Project-local guidance stays authoritative.

Deterministic, standard-library only, network-free.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

# harness_recommendations.py is run both as a standalone script (from the kit
# root scripts/ directory) and as a kit module copied under the kit's
# .agents/skills/bootstrap-project/scripts/. Make the install_skills package
# importable regardless of how this file was launched.
if not __package__:
    here = Path(__file__).resolve().parent
    for candidate in (
        here,
        here.parents[0] / ".agents" / "skills" / "bootstrap-project" / "scripts",
    ):
        if (candidate / "install_skills").is_dir():
            sys.path.insert(0, str(candidate))
            break

# Canonical marker for the installer-managed routing block. Presence of this
# block in a root AGENTS.md (or a nested .agents/AGENTS.md) is a valid managed
# integration state and must never be recommended for removal or replacement.
from install_skills.constants import ROUTE_START


def read_text_safe(path: Path) -> str | None:
    try:
        if path.is_symlink() or not path.is_file():
            return None
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def is_thin_root_agents(text: str) -> bool:
    """Return True when root AGENTS.md is a thin pointer.

    Thin means: references canonical `.agents/AGENTS.md` (or the managed
    routing block) and does not duplicate canonical invariants.  Line count
    is not authoritative - a thin file that legitimately contains project
    notes may be longer - so the check relies on invariant absence, not an
    arbitrary 40-line threshold.
    """
    has_ref = ROUTE_START in text or ".agents/AGENTS.md" in text
    # Thick file contains canonical invariants duplicated verbatim
    thick_markers = ["Product boundary", "Repository invariants", "Skill index"]
    thick_count = sum(1 for m in thick_markers if m in text)
    return has_ref and thick_count == 0


def expected_root_agents() -> str:
    return (
        "# Agent instructions\n\n"
        "This file is the thin universal entrypoint. Canonical guidance lives under "
        "`.agents/`.\n"
    )


def expected_claude() -> str:
    return "@AGENTS.md\n@.agents/AGENTS.md\n@.agents/OPERATING.md\n"


def expected_gemini() -> str:
    return "@./AGENTS.md\n@./.agents/AGENTS.md\n@./.agents/OPERATING.md\n"


def expected_copilot() -> str:
    return "# GitHub Copilot instructions\n\nSee AGENTS.md\n"


def recommendation_for_file(
    kit_root: Path, target_root: Path, relative: str
) -> dict | None:
    target_path = target_root / relative
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
        # The installer may have written a root AGENTS.md that contains only the
        # managed routing block. That is a valid managed integration state; do
        # not recommend replacing it with the kit's thin template.
        if ROUTE_START in text and ".agents/AGENTS.md" not in text:
            return None
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
    kit_path = kit_root / relative
    if kit_path.is_file() and text is not None:
        try:
            kit_text = kit_path.read_text(encoding="utf-8")
            if text.strip() != kit_text.strip():
                # Only for .agents files that are canonical
                if relative.startswith(".agents/"):
                    return {
                        "file": relative,
                        "status": "REVIEW",
                        "review_required": True,
                        "owner": "source-canonical-guidance",
                        "reason": f"{relative} differs from kit canonical",
                        "current": text,
                        "desired": None,
                        "action": "Review via skill-authoring; keep target-local invariants, merge upstream improvements if generic",
                    }
        except OSError:
            pass
    return None


def collect_harness_recommendations(kit_root: Path, target_root: Path) -> list[dict]:
    kit_root = Path(kit_root)
    recs: list[dict] = []
    # Always check core files
    for rel in [
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
    ]:
        r = recommendation_for_file(kit_root, target_root, rel)
        if r:
            recs.append(r)
    # Check .agents hierarchy. These are project-local policy: never emit the
    # kit's own canonical body as paste-ready target content. Missing canonical
    # files are a required REVIEW item, not a CREATE with kit policy.
    for rel in [".agents/AGENTS.md", ".agents/OPERATING.md"]:
        tp = target_root / rel
        kp = kit_root / rel
        if tp.exists() and kp.exists():
            try:
                t_text = tp.read_text(encoding="utf-8")
                k_text = kp.read_text(encoding="utf-8")
                if t_text.strip() != k_text.strip():
                    # Do not auto-recommend overwrite; flag for ADAPT review.
                    recs.append(
                        {
                            "file": rel,
                            "status": "REVIEW",
                            "review_required": True,
                            "owner": "source-canonical-guidance",
                            "reason": f"{rel} local content differs from kit; may need ADAPT merge",
                            "current": t_text,
                            "desired": None,
                            "action": "Compare via harness-adaptation + skill-authoring; preserve local invariants",
                        }
                    )
            except OSError:
                pass
        elif not tp.exists() and kp.exists():
            # The target still needs an explicit adaptation decision: a target
            # that wants kit canonical content should
            # create it through harness-adaptation / skill-authoring rather than
            # copy the kit's repository policy verbatim.
            recs.append(
                {
                    "file": rel,
                    "status": "REVIEW",
                    "review_required": True,
                    "owner": "source-canonical-guidance",
                    "reason": f"Missing canonical {rel}",
                    "current": "",
                    "desired": None,
                    "action": "Create/adapt via harness-adaptation + skill-authoring with approval gate; "
                    "preserve target-local invariants",
                }
            )
    # Check optional harness dirs
    for rel in [".cursor/rules", ".cursorrules", ".clinerules"]:
        r = recommendation_for_file(kit_root, target_root, rel)
        if r:
            recs.append(r)
    return recs


def render_diff(current: str, desired: str, rel: str) -> str:
    a = current.splitlines() if current else []
    b = desired.splitlines() if desired else []
    diff = difflib.unified_diff(
        a, b, fromfile=f"a/{rel}", tofile=f"b/{rel}", lineterm=""
    )
    return "\n".join(diff)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kit-root", default=".", help="Kit root (defaults to repo root)"
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
    args = parser.parse_args(argv)

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
    out.append("# Harness and canonical-guidance review")
    out.append("")
    out.append(f"- Kit: `{kit_root}`")
    out.append(f"- Target: `{target_root}`")
    out.append(f"- Findings: **{len(recs)}**")
    out.append("")
    if not recs:
        out.append(
            "No recommendations — harness entrypoints and canonical guidance are aligned."
        )
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
                        out.append(diff)
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
