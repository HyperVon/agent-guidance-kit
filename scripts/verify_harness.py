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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EVIDENCE_VERSION = 1
VALID_RESULTS = {"VERIFIED", "DOCUMENTED", "BEST_EFFORT"}


class CompatibilityUpdateError(RuntimeError):
    """Raised when evidence cannot be reconciled to exactly one doc row."""


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
    if not isinstance(result, str) or result not in VALID_RESULTS:
        errors.append(
            f"evidence.result must be one of {', '.join(sorted(VALID_RESULTS))}"
        )
    text_fields = (
        "harness",
        "harness_version",
        "date",
        "task",
        "observed_instruction_discovery",
        "observed_skill_routing",
        "supporting_output",
        "result",
    )
    for field in text_fields:
        if field in value and not isinstance(value[field], str):
            errors.append(f"evidence.{field} must be a string")

    required = (
        (
            "harness",
            "date",
            "task",
            "observed_instruction_discovery",
            "observed_skill_routing",
            "supporting_output",
        )
        if result == "VERIFIED"
        else ("harness", "date")
    )
    for field in required:
        if field not in value:
            prefix = "VERIFIED evidence" if result == "VERIFIED" else "evidence"
            errors.append(f"{prefix} requires '{field}'")
        elif isinstance(value[field], str) and not value[field].strip():
            prefix = "VERIFIED evidence" if result == "VERIFIED" else "evidence"
            errors.append(f"{prefix} requires '{field}'")

    def text(name: str) -> str:
        raw = value.get(name, "")
        return raw.strip() if isinstance(raw, str) else ""

    # Normalize.
    normalized = {
        "version": EVIDENCE_VERSION,
        "harness": text("harness"),
        "harness_version": text("harness_version"),
        "date": text("date"),
        "task": text("task"),
        "observed_instruction_discovery": text("observed_instruction_discovery"),
        "observed_skill_routing": text("observed_skill_routing"),
        "supporting_output": text("supporting_output"),
        "result": result.strip() if isinstance(result, str) and not errors else "",
    }
    return normalized, errors


def _normalize_harness_name(value: str) -> str:
    return " ".join(value.split()).casefold()


