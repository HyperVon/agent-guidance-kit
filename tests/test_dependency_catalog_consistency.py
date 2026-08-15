from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/bootstrap-project/scripts"))
import install_skills  # noqa: E402


def _source_skill_names() -> set[str]:
    skills_root = ROOT / ".agents/skills"
    return {
        path.name
        for path in skills_root.iterdir()
        if path.is_dir() and not path.is_symlink() and not path.name.startswith(".")
    }


def _read_catalog(path: Path) -> dict[str, dict[str, object]]:
    """Read the catalog JSON directly, independent of install_skills."""
    value = json.loads(path.read_text(encoding="utf-8"))
    return value["skills"]  # type: ignore[no-any-return]


class DependencyCatalogConsistencyTest(unittest.TestCase):
    def test_catalog_matches_source_skills(self) -> None:
        """The dependency catalog must list exactly the source skills.

        This detects catalog/source drift independently of load_dependencies:
        the raw catalog is read, the expected name set is derived from
        .agents/skills, and they are compared directly. A drift therefore
        surfaces as a failing assertion rather than a raise that shadows the
        headline check.
        """
        catalog = _read_catalog(ROOT / install_skills.DEPENDENCIES)
        self.assertEqual(set(catalog), _source_skill_names())

    def test_load_dependencies_succeeds_on_repo(self) -> None:
        """load_dependencies (the production contract) must accept the repo.

        The catalog==source invariant is asserted independently above; here
        we only confirm the real entry point does not raise.
        """
        catalog = install_skills.load_dependencies(ROOT)
        self.assertIsNotNone(catalog)

    def test_catalog_entries_satisfy_load_dependencies_schema(self) -> None:
        """Every catalog entry must satisfy load_dependencies' full schema.

        Independently re-checks the invariants enforced by
        dependencies.py:ref load_dependencies so this suite detects any
        relaxation: requires/related are lists, reference only known skills,
        no self-reference, no requires/related overlap, and route carries
        no ``|`` or newline.
        """
        catalog = _read_catalog(ROOT / install_skills.DEPENDENCIES)
        source_names = _source_skill_names()
        for name, entry in catalog.items():
            self.assertIsInstance(entry.get("requires"), list)
            self.assertIsInstance(entry.get("related"), list)
            route = entry.get("route")
            self.assertIsInstance(route, str)
            self.assertTrue(route)
            self.assertNotIn("|", route)
            self.assertNotIn("\n", route)
            requires = list(entry["requires"])  # type: ignore[arg-type]
            related = list(entry["related"])  # type: ignore[arg-type]
            for ref in requires + related:
                self.assertIn(ref, source_names)
            self.assertNotIn(name, requires)
            self.assertNotIn(name, related)
            self.assertEqual(set(requires) & set(related), set())

    def test_get_mandatory_skill_is_unambiguous(self) -> None:
        """The mandatory resolve_source provider must be unique.

        load_dependencies requires the catalog to match source skills, but
        only this assertion guards get_mandatory_skill's "exactly one
        no-dependency provider of scripts/resolve_source.py" invariant
        (dependencies.py:get_mandatory_skill). A future requires:[] skill that
        also ships scripts/resolve_source.py would make build_plan raise
        AdoptionError for every caller; this test names that gate.
        """
        self.assertEqual(
            install_skills.get_mandatory_skill(ROOT), "agent-guidance-maintenance"
        )


if __name__ == "__main__":
    unittest.main()
