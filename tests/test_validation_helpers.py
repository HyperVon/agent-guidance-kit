from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_repository = load("validate_repository", ROOT / "scripts/validate_repository.py")
public_hygiene = load("public_hygiene_check", ROOT / "scripts/public_hygiene_check.py")


class ValidationHelpersTest(unittest.TestCase):
    def test_simple_frontmatter_accepts_project_subset(self) -> None:
        values, error = validate_repository.simple_frontmatter(
            '---\nname: example-skill\ndescription: "A useful description that is long enough for routing."\n---\n\n# Example\n'
        )
        self.assertIsNone(error)
        self.assertEqual("example-skill", values["name"])

    def test_simple_frontmatter_accepts_folded_description(self) -> None:
        values, error = validate_repository.simple_frontmatter(
            '---\nname: example\ndescription: >-\n  folded text\n---\n'
        )
        self.assertIsNone(error)
        self.assertEqual("folded text", values["description"])

    def test_simple_frontmatter_rejects_nested_structure(self) -> None:
        _, error = validate_repository.simple_frontmatter(
            '---\nname: example\ndescription:\n  nested: value\n---\n'
        )
        self.assertIsNotNone(error)

    def test_hygiene_patterns_recognize_representative_secrets(self) -> None:
        checks = dict(public_hygiene.patterns())
        self.assertIsNotNone(checks["AWS access key"].search("AKIA" + "IOSFODNN7EXAMPLE"))
        self.assertIsNotNone(checks["private key block"].search("BEGIN " + "PRIVATE KEY"))


if __name__ == "__main__":
    unittest.main()
