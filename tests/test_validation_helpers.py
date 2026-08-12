from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
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
guidance_inventory = load(
    "guidance_inventory",
    ROOT / ".agents/skills/skill-optimizer/scripts/guidance_inventory.py",
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
        bin_dir = Path(tempfile.mkdtemp())
        fake_node = bin_dir / "node"
        fake_node.write_text("#!/bin/sh\necho 'v28.0.0'\n", encoding="utf-8")
        fake_node.chmod(0o755)
        original_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{bin_dir}:{original_path}"
        original_which = setup_dev.shutil.which
        try:
            buf = io.StringIO()
            with redirect_stderr(buf):
                result = setup_dev.node_toolchain()
            self.assertIsNotNone(result)
            self.assertIn("newer than CI-validated 26", buf.getvalue())
        finally:
            os.environ["PATH"] = original_path
            setup_dev.shutil.which = original_which

    def test_node_toolchain_no_warning_for_ci_validated_versions(self) -> None:
        bin_dir = Path(tempfile.mkdtemp())
        fake_node = bin_dir / "node"
        fake_node.write_text("#!/bin/sh\necho 'v26.0.0'\n", encoding="utf-8")
        fake_node.chmod(0o755)
        original_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{bin_dir}:{original_path}"
        original_which = setup_dev.shutil.which
        try:
            buf = io.StringIO()
            with redirect_stderr(buf):
                result = setup_dev.node_toolchain()
            self.assertIsNotNone(result)
            self.assertEqual("", buf.getvalue())
        finally:
            os.environ["PATH"] = original_path
            setup_dev.shutil.which = original_which

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
                rel_paths = {str(f.relative_to(root)) for f in files}
                self.assertIn("src/app.py", rel_paths)
                self.assertFalse(any(".venv" in p for p in rel_paths))
                self.assertFalse(any("node_modules" in p for p in rel_paths))
                self.assertFalse(any("dist" in p for p in rel_paths))
                self.assertFalse(any("build" in p for p in rel_paths))
            finally:
                public_hygiene.subprocess.run = original_git


if __name__ == "__main__":
    unittest.main()
