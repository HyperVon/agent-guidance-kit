from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/bootstrap-project/scripts"))
import install_skills

INVENTORY_SCRIPT = (
    ROOT / ".agents/skills/bootstrap-project/scripts/inventory_project.py"
)
RESOLVE_SCRIPT = (
    ROOT / ".agents/skills/agent-guidance-maintenance/scripts/resolve_source.py"
)

SPEC_INV = importlib.util.spec_from_file_location("inventory_project", INVENTORY_SCRIPT)
assert SPEC_INV and SPEC_INV.loader
inventory_project = importlib.util.module_from_spec(SPEC_INV)
SPEC_INV.loader.exec_module(inventory_project)

SPEC_RES = importlib.util.spec_from_file_location("resolve_source", RESOLVE_SCRIPT)
assert SPEC_RES and SPEC_RES.loader
resolve_source = importlib.util.module_from_spec(SPEC_RES)
SPEC_RES.loader.exec_module(resolve_source)


class BootstrapIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.target = base / "target"
        self.target.mkdir()
        subprocess.run(
            ["git", "init", "--quiet", str(self.target)],
            check=True,
            capture_output=True,
        )
        # Provide some existing project content for inventory coverage
        (self.target / "src").mkdir()
        (self.target / "src/app.py").write_text("print('hello')\n", encoding="utf-8")
        (self.target / "AGENTS.md").write_text(
            "# Local rules\n\nKeep this local content.\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_inventory_and_source_resolution(self) -> None:
        facts = inventory_project.inventory(self.target, 200)

        self.assertIn("Python", facts["languages_by_file_count"])
        self.assertIn("AGENTS.md", facts["guidance_files"])
        self.assertIn("AGENTS.md", facts["harness_markers"])
        self.assertIsInstance(facts["files_scanned"], int)

        # Explicit source resolution must return the real kit root
        root, method = resolve_source.resolve_source(self.target, ROOT, environment={})
        self.assertEqual(ROOT.resolve(), root)
        self.assertEqual("explicit", method)

        # Environment variable path also works
        alt_env = {resolve_source.ENVIRONMENT_VARIABLE: str(ROOT)}
        root2, method2 = resolve_source.resolve_source(self.target, environment=alt_env)
        self.assertEqual(ROOT.resolve(), root2)
        self.assertEqual("environment", method2)

    def test_full_bootstrap_build_apply_validate(self) -> None:
        # Use a skill with no dependencies to keep closure simple
        requested = ["ai-slop-detector"]
        plan = install_skills.build_plan(ROOT, self.target, requested)

        # Plan must include mandatory maintenance skill automatically
        names = [item["name"] for item in plan["skills"]]
        self.assertIn("agent-guidance-maintenance", names)
        self.assertIn("ai-slop-detector", names)

        # Source resolution for a fresh git worktree should be CONFIGURE
        self.assertEqual("CONFIGURE", plan["source_resolution"]["status"])

        receipt_path = install_skills.apply_plan(ROOT, self.target, plan)

        # Receipts are written under .agents/.agent-guidance-kit/receipts/
        self.assertTrue(receipt_path.is_file())
        self.assertEqual(
            (
                self.target.resolve()
                / install_skills.RECEIPTS
                / f"{plan['plan_id']}.json"
            ),
            receipt_path.resolve(),
        )
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(plan["plan_id"], receipt["plan_id"])

        # Installed skills exist and match source digests
        for item in plan["skills"]:
            dest = self.target / Path(item["destination"])
            self.assertTrue(dest.is_dir(), f"missing destination {dest}")
            self.assertTrue((dest / "SKILL.md").is_file())
            digest = install_skills.manifest_digest(install_skills.tree_manifest(dest))
            self.assertEqual(item["source_digest"], digest)

        # Managed route block is updated and preserves local content
        agents_content = (self.target / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Keep this local content.", agents_content)
        self.assertEqual(1, agents_content.count(install_skills.ROUTE_START))
        self.assertEqual(1, agents_content.count(install_skills.ROUTE_END))
        self.assertIn(".agents/skills/ai-slop-detector/SKILL.md", agents_content)

        # Source locator was configured and is ignored
        locator = self.target / install_skills.SOURCE_LOCATOR
        self.assertTrue(locator.is_file())
        ignored = subprocess.run(
            [
                "git",
                "-C",
                str(self.target),
                "check-ignore",
                "--quiet",
                "--",
                locator.as_posix(),
            ],
            check=False,
        )
        self.assertEqual(0, ignored.returncode)

        # validate_installed must succeed on a clean target
        install_skills.validate_installed(self.target, plan)

    def test_idempotent_reapply_produces_no_changes(self) -> None:
        requested = ["code-review"]
        plan = install_skills.build_plan(ROOT, self.target, requested)
        first_receipt = install_skills.apply_plan(ROOT, self.target, plan)

        agents_before = (self.target / "AGENTS.md").read_bytes()
        receipt_bytes_before = first_receipt.read_bytes()
        skills_before = {
            item["name"]: install_skills.manifest_digest(
                install_skills.tree_manifest(self.target / Path(item["destination"]))
            )
            for item in plan["skills"]
        }

        # Idempotent re-apply with same plan
        second_receipt = install_skills.apply_plan(ROOT, self.target, plan)
        self.assertEqual(first_receipt, second_receipt)
        self.assertEqual(receipt_bytes_before, second_receipt.read_bytes())
        self.assertEqual(agents_before, (self.target / "AGENTS.md").read_bytes())
        for item in plan["skills"]:
            digest = install_skills.manifest_digest(
                install_skills.tree_manifest(self.target / Path(item["destination"]))
            )
            self.assertEqual(skills_before[item["name"]], digest)

        # Re-planning with same inputs yields UNCHANGED statuses
        second_plan = install_skills.build_plan(ROOT, self.target, requested)
        for item in second_plan["skills"]:
            self.assertEqual("UNCHANGED", item["status"])
        self.assertEqual("UNCHANGED", second_plan["routing"]["status"])

    def test_tampered_target_fails_closed(self) -> None:
        requested = ["quality-hardening"]
        plan = install_skills.build_plan(ROOT, self.target, requested)
        install_skills.apply_plan(ROOT, self.target, plan)

        # Tamper installed skill content — validate_installed must fail
        skill_file = self.target / ".agents/skills/quality-hardening/SKILL.md"
        skill_file.write_text("tampered content\n", encoding="utf-8")
        with self.assertRaisesRegex(
            install_skills.AdoptionError, "receipt|matches its receipt|changed"
        ):
            install_skills.validate_installed(self.target, plan)

        # Restore then tamper the managed route block
        plan2 = install_skills.build_plan(ROOT, self.target, requested)
        # plan2 will be CONFLICT because installed skill is now modified
        self.assertEqual(
            "CONFLICT",
            next(i for i in plan2["skills"] if i["name"] == "quality-hardening")[
                "status"
            ],
        )

        # Clean tamper for route test — reinstall clean
        shutil.rmtree(self.target / ".agents/skills/quality-hardening")
        # Need to also clear receipt so we can re-apply clean
        for receipt in (self.target / install_skills.RECEIPTS).glob("*.json"):
            receipt.unlink()
        shutil.rmtree(self.target / ".agents/skills/agent-guidance-maintenance")
        # Reset AGENTS.md to state before tamper by re-applying
        # Simplest: recreate target routing cleanly
        clean_plan = install_skills.build_plan(ROOT, self.target, requested)
        install_skills.apply_plan(ROOT, self.target, clean_plan)
        agents = self.target / "AGENTS.md"
        tampered = agents.read_text(encoding="utf-8").replace(
            install_skills.ROUTE_START, "TAMPERED"
        )
        agents.write_text(tampered, encoding="utf-8")
        with self.assertRaisesRegex(
            install_skills.AdoptionError, "managed AGENTS route"
        ):
            install_skills.validate_installed(self.target, clean_plan)


if __name__ == "__main__":
    unittest.main()
