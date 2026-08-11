from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agents/skills/agent-guidance-maintenance/scripts/resolve_source.py"
SPEC = importlib.util.spec_from_file_location("resolve_source", SCRIPT)
assert SPEC and SPEC.loader
resolve_source = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resolve_source)


class SourceResolutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.target = base / "target"
        self.target.mkdir()
        self.kit = base / "agent-guidance-kit"
        required = (
            self.kit / ".agents/skill-dependencies.json",
            self.kit / ".agents/skills/bootstrap-project/SKILL.md",
            self.kit / ".agents/skills/bootstrap-project/scripts/install_skills.py",
            self.kit / ".agents/skills/agent-guidance-maintenance/SKILL.md",
        )
        for path in required:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_explicit_source_precedes_environment(self) -> None:
        root, method = resolve_source.resolve_source(
            self.target,
            self.kit,
            {resolve_source.ENVIRONMENT_VARIABLE: "/missing"},
        )

        self.assertEqual(self.kit.resolve(), root)
        self.assertEqual("explicit", method)

    def test_environment_source_precedes_adjacent_sibling(self) -> None:
        alternate = self.target.parent / "alternate"
        alternate.mkdir()
        for relative in (
            ".agents/skill-dependencies.json",
            ".agents/skills/bootstrap-project/SKILL.md",
            ".agents/skills/bootstrap-project/scripts/install_skills.py",
            ".agents/skills/agent-guidance-maintenance/SKILL.md",
        ):
            path = alternate / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="utf-8")

        root, method = resolve_source.resolve_source(
            self.target,
            environment={resolve_source.ENVIRONMENT_VARIABLE: str(alternate)},
        )

        self.assertEqual(alternate.resolve(), root)
        self.assertEqual("environment", method)

    def test_configured_locator_is_ignored_and_resolved(self) -> None:
        subprocess.run(
            ["git", "init", "--quiet", str(self.target)],
            check=True,
            capture_output=True,
        )

        locator = resolve_source.configure_locator(self.target, self.kit)
        root, method = resolve_source.resolve_source(self.target, environment={})
        payload = json.loads(locator.read_text(encoding="utf-8"))
        ignored = subprocess.run(
            [
                "git",
                "-C",
                str(self.target),
                "check-ignore",
                "--quiet",
                "--",
                resolve_source.LOCATOR.as_posix(),
            ],
            check=False,
        )

        self.assertEqual(0, ignored.returncode)
        self.assertFalse(Path(payload["kit_root"]).is_absolute())
        self.assertEqual(self.kit.resolve(), root)
        self.assertEqual("target-local locator", method)

    def test_unignored_locator_is_rejected(self) -> None:
        subprocess.run(
            ["git", "init", "--quiet", str(self.target)],
            check=True,
            capture_output=True,
        )
        locator = self.target / resolve_source.LOCATOR
        locator.parent.mkdir(parents=True)
        locator.write_text(
            json.dumps({"kit_root": str(self.kit)}),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            resolve_source.SourceResolutionError, "not ignored"
        ):
            resolve_source.resolve_source(self.target, environment={})

    def test_symlinked_locator_parent_is_rejected(self) -> None:
        subprocess.run(
            ["git", "init", "--quiet", str(self.target)],
            check=True,
            capture_output=True,
        )
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        try:
            os.symlink(outside, self.target / ".agents")
        except (AttributeError, NotImplementedError, OSError) as error:
            self.skipTest(f"symlink creation is unavailable: {error}")

        with self.assertRaisesRegex(
            resolve_source.SourceResolutionError, "locator parent is unsafe"
        ):
            resolve_source.configure_locator(self.target, self.kit)
        self.assertFalse((outside / ".agent-guidance-kit").exists())

    def test_adjacent_sibling_is_the_final_automatic_fallback(self) -> None:
        root, method = resolve_source.resolve_source(self.target, environment={})

        self.assertEqual(self.kit.resolve(), root)
        self.assertEqual("adjacent sibling", method)

    def test_unresolved_source_stops_and_asks(self) -> None:
        renamed = self.kit.with_name("not-the-conventional-name")
        self.kit.rename(renamed)

        with self.assertRaisesRegex(
            resolve_source.SourceResolutionError, "provide --kit-root"
        ):
            resolve_source.resolve_source(self.target, environment={})


if __name__ == "__main__":
    unittest.main()
