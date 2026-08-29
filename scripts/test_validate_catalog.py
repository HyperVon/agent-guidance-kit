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
                "---\n"
                "name: example\n"
                "description: >-\n"
                "  First line supplies a valid description.\n"
                "  Second line completes it.\n"
                "---\n"
                "# Example\n",
                encoding="utf-8",
            )
            self.assertEqual(
                parse_frontmatter(path),
                (
                    "example",
                    "First line supplies a valid description. Second line completes it.",
                ),
            )

    def test_accepts_description_length_boundaries(self) -> None:
        for length in (40, 1024):
            with self.subTest(length=length), TemporaryDirectory() as directory:
                path = Path(directory) / "SKILL.md"
                path.write_text(
                    f"---\nname: example\ndescription: {'x' * length}\n---\n# Example\n",
                    encoding="utf-8",
                )
                self.assertEqual(len(parse_frontmatter(path)[1]), length)

    def test_ignores_optional_frontmatter_fields_after_description(self) -> None:
        description = "x" * 1024
        compatibility = "y" * 500
        with TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(
                "---\n"
                "name: example\n"
                "description: >-\n"
                f"  {description}\n"
                f"compatibility: {compatibility}\n"
                "metadata:\n"
                "  owner: platform\n"
                "---\n"
                "# Example\n",
                encoding="utf-8",
            )
            self.assertEqual(parse_frontmatter(path), ("example", description))

    def test_rejects_description_outside_length_boundaries(self) -> None:
        for length in (39, 1025):
            with self.subTest(length=length), TemporaryDirectory() as directory:
                path = Path(directory) / "SKILL.md"
                path.write_text(
                    f"---\nname: example\ndescription: {'x' * length}\n---\n# Example\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ValueError, "description length"):
                    parse_frontmatter(path)

    def test_rejects_empty_skill_body(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(
                "---\n"
                "name: example\n"
                "description: This description is comfortably longer than forty characters.\n"
                "---\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "skill body is empty"):
                parse_frontmatter(path)

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
