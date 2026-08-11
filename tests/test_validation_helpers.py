from __future__ import annotations

import importlib.util
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
