#!/usr/bin/env python3
"""Verify harness discovery for the kit without manufacturing evidence.

The kit's guidance hierarchy (root `AGENTS.md`, `.agents/AGENTS.md`,
`.agents/OPERATING.md`, `.agents/skills/`) must be real and parseable for the
kit to be structurally valid. That is a *structural* check only: it says
nothing about whether a given harness will actually discover those files.

Harness discovery is a *separate* claim that must be supported by external
evidence from a real harness exercise (a probe task whose behavior shows the
harness read the canonical files and routed to a skill). This script never
asserts that a harness works merely because the kit's files exist, and it never
reports `VERIFIED` without valid evidence.

Usage:

    python scripts/verify_harness.py --harness <name>
    python scripts/verify_harness.py --evidence <file.json|--evidence ->
    python scripts/verify_harness.py --evidence <file.json> --update

Evidence JSON contract (all fields except `version` are strings):

    {
      "harness": "muse code",            # harness name
      "harness_version": "0.1.0",        # optional
      "date": "2026-08-12",              # execution date (use the real date)
      "task": "Inspect this repo and run the code-review skill",
      "observed_instruction_discovery": "Agent read AGENTS.md and .agents/AGENTS.md",
      "observed_skill_routing": "Agent loaded .agents/skills/code-review/SKILL.md",
      "supporting_output": "link or quoted excerpt, or path to a transcript",
      "result": "VERIFIED"               # VERIFIED | DOCUMENTED | BEST_EFFORT
    }

`VERIFIED` requires all observed_* fields and `supporting_output`. `DOCUMENTED`
may be recorded when a public harness contract exists. `BEST_EFFORT` marks an
explicit discovery gap.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EVIDENCE_VERSION = 1
VALID_RESULTS = {"VERIFIED", "DOCUMENTED", "BEST_EFFORT"}


def structural_checks(harness: str, verbose: bool) -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    canonical = ROOT / ".agents/AGENTS.md"
    operating = ROOT / ".agents/OPERATING.md"
    skills_root = ROOT / ".agents/skills"

    for p, label in [
        (canonical, "canonical .agents/AGENTS.md"),
        (operating, "canonical .agents/OPERATING.md"),
        (skills_root, "skills catalog"),
    ]:
        if p.is_symlink() or not p.exists():
            notes.append(f"FAIL {label} missing or symlinked: {p}")
            ok = False
        else:
            notes.append(f"OK {label} present: {p.relative_to(ROOT)}")
            if verbose:
                notes.append(
                    f"  - readable, size {p.stat().st_size if p.is_file() else 'dir'}"
                )

    agents_root = ROOT / "AGENTS.md"
    if agents_root.exists():
        if agents_root.is_symlink():
            notes.append("FAIL root AGENTS.md is symlinked")
            ok = False
        else:
            try:
                txt = agents_root.read_text(encoding="utf-8")
                if ".agents/AGENTS.md" in txt or ".agents/OPERATING.md" in txt:
                    notes.append("OK root AGENTS.md references canonical guidance")
                else:
                    notes.append(
                        "WARN root AGENTS.md does not reference canonical .agents/AGENTS.md"
                    )
            except OSError as e:
                notes.append(f"FAIL reading root AGENTS.md: {e}")
                ok = False

    for name, path in [
        ("CLAUDE.md", ROOT / "CLAUDE.md"),
        ("GEMINI.md", ROOT / "GEMINI.md"),
        (".github/copilot-instructions.md", ROOT / ".github/copilot-instructions.md"),
    ]:
        if path.exists():
            if path.is_symlink():
                notes.append(f"FAIL harness entrypoint {name} is symlinked")
                ok = False
            else:
                try:
                    text = path.read_text(encoding="utf-8")
                    has_canonical = ".agents/AGENTS.md" in text or "AGENTS.md" in text
                    if has_canonical:
                        notes.append(f"OK {name} references canonical guidance")
                    else:
                        notes.append(
                            f"WARN {name} does not reference canonical guidance"
                        )
                except OSError:
                    notes.append(f"WARN {name} unreadable")

    if skills_root.is_dir() and not skills_root.is_symlink():
        skills = [
            d
            for d in skills_root.iterdir()
            if d.is_dir() and not d.name.startswith(".") and not d.is_symlink()
        ]
        notes.append(f"OK skills catalog contains {len(skills)} skills")
        valid = sum(
            1
            for s in skills
            if (s / "SKILL.md").is_file() and not (s / "SKILL.md").is_symlink()
        )
        notes.append(f"OK {valid}/{len(skills)} skills have real SKILL.md")
        if valid == 0:
            ok = False
            notes.append("FAIL no valid skills found")
    else:
        notes.append("FAIL skills catalog missing")
        ok = False

    return ok, notes


def validate_evidence(value: object) -> tuple[dict, list[str]]:
    """Return (normalized evidence, errors). Empty errors means valid."""
    errors: list[str] = []
    if not isinstance(value, dict):
        return {}, ["evidence must be a JSON object"]
    version = value.get("version")
    if version is not None and version != EVIDENCE_VERSION:
        errors.append(f"evidence.version must be {EVIDENCE_VERSION} or omitted")
    result = value.get("result")
    if result not in VALID_RESULTS:
        errors.append(
            f"evidence.result must be one of {', '.join(sorted(VALID_RESULTS))}"
        )
    elif result == "VERIFIED":
        for required in (
            "harness",
            "date",
            "task",
            "observed_instruction_discovery",
            "observed_skill_routing",
            "supporting_output",
        ):
            if not str(value.get(required, "")).strip():
                errors.append(f"VERIFIED evidence requires '{required}'")
    else:
        for required in ("harness", "date"):
            if not str(value.get(required, "")).strip():
                errors.append(f"evidence '{required}' is required")
    # Normalize.
    normalized = {
        "version": EVIDENCE_VERSION,
        "harness": str(value.get("harness", "")).strip(),
        "harness_version": str(value.get("harness_version", "")).strip(),
        "date": str(value.get("date", "")).strip(),
        "task": str(value.get("task", "")).strip(),
        "observed_instruction_discovery": str(
            value.get("observed_instruction_discovery", "")
        ).strip(),
        "observed_skill_routing": str(value.get("observed_skill_routing", "")).strip(),
        "supporting_output": str(value.get("supporting_output", "")).strip(),
        "result": str(result).strip()
        if (result in VALID_RESULTS and not errors)
        else "",
    }
    return normalized, errors


def apply_evidence_to_compatibility(evidence: dict, doc_path: Path) -> tuple[bool, str]:
    """Update a single harness row in docs/harness-compatibility.md.

    Returns (changed, message). Only `VERIFIED` evidence updates the status
    column to VERIFIED; other results leave the row untouched (documentation
    records the public contract separately). Failure to reconcile the row is
    reported, not silently swallowed.
    """
    text = doc_path.read_text(encoding="utf-8")
    if evidence["result"] != "VERIFIED":
        return False, "non-VERIFIED evidence does not rewrite the doc"
    name_pattern = re.compile(
        r"^\|[^|]*" + re.escape(evidence["harness"]) + r"[^|]*\|",
        re.IGNORECASE,
    )
    new_lines = []
    replaced = 0
    for line in text.splitlines():
        if name_pattern.match(line) and replaced == 0:
            cells = line.split("|")
            # A table row is "| c1 | c2 | ... | status |"; cells[-2] is status.
            if len(cells) >= 3:
                cells[-2] = " VERIFIED "
                replaced += 1
                new_lines.append("|".join(cells))
                continue
        new_lines.append(line)
    if replaced == 0:
        return False, "no matching harness row"
    doc_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return True, f"updated {replaced} row(s)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", default="unknown", help="Harness name to record")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON"
    )
    parser.add_argument(
        "--evidence",
        help="Path to a JSON evidence file, or '-' to read stdin",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update docs/harness-compatibility.md from valid evidence",
    )
    parser.add_argument(
        "--target", help="Optional target directory to probe (defaults to kit root)"
    )
    parser.add_argument(
        "--doc",
        default=str(ROOT / "docs/harness-compatibility.md"),
        help="Compatibility doc to update (defaults to the kit's doc)",
    )
    args = parser.parse_args(argv)

    ok, notes = structural_checks(args.harness, args.verbose)

    evidence: dict | None = None
    evidence_errors: list[str] = []
    if args.evidence:
        raw = (
            sys.stdin.read()
            if args.evidence == "-"
            else Path(args.evidence).read_text(encoding="utf-8")
        )
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, OSError) as error:
            evidence_errors.append(f"invalid evidence JSON: {error}")
        else:
            evidence, evidence_errors = validate_evidence(value)

    if evidence_errors:
        for e in evidence_errors:
            notes.append(f"FAIL evidence: {e}")
        ok = False
        verdict = "INVALID EVIDENCE"
    elif evidence:
        verdict = evidence["result"]
        notes.append(
            f"EVIDENCE {evidence['result']} for {evidence['harness']} "
            f"({evidence.get('date', 'no date')})"
        )
        # Structural validity is necessary but not sufficient.
        if evidence["result"] == "VERIFIED" and not ok:
            notes.append("FAIL structural checks failed; cannot record VERIFIED")
            ok = False
            verdict = "INVALID EVIDENCE"
    else:
        verdict = "STRUCTURALLY VALID" if ok else "STRUCTURAL FAILURE"
        notes.append(
            "NOTE no harness evidence supplied; structural validity does not "
            "establish discovery. File presence alone earns at most DOCUMENTED."
        )

    # Probe optional target.
    if args.target:
        t = Path(args.target).expanduser().resolve()
        if t.is_symlink() or not t.is_dir():
            notes.append(f"FAIL target {t} is not a real directory")
            ok = False
        else:
            notes.append(f"OK target {t} is a real directory")

    if args.json:
        payload = {
            "harness": args.harness,
            "verdict": verdict,
            "structurally_valid": ok,
            "notes": notes,
            "root": str(ROOT),
            "evidence": evidence,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        failed = bool(evidence_errors) or (not ok and not evidence)
        return 1 if failed else 0

    for n in notes:
        print(n)
    print(f"Harness probe ({args.harness}): {verdict}")

    if args.update:
        if not evidence or evidence_errors:
            print(
                "ERROR --update requires valid --evidence; refusing to change docs.",
                file=sys.stderr,
            )
            return 1
        doc = Path(args.doc)
        if not (Path(doc).is_file() and not Path(doc).is_symlink()):
            print(f"ERROR cannot update {doc}: missing or symlinked", file=sys.stderr)
            return 1
        try:
            changed, message = apply_evidence_to_compatibility(evidence, doc)
        except Exception as error:  # noqa: BLE001 — report, do not crash
            print(f"ERROR updating compatibility doc: {error}", file=sys.stderr)
            return 1
        try:
            displayed = doc.relative_to(ROOT)
        except ValueError:
            displayed = doc
        if changed:
            print(f"Updated {displayed}: {message}")
        else:
            print(f"No change to {displayed}: {message}")

    # Exit code: structural failure or invalid evidence is a non-zero exit.
    return 1 if (not ok or evidence_errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
