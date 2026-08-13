from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/harness_recommendations.py"


def load():
    spec = importlib.util.spec_from_file_location("harness_recommendations", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HarnessRecommendationsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.kit = self.base / "kit"
        self.target = self.base / "target"
        self.kit.mkdir()
        # Minimal kit with canonical files.
        (self.kit / ".agents").mkdir(parents=True)
        (self.kit / ".agents/AGENTS.md").write_text(
            "# Kit canonical\n\nProduct boundary ... Skill index ...\n",
            encoding="utf-8",
        )
        (self.kit / ".agents/OPERATING.md").write_text(
            "# Kit operating\n\nAlways-on norms.\n", encoding="utf-8"
        )
        (self.kit / "AGENTS.md").write_text(
            "# Agent instructions\n\nThis file is the thin universal entrypoint.\n",
            encoding="utf-8",
        )
        self.target.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _recs(self, *, with_kit_files: bool = True):
        module = load()
        if not with_kit_files:
            # Simulate a kit whose canonical files are absent so the
            # recommendation can never leak kit policy for missing targets.
            import shutil

            shutil.rmtree(self.kit / ".agents")
        return module.collect_harness_recommendations(self.kit, self.target)

    def _by_file(self, recs):
        return {r["file"]: r for r in recs}

    def test_route_block_only_root_agents_gets_no_destructive_recommendation(
        self,
    ) -> None:
        route_start = "<!-- agent-guidance-kit:routes:start -->"
        route_end = "<!-- agent-guidance-kit:routes:end -->"
        (self.target / "AGENTS.md").write_text(
            f"{route_start}\n## Agent Guidance Kit skills\n\n"
            "| Task | Skill |\n| :--- | :--- |\n"
            f"| Inspect a project | [bootstrap-project](.agents/skills/bootstrap-project/SKILL.md) |\n"
            f"{route_end}\n",
            encoding="utf-8",
        )
        recs = self._recs()
        files = self._by_file(recs)
        self.assertNotIn("AGENTS.md", files)

    def test_missing_agents_agents_does_not_inject_kit_policy(self) -> None:
        # Target has no .agents/AGENTS.md; the recommender must not propose the
        # kit's own repository policy as paste-ready target content.
        recs = self._recs()
        files = self._by_file(recs)
        self.assertIn(".agents/AGENTS.md", files)
        rec = files[".agents/AGENTS.md"]
        self.assertEqual("REVIEW", rec["status"])
        self.assertIsNone(rec["desired"])
        self.assertNotIn("Product boundary", rec["action"])
        self.assertNotIn("Skill index", rec["action"])

    def test_missing_agents_operating_does_not_inject_kit_policy(self) -> None:
        recs = self._recs()
        files = self._by_file(recs)
        self.assertIn(".agents/OPERATING.md", files)
        rec = files[".agents/OPERATING.md"]
        self.assertEqual("REVIEW", rec["status"])
        self.assertIsNone(rec["desired"])

    def test_canonical_operating_drift_is_a_required_plan_item(self) -> None:
        (self.target / ".agents").mkdir(parents=True)
        (self.target / ".agents/OPERATING.md").write_text(
            "# Target operating\n\nTarget-specific rules.\n", encoding="utf-8"
        )
        recs = self._recs()
        rec = self._by_file(recs)[".agents/OPERATING.md"]
        self.assertEqual("REVIEW", rec["status"])
        self.assertTrue(rec["review_required"])
        self.assertEqual("source-canonical-guidance", rec["owner"])

    def test_no_truncation_of_recommendation_bodies(self) -> None:
        # A genuinely thin root AGENTS.md with a long body must be reported in
        # full, never silently truncated to a fragment.
        long_body = "# Title\n\n" + ("Some project line.\n" * 400)
        (self.target / "AGENTS.md").write_text(long_body, encoding="utf-8")
        module = load()
        rec = module.recommendation_for_file(self.kit, self.target, "AGENTS.md")
        # The target already references canonical .agents/AGENTS.md? No -> it will
        # be a RECOMMEND with full current body (no truncation).
        self.assertIsNotNone(rec)
        self.assertEqual(long_body, rec["current"])
        self.assertNotIn("[...]", rec["current"])

    def test_route_block_root_without_reference_is_accepted(self) -> None:
        # Root AGENTS.md that contains only the managed block and no .agents
        # reference is a valid managed state and is not flagged.
        route_start = "<!-- agent-guidance-kit:routes:start -->"
        route_end = "<!-- agent-guidance-kit:routes:end -->"
        (self.target / ".agents").mkdir(parents=True)
        (self.target / ".agents/AGENTS.md").write_text(
            "# Project canonical\n\nProduct boundary here.\n", encoding="utf-8"
        )
        (self.target / "AGENTS.md").write_text(
            f"{route_start}\nblock\n{route_end}\n", encoding="utf-8"
        )
        recs = self._recs()
        files = self._by_file(recs)
        self.assertNotIn("AGENTS.md", files)
        # The nested canonical still differs -> REVIEW, never with kit body.
        if ".agents/AGENTS.md" in files:
            self.assertIsNone(files[".agents/AGENTS.md"]["desired"])

    def test_render_diff_keeps_headers_on_separate_lines(self) -> None:
        module = load()
        diff = module.render_diff("# Old\nline\n", "# New\nline\n", "AGENTS.md")
        self.assertEqual(
            [
                "--- a/AGENTS.md",
                "+++ b/AGENTS.md",
                "@@ -1,2 +1,2 @@",
                "-# Old",
                "+# New",
                " line",
            ],
            diff.splitlines(),
        )
        # Diff body lines already represent complete logical lines; joining
        # them must not insert artificial blank lines.
        self.assertNotIn("\n\n", diff)

    def test_command_runs_without_error(self) -> None:
        module = load()
        self.assertEqual(
            0,
            module.main(
                [
                    "--kit-root",
                    str(self.kit),
                    "--target",
                    str(self.target),
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
