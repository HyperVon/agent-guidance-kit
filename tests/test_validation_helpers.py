from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_repository = load(
    "validate_repository", ROOT / "scripts/validate_repository.py"
)
public_hygiene = load("public_hygiene_check", ROOT / "scripts/public_hygiene_check.py")
check = load("check", ROOT / "scripts/check.py")
setup_dev = load("setup_dev", ROOT / "scripts/setup_dev.py")


class ValidationHelpersTest(unittest.TestCase):
    def test_repository_validation_excludes_dependency_and_build_directories(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            self.assertFalse(
                validate_repository.is_project_path(
                    root / "node_modules/package/README.md", root
                )
            )
            self.assertFalse(
                validate_repository.is_project_path(root / ".venv/tool.py", root)
            )
            self.assertTrue(
                validate_repository.is_project_path(root / "docs/design.md", root)
            )

    def test_evaluation_cases_require_routing_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            evals = root / "evals/evals.json"
            evals.parent.mkdir()
            evals.write_text(
                '{"skill_name":"example","evals":['
                '{"id":1,"kind":"matching","prompt":"match",'
                '"expected_output":"out"},'
                '{"id":2,"kind":"neighboring","prompt":"near",'
                '"expected_output":"out"},'
                '{"id":3,"kind":"ambiguous","prompt":"unclear",'
                '"expected_output":"out"}]}'
            )
            errors: list[str] = []

            validate_repository.validate_evals(root, "example", errors)

            self.assertEqual([], errors)

    def test_evaluation_cases_reject_duplicate_ids_and_missing_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            evals = root / "evals/evals.json"
            evals.parent.mkdir()
            evals.write_text(
                '{"skill_name":"example","evals":['
                '{"id":1,"kind":"matching","prompt":"match",'
                '"expected_output":"out"},'
                '{"id":1,"kind":"edge","prompt":"edge",'
                '"expected_output":"out"},'
                '{"id":2,"kind":"edge","prompt":"edge",'
                '"expected_output":"out"}]}'
            )
            errors: list[str] = []

            validate_repository.validate_evals(root, "example", errors)

            self.assertTrue(any("unique integer" in error for error in errors))
            self.assertTrue(any("cover matching" in error for error in errors))

    def test_evaluation_cases_accept_safe_fixture_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            fixture = root / "evals/files/example.txt"
            fixture.parent.mkdir(parents=True)
            fixture.write_text("fixture")
            evals = root / "evals/evals.json"
            evals.write_text(
                '{"skill_name":"example","evals":['
                '{"id":1,"kind":"matching","prompt":"match",'
                '"expected_output":"out","files":["evals/files/example.txt"]},'
                '{"id":2,"kind":"neighboring","prompt":"near",'
                '"expected_output":"out"},'
                '{"id":3,"kind":"ambiguous","prompt":"unclear",'
                '"expected_output":"out"}]}'
            )
            errors: list[str] = []

            self.assertTrue(validate_repository.validate_evals(root, "example", errors))
            self.assertEqual([], errors)

    def test_evaluation_cases_reject_escaping_fixture_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "skill"
            root.mkdir()
            evals = root / "evals/evals.json"
            evals.parent.mkdir()
            evals.write_text(
                '{"skill_name":"example","evals":['
                '{"id":1,"kind":"matching","prompt":"match",'
                '"expected_output":"out","files":["../outside.txt"]},'
                '{"id":2,"kind":"neighboring","prompt":"near",'
                '"expected_output":"out"},'
                '{"id":3,"kind":"ambiguous","prompt":"unclear",'
                '"expected_output":"out"}]}'
            )
            errors: list[str] = []

            validate_repository.validate_evals(root, "example", errors)

            self.assertTrue(any("escapes skill" in error for error in errors))

    def test_evaluation_cases_reject_symlinked_fixture_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "skill"
            fixture = root / "evals/files/example.txt"
            fixture.parent.mkdir(parents=True)
            real_fixture = root / "evals/files/real.txt"
            real_fixture.write_text("fixture")
            try:
                os.symlink(real_fixture, fixture)
            except (AttributeError, NotImplementedError, OSError) as error:
                self.skipTest(f"symlink creation is unavailable: {error}")
            evals = root / "evals/evals.json"
            evals.write_text(
                '{"skill_name":"example","evals":['
                '{"id":1,"kind":"matching","prompt":"match",'
                '"expected_output":"out","files":["evals/files/example.txt"]},'
                '{"id":2,"kind":"neighboring","prompt":"near",'
                '"expected_output":"out"},'
                '{"id":3,"kind":"ambiguous","prompt":"unclear",'
                '"expected_output":"out"}]}'
            )
            errors: list[str] = []

            validate_repository.validate_evals(root, "example", errors)

            self.assertTrue(
                any("fixture must be a real file" in error for error in errors)
            )

    def test_markdownlint_command_uses_published_cli_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            cli = root / "node_modules/markdownlint-cli2/markdownlint-cli2-bin.mjs"
            cli.parent.mkdir(parents=True)
            cli.touch()

            self.assertEqual(
                ["node-test", str(cli)],
                check.markdownlint_command(root=root, node="node-test"),
            )

    def test_existing_virtual_environment_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            venv_dir = Path(temporary_directory) / ".venv"
            python = setup_dev.venv_python(venv_dir)
            python.parent.mkdir(parents=True)
            python.touch()

            self.assertEqual(python, setup_dev.ensure_venv(venv_dir))

    def test_incomplete_virtual_environment_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            venv_dir = Path(temporary_directory) / ".venv"
            venv_dir.mkdir()

            with self.assertRaisesRegex(RuntimeError, "not a complete"):
                setup_dev.ensure_venv(venv_dir)

    def test_simple_frontmatter_accepts_project_subset(self) -> None:
        values, error = validate_repository.simple_frontmatter(
            '---\nname: example-skill\ndescription: "A useful description that is long enough for routing."\n---\n\n# Example\n'
        )
        self.assertIsNone(error)
        self.assertEqual("example-skill", values["name"])

    def test_simple_frontmatter_accepts_folded_description(self) -> None:
        values, error = validate_repository.simple_frontmatter(
            "---\nname: example\ndescription: >-\n  folded text\n---\n"
        )
        self.assertIsNone(error)
        self.assertEqual("folded text", values["description"])

    def test_simple_frontmatter_accepts_standard_optional_fields(self) -> None:
        values, error = validate_repository.simple_frontmatter(
            "---\n"
            "name: example\n"
            "description: A useful portable skill description.\n"
            "license: Apache-2.0\n"
            "compatibility: Requires Python 3.11 or newer\n"
            "metadata:\n"
            "  author: example-org\n"
            '  version: "1.0"\n'
            "allowed-tools: Read Bash(git:*)\n"
            "---\n"
        )

        self.assertIsNone(error)
        self.assertEqual(
            {"author": "example-org", "version": "1.0"}, values["metadata"]
        )

    def test_simple_frontmatter_rejects_non_string_metadata_values(self) -> None:
        _, error = validate_repository.simple_frontmatter(
            "---\nname: example\ndescription: useful\nmetadata:\n  version: 1\n---\n"
        )

        self.assertIsNotNone(error)

    def test_simple_frontmatter_rejects_nested_structure(self) -> None:
        _, error = validate_repository.simple_frontmatter(
            "---\nname: example\ndescription:\n  nested: value\n---\n"
        )
        self.assertIsNotNone(error)

    def test_hygiene_patterns_recognize_representative_secrets(self) -> None:
        checks = dict(public_hygiene.patterns())
        self.assertIsNotNone(
            checks["AWS access key"].search("AKIA" + "IOSFODNN7EXAMPLE")
        )
        self.assertIsNotNone(
            checks["private key block"].search("BEGIN " + "PRIVATE KEY")
        )


if __name__ == "__main__":
    unittest.main()
