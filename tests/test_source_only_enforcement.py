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

    def test_structured_marker_blocks_without_prose(self):
        # A skill declaring `source_only: true` must be refused even when its
        # prose never mentions SOURCE_ONLY (the structured marker is authoritative).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / ".agents" / "skills" / "maintainer-tool"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: maintainer-tool\n"
                "description: A maintainer-only tool that must never ship to targets.\n"
                "source_only: true\n"
                "---\n",
                encoding="utf-8",
            )
            with self.assertRaises(AdoptionError):
                assert_not_source_only(root, ["maintainer-tool"])

    def test_prose_only_fallback_still_blocks(self):
        # Skills that predate the structured marker but say "is `SOURCE_ONLY`" in
        # prose must still be refused (regex backstop remains).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / ".agents" / "skills" / "legacy-only"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: legacy-only\n"
                "description: A tool that is SOURCE_ONLY via prose only.\n"
                "---\n"
                "This skill is `SOURCE_ONLY` and never shipped to targets.\n",
                encoding="utf-8",
            )
            with self.assertRaises(AdoptionError):
                assert_not_source_only(root, ["legacy-only"])

    def test_structured_marker_with_crlf_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / ".agents" / "skills" / "crlf-tool"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_bytes(
                b"---\r\n"
                b"name: crlf-tool\r\n"
                b"description: A maintainer-only tool with CRLF line endings.\r\n"
                b"source_only: true\r\n"
                b"---\r\n"
                b"# CRLF Tool\r\n"
            )
            with self.assertRaises(AdoptionError):
                assert_not_source_only(root, ["crlf-tool"])

    def test_ordinary_skill_without_marker_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / ".agents" / "skills" / "ordinary"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: ordinary\n"
                "description: An ordinary adoptable skill with no source-only marker.\n"
                "---\n",
                encoding="utf-8",
            )
            assert_not_source_only(root, ["ordinary"])  # must not raise


if __name__ == "__main__":
    unittest.main()
