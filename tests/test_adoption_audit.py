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


def _inventory(**overrides: object) -> dict:
    base = {
        "languages_by_file_count": {},
        "build_files": [],
        "test_roots": [],
        "ci_files": [],
        "guidance_files": [],
        "harness_markers": [],
        "git": {"repository": True},
    }
    base.update(overrides)
    return base


class MatchSignalsTest(unittest.TestCase):
    def test_signals_match_repo_characteristics(self):
        inv = _inventory(
            build_files=["package.json", "pyproject.toml"],
            ci_files=[".github/workflows/check.yml"],
            test_roots=["tests"],
            languages_by_file_count={"TypeScript": 5},
            harness_markers=[".agents", ".kilo"],
            guidance_files=["README.md", "skills/foo/SKILL.md"],
        )
        self.assertTrue(adoption_audit.match_signals("dependency-upgrade", inv))
        self.assertTrue(adoption_audit.match_signals("security-review", inv))
        self.assertTrue(adoption_audit.match_signals("threat-modeling", inv))
        self.assertTrue(adoption_audit.match_signals("git-github-workflow", inv))
        self.assertTrue(adoption_audit.match_signals("quality-hardening", inv))
        self.assertTrue(adoption_audit.match_signals("frontend-quality-review", inv))
        self.assertTrue(adoption_audit.match_signals("harness-adaptation", inv))
        self.assertTrue(adoption_audit.match_signals("skill-authoring", inv))
        self.assertTrue(adoption_audit.match_signals("skill-reviewer", inv))
        self.assertTrue(adoption_audit.match_signals("rules-and-skills-audit", inv))
        self.assertTrue(adoption_audit.match_signals("skill-evaluation", inv))
        self.assertTrue(adoption_audit.match_signals("skill-optimizer", inv))
        self.assertTrue(adoption_audit.match_signals("upstream-contribution", inv))

    def test_reasons_are_explanatory_strings(self):
        inv = _inventory(
            build_files=["package.json"],
            ci_files=[".github/workflows/check.yml"],
            test_roots=["tests"],
        )
        for name in ("dependency-upgrade", "threat-modeling", "quality-hardening"):
            reasons = adoption_audit.match_signals(name, inv)
            self.assertTrue(reasons, name)
            self.assertTrue(all(isinstance(r, str) and r for r in reasons), name)

    def test_unmapped_skill_has_no_signals(self):
        inv = _inventory(build_files=["package.json"])
        self.assertEqual(adoption_audit.match_signals("code-review", inv), [])

    def test_no_signal_when_characteristics_absent(self):
        inv = _inventory()
        self.assertEqual(adoption_audit.match_signals("dependency-upgrade", inv), [])
        self.assertEqual(adoption_audit.match_signals("quality-hardening", inv), [])


class RunAuditTest(unittest.TestCase):
    def test_audit_partitions_catalog(self):
        report = adoption_audit.run_audit(_ROOT, _ROOT)
        catalog_names = {s["name"] for s in adoption_audit.read_catalog(_ROOT)}
        self.assertEqual(report["catalog_total"], len(catalog_names))

        # catalog-discovery is SOURCE_ONLY and excluded from proposals.
        self.assertEqual(report["source_only_excluded"], ["catalog-discovery"])
        self.assertIn("agent-guidance-maintenance", report["adopted"])

        proposed = {s["name"] for s in report["suggestions"] + report["available"]}
        self.assertNotIn("catalog-discovery", proposed)
        self.assertFalse(proposed & set(report["adopted"]))

        # The partition covers the whole catalog exactly once.
        covered = (
            set(report["adopted"])
            | set(report["source_only_excluded"])
            | {s["name"] for s in report["suggestions"]}
            | {s["name"] for s in report["available"]}
        )
        self.assertEqual(covered, catalog_names)

    def test_suggestions_carry_reasons(self):
        report = adoption_audit.run_audit(_ROOT, _ROOT)
        for skill in report["suggestions"]:
            self.assertIn("reasons", skill)
            self.assertTrue(skill["reasons"])


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
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("suggestions", payload)

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
        self.assertIn("Agent Guidance Kit adoption audit", result.stdout)


if __name__ == "__main__":
    unittest.main()
