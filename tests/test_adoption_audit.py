#!/usr/bin/env python3
"""Tests for the agent-guidance-maintenance adoption audit helper."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / ".agents/skills/agent-guidance-maintenance/scripts/adoption_audit.py"
sys.path.insert(0, str(_SCRIPT.parent))

import adoption_audit  # noqa: E402


class RunAuditTest(unittest.TestCase):
    def test_audit_indexes_adoptable_unadopted_skills(self):
        report = adoption_audit.run_audit(_ROOT, _ROOT)
        catalog = adoption_audit.read_catalog(_ROOT)
        catalog_names = {s["name"] for s in catalog}
        self.assertEqual(report["catalog_total"], len(catalog_names))

        source_only = {s["name"] for s in catalog if s["source_only"]}
        candidate_names = {c["name"] for c in report["candidates"]}
        # Candidates == catalog minus adopted minus SOURCE_ONLY (hidden).
        expected = catalog_names - set(report["adopted"]) - source_only
        self.assertEqual(candidate_names, expected)
        self.assertIn("agent-guidance-maintenance", report["adopted"])
        # catalog-discovery is SOURCE_ONLY, so it must NOT be surfaced.
        self.assertNotIn("catalog-discovery", candidate_names)

    def test_collisions_are_candidates_not_exclusions(self):
        report = adoption_audit.run_audit(_ROOT, _ROOT)
        candidate_names = {c["name"] for c in report["candidates"]}
        collisions = report.get("collisions", [])
        self.assertIsInstance(collisions, list)
        # Collisions must be non-empty in the self-audit (every catalog skill is
        # also a local skill) so the assertion below is meaningful, not vacuous.
        self.assertGreater(len(collisions), 0)
        # A collision is an evaluate-don't-drop signal: the same-named catalog
        # skill must remain a candidate, never silently excluded. Pin a known
        # catalog skill that is present locally and not SOURCE_ONLY.
        self.assertIn("code-review", collisions)
        self.assertIn("code-review", candidate_names)
        for name in collisions:
            self.assertIn(name, candidate_names)
            self.assertNotIn(name, report["adopted"])

    def test_partition_is_consistent(self):
        report = adoption_audit.run_audit(_ROOT, _ROOT)
        catalog = adoption_audit.read_catalog(_ROOT)
        source_only = {s["name"] for s in catalog if s["source_only"]}
        covered = (
            set(report["adopted"])
            | {c["name"] for c in report["candidates"]}
            | source_only
        )
        self.assertEqual(covered, {s["name"] for s in catalog})
        # catalog_total counts every skill, including the hidden SOURCE_ONLY ones.
        self.assertEqual(
            len(report["adopted"]) + len(report["candidates"]) + len(source_only),
            report["catalog_total"],
        )

    def test_candidates_expose_paths(self):
        report = adoption_audit.run_audit(_ROOT, _ROOT)
        for candidate in report["candidates"]:
            self.assertIn("name", candidate)
            self.assertIn("description", candidate)
            self.assertTrue(candidate["skill_path"].endswith("SKILL.md"))
        # The index applies no ranking or applicability verdict, and does not
        # surface SOURCE_ONLY metadata.
        self.assertNotIn("mechanical_hints", report["candidates"][0])
        self.assertNotIn("source_only", report["candidates"][0])


class CliTest(unittest.TestCase):
    def test_cli_emits_valid_json(self):
        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPT),
                "--target",
                str(_ROOT),
                "--kit-root",
                str(_ROOT),
                "--format",
                "json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 4)
        self.assertIn("candidates", payload)
        self.assertNotIn("suggestions", payload)
        self.assertNotIn("available", payload)
        self.assertNotIn("source_only_excluded", payload)

    def test_cli_markdown_runs(self):
        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPT),
                "--target",
                str(_ROOT),
                "--kit-root",
                str(_ROOT),
                "--format",
                "markdown",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Candidate skills to evaluate", result.stdout)
        self.assertIn("you decide applicability", result.stdout)


if __name__ == "__main__":
    unittest.main()