def _markdown_table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    content = stripped[1:-1] if stripped.endswith("|") else stripped[1:]
    cells = [cell.strip() for cell in content.split("|")]
    return cells if len(cells) >= 2 else None


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
    expected = _normalize_harness_name(evidence["harness"])
    lines = text.splitlines(keepends=True)
    matches: list[tuple[int, list[str], str]] = []
    for index, raw_line in enumerate(lines):
        line = raw_line.rstrip("\r\n")
        cells = _markdown_table_cells(line)
        if not cells:
            continue
        first_cell = _normalize_harness_name(cells[0])
        if first_cell in {"", "harness"} or set(cells[0]) <= {"-", ":", " "}:
            continue
        if first_cell == expected:
            matches.append((index, cells, raw_line))

    if not matches:
        raise CompatibilityUpdateError(
            f"no exact harness row for {evidence['harness']!r}"
        )
    if len(matches) > 1:
        raise CompatibilityUpdateError(
            f"ambiguous harness row for {evidence['harness']!r}: "
            f"found {len(matches)} exact matches"
        )

    index, cells, raw_line = matches[0]
    cells[-1] = "VERIFIED"
    replacement = "| " + " | ".join(cells) + " |"
    line_without_ending = raw_line.rstrip("\r\n")
    line_ending = raw_line[len(line_without_ending) :]
    new_lines = list(lines)
    new_lines[index] = replacement + line_ending
    new_text = "".join(new_lines)
    if new_text == text:
        return False, "matching harness row is already VERIFIED"
    doc_path.write_text(new_text, encoding="utf-8")
    return True, "updated 1 exact harness row"


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

    structurally_valid, notes = structural_checks(args.harness, args.verbose)

    evidence: dict | None = None
    evidence_errors: list[str] = []
    if args.evidence:
        try:
            raw = (
                sys.stdin.read()
                if args.evidence == "-"
                else Path(args.evidence).read_text(encoding="utf-8")
            )
            value = json.loads(raw)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as error:
            evidence_errors.append(f"invalid evidence JSON: {error}")
        else:
            evidence, evidence_errors = validate_evidence(value)

    evidence_valid: bool | None = None if not args.evidence else not evidence_errors
    evidence_result = evidence.get("result") if evidence else None
    if evidence_errors:
        for e in evidence_errors:
            notes.append(f"FAIL evidence: {e}")
        verdict = "INVALID EVIDENCE"
    elif evidence:
        verdict = evidence["result"]
        notes.append(
            f"EVIDENCE {evidence['result']} for {evidence['harness']} "
            f"({evidence.get('date', 'no date')})"
        )
        # Structural validity is necessary but not sufficient.
        if evidence["result"] == "VERIFIED" and not structurally_valid:
            notes.append("FAIL structural checks failed; cannot record VERIFIED")
            verdict = "INVALID EVIDENCE"
    else:
        verdict = "STRUCTURALLY VALID" if structurally_valid else "STRUCTURAL FAILURE"
        notes.append(
            "NOTE no harness evidence supplied; structural validity does not "
            "establish discovery. File presence alone earns at most DOCUMENTED."
        )

    # Probe optional target.
    target_valid = True
    if args.target:
        t = Path(args.target).expanduser().resolve()
        if t.is_symlink() or not t.is_dir():
            notes.append(f"FAIL target {t} is not a real directory")
            target_valid = False
        else:
            notes.append(f"OK target {t} is a real directory")

    update_attempted = bool(args.update)
    compatibility_document_changed = False
    update_message: str | None = None
    update_error: str | None = None
    update_succeeded = not update_attempted
    if args.update:
        if not evidence or evidence_errors:
            update_error = (
                "--update requires valid --evidence; refusing to change docs."
            )
        elif not structurally_valid and evidence["result"] == "VERIFIED":
            update_error = "structural checks failed; refusing to record VERIFIED."
        elif evidence["result"] != "VERIFIED":
            update_error = (
                "--update requires VERIFIED evidence; refusing to change docs."
            )
        else:
            doc = Path(args.doc)
            if not (doc.is_file() and not doc.is_symlink()):
                update_error = f"cannot update {doc}: missing or symlinked"
            else:
                try:
                    (
                        compatibility_document_changed,
                        update_message,
                    ) = apply_evidence_to_compatibility(evidence, doc)
                except (CompatibilityUpdateError, OSError, UnicodeError) as error:
                    update_error = f"updating compatibility doc failed: {error}"
                else:
                    update_succeeded = True

    command_succeeded = (
        structurally_valid
        and target_valid
        and evidence_valid is not False
        and update_succeeded
    )

    if args.json:
        payload = {
            "command_succeeded": command_succeeded,
            "compatibility_document_changed": compatibility_document_changed,
            "evidence": evidence,
            "evidence_result": evidence_result,
            "evidence_valid": evidence_valid,
            "harness": args.harness,
            "notes": notes,
            "root": str(ROOT),
            "structurally_valid": structurally_valid,
            "target_valid": target_valid,
            "update_attempted": update_attempted,
            "update_error": update_error,
            "update_message": update_message,
            "update_succeeded": update_succeeded,
            "verdict": verdict,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if command_succeeded else 1

    for n in notes:
        print(n)
    print(f"Harness probe ({args.harness}): {verdict}")
    if args.update:
        if update_error:
            print(f"ERROR {update_error}", file=sys.stderr)
        else:
            doc = Path(args.doc)
            try:
                displayed = doc.relative_to(ROOT)
            except ValueError:
                displayed = doc
            if compatibility_document_changed:
                print(f"Updated {displayed}: {update_message}")
            else:
                print(f"No change to {displayed}: {update_message}")

    return 0 if command_succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
