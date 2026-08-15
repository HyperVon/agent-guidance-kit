#!/usr/bin/env python3
"""Tests that SOURCE_ONLY skills cannot be adopted into a target."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/bootstrap-project/scripts"))

from install_skills.validation import (  # noqa: E402
    AdoptionError,
    assert_not_source_only,
)


class SourceOnlyEnforcementTest(unittest.TestCase):
    def test_assert_not_source_only_refuses_catalog_discovery(self):
        with self.assertRaises(AdoptionError):
            assert_not_source_only(ROOT, ["catalog-discovery"])

    def test_assert_not_source_only_allows_normal_skill(self):
        # Must not raise for an ordinary adoptable skill.
        assert_not_source_only(ROOT, ["code-review"])

    def test_plan_refuses_source_only_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            target.mkdir()
            installer = (
                ROOT / ".agents/skills/bootstrap-project/scripts/install_skills.py"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(installer),
                    "plan",
                    "--kit-root",
                    str(ROOT),
                    "--target",
                    str(target),
                    "--skill",
                    "catalog-discovery",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SOURCE_ONLY", result.stderr)


if __name__ == "__main__":
    unittest.main()
