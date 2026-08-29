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
        for length in (1, 1024):
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
                "  owner name: platform\n"
                "  empty value:\n"
                "  notes: >-\n"
                "    metadata block value\n"
                "---\n"
                "# Example\n",
                encoding="utf-8",
            )
            self.assertEqual(parse_frontmatter(path), ("example", description))

    def test_rejects_overlong_folded_description_with_blank_line(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(
                "---\n"
                "name: example\n"
                "description: >-\n"
                f"  {'x' * 40}\n"
                "\n"
                f"  {'y' * 2000}\n"
                "---\n"
                "# Example\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Description exceeds"):
                parse_frontmatter(path)

    def test_parses_quoted_scalars_and_inline_comments(self) -> None:
        cases = (
            (
                '"A description with a # marker and enough characters to pass."',
                "A description with a # marker and enough characters to pass.",
            ),
            (
                '"A description with a YAML escape \\x41 and enough characters."',
                "A description with a YAML escape A and enough characters.",
            ),
            (
                "'A description with doubled '' quotes and enough characters.' # comment",
                "A description with doubled ' quotes and enough characters.",
            ),
            (
                "A description with enough characters to pass here. # comment",
                "A description with enough characters to pass here.",
            ),
        )
        for value, expected in cases:
            with self.subTest(value=value), TemporaryDirectory() as directory:
                path = Path(directory) / "SKILL.md"
                path.write_text(
                    f"---\nname: example\ndescription: {value}\n---\n# Example\n",
                    encoding="utf-8",
                )
                self.assertEqual(parse_frontmatter(path), ("example", expected))

    def test_parses_comments_quoted_keys_and_multiline_scalars(self) -> None:
        cases = (
            (
                "---\n"
                "  # indented comment before the first field\n"
                '"name": example # inline comment\n'
                "  # indented comment between fields\n"
                '"description": This description is\n'
                "  comfortably longer than forty characters.\n"
                "# comment before an optional field\n"
                'license: "MIT"\n'
                "---\n"
                "# Example\n",
                (
                    "example",
                    "This description is comfortably longer than forty characters.",
                ),
            ),
            (
                "---\n"
                "name: example\n"
                'description: "This description is\n'
                "  comfortably longer than forty characters.\"\n"
                "---\n"
                "# Example\n",
                (
                    "example",
                    "This description is comfortably longer than forty characters.",
                ),
            ),
        )
        for content, expected in cases:
            with self.subTest(content=content), TemporaryDirectory() as directory:
                path = Path(directory) / "SKILL.md"
                path.write_text(content, encoding="utf-8")
                self.assertEqual(parse_frontmatter(path), expected)

    def test_preserves_block_scalar_boundaries(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(
                "---\n"
                "name: example\n"
                "description: >-\n"
                "  first line with enough words to pass the minimum.\n"
                "    more indented line\n"
                "  final line.\n"
                "---\n"
                "# Example\n",
                encoding="utf-8",
            )
            self.assertEqual(
                parse_frontmatter(path)[1],
                "first line with enough words to pass the minimum.\n  more indented line\nfinal line.",
            )

    def test_preserves_explicit_block_indent_after_leading_blank(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(
                "---\n"
                "name: example\n"
                "description: >2-\n"
                "\n"
                "    first line with enough words to pass the minimum.\n"
                "---\n"
                "# Example\n",
                encoding="utf-8",
            )
            self.assertEqual(parse_frontmatter(path)[1], "first line with enough words to pass the minimum.")

    def test_rejects_malformed_frontmatter_and_invalid_names(self) -> None:
        cases = (
            "name: example\ndescription: This description is comfortably longer than forty characters.\nnot yaml at all\n",
            "name: example\ndescription: 'This description is comfortably longer than forty characters.'oops\n",
            "name: example\ndescription: > -\n  This description is comfortably longer than forty characters.\n",
            "name: example\ndescription: - This description is comfortably longer than forty characters.\n",
            "name: example\ndescription: >-\n\tThis description is comfortably longer than forty characters.\n",
            "name: foo--bar\ndescription: This description is comfortably longer than forty characters.\n",
            "name: -foo\ndescription: This description is comfortably longer than forty characters.\n",
            "name: Foo\ndescription: This description is comfortably longer than forty characters.\n",
            "name: foo_bar\ndescription: This description is comfortably longer than forty characters.\n",
            f"name: {'x' * 65}\ndescription: This description is comfortably longer than forty characters.\n",
            "name: example\ndescription: \"                                        \"\n",
        )
        for frontmatter in cases:
            with self.subTest(frontmatter=frontmatter), TemporaryDirectory() as directory:
                path = Path(directory) / "SKILL.md"
                path.write_text(f"---\n{frontmatter}---\n# Example\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    parse_frontmatter(path)

    def test_rejects_invalid_opening_marker(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(
                " ---\n"
                "name: example\n"
                "description: This description is comfortably longer than forty characters.\n"
                "---\n"
                "# Example\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "start with YAML frontmatter"):
                parse_frontmatter(path)

    def test_rejects_invalid_closing_marker(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(
                "---\n"
                "name: example\n"
                "description: This description is comfortably longer than forty characters.\n"
                "---not-a-delimiter\n"
                "# Example\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "closing marker"):
                parse_frontmatter(path)

    def test_rejects_literal_frontmatter_control_characters(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(
                "---\n"
                "name: example\n"
                "description: This description is comfortably longer than forty characters.\x1b\n"
                "---\n"
                "# Example\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                parse_frontmatter(path)

    def test_rejects_unsupported_optional_frontmatter_values(self) -> None:
        cases = (
            "compatibility: [python, node]",
            "license: {name: MIT}",
            "allowed-tools: *alias",
            "metadata: [owner]",
            "metadata: {}",
        )
        for field in cases:
            with self.subTest(field=field), TemporaryDirectory() as directory:
                path = Path(directory) / "SKILL.md"
                path.write_text(
                    "---\n"
                    "name: example\n"
                    "description: This description is comfortably longer than forty characters.\n"
                    f"{field}\n"
                    "---\n"
                    "# Example\n",
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    parse_frontmatter(path)

    def test_rejects_overlong_compatibility(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(
                "---\n"
                "name: example\n"
                "description: This description is comfortably longer than forty characters.\n"
                f"compatibility: {'x' * 501}\n"
                "---\n"
                "# Example\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Compatibility"):
                parse_frontmatter(path)

    def test_rejects_description_outside_length_boundaries(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(
                f"---\nname: example\ndescription: {'x' * 1025}\n---\n# Example\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Description exceeds"):
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
