from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agents/skills/bootstrap-project/scripts/inventory_project.py"
SPEC = importlib.util.spec_from_file_location("inventory_project", SCRIPT)
assert SPEC and SPEC.loader
inventory_project = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory_project)


class InventoryProjectTest(unittest.TestCase):
    def test_inventory_reports_facts_and_does_not_follow_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            (root / "src").mkdir()
            (root / "src/main.py").write_text("print('safe')\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests/test_main.py").write_text("pass\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
            (root / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
            (root / "GEMINI.md").write_text("@./AGENTS.md\n", encoding="utf-8")
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/check.yml").write_text("name: check\n", encoding="utf-8")
            outside = Path(temp) / "outside"
            outside.mkdir()
            (outside / "private.py").write_text("secret = True\n", encoding="utf-8")
            if hasattr(os, "symlink"):
                os.symlink(outside, root / "linked")

            result = inventory_project.inventory(root, 100)

            self.assertEqual(2, result["languages_by_file_count"]["Python"])
            self.assertIn("pyproject.toml", result["build_files"])
            self.assertIn("AGENTS.md", result["guidance_files"])
            self.assertIn("GEMINI.md", result["guidance_files"])
            self.assertIn("AGENTS.md", result["harness_markers"])
            self.assertIn("GEMINI.md", result["harness_markers"])
            self.assertIn(".github/workflows/check.yml", result["ci_files"])
            self.assertIn("tests", result["test_roots"])
            if hasattr(os, "symlink"):
                self.assertIn("linked", result["symlinks_not_followed"])
                self.assertEqual(2, result["languages_by_file_count"]["Python"])

    def test_inventory_honors_file_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index in range(3):
                (root / f"file-{index}.py").write_text("pass\n", encoding="utf-8")

            result = inventory_project.inventory(root, 2)

            self.assertTrue(result["truncated"])
            self.assertEqual(2, result["files_scanned"])


if __name__ == "__main__":
    unittest.main()
