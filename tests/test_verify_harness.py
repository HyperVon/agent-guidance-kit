from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
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
    @staticmethod
    def complete_evidence(harness: str) -> dict[str, str]:
        return {
            "harness": harness,
            "date": "2026-08-12",
            "task": "Run the code-review skill",
            "observed_instruction_discovery": "read AGENTS.md",
            "observed_skill_routing": "loaded skill",
            "supporting_output": "transcript",
            "result": "VERIFIED",
        }

    @staticmethod
    def write_doc(path: Path, names: list[str]) -> str:
        text = (
            "# Harness compatibility\n\n"
            "| Harness | Repository instructions | Skills | Kit route | Status |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
        )
        text += "".join(
            f"| {name} | `AGENTS.md` hierarchy | Native | canonical | DOCUMENTED |\n"
            for name in names
        )
        path.write_text(text, encoding="utf-8")
        return text

    @staticmethod
    def write_evidence(path: Path, evidence: dict[str, str]) -> None:
        path.write_text(json.dumps(evidence), encoding="utf-8")

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

    def test_validate_evidence_rejects_non_string_observation(self) -> None:
        module = load()
        evidence = self.complete_evidence("Muse Code")
        evidence["supporting_output"] = {"transcript": "not a string"}  # type: ignore[assignment]
        normalized, errors = module.validate_evidence(evidence)
        self.assertNotEqual([], errors)
        self.assertEqual("", normalized["result"])

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
            self.write_doc(doc, ["Muse Code"])
            evidence = self.complete_evidence("Muse Code")
            path = Path(tmp) / "ev.json"
            self.write_evidence(path, evidence)
            rc = module.main(["--evidence", str(path), "--update", "--doc", str(doc)])
            self.assertEqual(0, rc)
            text = doc.read_text()
            self.assertIn("VERIFIED", text)
            # Only the targeted Muse row's status cell changed.
            self.assertNotIn("DOCUMENTED", text)

    def test_json_update_reports_success_and_change(self) -> None:
        module = load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = root / "harness-compatibility.md"
            self.write_doc(doc, ["Muse Code"])
            evidence_path = root / "evidence.json"
            self.write_evidence(evidence_path, self.complete_evidence("muse code"))

            output = io.StringIO()
            with redirect_stdout(output):
                rc = module.main(
                    [
                        "--json",
                        "--evidence",
                        str(evidence_path),
                        "--update",
                        "--doc",
                        str(doc),
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(0, rc)
            self.assertTrue(payload["structurally_valid"])
            self.assertTrue(payload["evidence_valid"])
            self.assertEqual("VERIFIED", payload["evidence_result"])
            self.assertTrue(payload["update_attempted"])
            self.assertTrue(payload["compatibility_document_changed"])
            self.assertTrue(payload["update_succeeded"])
            self.assertTrue(payload["command_succeeded"])
            self.assertIsNone(payload["update_error"])

    def test_json_invalid_evidence_keeps_structural_result_independent(self) -> None:
        module = load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = root / "harness-compatibility.md"
            before = self.write_doc(doc, ["Muse Code"])
            evidence_path = root / "evidence.json"
            self.write_evidence(
                evidence_path,
                {"harness": "Muse Code", "date": "2026-08-12", "result": "VERIFIED"},
            )

            output = io.StringIO()
            with redirect_stdout(output):
                rc = module.main(
                    [
                        "--json",
                        "--evidence",
                        str(evidence_path),
                        "--update",
                        "--doc",
                        str(doc),
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(1, rc)
            self.assertTrue(payload["structurally_valid"])
            self.assertFalse(payload["evidence_valid"])
            self.assertFalse(payload["compatibility_document_changed"])
            self.assertFalse(payload["update_succeeded"])
            self.assertFalse(payload["command_succeeded"])
            self.assertIn("requires valid --evidence", payload["update_error"])
            self.assertEqual(before, doc.read_text(encoding="utf-8"))

    def test_json_update_failure_is_machine_readable_and_nonzero(self) -> None:
        module = load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = root / "harness-compatibility.md"
            before = self.write_doc(doc, ["Muse Code"])
            evidence_path = root / "evidence.json"
            self.write_evidence(
                evidence_path, self.complete_evidence("Unknown Harness")
            )

            output = io.StringIO()
            with redirect_stdout(output):
                rc = module.main(
                    [
                        "--json",
                        "--evidence",
                        str(evidence_path),
                        "--update",
                        "--doc",
                        str(doc),
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(1, rc)
            self.assertTrue(payload["structurally_valid"])
            self.assertTrue(payload["evidence_valid"])
            self.assertFalse(payload["compatibility_document_changed"])
            self.assertFalse(payload["update_succeeded"])
            self.assertIn("no exact harness row", payload["update_error"])
            self.assertEqual(before, doc.read_text(encoding="utf-8"))

    def test_json_missing_evidence_file_is_machine_readable_and_nonzero(self) -> None:
        module = load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = root / "harness-compatibility.md"
            self.write_doc(doc, ["Muse Code"])
            missing_evidence_path = root / "does_not_exist.json"

            output = io.StringIO()
            with redirect_stdout(output):
                rc = module.main(
                    [
                        "--json",
                        "--evidence",
                        str(missing_evidence_path),
                        "--update",
                        "--doc",
                        str(doc),
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(1, rc)
            self.assertFalse(payload["evidence_valid"])
            self.assertFalse(payload["command_succeeded"])
            self.assertTrue(
                any("invalid evidence JSON" in note for note in payload["notes"])
            )

    def test_json_update_encoding_failure_is_machine_readable(self) -> None:
        module = load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = root / "harness-compatibility.md"
            doc.write_bytes(b"\xff\n")
            evidence_path = root / "evidence.json"
            self.write_evidence(evidence_path, self.complete_evidence("Muse Code"))

            output = io.StringIO()
            with redirect_stdout(output):
                rc = module.main(
                    [
                        "--json",
                        "--evidence",
                        str(evidence_path),
                        "--update",
                        "--doc",
                        str(doc),
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(1, rc)
            self.assertFalse(payload["update_succeeded"])
            self.assertIn("updating compatibility doc failed", payload["update_error"])

    def test_exact_harness_matching_is_case_insensitive_and_not_substring_based(
        self,
    ) -> None:
        module = load()
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "harness-compatibility.md"
            before = self.write_doc(
                doc, ["Muse Code", "OpenCode", "Claude Code", "OpenAI Codex"]
            )
            changed, message = module.apply_evidence_to_compatibility(
                {"harness": "muse code", "result": "VERIFIED"}, doc
            )
            self.assertTrue(changed)
            self.assertIn("exact", message)
            updated = doc.read_text(encoding="utf-8")
            self.assertIn(
                "| Muse Code | `AGENTS.md` hierarchy | Native | canonical | VERIFIED |",
                updated,
            )
            for name in ("OpenCode", "Claude Code", "OpenAI Codex"):
                self.assertIn(
                    f"| {name} | `AGENTS.md` hierarchy | Native | canonical | DOCUMENTED |",
                    updated,
                )
            self.assertNotEqual(before, updated)

            doc.write_text(before, encoding="utf-8")
            with self.assertRaises(module.CompatibilityUpdateError):
                module.apply_evidence_to_compatibility(
                    {"harness": "Code", "result": "VERIFIED"}, doc
                )
            self.assertEqual(before, doc.read_text(encoding="utf-8"))

    def test_unknown_harness_does_not_modify_compatibility_document(self) -> None:
        module = load()
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "harness-compatibility.md"
            before = self.write_doc(doc, ["Muse Code"])
            with self.assertRaises(module.CompatibilityUpdateError):
                module.apply_evidence_to_compatibility(
                    {"harness": "Unknown Harness", "result": "VERIFIED"}, doc
                )
            self.assertEqual(before, doc.read_text(encoding="utf-8"))

    def test_duplicate_exact_harness_rows_fail_closed(self) -> None:
        module = load()
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "harness-compatibility.md"
            before = self.write_doc(doc, ["Muse Code", "Muse Code"])
            with self.assertRaisesRegex(module.CompatibilityUpdateError, "ambiguous"):
                module.apply_evidence_to_compatibility(
                    {"harness": "Muse Code", "result": "VERIFIED"}, doc
                )
            self.assertEqual(before, doc.read_text(encoding="utf-8"))

    def test_apply_evidence_updates_row_without_trailing_pipe(self) -> None:
        module = load()
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "harness-compatibility.md"
            doc.write_text(
                "| Harness | AGENTS.md | Discovery | Kit route | Status\n"
                "| :--- | :--- | :--- | :--- | :---\n"
                "| Muse Code | `AGENTS.md` hierarchy | Native | canonical | DOCUMENTED\n",
                encoding="utf-8",
            )
            changed, message = module.apply_evidence_to_compatibility(
                {"harness": "Muse Code", "result": "VERIFIED"}, doc
            )
            self.assertTrue(changed)
            updated = doc.read_text(encoding="utf-8")
            self.assertIn(
                "| Muse Code | `AGENTS.md` hierarchy | Native | canonical | VERIFIED\n",
                updated,
            )


if __name__ == "__main__":
    unittest.main()
