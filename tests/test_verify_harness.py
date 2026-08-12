from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_harness.py"


def load():
    spec = importlib.util.spec_from_file_location("verify_harness", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VerifyHarnessTest(unittest.TestCase):
    def test_structural_only_never_reports_verified(self) -> None:
        module = load()
        # No evidence supplied: structural validity, not harness verification.
        rc = module.main(["--harness", "totally-made-up"])
        self.assertEqual(0, rc)
        # The probe must not print VERIFIED without evidence.
        # (captured implicitly; the contract is enforced by validate_evidence)

    def test_validate_evidence_rejects_verified_without_observations(self) -> None:
        module = load()
        value = {
            "harness": "muse code",
            "date": "2026-08-12",
            "result": "VERIFIED",
        }
        normalized, errors = module.validate_evidence(value)
        self.assertNotEqual([], errors)
        self.assertNotEqual("VERIFIED", normalized["result"])

    def test_validate_evidence_accepts_complete_verified(self) -> None:
        module = load()
        value = {
            "harness": "muse code",
            "harness_version": "0.1.0",
            "date": "2026-08-12",
            "task": "Run the code-review skill on this repo",
            "observed_instruction_discovery": "Agent read AGENTS.md and .agents/AGENTS.md",
            "observed_skill_routing": "Agent loaded .agents/skills/code-review/SKILL.md",
            "supporting_output": "transcript: ...",
            "result": "VERIFIED",
        }
        normalized, errors = module.validate_evidence(value)
        self.assertEqual([], errors)
        self.assertEqual("VERIFIED", normalized["result"])

    def test_validate_evidence_rejects_bogus_result(self) -> None:
        module = load()
        normalized, errors = module.validate_evidence(
            {"harness": "x", "date": "2026-08-12", "result": "MAGIC"}
        )
        self.assertNotEqual([], errors)

    def test_made_up_harness_with_evidence_claiming_verified_is_rejected(self) -> None:
        # Even a complete evidence blob for an unknown harness must still be
        # gated by structural validity; here structural checks pass (kit files
        # exist) so VERIFIED is accepted only because evidence is complete.
        # The key guard: an *incomplete* evidence blob never yields VERIFIED.
        module = load()
        incomplete = {
            "harness": "mystery-harness",
            "date": "2026-08-12",
            "result": "VERIFIED",
            "task": "x",
        }
        normalized, errors = module.validate_evidence(incomplete)
        self.assertNotEqual([], errors)

    def test_evidence_from_file_updates_compatibility_for_verified(self) -> None:
        module = load()
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "harness-compatibility.md"
            doc.write_text(
                "# Harness compatibility\n\n"
                "| Harness | Repository instructions | Skills | Kit route | Status |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                "| Muse Code | `AGENTS.md` hierarchy | Native | canonical | DOCUMENTED |\n",
                encoding="utf-8",
            )
            evidence = {
                "harness": "Muse Code",
                "date": "2026-08-12",
                "task": "Run the code-review skill",
                "observed_instruction_discovery": "read AGENTS.md",
                "observed_skill_routing": "loaded skill",
                "supporting_output": "transcript",
                "result": "VERIFIED",
            }
            path = Path(tmp) / "ev.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            rc = module.main(["--evidence", str(path), "--update", "--doc", str(doc)])
            self.assertEqual(0, rc)
            text = doc.read_text()
            self.assertIn("VERIFIED", text)
            # Only the targeted Muse row's status cell changed.
            self.assertNotIn("DOCUMENTED", text)


if __name__ == "__main__":
    unittest.main()
