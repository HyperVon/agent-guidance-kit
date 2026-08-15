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
    def test_audit_indexes_every_unadopted_skill(self):
        report = adoption_audit.run_audit(_ROOT, _ROOT)
        catalog_names = {s["name"] for s in adoption_audit.read_catalog(_ROOT)}
        self.assertEqual(report["catalog_total"], len(catalog_names))

        candidate_names = {c["name"] for c in report["candidates"]}
        # Candidates == catalog minus what the target has adopted. No skill is
        # excluded by a SOURCE_ONLY or other label.
        self.assertEqual(candidate_names, catalog_names - set(report["adopted"]))
        self.assertIn("agent-guidance-maintenance", report["adopted"])
        # catalog-discovery is not adopted here, so it must appear as a
        # source_only candidate rather than being hidden.
        catalog_discovery = next(
            (c for c in report["candidates"] if c["name"] == "catalog-discovery"),
            None,
        )
        self.assertIsNotNone(catalog_discovery)
        self.assertTrue(catalog_discovery["source_only"])

    def test_partition_is_consistent(self):
        report = adoption_audit.run_audit(_ROOT, _ROOT)
        covered = set(report["adopted"]) | {c["name"] for c in report["candidates"]}
        catalog_names = {s["name"] for s in adoption_audit.read_catalog(_ROOT)}
        self.assertEqual(covered, catalog_names)
        self.assertEqual(
            len(report["adopted"]) + len(report["candidates"]),
            report["catalog_total"],
        )

    def test_candidates_expose_paths_and_flags(self):
        report = adoption_audit.run_audit(_ROOT, _ROOT)
        for candidate in report["candidates"]:
            self.assertIn("name", candidate)
            self.assertIn("description", candidate)
            self.assertTrue(candidate["skill_path"].endswith("SKILL.md"))
            self.assertIsInstance(candidate["source_only"], bool)
        # The index applies no ranking; no applicability verdict is present.
        self.assertNotIn("mechanical_hints", report["candidates"][0])


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
        self.assertEqual(payload["schema_version"], 3)
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
