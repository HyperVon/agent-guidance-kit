from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Import from the package
sys.path.insert(0, str(ROOT / ".agents/skills/bootstrap-project/scripts"))
import install_skills


class InstallSkillsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.kit = base / "kit"
        self.target = base / "target"
        self.kit.mkdir()
        self.target.mkdir()
        subprocess.run(
            ["git", "init", "--quiet", str(self.target)],
            check=True,
            capture_output=True,
        )
        self.catalog: dict[str, dict[str, object]] = {}
        self.add_skill("bootstrap-project")
        installer = (
            self.kit / ".agents/skills/bootstrap-project/scripts/install_skills.py"
        )
        installer.parent.mkdir(parents=True)
        installer.write_text("# test installer marker\n", encoding="utf-8")
        maintenance = self.add_skill("agent-guidance-maintenance")
        resolver = maintenance / "scripts/resolve_source.py"
        resolver.parent.mkdir()
        shutil.copy2(
            ROOT
            / ".agents/skills/agent-guidance-maintenance/scripts/resolve_source.py",
            resolver,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_catalog(self) -> None:
        path = self.kit / ".agents/skill-dependencies.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"schema_version": 1, "skills": self.catalog}),
            encoding="utf-8",
        )

    def add_skill(
        self,
        name: str,
        body: str = "# Skill\n",
        *,
        requires: list[str] | None = None,
        related: list[str] | None = None,
    ) -> Path:
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
        self.catalog[name] = {
            "requires": requires or [],
            "related": related or [],
            "route": f"Use {name} for its test workflow",
        }
        self.write_catalog()
        return directory

    def test_plan_apply_and_idempotent_receipt(self) -> None:
        self.add_skill("alpha")
        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])

        statuses = {item["name"]: item["status"] for item in plan["skills"]}
        self.assertEqual(
            {"agent-guidance-maintenance": "CREATE", "alpha": "CREATE"},
            statuses,
        )
        receipt = install_skills.apply_plan(self.kit, self.target, plan)

        installed = self.target / ".agents/skills/alpha/SKILL.md"
        self.assertTrue(installed.is_file())
        self.assertTrue(receipt.is_file())
        self.assertTrue((self.target / "AGENTS.md").is_file())
        locator = self.target / ".agents/.agent-guidance-kit/source.json"
        self.assertTrue(locator.is_file())
        ignored = subprocess.run(
            [
                "git",
                "-C",
                str(self.target),
                "check-ignore",
                "--quiet",
                "--",
                ".agents/.agent-guidance-kit/source.json",
            ],
            check=False,
        )
        self.assertEqual(0, ignored.returncode)
        self.assertEqual(plan["plan_id"], json.loads(receipt.read_text())["plan_id"])
        self.assertEqual(
            receipt, install_skills.apply_plan(self.kit, self.target, plan)
        )

    def test_adjacent_source_resolution_does_not_create_locator(self) -> None:
        adjacent_kit = Path(self.temp.name) / "agent-guidance-kit"
        self.kit.rename(adjacent_kit)
        self.kit = adjacent_kit
        self.add_skill("alpha")
        environment_value = os.environ.pop(install_skills.SOURCE_ENVIRONMENT, None)
        try:
            plan = install_skills.build_plan(self.kit, self.target, ["alpha"])
            self.assertEqual("UNCHANGED", plan["source_resolution"]["status"])
            self.assertEqual("adjacent sibling", plan["source_resolution"]["method"])
            install_skills.apply_plan(self.kit, self.target, plan)
        finally:
            if environment_value is not None:
                os.environ[install_skills.SOURCE_ENVIRONMENT] = environment_value

        self.assertFalse((self.target / install_skills.SOURCE_LOCATOR).exists())

    def test_conflict_blocks_all_selected_skills(self) -> None:
        self.add_skill("alpha")
        self.add_skill("beta")
        conflict = self.target / ".agents/skills/beta"
        conflict.mkdir(parents=True)
        (conflict / "SKILL.md").write_text("local content\n", encoding="utf-8")
        plan = install_skills.build_plan(self.kit, self.target, ["alpha", "beta"])

        statuses = {item["name"]: item["status"] for item in plan["skills"]}
        self.assertEqual(
            {
                "agent-guidance-maintenance": "CREATE",
                "alpha": "CREATE",
                "beta": "CONFLICT",
            },
            statuses,
        )
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

    def test_source_locator_rolls_back_after_post_configuration_failure(self) -> None:
        self.add_skill("alpha")
        environment_value = os.environ.pop(install_skills.SOURCE_ENVIRONMENT, None)
        try:
            plan = install_skills.build_plan(self.kit, self.target, ["alpha"])
            self.assertEqual("CONFIGURE", plan["source_resolution"]["status"])
            route_path = self.target / plan["routing"]["path"]
            route_before = route_path.read_bytes() if route_path.exists() else None

            exclude_path = Path(
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(self.target),
                        "rev-parse",
                        "--path-format=absolute",
                        "--git-path",
                        "info/exclude",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            )
            exclude_before = (
                exclude_path.read_bytes() if exclude_path.exists() else None
            )

            original_validate = install_skills.apply.validate_installed_impl

            def fail_after_configuration(*args: object, **kwargs: object) -> None:
                raise install_skills.AdoptionError(
                    "injected post-configuration failure"
                )

            install_skills.apply.validate_installed_impl = fail_after_configuration
            try:
                with self.assertRaisesRegex(
                    install_skills.AdoptionError, "post-configuration failure"
                ):
                    install_skills.apply_plan(self.kit, self.target, plan)
            finally:
                install_skills.apply.validate_installed_impl = original_validate
        finally:
            if environment_value is not None:
                os.environ[install_skills.SOURCE_ENVIRONMENT] = environment_value

        locator = self.target / install_skills.SOURCE_LOCATOR
        self.assertFalse(locator.exists())
        self.assertFalse((self.target / ".agents/skills/alpha").exists())
        self.assertFalse(
            (self.target / ".agents/skills/agent-guidance-maintenance").exists()
        )
        if route_before is None:
            self.assertFalse(route_path.exists())
        else:
            self.assertEqual(route_before, route_path.read_bytes())
        exclude_after = exclude_path.read_bytes() if exclude_path.exists() else None
        self.assertEqual(exclude_before, exclude_after)
        self.assertFalse(
            any((self.target / install_skills.RECEIPTS).glob("*.json"))
            if (self.target / install_skills.RECEIPTS).is_dir()
            else False
        )

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

        statuses = {item["name"]: item["status"] for item in plan["skills"]}
        self.assertEqual("UNCHANGED", statuses["alpha"])
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

    def test_evaluation_material_is_not_planned_or_copied(self) -> None:
        source = self.add_skill("alpha")
        fixture = source / "evals/files/example.txt"
        fixture.parent.mkdir(parents=True)
        fixture.write_text("kit-only evaluation fixture\n", encoding="utf-8")

        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])
        planned = {item["path"] for item in plan["skills"][0]["files"]}
        install_skills.apply_plan(self.kit, self.target, plan)

        self.assertFalse(any(path.startswith("evals/") for path in planned))
        self.assertFalse((self.target / ".agents/skills/alpha/evals").exists())

    def test_required_dependencies_are_added_but_related_skills_are_not(self) -> None:
        self.add_skill("alpha")
        self.add_skill("gamma")
        self.add_skill(
            "beta",
            "# Skill\n\nUse [alpha](../alpha/SKILL.md). Related: `gamma`.\n",
            requires=["alpha"],
            related=["gamma"],
        )

        plan = install_skills.build_plan(self.kit, self.target, ["beta"])

        self.assertEqual(
            ["agent-guidance-maintenance", "alpha", "beta"],
            [item["name"] for item in plan["skills"]],
        )
        self.assertIn(
            "required by beta", plan["selection"]["automatically_added"]["alpha"]
        )
        self.assertNotIn("gamma", [item["name"] for item in plan["skills"]])

    def test_relative_link_to_optional_skill_is_rejected_during_planning(self) -> None:
        self.add_skill("alpha")
        self.add_skill(
            "beta",
            "# Skill\n\nUse [alpha](../alpha/SKILL.md).\n",
            related=["alpha"],
        )

        with self.assertRaisesRegex(
            install_skills.AdoptionError, "relative links to non-required"
        ):
            install_skills.build_plan(self.kit, self.target, ["beta"])

    def test_required_dependency_does_not_need_a_prose_link(self) -> None:
        self.add_skill("alpha")
        self.add_skill("beta", requires=["alpha"])

        plan = install_skills.build_plan(self.kit, self.target, ["beta"])

        self.assertEqual(
            ["agent-guidance-maintenance", "alpha", "beta"],
            [item["name"] for item in plan["skills"]],
        )

    def test_explicitly_requested_dependency_is_not_auto_added(self) -> None:
        # When a dependency is also explicitly requested, it must not appear in
        # automatically_added even if another requested skill also requires it.
        self.add_skill("alpha")
        self.add_skill("gamma")
        self.add_skill(
            "beta",
            "# Skill\n",
            requires=["alpha"],
        )

        plan = install_skills.build_plan(self.kit, self.target, ["beta", "alpha"])

        auto = plan["selection"]["automatically_added"]
        self.assertNotIn("alpha", auto)
        self.assertNotIn("beta", auto)
        self.assertIn("agent-guidance-maintenance", auto)

    def test_existing_agents_content_is_preserved_around_managed_routes(self) -> None:
        self.add_skill("alpha")
        agents = self.target / "AGENTS.md"
        agents.write_text("# Local rules\n\nKeep this content.\n", encoding="utf-8")

        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])
        self.assertEqual("APPEND", plan["routing"]["status"])
        install_skills.apply_plan(self.kit, self.target, plan)

        content = agents.read_text(encoding="utf-8")
        self.assertIn("Keep this content.", content)
        self.assertEqual(1, content.count(install_skills.ROUTE_START))
        self.assertIn(".agents/skills/alpha/SKILL.md", content)

    def test_crlf_agents_content_and_routes_keep_crlf_line_endings(self) -> None:
        self.add_skill("alpha")
        agents = self.target / "AGENTS.md"
        agents.write_bytes(b"# Local rules\r\n\r\nKeep this content.\r\n")

        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])
        install_skills.apply_plan(self.kit, self.target, plan)

        content = agents.read_bytes()
        self.assertTrue(content.startswith(b"# Local rules\r\n\r\n"))
        self.assertIn(install_skills.ROUTE_START.encode("utf-8"), content)
        self.assertNotIn(b"\n", content.replace(b"\r\n", b""))

    def test_malformed_managed_route_block_is_a_plan_conflict(self) -> None:
        self.add_skill("alpha")
        (self.target / "AGENTS.md").write_text(
            f"# Local\n\n{install_skills.ROUTE_START}\n",
            encoding="utf-8",
        )

        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])

        self.assertEqual("CONFLICT", plan["routing"]["status"])
        with self.assertRaisesRegex(install_skills.AdoptionError, "routing conflict"):
            install_skills.apply_plan(self.kit, self.target, plan)

    def test_locally_modified_managed_route_block_is_a_conflict(self) -> None:
        self.add_skill("alpha")
        initial = install_skills.build_plan(self.kit, self.target, ["alpha"])
        install_skills.apply_plan(self.kit, self.target, initial)
        agents = self.target / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8").replace(
                "Use alpha for its test workflow",
                "Locally customized alpha route",
            ),
            encoding="utf-8",
        )
        self.add_skill("beta")

        plan = install_skills.build_plan(self.kit, self.target, ["beta"])

        self.assertEqual("CONFLICT", plan["routing"]["status"])
        self.assertIn("receipt-owned", plan["routing"]["conflict"]["reason"])

    def test_local_content_outside_managed_routes_is_preserved_on_route_update(
        self,
    ) -> None:
        self.add_skill("alpha")
        initial = install_skills.build_plan(self.kit, self.target, ["alpha"])
        install_skills.apply_plan(self.kit, self.target, initial)
        agents = self.target / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8") + "\nLocal owner note.\n",
            encoding="utf-8",
        )
        self.add_skill("beta")

        plan = install_skills.build_plan(self.kit, self.target, ["beta"])
        self.assertEqual("UPDATE", plan["routing"]["status"])
        install_skills.apply_plan(self.kit, self.target, plan)

        content = agents.read_text(encoding="utf-8")
        self.assertIn("Local owner note.", content)
        self.assertIn(".agents/skills/beta/SKILL.md", content)

    def test_missing_receipt_owned_skill_blocks_a_later_plan(self) -> None:
        self.add_skill("alpha")
        initial = install_skills.build_plan(self.kit, self.target, ["alpha"])
        install_skills.apply_plan(self.kit, self.target, initial)
        shutil.rmtree(self.target / ".agents/skills/alpha")
        self.add_skill("beta")

        plan = install_skills.build_plan(self.kit, self.target, ["beta"])

        self.assertEqual("CONFLICT", plan["routing"]["status"])
        self.assertIn("alpha", plan["routing"]["conflict"]["reason"])

    def test_malformed_receipt_skill_identity_fails_closed(self) -> None:
        self.add_skill("alpha")
        directory = self.target / install_skills.RECEIPTS
        directory.mkdir(parents=True)
        (directory / "malformed.json").write_text(
            json.dumps(
                {"skills": [{"name": "../../escape", "source_digest": "a" * 64}]}
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            install_skills.AdoptionError, "identity or digest is malformed"
        ):
            install_skills.build_plan(self.kit, self.target, ["alpha"])

    def test_receipt_owned_skill_updates_but_local_modification_conflicts(self) -> None:
        source = self.add_skill("alpha", "# Skill\n\nVersion one.\n")
        initial = install_skills.build_plan(self.kit, self.target, ["alpha"])
        install_skills.apply_plan(self.kit, self.target, initial)

        (source / "SKILL.md").write_text(
            '---\nname: alpha\ndescription: "A sufficiently detailed test skill description for validation."\n---\n\n# Skill\n\nVersion two.\n',
            encoding="utf-8",
        )
        update = install_skills.build_plan(self.kit, self.target, ["alpha"])
        statuses = {item["name"]: item["status"] for item in update["skills"]}
        self.assertEqual("UPDATE", statuses["alpha"])
        install_skills.apply_plan(self.kit, self.target, update)
        self.assertIn(
            "Version two",
            (self.target / ".agents/skills/alpha/SKILL.md").read_text(),
        )

        (self.target / ".agents/skills/alpha/SKILL.md").write_text(
            "local modification\n", encoding="utf-8"
        )
        (source / "SKILL.md").write_text("source version three\n", encoding="utf-8")
        conflict = install_skills.build_plan(self.kit, self.target, ["alpha"])
        statuses = {item["name"]: item["status"] for item in conflict["skills"]}
        self.assertEqual("CONFLICT", statuses["alpha"])

    def test_selective_install_has_closed_links_and_complete_managed_index(
        self,
    ) -> None:
        plan_path = Path(self.temp.name) / "selective-plan.json"
        environment = dict(os.environ)
        environment.pop(install_skills.SOURCE_ENVIRONMENT, None)
        planned = subprocess.run(
            [
                os.sys.executable,
                str(install_skills.SCRIPT),
                "plan",
                "--kit-root",
                str(ROOT),
                "--target",
                str(self.target),
                "--skill",
                "ai-slop-detector",
                "--skill",
                "security-review",
                "--skill",
                "skill-authoring",
                "--output",
                str(plan_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(0, planned.returncode, planned.stderr)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))

        denied = subprocess.run(
            [
                os.sys.executable,
                str(install_skills.SCRIPT),
                "apply",
                "--kit-root",
                str(ROOT),
                "--target",
                str(self.target),
                "--plan",
                str(plan_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(2, denied.returncode)
        self.assertIn("requires --approve", denied.stderr)
        self.assertFalse((self.target / ".agents/skills/ai-slop-detector").exists())

        applied = subprocess.run(
            [
                os.sys.executable,
                str(install_skills.SCRIPT),
                "apply",
                "--kit-root",
                str(ROOT),
                "--target",
                str(self.target),
                "--plan",
                str(plan_path),
                "--approve",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(0, applied.returncode, applied.stderr)
        validator = (
            self.target
            / ".agents/skills/agent-guidance-maintenance/scripts/validate_adoption.py"
        )

        result = subprocess.run(
            [
                str(Path(os.sys.executable)),
                str(validator),
                "--target",
                str(self.target),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        selected = {item["name"] for item in plan["skills"]}
        self.assertEqual(
            {
                "agent-guidance-maintenance",
                "ai-slop-detector",
                "security-review",
                "skill-authoring",
                "skill-evaluation",
            },
            selected,
        )

        shutil.rmtree(self.target / ".agents/skills/security-review")
        missing = subprocess.run(
            [
                str(Path(os.sys.executable)),
                str(validator),
                "--target",
                str(self.target),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(1, missing.returncode)
        self.assertIn("receipt-owned skill is missing", missing.stderr)

    def test_generate_diff_update_renders_headers_on_separate_lines(self) -> None:
        # Force an UPDATE so generate_diff emits a unified diff, then assert the
        # --- / +++ / @@ headers are on distinct lines (no mashed rendering).
        source = self.add_skill("alpha")
        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])
        install_skills.apply_plan(self.kit, self.target, plan)
        (source / "SKILL.md").write_text(
            "# Alpha\n\nUpdated body for diff.\n", encoding="utf-8"
        )
        update_plan = install_skills.build_plan(self.kit, self.target, ["alpha"])
        diff = install_skills.generate_diff(update_plan, self.kit, self.target)
        self.assertIn("--- a/", diff)
        self.assertIn("+++ b/", diff)
        # A mashed header would look like "--- a/x.md+++ b/x.md".
        self.assertNotRegex(diff, r"--- a/.*\+\+\+ b/")

    def test_python_minus_m_entrypoint_plan_succeeds(self) -> None:
        # The package must have exactly one canonical CLI; `python -m
        # install_skills` is a real shipped entrypoint (it is copied into
        # adopting repositories) and must not crash on a valid plan.
        plan_path = Path(self.temp.name) / "module-plan.json"
        environment = dict(os.environ)
        environment.pop(install_skills.SOURCE_ENVIRONMENT, None)
        planned = subprocess.run(
            [
                os.sys.executable,
                "-m",
                "install_skills",
                "plan",
                "--kit-root",
                str(ROOT),
                "--target",
                str(self.target),
                "--skill",
                "ai-slop-detector",
                "--output",
                str(plan_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            cwd=str(ROOT / ".agents/skills/bootstrap-project/scripts"),
        )
        self.assertEqual(0, planned.returncode, planned.stderr)
        self.assertTrue(plan_path.is_file(), planned.stderr)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        self.assertEqual(
            {"agent-guidance-maintenance", "ai-slop-detector"},
            {item["name"] for item in plan["skills"]},
        )

    def test_fenced_code_link_does_not_block_adoption(self) -> None:
        # A relative link to a sibling skill inside a fenced code block is an
        # example, not a real dependency declaration. It must not be treated as
        # an undeclared link during adoption (Finding G: consistency with
        # repository validation which strips fenced code).
        self.add_skill("alpha")
        self.add_skill(
            "beta",
            "# Skill\n\nExample:\n\n```markdown\n[alpha](../alpha/SKILL.md)\n```\n",
            related=["alpha"],
        )

        plan = install_skills.build_plan(self.kit, self.target, ["beta"])
        self.assertEqual("CREATE", plan["skills"][1]["status"])
        install_skills.apply_plan(self.kit, self.target, plan)
        self.assertTrue((self.target / ".agents/skills/beta/SKILL.md").is_file())

    def test_real_relative_link_to_undeclared_skill_still_rejected(self) -> None:
        # A real (non-fenced) relative link to a non-required skill must still
        # be rejected. Stripping fenced code must not over-permit real links
        # (Finding G: negative counterpart to the fenced-code test).
        self.add_skill("alpha")
        self.add_skill(
            "beta",
            "# Skill\n\nSee [alpha](../alpha/SKILL.md) for background.\n",
            related=["alpha"],
        )

        with self.assertRaisesRegex(
            install_skills.AdoptionError, "relative links to non-required"
        ):
            install_skills.build_plan(self.kit, self.target, ["beta"])

    def test_restore_routing_survives_symlinked_rollback_temp(self) -> None:
        # If a previous crash left a symlinked rollback temp, restore_routing
        # must clear it (removing only the link, not the target) and not mask
        # the original installation exception (Finding I).
        import os

        self.add_skill("alpha")
        plan = install_skills.build_plan(self.kit, self.target, ["alpha"])
        route_path = self.target / plan["routing"]["path"]

        # Install once to create the route file as a real file
        install_skills.apply_plan(self.kit, self.target, plan)
        self.assertTrue(route_path.exists())
        self.assertFalse(route_path.is_symlink())

        # Simulate a stale rollback temp symlink pointing elsewhere
        target_elsewhere = self.target / "elsewhere.txt"
        target_elsewhere.write_text("outside\n", encoding="utf-8")
        rollback_temp = (
            route_path.parent / f".{route_path.name}.agent-guidance-kit-rollback"
        )
        if rollback_temp.exists() or rollback_temp.is_symlink():
            rollback_temp.unlink(missing_ok=True)
        try:
            os.symlink(target_elsewhere, rollback_temp)
        except (AttributeError, NotImplementedError, OSError) as error:
            self.skipTest(f"symlink creation is unavailable: {error}")

        self.assertTrue(rollback_temp.is_symlink())

        # restore_routing should clear the symlinked temp without error
        from install_skills.routing import restore_routing

        restore_routing(
            self.target,
            {"path": str(plan["routing"]["path"])},
            b"restored content\n",
        )
        self.assertFalse(rollback_temp.is_symlink())
        self.assertFalse(rollback_temp.exists())
        self.assertEqual("restored content\n", route_path.read_text(encoding="utf-8"))
        # The symlink target must not have been overwritten
        self.assertEqual("outside\n", target_elsewhere.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
