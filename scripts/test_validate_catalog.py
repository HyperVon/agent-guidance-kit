import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from validate_catalog import parse_frontmatter


ROOT = Path(__file__).resolve().parents[1]


class CatalogValidatorTests(unittest.TestCase):
    def test_parses_folded_description(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(
                "---\nname: example\ndescription: >-\n  First line.\n  Second line.\n---\n",
                encoding="utf-8",
            )
            self.assertEqual(parse_frontmatter(path), ("example", "First line. Second line."))

    def test_repository_catalog_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_catalog.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("25 skills", result.stdout)


if __name__ == "__main__":
    unittest.main()
