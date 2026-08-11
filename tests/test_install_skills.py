from __future__ import annotations

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agents/skills/bootstrap-project/scripts/install_skills.py"
SPEC = importlib.util.spec_from_file_location("install_skills", SCRIPT)
assert SPEC and SPEC.loader
install_skills = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install_skills)


class InstallSkillsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.kit = base / "kit"
        self.target = base / "target"
        self.kit.mkdir()
        self.target.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_skill(self, name: str, body: str = "# Skill\n") -> Path:
        directory = self.kit / ".agents/skills" / name
        (directory / "agents").mkdir(parents=True)
        (directory / "SKILL.md").write_text(
            f'---\nname: {name}\ndescription: "A sufficiently detailed test skill description for validation."\n---\n\n{body}',
            encoding="utf-8",
        )
        (directory / "agents/openai.yaml").write_text(
            f'interface:\n  display_name: "Test"\n  short_description: "A sufficiently long description"\n'
            f'  default_prompt: "Use ${name} for this test."\n',
            encoding="utf-8",
        )
        return directory

    def test_plan_apply_and_idempotent_receipt(self) -> None:
        self.add_skill("alpha")
        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])

        self.assertEqual("CREATE", plan["skills"][0]["status"])
        receipt = install_skills.apply_plan(self.kit, self.target, plan)

        installed = self.target / ".agents/skills/alpha/SKILL.md"
        self.assertTrue(installed.is_file())
        self.assertTrue(receipt.is_file())
        self.assertEqual(plan["plan_id"], json.loads(receipt.read_text())["plan_id"])
        self.assertEqual(
            receipt, install_skills.apply_plan(self.kit, self.target, plan)
        )

    def test_conflict_blocks_all_selected_skills(self) -> None:
        self.add_skill("alpha")
        self.add_skill("beta")
        conflict = self.target / ".agents/skills/beta"
        conflict.mkdir(parents=True)
        (conflict / "SKILL.md").write_text("local content\n", encoding="utf-8")
        plan = install_skills.build_plan(self.kit, self.target, ["alpha", "beta"])

        statuses = {item["name"]: item["status"] for item in plan["skills"]}
        self.assertEqual({"alpha": "CREATE", "beta": "CONFLICT"}, statuses)
        with self.assertRaisesRegex(install_skills.AdoptionError, "conflicts"):
            install_skills.apply_plan(self.kit, self.target, plan)
        self.assertFalse((self.target / ".agents/skills/alpha").exists())

    def test_source_drift_invalidates_plan(self) -> None:
        source = self.add_skill("alpha")
        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])
        (source / "SKILL.md").write_text("changed after approval\n", encoding="utf-8")

        with self.assertRaisesRegex(
            install_skills.AdoptionError, "changed after planning"
        ):
            install_skills.apply_plan(self.kit, self.target, plan)
        self.assertFalse((self.target / ".agents/skills/alpha").exists())

    def test_target_drift_invalidates_plan(self) -> None:
        self.add_skill("alpha")
        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])
        destination = self.target / ".agents/skills/alpha"
        destination.mkdir(parents=True)
        (destination / "SKILL.md").write_text("appeared later\n", encoding="utf-8")

        with self.assertRaisesRegex(
            install_skills.AdoptionError, "changed after planning"
        ):
            install_skills.apply_plan(self.kit, self.target, plan)

    def test_tampered_plan_is_rejected(self) -> None:
        self.add_skill("alpha")
        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])
        plan["skills"][0]["destination"] = ".agents/skills/elsewhere"

        with self.assertRaisesRegex(install_skills.AdoptionError, "plan digest"):
            install_skills.apply_plan(self.kit, self.target, plan)

    def test_identical_existing_skill_is_unchanged(self) -> None:
        source = self.add_skill("alpha")
        destination = self.target / ".agents/skills/alpha"
        destination.parent.mkdir(parents=True)
        shutil.copytree(source, destination)
        before = install_skills.manifest_digest(
            install_skills.tree_manifest(destination)
        )
        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])

        self.assertEqual("UNCHANGED", plan["skills"][0]["status"])
        install_skills.apply_plan(self.kit, self.target, plan)
        after = install_skills.manifest_digest(
            install_skills.tree_manifest(destination)
        )
        self.assertEqual(before, after)

    def test_symlinked_target_ancestor_is_rejected(self) -> None:
        self.add_skill("alpha")
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        try:
            os.symlink(outside, self.target / ".agents")
        except (AttributeError, NotImplementedError, OSError) as error:
            self.skipTest(f"symlink creation is unavailable: {error}")

        with self.assertRaisesRegex(
            install_skills.AdoptionError, "symlinked destination"
        ):
            install_skills.build_plan(self.kit, self.target, ["alpha"])

    def test_source_symlink_is_rejected(self) -> None:
        source = self.add_skill("alpha")
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        try:
            os.symlink(outside, source / "linked.txt")
        except (AttributeError, NotImplementedError, OSError) as error:
            self.skipTest(f"symlink creation is unavailable: {error}")

        with self.assertRaisesRegex(
            install_skills.AdoptionError, "symlinks are not allowed"
        ):
            install_skills.build_plan(self.kit, self.target, ["alpha"])

    def test_transient_development_files_are_not_planned_or_copied(self) -> None:
        source = self.add_skill("alpha")
        cache = source / "scripts/__pycache__"
        cache.mkdir(parents=True)
        (cache / "helper.pyc").write_bytes(b"bytecode")
        (source / ".DS_Store").write_bytes(b"metadata")
        (source / "notes.md~").write_text("editor backup\n", encoding="utf-8")

        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])
        planned = {item["path"] for item in plan["skills"][0]["files"]}
        install_skills.apply_plan(self.kit, self.target, plan)

        self.assertFalse(any("__pycache__" in path for path in planned))
        self.assertNotIn(".DS_Store", planned)
        self.assertNotIn("notes.md~", planned)
        destination = self.target / ".agents/skills/alpha"
        self.assertFalse((destination / "scripts/__pycache__").exists())
        self.assertFalse((destination / ".DS_Store").exists())
        self.assertFalse((destination / "notes.md~").exists())


if __name__ == "__main__":
    unittest.main()
