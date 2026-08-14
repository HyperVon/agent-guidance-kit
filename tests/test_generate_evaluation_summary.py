from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate_evaluation_summary.py"


def load():
    spec = importlib.util.spec_from_file_location("generate_evaluation_summary", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GenerateEvaluationSummaryTest(unittest.TestCase):
    def test_parse_timestamp_normalizes_naive_and_aware(self) -> None:
        module = load()
        ts_naive = module.parse_timestamp("2026-08-12T10:00:00")
        ts_z = module.parse_timestamp("2026-08-12T10:00:00Z")
        ts_offset = module.parse_timestamp("2026-08-12T10:00:00+00:00")
        ts_invalid = module.parse_timestamp("invalid-date")

        # None of them should be naive (tzinfo must not be None)
        self.assertIsNotNone(ts_naive.tzinfo)
        self.assertIsNotNone(ts_z.tzinfo)
        self.assertIsNotNone(ts_offset.tzinfo)
        self.assertIsNotNone(ts_invalid.tzinfo)

        # Comparing timestamps parsed from naive vs aware strings must not raise TypeError
        self.assertEqual(ts_naive, ts_z)
        self.assertEqual(ts_z, ts_offset)
        self.assertTrue(ts_naive > ts_invalid)

    def test_latest_per_key_deduplication(self) -> None:
        module = load()
        key = ("test-skill", "harness-a", "provider-a", "model-a", "high")
        rec_older = {
            "key": key,
            "run_id": "run-1",
            "timestamp_dt": datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
            "skill_name": "test-skill",
        }
        rec_newer = {
            "key": key,
            "run_id": "run-2",
            "timestamp_dt": datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
            "skill_name": "test-skill",
        }
        latest = module.latest_per_key([rec_older, rec_newer])
        self.assertEqual(1, len(latest))
        self.assertEqual("run-2", latest[key]["run_id"])

        # Equal timestamp tie-breaker uses run_id
        rec_same_time_a = {
            "key": key,
            "run_id": "run-01",
            "timestamp_dt": datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
            "skill_name": "test-skill",
        }
        rec_same_time_b = {
            "key": key,
            "run_id": "run-02",
            "timestamp_dt": datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
            "skill_name": "test-skill",
        }
        latest_tie = module.latest_per_key([rec_same_time_a, rec_same_time_b])
        self.assertEqual("run-02", latest_tie[key]["run_id"])

    def test_generate_summary_text_with_empty_and_invalid_results(self) -> None:
        module = load()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            results_dir = tmp_root / "docs/evaluations/results"
            results_dir.mkdir(parents=True)
            skills_dir = tmp_root / ".agents/skills"
            skills_dir.mkdir(parents=True)

            # Create a non-dict JSON file and a malformed JSON file
            (results_dir / "invalid.json").write_text("not json", encoding="utf-8")
            (results_dir / "list.json").write_text("[1, 2, 3]", encoding="utf-8")

            with (
                patch.object(module, "RESULTS_ROOT", results_dir),
                patch.object(module, "SKILLS_ROOT", skills_dir),
                patch.object(module, "ROOT", tmp_root),
            ):
                summary = module.generate_summary_text()

            self.assertIn("# Evaluation Summary", summary)
            self.assertIn("No executed results yet.", summary)
            self.assertIn("`list.json` | _invalid_", summary)
            self.assertIn("`invalid.json` | _invalid_", summary)

    def test_cli_write_and_check_modes(self) -> None:
        module = load()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            summary_file = tmp_root / "docs/evaluations/SUMMARY.md"
            results_dir = tmp_root / "docs/evaluations/results"
            results_dir.mkdir(parents=True)
            skills_dir = tmp_root / ".agents/skills"
            skills_dir.mkdir(parents=True)

            with (
                patch.object(module, "SUMMARY_PATH", summary_file),
                patch.object(module, "RESULTS_ROOT", results_dir),
                patch.object(module, "SKILLS_ROOT", skills_dir),
                patch.object(module, "ROOT", tmp_root),
            ):
                # When summary is missing, --check exits 1
                with patch("sys.argv", ["generate_evaluation_summary.py", "--check"]):
                    rc = module.main()
                self.assertEqual(1, rc)

                # --write creates the summary file
                stdout_buf = io.StringIO()
                with (
                    patch("sys.argv", ["generate_evaluation_summary.py", "--write"]),
                    redirect_stdout(stdout_buf),
                ):
                    rc = module.main()
                self.assertEqual(0, rc)
                self.assertTrue(summary_file.is_file())

                # --check passes when file is fresh
                stdout_buf = io.StringIO()
                with (
                    patch("sys.argv", ["generate_evaluation_summary.py", "--check"]),
                    redirect_stdout(stdout_buf),
                ):
                    rc = module.main()
                self.assertEqual(0, rc)


if __name__ == "__main__":
    unittest.main()
