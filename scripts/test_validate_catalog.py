import subprocess
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import validate_catalog
from validate_catalog import parse_frontmatter


ROOT = Path(__file__).resolve().parents[1]
VALID_DESCRIPTION = "A description that identifies this example skill and its trigger."


def document(frontmatter: str, body: str = "# Example\n") -> str:
    return f"---\n{frontmatter}---\n{body}"


@contextmanager
def temporary_skill(content: str, directory_name: str = "example"):
    with TemporaryDirectory() as directory:
        skill_dir = Path(directory) / directory_name
        skill_dir.mkdir()
        path = skill_dir / "SKILL.md"
        path.write_text(content, encoding="utf-8")
        yield path


def write_skill(skills_root: Path, directory_name: str, name: str) -> Path:
    skill_dir = skills_root / directory_name
    skill_dir.mkdir(parents=True)
    path = skill_dir / "SKILL.md"
    path.write_text(document(f"name: {name}\ndescription: {VALID_DESCRIPTION}\n"), encoding="utf-8")
    return path


class CatalogValidatorTests(unittest.TestCase):
    def test_repository_catalog_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_catalog.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("25 skills", result.stdout)

    def test_parses_folded_description(self) -> None:
        content = document(
            "name: example\n"
            "description: >-\n"
            "  First line supplies a valid description.\n"
            "  Second line completes it.\n"
        )
        with temporary_skill(content) as path:
            self.assertEqual(
                parse_frontmatter(path),
                ("example", "First line supplies a valid description. Second line completes it."),
            )

    def test_parses_quoted_scalars(self) -> None:
        content = document(
            'name: "example"\n'
            'description: "A description with a # marker and enough context to pass."\n'
        )
        with temporary_skill(content) as path:
            self.assertEqual(
                parse_frontmatter(path),
                ("example", "A description with a # marker and enough context to pass."),
            )

    def test_preserves_yaml_12_plain_scalars(self) -> None:
        content = document("name: on\ndescription: off\n")
        with temporary_skill(content) as path:
            self.assertEqual(parse_frontmatter(path), ("on", "off"))

    def test_rejects_duplicate_frontmatter_keys(self) -> None:
        content = document(
            "name: example\n"
            f"description: {VALID_DESCRIPTION}\n"
            "name: other\n"
        )
        with temporary_skill(content) as path:
            with self.assertRaisesRegex(ValueError, "duplicate key"):
                parse_frontmatter(path)

    def test_accepts_supported_optional_fields(self) -> None:
        content = document(
            "name: example\n"
            f"description: {VALID_DESCRIPTION}\n"
            "license: Apache-2.0\n"
            "allowed-tools: Read Bash\n"
            "compatibility: Requires Python and a shell.\n"
            "metadata:\n"
            "  owner: platform\n"
            '  version: "1"\n'
        )
        with temporary_skill(content) as path:
            self.assertEqual(parse_frontmatter(path), ("example", VALID_DESCRIPTION))

    def test_rejects_malformed_or_non_mapping_frontmatter(self) -> None:
        cases = (
            "name: example\ndescription: [unterminated\n",
            "? [unhashable, key]\n: value\n",
            "name: example\ndescription: contains a separator\x1c\n",
            "- name\n- description\n",
        )
        for frontmatter in cases:
            with self.subTest(frontmatter=frontmatter), temporary_skill(document(frontmatter)) as path:
                with self.assertRaises(ValueError):
                    parse_frontmatter(path)

    def test_rejects_invalid_opening_fence(self) -> None:
        content = (
            " ---\n"
            "name: example\n"
            f"description: {VALID_DESCRIPTION}\n"
            "---\n"
            "# Example\n"
        )
        with temporary_skill(content) as path:
            with self.assertRaisesRegex(ValueError, "start with YAML frontmatter"):
                parse_frontmatter(path)

    def test_rejects_invalid_closing_fence(self) -> None:
        content = (
            "---\n"
            "name: example\n"
            f"description: {VALID_DESCRIPTION}\n"
            "---not-a-delimiter\n"
            "# Example\n"
        )
        with temporary_skill(content) as path:
            with self.assertRaisesRegex(ValueError, "closing marker"):
                parse_frontmatter(path)

    def test_rejects_missing_required_fields(self) -> None:
        cases = (
            (f"description: {VALID_DESCRIPTION}\n", "name"),
            ("name: example\n", "description"),
        )
        for frontmatter, field in cases:
            with self.subTest(field=field), temporary_skill(document(frontmatter)) as path:
                with self.assertRaisesRegex(ValueError, f"(?i)missing.*{field}"):
                    parse_frontmatter(path)

    def test_rejects_invalid_skill_names(self) -> None:
        cases = (
            "Foo",
            "-example",
            "example-",
            "example--name",
            "example_name",
            "ⓐ",
            "ℂ",
            "x" * 65,
        )
        for name in cases:
            with self.subTest(name=name), temporary_skill(
                document(f"name: {name}\ndescription: {VALID_DESCRIPTION}\n")
            ) as path:
                with self.assertRaises(ValueError):
                    parse_frontmatter(path)

    def test_rejects_surrounding_name_whitespace(self) -> None:
        content = document(f'name: " example "\ndescription: {VALID_DESCRIPTION}\n')
        with temporary_skill(content) as path:
            with self.assertRaises(ValueError):
                parse_frontmatter(path)

    def test_rejects_non_string_skill_name(self) -> None:
        with temporary_skill(document(f"name: 123\ndescription: {VALID_DESCRIPTION}\n")) as path:
            with self.assertRaisesRegex(ValueError, "name.*non-empty string"):
                parse_frontmatter(path)

    def test_rejects_non_string_or_empty_description(self) -> None:
        for description in ("123", "[]", '""'):
            with self.subTest(description=description), temporary_skill(
                document(f"name: example\ndescription: {description}\n")
            ) as path:
                with self.assertRaisesRegex(ValueError, "description.*non-empty string"):
                    parse_frontmatter(path)

    def test_rejects_directory_name_mismatch(self) -> None:
        content = document(f"name: example\ndescription: {VALID_DESCRIPTION}\n")
        with temporary_skill(content, directory_name="different") as path:
            with self.assertRaisesRegex(ValueError, "Directory name"):
                parse_frontmatter(path, check_directory=True)

    def test_enforces_description_length_boundaries(self) -> None:
        for length in (1, 1024):
            with self.subTest(length=length), temporary_skill(
                document(f"name: example\ndescription: {'x' * length}\n")
            ) as path:
                self.assertEqual(len(parse_frontmatter(path)[1]), length)

        with temporary_skill(document(f"name: example\ndescription: {'x' * 1025}\n")) as path:
            with self.assertRaisesRegex(ValueError, "Description exceeds"):
                parse_frontmatter(path)

    def test_enforces_compatibility_length_and_type(self) -> None:
        for value in ("x" * 500,):
            with self.subTest(value_length=len(value)), temporary_skill(
                document(f"name: example\ndescription: {VALID_DESCRIPTION}\ncompatibility: {value}\n")
            ) as path:
                parse_frontmatter(path)

        cases = ("", "   ", "x" * 501, "[python, node]")
        for compatibility in cases:
            with self.subTest(compatibility=compatibility), temporary_skill(
                document(
                    f"name: example\ndescription: {VALID_DESCRIPTION}\ncompatibility: {compatibility}\n"
                )
            ) as path:
                with self.assertRaisesRegex(ValueError, "Compatibility|compatibility"):
                    parse_frontmatter(path)

    def test_rejects_unsupported_fields_and_optional_types(self) -> None:
        cases = (
            "owner: platform",
            "license: {name: MIT}",
            "allowed-tools: [Read, Bash]",
            "metadata: [owner]",
            "metadata:\n  owner: 1\n",
        )
        for field in cases:
            with self.subTest(field=field), temporary_skill(
                document(f"name: example\ndescription: {VALID_DESCRIPTION}\n{field}")
            ) as path:
                with self.assertRaises(ValueError):
                    parse_frontmatter(path)

    def test_rejects_empty_skill_body(self) -> None:
        content = document(f"name: example\ndescription: {VALID_DESCRIPTION}\n", body="  \n")
        with temporary_skill(content) as path:
            with self.assertRaisesRegex(ValueError, "skill body is empty"):
                parse_frontmatter(path)

    def test_reports_missing_yaml_dependency(self) -> None:
        content = document(f"name: example\ndescription: {VALID_DESCRIPTION}\n")
        with temporary_skill(content) as path, patch.object(validate_catalog, "yaml", None):
            with self.assertRaisesRegex(ValueError, "PyYAML is required"):
                parse_frontmatter(path)

    def test_rejects_readme_catalog_mismatch_and_duplicate_names(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            skills_root = root / "skills"
            skills_root.mkdir()
            write_skill(skills_root, "first", "duplicate")
            write_skill(skills_root, "second", "duplicate")
            (root / "README.md").write_text(
                "# Catalog\n\n| Skill | What it does |\n| :--- | :--- |\n"
                "| [unknown](skills/unknown/SKILL.md) | Example |\n",
                encoding="utf-8",
            )

            with patch.object(validate_catalog, "ROOT", root), patch.object(
                validate_catalog, "SKILLS_ROOT", skills_root
            ):
                errors = validate_catalog.validate()

        self.assertTrue(any("duplicate skill name 'duplicate'" in error for error in errors))
        self.assertTrue(any("appears 0 times" in error for error in errors))
        self.assertTrue(any("removed or unknown skill 'unknown'" in error for error in errors))

    def test_rejects_missing_and_escaping_repository_links(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            skills_root = root / "skills"
            skill_file = write_skill(skills_root, "example", "example")
            skill_file.write_text(
                document(
                    f"name: example\ndescription: {VALID_DESCRIPTION}\n",
                    body=(
                        "[missing](references/missing.md)\n"
                        "[escape](../../../outside.md)\n"
                        "[external](https://example.com)\n"
                    ),
                ),
                encoding="utf-8",
            )
            readme = root / "README.md"
            readme.write_text(
                "# Catalog\n\n[example](skills/example/SKILL.md)\n",
                encoding="utf-8",
            )

            with patch.object(validate_catalog, "ROOT", root), patch.object(
                validate_catalog, "SKILLS_ROOT", skills_root
            ), patch.object(validate_catalog, "tracked_markdown_files", return_value=[skill_file, readme]):
                errors = validate_catalog.validate()

        self.assertTrue(any("missing link target" in error for error in errors))
        self.assertTrue(any("link escapes repository" in error for error in errors))

    def test_accepts_unicode_skill_names_in_readme_catalog(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            skills_root = root / "skills"
            skill_file = write_skill(skills_root, "café", "café")
            readme = root / "README.md"
            readme.write_text("# Catalog\n\n| Skill | What it does |\n| :--- | :--- |\n| [café](skills/café/SKILL.md) | Example |\n", encoding="utf-8")

            with patch.object(validate_catalog, "ROOT", root), patch.object(
                validate_catalog, "SKILLS_ROOT", skills_root
            ), patch.object(validate_catalog, "tracked_markdown_files", return_value=[skill_file, readme]):
                errors = validate_catalog.validate()

        self.assertEqual(errors, [])

if __name__ == "__main__":
    unittest.main()
