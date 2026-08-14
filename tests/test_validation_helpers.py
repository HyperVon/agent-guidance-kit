from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import call, patch

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
guidance_inventory = load(
    "guidance_inventory",
    ROOT / ".agents/skills/skill-optimizer/scripts/guidance_inventory.py",
)
validate_adoption = load(
    "validate_adoption",
    ROOT / ".agents/skills/agent-guidance-maintenance/scripts/validate_adoption.py",
)


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

    def test_agent_skills_command_uses_current_python_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            skill = root / ".agents/skills/example"
            skill.mkdir(parents=True)
            python = root / ".venv/bin/python"
            validator = python.parent / "agentskills"
            validator.parent.mkdir(parents=True)
            validator.touch()

            self.assertEqual(
                [[str(validator), "validate", str(skill)]],
                check.agent_skills_commands(root=root, python=str(python)),
            )

    def test_agent_skills_command_finds_windows_scripts_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            skill = root / ".agents/skills/example"
            skill.mkdir(parents=True)
            python = root / "python.exe"
            validator = root / "Scripts/agentskills.exe"
            validator.parent.mkdir(parents=True)
            validator.touch()

            self.assertEqual(
                [[str(validator), "validate", str(skill)]],
                check.agent_skills_commands(root=root, python=str(python)),
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

    def test_validate_harness_imports_does_not_duplicate_copilot_errors(
        self,
    ) -> None:
        # When .github/copilot-instructions.md is missing, the error must appear
        # exactly once (Finding A: previously duplicated).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".agents").mkdir()
            (root / ".agents/AGENTS.md").write_text(
                "# Canonical\n\nProduct boundary\n", encoding="utf-8"
            )
            (root / "AGENTS.md").write_text(
                "# Pointer to .agents/AGENTS.md\n", encoding="utf-8"
            )
            errors: list[str] = []
            validate_repository.validate_harness_imports(root, errors)
            copilot_errors = [e for e in errors if "copilot-instructions.md" in e]
            self.assertEqual(1, len(copilot_errors))

    def test_node_toolchain_warns_for_versions_above_26(self) -> None:
        # CI matrix validates Node 22 and 26. Versions strictly above 26
        # should receive a warning (Finding D: was > 30).
        completed = subprocess.CompletedProcess(
            ["node", "--version"], 0, stdout="v28.0.0\n", stderr=""
        )
        with (
            patch.object(
                setup_dev.shutil,
                "which",
                side_effect=lambda name: {"node": "node", "npm": "npm"}[name],
            ) as which,
            patch.object(setup_dev.subprocess, "run", return_value=completed) as run,
        ):
            buf = io.StringIO()
            with redirect_stderr(buf):
                result = setup_dev.node_toolchain()
        self.assertEqual(("node", "npm"), result)
        self.assertEqual([call("node"), call("npm")], which.call_args_list)
        run.assert_called_once_with(
            ["node", "--version"], check=False, capture_output=True, text=True
        )
        self.assertIn("newer than CI-validated 26", buf.getvalue())

    def test_node_toolchain_no_warning_for_ci_validated_versions(self) -> None:
        completed = subprocess.CompletedProcess(
            ["node", "--version"], 0, stdout="v26.0.0\n", stderr=""
        )
        with (
            patch.object(
                setup_dev.shutil,
                "which",
                side_effect=lambda name: {"node": "node", "npm": "npm"}[name],
            ),
            patch.object(setup_dev.subprocess, "run", return_value=completed),
        ):
            buf = io.StringIO()
            with redirect_stderr(buf):
                result = setup_dev.node_toolchain()
        self.assertEqual(("node", "npm"), result)
        self.assertEqual("", buf.getvalue())

    def test_guidance_inventory_output_refuses_to_overwrite(self) -> None:
        # --output must use exclusive creation; an existing file must not be
        # silently overwritten (Finding B).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            (root / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
            output = root / "inventory.md"
            output.write_text("stale\n", encoding="utf-8")
            rc = guidance_inventory.main(["--root", str(root), "--output", str(output)])
            self.assertEqual(2, rc)
            self.assertEqual("stale\n", output.read_text(encoding="utf-8"))

    def test_guidance_inventory_output_creates_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            (root / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
            output = root / "inventory.md"
            rc = guidance_inventory.main(["--root", str(root), "--output", str(output)])
            self.assertEqual(0, rc)
            self.assertTrue(output.is_file())
            self.assertIn("Guidance inventory", output.read_text(encoding="utf-8"))

    def test_public_hygiene_fallback_excludes_dependency_directories(self) -> None:
        # When git is unavailable, the fallback walk must skip .venv,
        # node_modules, dist, build, etc. (Finding H).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "src").mkdir(parents=True)
            (root / "src/app.py").write_text("print('hello')\n", encoding="utf-8")
            for dep_dir in (".venv", "node_modules", "dist", "build"):
                file_path = root / dep_dir / "secret.txt"
                file_path.parent.mkdir(parents=True)
                file_path.write_text("AKIA" + "IOSFODNN7EXAMPLE\n", encoding="utf-8")
            original_git = public_hygiene.subprocess.run
            try:

                def raise_git_failure(*args, **kwargs):
                    raise subprocess.CalledProcessError(128, "git")

                public_hygiene.subprocess.run = raise_git_failure
                files = public_hygiene.candidate_files(root)
                rel_paths = {f.relative_to(root) for f in files}
                self.assertIn(Path("src") / "app.py", rel_paths)
                self.assertFalse(any(".venv" in p.parts for p in rel_paths))
                self.assertFalse(any("node_modules" in p.parts for p in rel_paths))
                self.assertFalse(any("dist" in p.parts for p in rel_paths))
                self.assertFalse(any("build" in p.parts for p in rel_paths))
            finally:
                public_hygiene.subprocess.run = original_git

    def test_public_hygiene_candidate_files_scopes_to_custom_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "custom_repo"
            root.mkdir()
            subprocess.run(
                ["git", "init", "--quiet", str(root)],
                check=True,
                capture_output=True,
            )
            (root / "custom.py").write_text("print('test')\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", "custom.py"],
                check=True,
                capture_output=True,
            )
            files = public_hygiene.candidate_files(root)
            self.assertIn(root / "custom.py", files)
            self.assertTrue(all(str(f).startswith(str(root)) for f in files))

    def test_validate_adoption_handles_non_utf8_files_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "target"
            root.mkdir()
            agents = root / "AGENTS.md"
            agents.write_bytes(b"\xff\xfe\x00\x00")
            errors = validate_adoption.validate_target(root)
            self.assertTrue(
                any("missing or duplicated" in e or "malformed" in e for e in errors)
            )

            # Test invalid UTF-8 in SKILL.md and nested markdown files
            agents.write_text(
                "<!-- agent-guidance-kit:routes:start -->\n"
                "| Task | Skill |\n| :--- | :--- |\n"
                "| Test | [test-skill](.agents/skills/test-skill/SKILL.md) |\n"
                "<!-- agent-guidance-kit:routes:end -->\n",
                encoding="utf-8",
            )
            receipt_dir = root / ".agents/.agent-guidance-kit/receipts"
            receipt_dir.mkdir(parents=True)
            (receipt_dir / "test.json").write_text(
                '{"skills": [{"name": "test-skill"}]}', encoding="utf-8"
            )
            skill_dir = root / ".agents/skills/test-skill"
            skill_dir.mkdir(parents=True)
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_bytes(b"\xff\xfe\x00\x00")
            errors_skill = validate_adoption.validate_target(root)
            self.assertTrue(any("unreadable SKILL.md" in e for e in errors_skill))

            # Test invalid UTF-8 in secondary markdown file
            skill_md.write_text(
                "---\nname: test-skill\ndescription: Test skill description.\n---\n# Test\n",
                encoding="utf-8",
            )
            nested_md = skill_dir / "extra.md"
            nested_md.write_bytes(b"\xff\xfe\x00\x00")
            errors_nested = validate_adoption.validate_target(root)
            self.assertTrue(any("unreadable Markdown" in e for e in errors_nested))


if __name__ == "__main__":
    unittest.main()
