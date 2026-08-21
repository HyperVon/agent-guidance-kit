#!/usr/bin/env python3
"""Unit tests for the evaluation validator.

Run from repo root:  python3 scripts/test_validate_evaluations.py

Tests the validator's failure detection directly (no network / no real runs).
"""
import argparse
import glob
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_routing_catalog as brc
import docker_isolation_preflight as dip
import eval_hashing as eh
import evaluation_harness as eha
import evaluation_protocols as ep
import run_catalog_routing_eval as rc
import run_execution_eval as ree
import run_harness_eval as rhe
import run_skill_regression_eval as rsre
import validate_evaluations as ve


# Helper to reset the shared error/warning lists between tests.
def reset():
    ve.errors.clear()
    ve.warnings.clear()


def fake_execution_attestation(request, response):
    """Build the worker attestation shape used by neutral test adapters."""
    receipt = response["workspace_receipt"]
    output = response.get("output", "")
    return {
        "protocol": eha.EXECUTION_ATTESTATION_PROTOCOL,
        "status": "verified",
        "confidence": "independently_verified",
        "verification_mode": "independent",
        "source": "worker",
        "worker_id": response["worker_id"],
        "session_id": response["session_id"],
        "nonce": request["attestation_nonce"],
        "request_hash": eha.attestation_request_hash(request),
        "observation_hash": eha.attestation_observation_hash(response),
        "workspace_receipt_hash": "sha256:" + hashlib.sha256(
            receipt.encode()).hexdigest(),
        "output_hash": "sha256:" + hashlib.sha256(
            output.encode()).hexdigest(),
        "returncode": response["returncode"],
    }


def fake_path(skill="foo"):
    return os.path.join(ROOT, "skills", skill, "evals", "evals.json")


def base_case(cid, kind, modes, **extra):
    c = {
        "id": cid,
        "kind": kind,
        "evaluation_modes": modes,
        "prompt": "do a thing",
        "fixture": {"status": "designed_only"},
    }
    c.update(extra)
    return c


def routing_ctx(target="foo"):
    return {
        "catalog_required": True,
        "comparison": "target-present-vs-target-absent",
        "catalog_source": "generated-from-current-catalog",
        "target_skill": target,
    }


def routing_exp(target="foo"):
    return {
        "experiment": "target-availability",
        "target_skill": target,
        "target_present": {"expected_selected_skill": target},
        "target_absent": {"expected_selected_skill": None,
                          "allowed_fallbacks": ["clarify", "generic-review"]},
    }


def exec_exp():
    return {"expected_output": "out", "assertions": ["an assertion"]}


class SchemaFailureTests(unittest.TestCase):
    def tearDown(self):
        reset()

    def test_four_cases(self):
        evals = [base_case(i, "matching", ["routing", "execution"]) for i in (1, 2, 3, 4)]
        ve.check_skill_shape(evals, "x/evals.json")
        self.assertTrue(any("exactly 5 cases" in e for e in ve.errors))

    def test_three_matching(self):
        evals = [
            base_case(1, "matching", ["routing", "execution"]),
            base_case(2, "matching", ["routing", "execution"]),
            base_case(3, "matching", ["routing", "execution"]),
            base_case(4, "ambiguous", ["routing"]),
            base_case(5, "edge", ["execution"]),
        ]
        ve.check_skill_shape(evals, "x/evals.json")
        self.assertTrue(any("matching" in e for e in ve.errors))

    def test_bad_ids(self):
        evals = [
            base_case(1, "matching", ["routing", "execution"]),
            base_case(2, "matching", ["routing", "execution"]),
            base_case(3, "neighboring", ["routing"]),
            base_case(4, "ambiguous", ["routing"]),
            base_case(6, "edge", ["execution"]),
        ]
        ve.check_skill_shape(evals, "x/evals.json")
        self.assertTrue(any("case ids must be [1,2,3,4,5]" in e for e in ve.errors))

    def test_routing_no_expectation(self):
        c = base_case(3, "neighboring", ["routing"],
                      routing_context=routing_ctx(),
                      routing=None)
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertTrue(any("missing 'routing' expectation" in e for e in ve.errors))

    def test_catalog_routing_mode_accepted_in_case(self):
        # Layer A catalog-routing must be a valid evaluation_mode.
        c = base_case(1, "matching", ["catalog-routing"],
                      routing_context=routing_ctx(),
                      routing=routing_exp())
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertFalse(any("bad evaluation_modes" in e for e in ve.errors))

    def test_routing_oracle_requires_expected_selection(self):
        c = base_case(1, "matching", ["catalog-routing"],
                      routing_context=routing_ctx(),
                      routing=routing_exp())
        del c["routing"]["target_present"]["expected_selected_skill"]
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertTrue(any("expected_selected_skill" in e
                            for e in ve.errors))

    def test_execution_no_assertions(self):
        c = base_case(5, "edge", ["execution"],
                      execution={"expected_output": "out", "assertions": []})
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertTrue(any("execution.assertions invalid" in e for e in ve.errors))


class ResultFailureTests(unittest.TestCase):
    def tearDown(self):
        reset()

    def _isolation_attestation(self, *case_ids):
        return {
            "protocol": ve.ISOLATION_ATTESTATION_PROTOCOL,
            "status": "verified",
            "verification_mode": "independent",
            "boundary": "os-level",
            "worker_isolation_verified": True,
            "isolation_method": "docker",
            "evidence_hashes": {
                str(case_id): "sha256:" + "e" * 64 for case_id in case_ids
            },
        }

    def _result(self, mode="execution", **over):
        method = "docker-isolated" if mode in ("execution",) else "harness-routing"
        res = {
            "result_schema_version": 2,
            "skill": "code-review",
            "evaluation_mode": mode,
            "method": method,
            "case_revision": "sha256:a",
            "fixture_revision": "sha256:b",
            "target_skill_revision": "sha256:c",
            "runtime": {"harness": "kilo", "harness_version": "unknown",
                        "model": "m", "reasoning_effort": "high",
                        "tool_policy": "sandbox", "network_policy": "none",
                        "isolation_method": "instruction-only (limited)"},
            "protocol": {"status": "limited", "worker_isolation_verified": True,
"target_guidance_present": "ev", "target_absent_in_baseline": "ev",
                          "target_guidance_hash": "sha256:g", "baseline_guidance_absent": "ev",
                         "contamination": "none", "routing_mechanism": None,
                         "conditions": ["target", "baseline"], "repeats": 3,
                         "isolation_attestation": self._isolation_attestation(1)},
            "runs": {"target": {"session_id": "g1", "container_id": "cg1", "output_hash": "h",
                                "selected_skill": "code-review"},
                     "baseline": {"session_id": "b1", "container_id": "cb1", "output_hash": "h"}},
            "cases": [{
                "case_id": 1,
                "raw_evidence_hash": "sha256:" + "e" * 64,
                "outcome": {"category": "skill_only_pass",
                            "measurement_status": "discriminating",
                            "protocol_status": "limited"},
                "verdict": {"target_pass": True, "baseline_pass": False},
                "assertions": [{"assertion": "frozen", "target": {"pass": True, "evidence": "e"},
                                "baseline": {"pass": False, "evidence": "e"}}],
            }],
        }
        res.update(over)
        return res

    def test_matrix_valid_while_result_invalid(self):
        tmp = tempfile.mkdtemp()
        try:
            resdir = os.path.join(tmp, "results")
            os.makedirs(resdir)
            # linked result is invalid
            open(os.path.join(resdir, "code-review.md"), "w").write(
                "protocol_status: invalid\nThis is exploratory.")
            matrix = os.path.join(tmp, "validation-matrix.md")
            open(matrix, "w").write(
                "| Skill | Cases | Fixtures | Routing | Execution | Protocol | Repeats | Result |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| [code-review](skills/code-review/evals/evals.json) | 5 | ready | not_run | exploratory | valid | 1 | [results](results/code-review.md) |\n")
            ve.EVALS_DIR = tmp
            ve.check_matrix_sync({"code-review"})
            self.assertTrue(any("valid" in e and "invalid" in e for e in ve.errors))
        finally:
            ve.EVALS_DIR = os.path.join(ROOT, "docs", "evaluations")
            shutil.rmtree(tmp, ignore_errors=True)

    def test_routing_no_selected_skill(self):
        res = self._result(mode="routing")
        res["runs"]["target"].pop("selected_skill")
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("selected_skill" in e for e in ve.errors))

    def test_execution_missing_baseline_absence(self):
        res = self._result()
        res["protocol"].pop("target_absent_in_baseline")
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("target_absent_in_baseline" in e for e in ve.errors))

    def test_passed_assertion_no_evidence(self):
        res = self._result()
        res["cases"][0]["assertions"][0]["target"]["evidence"] = ""
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("passing target assertion has no evidence" in e for e in ve.errors))

    def test_shared_session_id(self):
        res = self._result()
        res["runs"]["baseline"]["session_id"] = "g1"
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("share a session_id" in e for e in ve.errors))

    def test_contaminated_claims_success(self):
        res = self._result()
        res["protocol"]["status"] = "contaminated"
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("cannot claim a success outcome" in e for e in ve.errors))

    def test_frozen_assertion_missing(self):
        # case_index provides a frozen assertion that the result omits
        case_index = {"code-review": {1: {"execution": {"assertions": ["frozen", "other"]}}}}
        res = self._result()
        ve.check_one_result("r.md", res, {"code-review"}, case_index)
        self.assertTrue(any("missing from graded result" in e for e in ve.errors))

    # --- routing result validation (mode-specific) ---
    def _routing_result(self, present="code-review", absent=None, **over):
        res = self._result(
            mode="routing",
            protocol={"status": "limited", "worker_isolation_verified": True,
                      "routing_mechanism": "harness-selection-log",
                      "target_guidance_present": None,
                      "target_absent_in_baseline": None, "contamination": "none"},
            runs={"target": {"session_id": "g1", "output_hash": "h",
                             "selected_skill": present},
                  "baseline": {"session_id": "b1", "output_hash": "h",
                               "selected_skill": absent}},
            cases=[{
                "case_id": 1,
                "outcome": {"category": "both_pass",
                            "measurement_status": "discriminating",
                            "protocol_status": "limited"},
                "verdict": {"target_pass": True, "baseline_pass": True},
                "runs": {"target": {"selected_skill": present},
                         "baseline": {"selected_skill": absent}},
                "assertions": [],
            }])
        res.update(over)
        return res

    def _routing_index(self, present="code-review", absent=None,
                       present_fallbacks=None, absent_fallbacks=None):
        return {"code-review": {1: {"routing": {
            "target_present": {"expected_selected_skill": present,
                               "allowed_fallbacks": present_fallbacks or []},
            "target_absent": {"expected_selected_skill": absent,
                              "allowed_fallbacks": absent_fallbacks or []}}}}}

    def test_routing_valid_passes(self):
        res = self._routing_result()
        ve.check_one_result("r.md", res, {"code-review"}, self._routing_index())
        self.assertEqual(ve.errors, [], ve.errors)

    def test_routing_target_present_wrong_fails(self):
        res = self._routing_result(present="wrong-skill")
        ve.check_one_result("r.md", res, {"code-review"}, self._routing_index())
        self.assertTrue(any("does not match captured selection" in e for e in ve.errors))

    def test_routing_target_absent_wrong_fails(self):
        res = self._routing_result(absent="some-skill")
        ve.check_one_result("r.md", res, {"code-review"}, self._routing_index())
        self.assertTrue(any("does not match captured selection" in e for e in ve.errors))

    def test_routing_result_ignores_assertions(self):
        # Routing grades harness selection evidence; execution assertions are not
        # required and must not be flagged as missing.
        res = self._routing_result()
        ve.check_one_result("r.md", res, {"code-review"}, self._routing_index())
        self.assertFalse(any("assertion" in e.lower() for e in ve.errors))

    def test_valid_requires_os_level_isolation(self):
        res = self._result()
        res["protocol"]["status"] = "valid"
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("OS-level isolation" in e for e in ve.errors))

    def test_valid_requires_structured_isolation_attestation(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"]["status"] = "valid"
        res["protocol"].pop("isolation_attestation")
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("requires isolation_attestation" in e
                            for e in ve.errors))

    def test_valid_isolation_attestation_must_bind_case_evidence(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"]["status"] = "valid"
        res["protocol"]["isolation_attestation"]["evidence_hashes"]["1"] = (
            "sha256:" + "f" * 64)
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("isolation_attestation raw hash does not match"
                            in e for e in ve.errors))

    # --- new Docker execution evidence checks (mode == execution) ---
    def test_execution_shared_container_id_fails(self):
        res = self._result()
        res["runs"]["target"]["container_id"] = "cb1"  # same as baseline
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("share a container_id" in e for e in ve.errors))

    def test_execution_missing_skill_hash_fails(self):
        res = self._result()
        res["protocol"].pop("target_guidance_hash")
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("target_guidance_hash" in e for e in ve.errors))

    def test_execution_missing_baseline_absence_proof_fails(self):
        res = self._result()
        res["protocol"].pop("baseline_guidance_absent")
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("baseline_guidance_absent" in e for e in ve.errors))

    # --- catalog-routing / harness-routing modes (Layer A / Layer C) ---
    def _routing_mode_result(self, mode):
        res = self._result(
            mode=mode,
            protocol={"status": "limited", "worker_isolation_verified": True,
                      "routing_mechanism": "harness-selection-log",
                      "target_guidance_present": None,
                      "target_absent_in_baseline": None,
                      "target_guidance_hash": None, "baseline_guidance_absent": None,
                      "contamination": "none"},
            runs={"target": {"session_id": "g1", "container_id": "cg1",
                             "output_hash": "h", "selected_skill": "code-review"},
                  "baseline": {"session_id": "b1", "container_id": "cb1",
                               "output_hash": "h", "selected_skill": None}},
            cases=[{
                "case_id": 1,
                "outcome": {"category": "both_pass",
                            "measurement_status": "discriminating",
                            "protocol_status": "limited"},
                "verdict": {"target_pass": True, "baseline_pass": True},
                "runs": {"target": {"selected_skill": "code-review"},
                         "baseline": {"selected_skill": None}},
                "assertions": [],
            }])
        return res

    def test_catalog_routing_mode_accepted(self):
        res = self._routing_mode_result("catalog-routing")
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertEqual(ve.errors, [], ve.errors)

    def test_harness_routing_mode_accepted(self):
        res = self._routing_mode_result("harness-routing")
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertEqual(ve.errors, [], ve.errors)

    def test_placebo_only_pass_valid(self):
        # T false, B false, P true => placebo_only_pass
        evals_path = os.path.join(ve.ROOT, "skills", "code-review", "evals",
                                  "evals.json")
        source = json.load(open(evals_path))
        case = next(c for c in source["evals"] if c["id"] == 1)
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"]["status"] = "valid"
        res["protocol"]["tier"] = "tier-2-strict-isolated"
        res["protocol"]["worker_isolation_verified"] = True
        res["protocol"]["conditions"] = ["target", "baseline", "placebo"]
        prompt_hash = "sha256:" + hashlib.sha256(
            case["prompt"].encode()).hexdigest()
        res["cases"] = [{
            "case_id": 1,
            "natural_task_hash": prompt_hash,
            "fixture_hash": case["fixture"]["content_hash"],
            "raw_evidence_hash": "sha256:" + "e" * 64,
            "repetitions": [
                {"rep": 1, "repetition_id": "id1", "runs": {"target": {"session_id": "t1", "container_id": "c1"}, "baseline": {"session_id": "b1", "container_id": "c2"}, "placebo": {"session_id": "p1", "container_id": "c3"}}},
                {"rep": 2, "repetition_id": "id2", "runs": {"target": {"session_id": "t2", "container_id": "c4"}, "baseline": {"session_id": "b2", "container_id": "c5"}, "placebo": {"session_id": "p2", "container_id": "c6"}}},
                {"rep": 3, "repetition_id": "id3", "runs": {"target": {"session_id": "t3", "container_id": "c7"}, "baseline": {"session_id": "b3", "container_id": "c8"}, "placebo": {"session_id": "p3", "container_id": "c9"}}},
            ],
            "outcome": {"category": "placebo_only_pass", "measurement_status": "non_discriminating", "protocol_status": "valid"},
            "verdict": {"target_pass": False, "baseline_pass": False, "placebo_pass": True},
            "assertions": [{"assertion": "frozen", "target": {"pass": False, "evidence": "e"}, "baseline": {"pass": False, "evidence": "e"}, "placebo": {"pass": True, "evidence": "e"}}],
        }]
        ve.check_one_result(
            "r.md", res, {"code-review"},
            {"code-review": {1: {"prompt": case["prompt"],
                                  "fixture": case["fixture"],
                                  "evaluation_modes": ["routing", "execution"],
                                  "execution": {"assertions": []}}}})
        self.assertEqual(ve.errors, [], ve.errors)

    def test_limited_execution_may_omit_valid_only_provenance(self):
        # Compact limited records remain readable, but they are not protocol-valid.
        res = self._result()
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertEqual(ve.errors, [], ve.errors)

    def test_missing_per_case_fixture_hash_fails(self):
        import hashlib
        import json
        import os
        evals_path = os.path.join(ve.ROOT, "skills", "code-review", "evals",
                                  "evals.json")
        source = json.load(open(evals_path))
        case = next(c for c in source["evals"] if c["id"] == 1)
        prompt_hash = "sha256:" + hashlib.sha256(
            case["prompt"].encode()).hexdigest()
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"].update({"status": "valid",
                                 "tier": "tier-2-strict-isolated",
                                 "worker_isolation_verified": True})
        res["cases"] = [{
            "case_id": 1,
            "natural_task_hash": prompt_hash,
            "repetitions": [
                {"rep": i, "repetition_id": f"id{i}", "runs": {
                    "target": {"session_id": f"t{i}",
                                "container_id": f"ct{i}"},
                    "baseline": {"session_id": f"b{i}",
                                  "container_id": f"cb{i}"}}}
                for i in (1, 2, 3)
            ],
            "outcome": {"category": "skill_only_pass",
                        "measurement_status": "discriminating",
                        "protocol_status": "valid"},
            "verdict": {"target_pass": True, "baseline_pass": False},
            "assertions": [{"assertion": "frozen",
                            "target": {"pass": True, "evidence": "e"},
                            "baseline": {"pass": False, "evidence": "e"}}],
        }]
        ve.check_one_result(
            "r.md", res, {"code-review"},
            {"code-review": {1: {"prompt": case["prompt"],
                                  "fixture": case["fixture"],
                                  "execution": {"assertions": ["frozen"]}}}})
        self.assertTrue(any("fixture_hash" in e for e in ve.errors), ve.errors)

    def test_valid_unknown_case_id_fails(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"].update({"status": "valid",
                                 "tier": "tier-2-strict-isolated",
                                 "worker_isolation_verified": True})
        res["cases"] = [{
            "case_id": 99,
            "natural_task_hash": "sha256:" + "a" * 64,
            "fixture_hash": "sha256:" + "b" * 64,
            "repetitions": [
                {"rep": i, "repetition_id": f"id{i}", "runs": {
                    "target": {"session_id": f"t{i}",
                                "container_id": f"ct{i}"},
                    "baseline": {"session_id": f"b{i}",
                                  "container_id": f"cb{i}"}}}
                for i in (1, 2, 3)
            ],
            "outcome": {"category": "skill_only_pass",
                        "measurement_status": "discriminating",
                        "protocol_status": "valid"},
            "verdict": {"target_pass": True, "baseline_pass": False},
            "assertions": [{"assertion": "frozen",
                            "target": {"pass": True, "evidence": "e"},
                            "baseline": {"pass": False, "evidence": "e"}}],
        }]
        ve.check_one_result(
            "r.md", res, {"code-review"},
            {"code-review": {1: {"prompt": "known",
                                  "fixture": {"content_hash": "sha256:b"},
                                  "execution": {"assertions": ["frozen"]}}}})
        self.assertTrue(any("case_id is not present" in e for e in ve.errors),
                        ve.errors)

    def test_all_conditions_pass_cannot_be_discriminating(self):
        res = self._result()
        res["cases"][0]["outcome"].update({
            "category": "both_pass", "measurement_status": "discriminating"})
        res["cases"][0]["verdict"] = {
            "target_pass": True, "baseline_pass": True}
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("discriminating measurement requires" in e
                            for e in ve.errors), ve.errors)

    def test_unique_target_advantage_cannot_be_non_discriminating(self):
        res = self._result()
        res["cases"][0]["outcome"].update({
            "category": "skill_only_pass",
            "measurement_status": "non_discriminating"})
        res["cases"][0]["verdict"] = {
            "target_pass": True, "baseline_pass": False}
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("cannot claim a unique target advantage" in e
                            for e in ve.errors), ve.errors)

    def test_placebo_pass_prevents_skill_only_pass_category(self):
        res = self._result()
        res["protocol"]["conditions"] = ["target", "baseline", "placebo"]
        res["cases"][0]["outcome"].update({
            "category": "skill_only_pass",
            "measurement_status": "non_discriminating"})
        res["cases"][0]["verdict"] = {
            "target_pass": True, "baseline_pass": False, "placebo_pass": True}
        res["cases"][0]["assertions"][0]["placebo"] = {
            "pass": True, "evidence": "e"}
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("expected non_discriminating" in e
                            for e in ve.errors), ve.errors)

    def test_routing_unknown_case_id_fails(self):
        res = self._routing_result()
        res["protocol"]["status"] = "valid"
        res["runtime"]["isolation_method"] = "docker"
        res["cases"][0]["case_id"] = 99
        ve.check_one_result("r.md", res, {"code-review"},
                            self._routing_index())
        self.assertTrue(any("case_id is not present" in e for e in ve.errors),
                        ve.errors)

    def test_boolean_case_id_fails_closed(self):
        res = self._result()
        res["cases"][0]["case_id"] = True
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("case_id must be integer" in e for e in ve.errors),
                        ve.errors)

    def test_non_object_outcome_and_verdict_fail_closed(self):
        res = self._result()
        res["cases"][0]["outcome"] = []
        res["cases"][0]["verdict"] = []
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("outcome must be an object" in e for e in ve.errors),
                        ve.errors)
        self.assertTrue(any("verdict must be an object" in e for e in ve.errors),
                        ve.errors)

    def test_malformed_protocol_conditions_fails_closed(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"].update({"status": "valid",
                                 "tier": "tier-2-strict-isolated",
                                 "worker_isolation_verified": True,
                                 "conditions": [{"name": "target"}]})
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("conditions must contain only" in e
                            for e in ve.errors), ve.errors)

    def test_truthy_nested_run_fails_closed(self):
        res = self._result()
        res["cases"][0]["repetitions"] = [{}]
        res["runs"]["target"] = True
        res["runs"].pop("baseline")
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("top-level runs.target must be an object" in e
                            for e in ve.errors), ve.errors)

    def test_truthy_assertion_grade_fails_closed(self):
        res = self._result()
        res["cases"][0]["assertions"][0]["target"] = True
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("target grade must be an object" in e
                            for e in ve.errors), ve.errors)

    def test_truthy_invalid_outcome_fails_closed(self):
        res = self._result()
        res["protocol"]["status"] = "invalid"
        res["cases"][0]["outcome"] = True
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("outcome.category" in e for e in ve.errors),
                        ve.errors)

    def test_valid_result_requires_cases(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"].update({"status": "valid",
                                 "tier": "tier-2-strict-isolated",
                                 "worker_isolation_verified": True})
        res["cases"] = []
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("valid result must contain at least one case" in e
                            for e in ve.errors), ve.errors)

    def test_valid_case_must_support_result_mode(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"].update({"status": "valid",
                                 "tier": "tier-2-strict-isolated",
                                 "worker_isolation_verified": True})
        case_index = {"code-review": {1: {
            "prompt": "do a thing",
            "fixture": {"content_hash": "sha256:b"},
            "evaluation_modes": ["routing"],
            "execution": {"assertions": []},
        }}}
        ve.check_one_result("r.md", res, {"code-review"}, case_index)
        self.assertTrue(any("does not support evaluation_mode" in e
                            for e in ve.errors), ve.errors)

    def test_case_protocol_status_must_match_top_level(self):
        res = self._result()
        res["cases"][0]["outcome"]["protocol_status"] = "valid"
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("outcome.protocol_status must match" in e
                            for e in ve.errors), ve.errors)

    def test_missing_placebo_verdict_fails(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"].update({"status": "valid",
                                 "tier": "tier-2-strict-isolated",
                                 "worker_isolation_verified": True,
                                 "conditions": ["target", "baseline", "placebo"]})
        res["cases"] = [{
            "case_id": 1,
            "natural_task_hash": "sha256:" + "a" * 64,
            "fixture_hash": "sha256:b",
            "repetitions": [
                {"rep": i, "repetition_id": f"id{i}", "runs": {
                    "target": {"session_id": f"t{i}",
                                "container_id": f"ct{i}"},
                    "baseline": {"session_id": f"b{i}",
                                  "container_id": f"cb{i}"},
                    "placebo": {"session_id": f"p{i}",
                                 "container_id": f"cp{i}"}}}
                for i in (1, 2, 3)
            ],
            "outcome": {"category": "skill_only_pass",
                        "measurement_status": "discriminating",
                        "protocol_status": "valid"},
            "verdict": {"target_pass": True, "baseline_pass": False},
            "assertions": [{"assertion": "frozen",
                            "target": {"pass": True, "evidence": "e"},
                            "baseline": {"pass": False, "evidence": "e"},
                            "placebo": {"pass": False, "evidence": "e"}}],
        }]
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("placebo_pass" in e for e in ve.errors), ve.errors)

    def test_execution_identity_duplicate_across_cases_fails(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"].update({"status": "valid",
                                 "tier": "tier-2-strict-isolated",
                                 "worker_isolation_verified": True})

        def case(cid, session_prefix):
            return {
                "case_id": cid,
                "natural_task_hash": "sha256:" + str(cid) * 64,
                "fixture_hash": "sha256:" + str(cid),
                "repetitions": [
                    {"rep": i, "repetition_id": f"{cid}-{i}", "runs": {
                        "target": {"session_id": session_prefix if i == 1 else f"t{cid}-{i}",
                                    "container_id": f"ct{cid}-{i}"},
                        "baseline": {"session_id": f"b{cid}-{i}",
                                      "container_id": f"cb{cid}-{i}"}}}
                    for i in (1, 2, 3)
                ],
                "outcome": {"category": "skill_only_pass",
                            "measurement_status": "discriminating",
                            "protocol_status": "valid"},
                "verdict": {"target_pass": True, "baseline_pass": False},
                "assertions": [{"assertion": "frozen",
                                "target": {"pass": True, "evidence": "e"},
                                "baseline": {"pass": False, "evidence": "e"}}],
            }

        res["cases"] = [case(1, "shared-session"),
                         case(2, "shared-session")]
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("across cases" in e and "session_id" in e
                            for e in ve.errors), ve.errors)

    def test_both_fail_with_placebo_true_is_inconsistent(self):
        # both_fail with placebo true should be placebo_only_pass, so both_fail is inconsistent
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"]["status"] = "valid"
        res["protocol"]["tier"] = "tier-2-strict-isolated"
        res["protocol"]["worker_isolation_verified"] = True
        res["cases"] = [{
            "case_id": 1,
            "natural_task_hash": "sha256:" + "a"*64,
            "fixture_hash": "sha256:b",
            "repetitions": [
                {"rep": 1, "repetition_id": "id1", "runs": {"target": {"session_id": "t1", "container_id": "c1"}, "baseline": {"session_id": "b1", "container_id": "c2"}, "placebo": {"session_id": "p1", "container_id": "c3"}}},
                {"rep": 2, "repetition_id": "id2", "runs": {"target": {"session_id": "t2", "container_id": "c4"}, "baseline": {"session_id": "b2", "container_id": "c5"}, "placebo": {"session_id": "p2", "container_id": "c6"}}},
                {"rep": 3, "repetition_id": "id3", "runs": {"target": {"session_id": "t3", "container_id": "c7"}, "baseline": {"session_id": "b3", "container_id": "c8"}, "placebo": {"session_id": "p3", "container_id": "c9"}}},
            ],
            "outcome": {"category": "both_fail", "measurement_status": "non_discriminating", "protocol_status": "valid"},
            "verdict": {"target_pass": False, "baseline_pass": False, "placebo_pass": True},
            "assertions": [{"assertion": "frozen", "target": {"pass": False, "evidence": "e"}, "baseline": {"pass": False, "evidence": "e"}, "placebo": {"pass": True, "evidence": "e"}}],
        }]
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("inconsistent" in e and "placebo_only_pass" in e for e in ve.errors), ve.errors)

    def test_per_case_natural_task_hash_mismatch_fails(self):
        # Create a case where case 1 uses case 5's hash
        import hashlib
        import json
        import os
        evals_path = os.path.join(ve.ROOT, "skills", "code-review", "evals", "evals.json")
        source = json.load(open(evals_path))
        case1_prompt = next(c for c in source["evals"] if c["id"] == 1)["prompt"]
        case5_prompt = next(c for c in source["evals"] if c["id"] == 5)["prompt"]
        wrong_hash = "sha256:" + hashlib.sha256(case5_prompt.encode()).hexdigest()
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"]["status"] = "valid"
        res["protocol"]["tier"] = "tier-2-strict-isolated"
        res["protocol"]["worker_isolation_verified"] = True
        res["cases"] = [{
            "case_id": 1,
            "natural_task_hash": wrong_hash,
            "fixture_hash": "sha256:b",
            "repetitions": [
                {"rep": 1, "repetition_id": "id1", "runs": {"target": {"session_id": "t1", "container_id": "c1"}, "baseline": {"session_id": "b1", "container_id": "c2"}, "placebo": {"session_id": "p1", "container_id": "c3"}}},
                {"rep": 2, "repetition_id": "id2", "runs": {"target": {"session_id": "t2", "container_id": "c4"}, "baseline": {"session_id": "b2", "container_id": "c5"}, "placebo": {"session_id": "p2", "container_id": "c6"}}},
                {"rep": 3, "repetition_id": "id3", "runs": {"target": {"session_id": "t3", "container_id": "c7"}, "baseline": {"session_id": "b3", "container_id": "c8"}, "placebo": {"session_id": "p3", "container_id": "c9"}}},
            ],
            "outcome": {"category": "skill_only_pass", "measurement_status": "discriminating", "protocol_status": "valid"},
            "verdict": {"target_pass": True, "baseline_pass": False, "placebo_pass": False},
            "assertions": [{"assertion": "frozen", "target": {"pass": True, "evidence": "e"}, "baseline": {"pass": False, "evidence": "e"}}],
        }]
        ve.check_one_result("r.md", res, {"code-review"}, {"code-review": {1: {"execution": {"assertions": ["frozen"]}, "prompt": case1_prompt}}})
        self.assertTrue(any("natural_task_hash" in e and "does not match" in e for e in ve.errors), ve.errors)

    def test_single_case_top_level_task_hash_mismatch_fails(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"].update({"status": "valid",
                                 "tier": "tier-2-strict-isolated",
                                 "worker_isolation_verified": True,
                                 "natural_task_hash": "sha256:" + "b" * 64})
        res["cases"] = [{
            "case_id": 1,
            "natural_task_hash": "sha256:" + "a" * 64,
            "fixture_hash": "sha256:b",
            "repetitions": [
                {"rep": i, "repetition_id": f"id{i}", "runs": {
                    "target": {"session_id": f"t{i}",
                                "container_id": f"ct{i}"},
                    "baseline": {"session_id": f"b{i}",
                                  "container_id": f"cb{i}"}}}
                for i in (1, 2, 3)
            ],
            "outcome": {"category": "skill_only_pass",
                        "measurement_status": "discriminating",
                        "protocol_status": "valid"},
            "verdict": {"target_pass": True, "baseline_pass": False},
            "assertions": [{"assertion": "frozen",
                            "target": {"pass": True, "evidence": "e"},
                            "baseline": {"pass": False, "evidence": "e"}}],
        }]
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("single-case protocol.natural_task_hash" in e
                            for e in ve.errors), ve.errors)

    def test_missing_per_case_repetitions_fails(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"]["status"] = "valid"
        res["protocol"]["tier"] = "tier-2-strict-isolated"
        res["protocol"]["worker_isolation_verified"] = True
        res["cases"] = [{
            "case_id": 1,
            "natural_task_hash": "sha256:" + "a"*64,
            "outcome": {"category": "skill_only_pass", "measurement_status": "discriminating", "protocol_status": "valid"},
            "verdict": {"target_pass": True, "baseline_pass": False},
            "assertions": [{"assertion": "frozen", "target": {"pass": True, "evidence": "e"}, "baseline": {"pass": False, "evidence": "e"}}],
        }]
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("repetitions" in e for e in ve.errors), ve.errors)

    def test_duplicate_repetition_id_fails(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"]["status"] = "valid"
        res["protocol"]["tier"] = "tier-2-strict-isolated"
        res["protocol"]["worker_isolation_verified"] = True
        res["cases"] = [{
            "case_id": 1,
            "natural_task_hash": "sha256:" + "a"*64,
            "fixture_hash": "sha256:b",
            "repetitions": [
                {"rep": 1, "repetition_id": "dup", "runs": {"target": {"session_id": "t1", "container_id": "c1"}, "baseline": {"session_id": "b1", "container_id": "c2"}}},
                {"rep": 2, "repetition_id": "dup", "runs": {"target": {"session_id": "t2", "container_id": "c3"}, "baseline": {"session_id": "b2", "container_id": "c4"}}},
                {"rep": 3, "repetition_id": "id3", "runs": {"target": {"session_id": "t3", "container_id": "c5"}, "baseline": {"session_id": "b3", "container_id": "c6"}}},
            ],
            "outcome": {"category": "skill_only_pass", "measurement_status": "discriminating", "protocol_status": "valid"},
            "verdict": {"target_pass": True, "baseline_pass": False},
            "assertions": [{"assertion": "frozen", "target": {"pass": True, "evidence": "e"}, "baseline": {"pass": False, "evidence": "e"}}],
        }]
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("duplicate repetition_id" in e for e in ve.errors), ve.errors)

    def test_duplicate_session_id_across_reps_fails(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"]["status"] = "valid"
        res["protocol"]["tier"] = "tier-2-strict-isolated"
        res["protocol"]["worker_isolation_verified"] = True
        res["cases"] = [{
            "case_id": 1,
            "natural_task_hash": "sha256:" + "a"*64,
            "fixture_hash": "sha256:b",
            "repetitions": [
                {"rep": 1, "repetition_id": "id1", "runs": {"target": {"session_id": "dup", "container_id": "c1"}, "baseline": {"session_id": "b1", "container_id": "c2"}}},
                {"rep": 2, "repetition_id": "id2", "runs": {"target": {"session_id": "dup", "container_id": "c3"}, "baseline": {"session_id": "b2", "container_id": "c4"}}},
                {"rep": 3, "repetition_id": "id3", "runs": {"target": {"session_id": "t3", "container_id": "c5"}, "baseline": {"session_id": "b3", "container_id": "c6"}}},
            ],
            "outcome": {"category": "skill_only_pass", "measurement_status": "discriminating", "protocol_status": "valid"},
            "verdict": {"target_pass": True, "baseline_pass": False},
            "assertions": [{"assertion": "frozen", "target": {"pass": True, "evidence": "e"}, "baseline": {"pass": False, "evidence": "e"}}],
        }]
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("duplicate session_id" in e for e in ve.errors), ve.errors)

    def test_incorrect_repeat_count_fails(self):
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"]["status"] = "valid"
        res["protocol"]["tier"] = "tier-2-strict-isolated"
        res["protocol"]["worker_isolation_verified"] = True
        res["cases"] = [{
            "case_id": 1,
            "natural_task_hash": "sha256:" + "a"*64,
            "fixture_hash": "sha256:b",
            "repetitions": [
                {"rep": 1, "repetition_id": "id1", "runs": {"target": {"session_id": "t1", "container_id": "c1"}, "baseline": {"session_id": "b1", "container_id": "c2"}}},
                {"rep": 2, "repetition_id": "id2", "runs": {"target": {"session_id": "t2", "container_id": "c3"}, "baseline": {"session_id": "b2", "container_id": "c4"}}},
            ],
            "outcome": {"category": "skill_only_pass", "measurement_status": "discriminating", "protocol_status": "valid"},
            "verdict": {"target_pass": True, "baseline_pass": False},
            "assertions": [{"assertion": "frozen", "target": {"pass": True, "evidence": "e"}, "baseline": {"pass": False, "evidence": "e"}}],
        }]
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("must contain 3 complete repetitions" in e for e in ve.errors), ve.errors)

    def test_protocol_requirements_are_mode_specific(self):
        self.assertEqual(ep.validate_declaration("smoke", ["target"], 1), [])
        self.assertTrue(ep.validate_declaration("qualification", ["target"], 1))
        self.assertTrue(ep.validate_declaration(
            "confirmation", ["target", "baseline", "placebo"], 1))
        self.assertEqual(
            ep.validate_declaration("regression", ["candidate", "reference"], 1),
            [],
        )

    def test_qualification_ignores_skill_contract_assertions_for_baseline_score(self):
        """A target-only heading contract cannot manufacture marginal value."""
        prompt = "Review this pull request and identify correctness problems."
        case_index = {"code-review": {1: {
            "prompt": prompt,
            "fixture": {"content_hash": "sha256:fixture"},
            "evaluation_modes": ["execution"],
            "execution": {"assertions": [
                {"text": "uses the skill-only report headings",
                 "type": "presentation", "scope": "skill-contract"},
                {"text": "identifies the real correctness defect",
                 "type": "behavioral", "scope": "shared-outcome"},
            ]},
        }}}
        res = self._result()
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"] = {
            "name": "qualification", "status": "valid",
            "worker_isolation_verified": True,
            "isolation_attestation": self._isolation_attestation(1),
            "target_guidance_present": "activated",
            "target_guidance_hash": "sha256:target",
            "target_absent_in_baseline": "absent",
            "baseline_guidance_absent": "absent",
            "contamination": "none",
            "conditions": ["target", "baseline"], "repeats": 1,
        }
        res["cases"] = [{
            "case_id": 1,
            "natural_task_hash": "sha256:" + hashlib.sha256(prompt.encode()).hexdigest(),
            "fixture_hash": "sha256:fixture",
            "raw_evidence_hash": "sha256:" + "e" * 64,
            "repetitions": [{"rep": 1, "repetition_id": "q1", "runs": {
                "target": {"session_id": "qt", "container_id": "qct"},
                "baseline": {"session_id": "qb", "container_id": "qcb"},
            }}],
            "outcome": {"category": "both_pass",
                        "measurement_status": "non_discriminating",
                        "protocol_status": "valid"},
            "verdict": {"target_pass": True, "baseline_pass": True},
            "early_stop": {"stopped": True,
                            "reason": "same shared outcome at n=1",
                            "next_protocol": "none"},
            "contract_adherence": "pass",
            "assertions": [
                {"assertion": "uses the skill-only report headings",
                 "scope": "skill-contract",
                 "target": {"pass": True, "evidence": "headings present"},
                 "baseline": {"pass": False, "evidence": "correct review without headings"}},
                {"assertion": "identifies the real correctness defect",
                 "scope": "shared-outcome",
                 "target": {"pass": True, "evidence": "defect at app.py:10"},
                 "baseline": {"pass": True, "evidence": "defect at app.py:10"}},
            ],
        }]
        ve.check_one_result("r.md", res, {"code-review"}, case_index)
        self.assertEqual(ve.errors, [], ve.errors)

        res["cases"][0]["assertions"].append({
            "assertion": "invented shared assertion",
            "scope": "shared-outcome",
            "target": {"pass": True, "evidence": "invented target evidence"},
            "baseline": {"pass": False, "evidence": "invented baseline evidence"},
        })
        reset()
        ve.check_one_result("r.md", res, {"code-review"}, case_index)
        self.assertTrue(any("not declared by the authoritative case" in e
                            for e in ve.errors), ve.errors)
        res["cases"][0]["assertions"].pop()

        # A dishonest result that lets the contract-only failure make the
        # baseline lose must be rejected by the validator.
        res["cases"][0]["outcome"] = {
            "category": "skill_only_pass", "measurement_status": "discriminating",
            "protocol_status": "valid",
        }
        res["cases"][0]["verdict"]["baseline_pass"] = False
        reset()
        ve.check_one_result("r.md", res, {"code-review"}, case_index)
        self.assertTrue(any("shared-outcome assertions" in e for e in ve.errors), ve.errors)

    def test_regression_conditions_and_status_are_validated(self):
        prompt = "Compare the current implementation with the previous revision."
        case_index = {"code-review": {1: {
            "prompt": prompt,
            "fixture": {"content_hash": "sha256:fixture"},
            "evaluation_modes": ["execution"],
            "execution": {"assertions": ["preserves the behavior"]},
        }}}
        res = self._result(mode="regression")
        res.update({"method": "docker-isolated",
                    "candidate_skill_revision": "sha256:candidate",
                    "reference_skill_revision": "sha256:reference"})
        res.pop("target_skill_revision", None)
        res["runtime"]["isolation_method"] = "docker"
        res["protocol"] = {
            "name": "regression", "status": "valid",
            "worker_isolation_verified": True,
            "isolation_attestation": self._isolation_attestation(1),
            "candidate_guidance_present": "activated",
            "reference_guidance_present": "activated",
            "candidate_guidance_hash": "sha256:candidate-tree",
            "reference_guidance_hash": "sha256:reference-tree",
            "conditions": ["candidate", "reference"], "repeats": 1,
            "contamination": "none",
        }
        res["cases"] = [{
            "case_id": 1,
            "natural_task_hash": "sha256:" + hashlib.sha256(prompt.encode()).hexdigest(),
            "fixture_hash": "sha256:fixture",
            "raw_evidence_hash": "sha256:" + "e" * 64,
            "repetitions": [{"rep": 1, "repetition_id": "r1", "runs": {
                "candidate": {"session_id": "rc", "container_id": "rcc"},
                "reference": {"session_id": "rr", "container_id": "rrc"},
            }}],
            "outcome": {"category": "both_pass",
                        "measurement_status": "non_discriminating",
                        "protocol_status": "valid",
                        "regression_status": "preserved_behavior"},
            "verdict": {"candidate_pass": True, "reference_pass": True},
            "assertions": [{"assertion": "preserves the behavior",
                            "candidate": {"pass": True, "evidence": "test passed"},
                            "reference": {"pass": True, "evidence": "test passed"}}],
        }]
        ve.check_one_result("r.md", res, {"code-review"}, case_index)
        self.assertEqual(ve.errors, [], ve.errors)

        # The same result shape may use neutral worker IDs without a container
        # or provider-specific field.
        res["method"] = "harness-adapter"
        for name, worker in (("candidate", "wc"), ("reference", "wr")):
            run = res["cases"][0]["repetitions"][0]["runs"][name]
            run["worker_id"] = worker
            run.pop("container_id", None)
        reset()
        ve.check_one_result("r.md", res, {"code-review"}, case_index)
        self.assertEqual(ve.errors, [], ve.errors)

    def test_regression_rejects_effectiveness_overclaim(self):
        ve.validate_regression_claim(
            "r.md", {"outcome": {"claim": "skill_effective"}}, ve.errors)
        self.assertTrue(any("skill_effective" in error for error in ve.errors),
                        ve.errors)

    def test_qualification_n1_non_discriminating_requires_honest_early_stop(self):
        self.assertEqual(
            ep.early_stop_recommendation(True, True),
            {"stopped": True,
             "reason": "target and baseline both passed shared-outcome criteria at n=1",
             "next_protocol": "none"},
        )
        self.assertEqual(ep.early_stop_recommendation(False, True)["stopped"], True)


class HarnessAdapterTests(unittest.TestCase):
    def tearDown(self):
        reset()

    def test_command_adapter_normalizes_neutral_response(self):
        response = {
            "run_status": "success",
            "returncode": 0,
            "worker_id": "worker-1",
            "session_id": "session-1",
            "output": "completed",
            "guidance_probe": "present",
            "guidance_context_probe": "present",
            "activation_mechanism": "adapter-defined",
            "workspace_receipt_path": eha.WORKSPACE_RECEIPT_PATH,
            "workspace_receipt": "receipt-token",
        }
        completed = subprocess.CompletedProcess(
            ["adapter"], 0, json.dumps(response), "")
        with unittest.mock.patch.object(eha.subprocess, "run",
                                        return_value=completed):
            adapter = eha.CommandHarnessAdapter("adapter", name="test")
            actual = adapter.run({"condition": "candidate"})
        self.assertEqual(actual["worker_id"], "worker-1")
        self.assertEqual(actual["guidance_context_probe"], "present")
        self.assertEqual(actual["adapter_metadata"]["protocol"],
                         eha.ADAPTER_PROTOCOL)

    def test_command_adapter_timeout_normalizes_partial_bytes(self):
        timeout = subprocess.TimeoutExpired(
            ["adapter"], 1, output=b"partial output", stderr=b"partial error")
        with unittest.mock.patch.object(eha.subprocess, "run",
                                        side_effect=timeout):
            actual = eha.CommandHarnessAdapter("adapter").run({})
        self.assertEqual(actual["run_status"], "failed")
        self.assertEqual(actual["stdout"], "partial output")
        self.assertEqual(actual["stderr"], "partial error")
        json.dumps(actual)

    def test_neutral_harness_rejects_symlinked_inputs(self):
        tmp = tempfile.mkdtemp()
        try:
            outside = os.path.join(tmp, "outside.txt")
            open(outside, "w").write("outside\n")
            skill = os.path.join(tmp, "skill")
            os.makedirs(os.path.join(skill, "references"))
            open(os.path.join(skill, "SKILL.md"), "w").write("# guidance\n")
            os.symlink(outside, os.path.join(skill, "references", "outside.md"))
            with self.assertRaisesRegex(ValueError, "symlink"):
                eha.skill_tree_hash(skill)
            workspace = os.path.join(tmp, "workspace")
            os.makedirs(workspace)
            with self.assertRaisesRegex(ValueError, "symlink"):
                eha.materialize_guidance(skill, workspace)

            fixture = os.path.join(tmp, "fixture")
            os.makedirs(fixture)
            os.symlink(outside, os.path.join(fixture, "README.md"))
            with self.assertRaisesRegex(ValueError, "symlink"):
                eha.copy_seed(fixture)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_neutral_runner_materializes_guidance_without_harness_path(self):
        tmp = tempfile.mkdtemp()
        try:
            seed = os.path.join(tmp, "seed")
            os.makedirs(seed)
            open(os.path.join(seed, "task.txt"), "w").write("task\n")
            skill = os.path.join(tmp, "skill")
            os.makedirs(skill)
            open(os.path.join(skill, "SKILL.md"), "w").write("# guidance\n")

            class FakeAdapter:
                def run(self, request):
                    guided = request["guidance"] is not None
                    receipt = open(os.path.join(
                        request["workspace"],
                        request["workspace_receipt_path"]), encoding="utf-8").read()
                    response = {
                        "run_status": "success",
                        "returncode": 0,
                        "worker_id": "worker-" + request["condition"],
                        "session_id": "session-" + request["condition"],
                        "output": "done",
                        "guidance_probe": "present" if guided else "absent",
                        "guidance_context_probe": "present" if guided else "none",
                        "activation_mechanism": "fake-adapter" if guided else "none",
                        "workspace_receipt_path": request["workspace_receipt_path"],
                        "workspace_receipt": receipt,
                    }
                    response["execution_attestation"] = fake_execution_attestation(
                        request, response)
                    return response

            repetition, _, workspaces = eha.run_condition_repetition(
                0, ["target", "baseline"], "do task", seed,
                {"target": {"skill_name": "sample", "source_dir": skill},
                 "baseline": None},
                "test-model", FakeAdapter(), protocol="qualification", case_id=1)
            self.assertTrue(repetition["starting_task_hashes_match"])
            self.assertEqual(
                repetition["workspace_receipt_path"],
                eha.WORKSPACE_RECEIPT_PATH)
            for name, condition in repetition["conditions"].items():
                self.assertEqual(condition["workspace_receipt_path"],
                                 eha.WORKSPACE_RECEIPT_PATH)
                self.assertEqual(
                    condition["workspace_receipt_hash"],
                    repetition["condition_workspace_receipt_hashes"][name])
                self.assertEqual(
                    condition["workspace_receipt_hash"],
                    "sha256:" + hashlib.sha256(
                        condition["workspace_receipt"].encode()).hexdigest())
            self.assertEqual(
                repetition["conditions"]["target"]["guidance_path"],
                eha.RUNTIME_TREATMENT_PATHS[0])
            self.assertIsNone(repetition["conditions"]["baseline"]["guidance_path"])
            self.assertNotEqual(
                repetition["conditions"]["target"]["starting_full_hash"],
                repetition["conditions"]["baseline"]["starting_full_hash"])
            for workspace in workspaces.values():
                self.assertFalse(os.path.exists(
                    os.path.join(workspace, ".kilo")))
                shutil.rmtree(workspace, ignore_errors=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_regression_materializes_git_revision_with_repository_shape(self):
        root, resolved = rsre.materialize_skill_revision("HEAD", "code-review")
        try:
            self.assertRegex(resolved, r"^[0-9a-f]{40}$")
            self.assertTrue(os.path.isfile(os.path.join(
                root, "skills", "code-review", "SKILL.md")))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_regression_builder_and_neutral_validator_round_trip_without_model(self):
        candidate_root = reference_root = None
        try:
            candidate_root, candidate_revision = rsre.materialize_skill_revision(
                "HEAD", "code-review")
            reference_root, reference_revision = rsre.materialize_skill_revision(
                "HEAD", "code-review")

            class FakeAdapter:
                name = "test"

                def run(self, request):
                    guidance = request["guidance"]
                    receipt = open(os.path.join(
                        request["workspace"],
                        request["workspace_receipt_path"]), encoding="utf-8").read()
                    response = {
                        "run_status": "success",
                        "returncode": 0,
                        "worker_id": "worker-" + request["condition"],
                        "session_id": "session-" + request["condition"],
                        "output": "completed",
                        "guidance_probe": "present",
                        "guidance_context_probe": "present",
                        "activation_mechanism": "fake-adapter",
                        "guidance_id": guidance["guidance_id"],
                        "guidance_hash": guidance["guidance_hash"],
                        "guidance_source": "external_runtime",
                        "activation_verified": True,
                        "context_verified": True,
                        "guidance_path": guidance["guidance_path"],
                        "guidance_content_hash": guidance["guidance_content_hash"],
                        "workspace_receipt_path": request["workspace_receipt_path"],
                        "workspace_receipt": receipt,
                    }
                    response["execution_attestation"] = fake_execution_attestation(
                        request, response)
                    return response

            args = argparse.Namespace(skill="code-review", case_id=5,
                                      model=None, reps=1)
            with unittest.mock.patch.object(
                    rsre, "materialize_fixture_seed",
                    wraps=rsre.materialize_fixture_seed) as materialize:
                evidence = rsre.build_evidence(
                    args, candidate_root, reference_root,
                    candidate_revision, reference_revision, FakeAdapter())
            self.assertEqual(materialize.call_count, 1)
            fixture_dir = materialize.call_args.args[0]
            self.assertEqual(
                os.path.commonpath((fixture_dir, reference_root)),
                reference_root)
            self.assertNotEqual(
                os.path.commonpath((fixture_dir, candidate_root)),
                candidate_root)
            self.assertEqual(evidence["result_schema_version"], 3)
            for key in ("candidate_skill_hash", "reference_skill_hash",
                        "case_set_hash", "fixture_hash", "runner_version",
                        "reproduction_status"):
                self.assertIn(key, evidence)
            for condition in evidence["repetitions"][0]["conditions"].values():
                self.assertEqual(
                    set(condition["attestation_layers"]),
                    {"adapter_claims", "evaluator_verification",
                     "independent_attestation"})
            self.assertEqual(ve.validate_generic_regression_evidence(evidence), [])
        finally:
            if candidate_root:
                shutil.rmtree(candidate_root, ignore_errors=True)
            if reference_root:
                shutil.rmtree(reference_root, ignore_errors=True)

    def _neutral_regression_evidence_fixture(self):
        skill = "code-review"
        evals_path = os.path.join(ROOT, "skills", skill, "evals", "evals.json")
        source = json.load(open(evals_path, encoding="utf-8"))
        case = next(item for item in source["evals"] if item["id"] == 5)
        fixture = case["fixture"]
        expected_fixture = (fixture.get("output_hash") or
                            fixture.get("content_hash"))
        evals_rel = os.path.relpath(evals_path, ROOT)
        skill_rel = os.path.dirname(os.path.dirname(evals_rel))
        fixture_rel = os.path.normpath(os.path.join(skill_rel, fixture["path"]))
        source_hash = "sha256:" + hashlib.sha256(
            open(evals_path, "rb").read()).hexdigest()
        prompt_hash = hashlib.sha256(case["prompt"].encode()).hexdigest()
        generator_source_hash = None
        if fixture.get("type") == "generator":
            generator_source_hash = "sha256:" + hashlib.sha256(
                open(os.path.join(ROOT, fixture_rel,
                                  fixture.get("source", "setup.sh")),
                     "rb").read()).hexdigest()
        candidate_hash = eha.skill_tree_hash(
            os.path.join(ROOT, "skills", skill))
        reference_hash = candidate_hash
        resolved_revision = rsre.resolve_revision("HEAD")
        repetition_id = "rep-neutral"
        case_anchor = {
            "revision": resolved_revision,
            "source_path": evals_rel,
            "source_hash": source_hash,
            "prompt_hash": prompt_hash,
            "fixture_type": fixture.get("type"),
            "fixture_path": fixture_rel,
            "fixture_hash": expected_fixture,
            "generator_source_hash": generator_source_hash,
        }

        def condition(name, worker, session, content_hash):
            receipt = "receipt-" + name
            output = "completed"
            nonce = "nonce-" + name
            request_hash = "sha256:" + hashlib.sha256(
                ("request-" + name).encode()).hexdigest()
            condition = {
                "repetition_id": repetition_id,
                "worker_id": worker,
                "session_id": session,
                "run_status": "success",
                "returncode": 0,
                "starting_task_hash": expected_fixture,
                "ending_task_hash": expected_fixture,
                "starting_full_hash": "sha256:full-" + name,
                "ending_full_hash": "sha256:end-" + name,
                "output": output,
                "guidance_probe": "present",
                "guidance_context_probe": "present",
                "activation_mechanism": "adapter-defined",
                "guidance_id": skill,
                "guidance_hash": content_hash,
                "guidance_source": "external_runtime",
                "activation_verified": True,
                "context_verified": True,
                "guidance_path": eha.RUNTIME_TREATMENT_PATHS[0],
                "guidance_content_hash": content_hash,
                "workspace_receipt_path": eha.WORKSPACE_RECEIPT_PATH,
                "workspace_receipt": receipt,
                "workspace_receipt_hash": "sha256:" + hashlib.sha256(
                    receipt.encode()).hexdigest(),
                "attestation_nonce": nonce,
                "execution_request_hash": request_hash,
            }
            condition["execution_observation_hash"] = eha.attestation_observation_hash(
                condition)
            condition["execution_attestation"] = {
                "protocol": eha.EXECUTION_ATTESTATION_PROTOCOL,
                "status": "verified",
                "confidence": "independently_verified",
                "verification_mode": "independent",
                "source": "worker",
                "worker_id": worker,
                "session_id": session,
                "nonce": nonce,
                "request_hash": request_hash,
                "observation_hash": condition["execution_observation_hash"],
                "workspace_receipt_hash": condition["workspace_receipt_hash"],
                "output_hash": "sha256:" + hashlib.sha256(
                    output.encode()).hexdigest(),
                "returncode": 0,
            }
            return condition

        evidence = {
            "evidence_type": "regression",
            "protocol": "regression",
            "harness": {"name": "test", "adapter_protocol": eha.ADAPTER_PROTOCOL},
            "skill": skill,
            "case_id": 5,
            "conditions": ["candidate", "reference"],
            "candidate_revision": resolved_revision,
            "reference_revision": resolved_revision,
            "fixture_revision": resolved_revision,
            "case_anchors": {
                "candidate": dict(case_anchor),
                "reference": dict(case_anchor),
            },
            "candidate_skill_source_path": "skills/code-review",
            "reference_skill_source_path": "skills/code-review",
            "candidate_skill_content_hash": candidate_hash,
            "reference_skill_content_hash": reference_hash,
            "candidate_guidance_path": eha.RUNTIME_TREATMENT_PATHS[0],
            "reference_guidance_path": eha.RUNTIME_TREATMENT_PATHS[0],
            "fixture_source_path": evals_rel,
            "fixture_path": fixture_rel,
            "fixture_source_hash": source_hash,
            "expected_fixture_hash": expected_fixture,
            "canonical_task_seed_hash": expected_fixture,
            "runtime_treatment_paths": list(eha.RUNTIME_TREATMENT_PATHS),
            "repetitions": [{
                "rep": 1,
                "repetition_id": repetition_id,
                "natural_task_hash": prompt_hash,
                "natural_task_identical_across_conditions": True,
                "condition_workspace_ids": {"candidate": "w1", "reference": "w2"},
                "condition_workspace_receipt_hashes": {
                    "candidate": "sha256:" + hashlib.sha256(
                        b"receipt-candidate").hexdigest(),
                    "reference": "sha256:" + hashlib.sha256(
                        b"receipt-reference").hexdigest(),
                },
                "workspace_receipt_path": eha.WORKSPACE_RECEIPT_PATH,
                "conditions": {
                    "candidate": condition("candidate", "w1", "s1", candidate_hash),
                    "reference": condition("reference", "w2", "s2", reference_hash),
                },
            }],
        }
        return evidence

    def test_neutral_regression_evidence_does_not_require_kilo_fields(self):
        evidence = self._neutral_regression_evidence_fixture()
        self.assertEqual(ve.validate_generic_regression_evidence(evidence), [])
        evidence["candidate_skill_content_hash"] = "sha256:" + "0" * 64
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("materialized Git revision" in error for error in errors), errors)
        evidence["candidate_skill_content_hash"] = evidence["reference_skill_content_hash"]
        evidence["repetitions"][0]["conditions"]["candidate"][
            "context_verified"] = False
        self.assertTrue(any("context_verified must be true" in error
                            for error in ve.validate_generic_regression_evidence(evidence)))

    def test_neutral_regression_binds_revision_local_case_anchors(self):
        evidence = self._neutral_regression_evidence_fixture()
        evidence["case_anchors"]["candidate"]["source_hash"] = "sha256:" + "c" * 64
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("case_anchors.candidate.source_hash" in error
                            for error in errors), errors)

        evidence = self._neutral_regression_evidence_fixture()
        evidence["fixture_revision"] = "not-the-reference-revision"
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("fixture_revision" in error for error in errors), errors)

    def test_neutral_regression_uses_recorded_revision_anchors(self):
        evidence = self._neutral_regression_evidence_fixture()
        candidate_anchor = dict(evidence["case_anchors"]["candidate"])
        reference_anchor = dict(evidence["case_anchors"]["reference"])
        for anchor, label in ((candidate_anchor, "candidate"),
                              (reference_anchor, "reference")):
            anchor["source_path"] = (
                f"skills/code-review/evals/historical-{label}.json")
            anchor["source_hash"] = "sha256:" + label[0] * 64
            anchor["fixture_path"] = (
                f"skills/code-review/evals/fixtures/historical-{label}")
        evidence["case_anchors"] = {
            "candidate": candidate_anchor,
            "reference": reference_anchor,
        }
        evidence["fixture_source_path"] = reference_anchor["source_path"]
        evidence["fixture_path"] = reference_anchor["fixture_path"]
        evidence["fixture_source_hash"] = reference_anchor["source_hash"]
        with unittest.mock.patch.object(
                ve, "_regression_case_anchor",
                side_effect=[candidate_anchor, reference_anchor]):
            self.assertEqual(
                ve.validate_generic_regression_evidence(evidence), [])

    def test_neutral_regression_requires_bound_workspace_receipts(self):
        evidence = self._neutral_regression_evidence_fixture()
        evidence["repetitions"][0]["conditions"]["reference"][
            "workspace_receipt"] = "receipt-candidate"
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("workspace receipt does not match" in error
                            for error in errors), errors)

        evidence = self._neutral_regression_evidence_fixture()
        candidate_receipt_hash = evidence["repetitions"][0][
            "condition_workspace_receipt_hashes"]["candidate"]
        evidence["repetitions"][0]["conditions"]["reference"][
            "workspace_receipt_hash"] = candidate_receipt_hash
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("workspace receipt hash is not bound" in error
                            for error in errors), errors)

    def test_neutral_regression_rejects_forged_guidance_identity(self):
        evidence = self._neutral_regression_evidence_fixture()
        evidence["repetitions"][0]["conditions"]["reference"][
            "guidance_hash"] = "sha256:" + "f" * 64
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("guidance_hash does not match" in error
                            for error in errors), errors)

    def test_neutral_regression_accepts_adapter_declared_evidence(self):
        evidence = self._neutral_regression_evidence_fixture()
        for condition in evidence["repetitions"][0]["conditions"].values():
            condition["execution_attestation"]["confidence"] = "adapter_declared"
        self.assertEqual(ve.validate_generic_regression_evidence(evidence), [])

    def test_neutral_regression_attestation_layers_are_recomputed(self):
        evidence = self._neutral_regression_evidence_fixture()
        repetition = evidence["repetitions"][0]
        for name, condition in repetition["conditions"].items():
            condition["attestation_layers"] = eha.build_attestation_layers(
                condition,
                expected_receipt_hash=repetition[
                    "condition_workspace_receipt_hashes"][name],
                expected_guidance_id="code-review",
                expected_guidance_hash=condition["guidance_hash"],
                guided=True,
            )
        self.assertEqual(ve.validate_generic_regression_evidence(evidence), [])
        evidence["repetitions"][0]["conditions"]["candidate"][
            "attestation_layers"]["adapter_claims"]["guidance_loaded"] = False
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("adapter_claims.guidance_loaded" in error
                            for error in errors), errors)

    def test_neutral_regression_rejects_unverified_execution_claim(self):
        evidence = self._neutral_regression_evidence_fixture()
        for condition in evidence["repetitions"][0]["conditions"].values():
            condition["execution_attestation"]["confidence"] = "adapter_declared"
        evidence["execution_verified"] = True
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("execution_verified=true" in error for error in errors),
                        errors)

    def test_neutral_regression_accepts_runtime_verified_execution_claim(self):
        evidence = self._neutral_regression_evidence_fixture()
        for condition in evidence["repetitions"][0]["conditions"].values():
            attestation = condition["execution_attestation"]
            attestation["confidence"] = "runtime_verified"
            attestation["runtime_evidence"] = {
                "worker_id": condition["worker_id"],
                "session_id": condition["session_id"],
                "observation_hash": condition["execution_observation_hash"],
            }
        evidence["protocol"] = {
            "name": "regression", "execution_verified": True}
        self.assertEqual(ve.validate_generic_regression_evidence(evidence), [])

    def test_neutral_regression_rejects_forged_runtime_attestation(self):
        evidence = self._neutral_regression_evidence_fixture()
        attestation = evidence["repetitions"][0]["conditions"]["candidate"][
            "execution_attestation"]
        attestation["confidence"] = "runtime_verified"
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("runtime_evidence" in error for error in errors),
                        errors)

    def test_neutral_regression_requires_bound_execution_attestation(self):
        evidence = self._neutral_regression_evidence_fixture()
        evidence["repetitions"][0]["conditions"]["reference"][
            "execution_attestation"]["nonce"] = "wrong-nonce"
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("execution_attestation nonce is not bound" in error
                            for error in errors), errors)

    def test_neutral_regression_binds_observed_probes(self):
        evidence = self._neutral_regression_evidence_fixture()
        evidence["repetitions"][0]["conditions"]["reference"][
            "guidance_probe"] = "absent"
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("execution observation is not evaluator-bound" in error
                            for error in errors), errors)

    def test_neutral_regression_rejects_unanchored_metadata(self):
        skill = "code-review"
        evals_path = os.path.join(ROOT, "skills", skill, "evals", "evals.json")
        case = next(item for item in json.load(open(evals_path, encoding="utf-8"))["evals"]
                    if item["id"] == 5)
        expected_fixture = (case["fixture"].get("output_hash")
                            or case["fixture"].get("content_hash"))
        evidence = {
            "evidence_type": "regression",
            "protocol": "regression",
            "harness": {"adapter_protocol": eha.ADAPTER_PROTOCOL},
            "skill": skill,
            "case_id": 5,
            "candidate_revision": rsre.resolve_revision("HEAD"),
            "reference_revision": rsre.resolve_revision("HEAD"),
            "candidate_skill_source_path": "outside",
            "reference_skill_source_path": "skills/code-review",
            "candidate_skill_content_hash": "sha256:candidate",
            "reference_skill_content_hash": "sha256:reference",
            "conditions": ["candidate", "reference"],
            "expected_fixture_hash": expected_fixture,
            "fixture_source_path": "skills/code-review/evals/evals.json",
            "fixture_path": os.path.normpath(os.path.join(
                "skills/code-review", case["fixture"]["path"])),
            "fixture_source_hash": "sha256:source",
            "repetitions": [],
        }
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("candidate_skill_source_path" in error for error in errors), errors)

        evidence["candidate_skill_source_path"] = "skills/code-review"
        evidence["expected_fixture_hash"] = None
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("frozen content/output hash" in error for error in errors), errors)

        evidence["expected_fixture_hash"] = expected_fixture
        evidence["candidate_revision"] = "f" * 40
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("existing Git commit SHA" in error for error in errors), errors)
        self.assertTrue(any("INVALID_REPRODUCTION_ENVIRONMENT" in error
                            for error in errors), errors)

    def test_neutral_regression_v3_requires_immutable_metadata(self):
        evidence = self._neutral_regression_evidence_fixture()
        evidence.update({
            "result_schema_version": 3,
            "reproduction_status": "reproducible",
            "runner_version": rsre.REGRESSION_RUNNER_VERSION,
            "candidate_skill_hash": evidence["candidate_skill_content_hash"],
            "reference_skill_hash": evidence["reference_skill_content_hash"],
            "fixture_hash": evidence["expected_fixture_hash"],
            "case_set_hash": rsre.case_set_hash(
                evidence["case_anchors"]["candidate"],
                evidence["case_anchors"]["reference"]),
        })
        self.assertEqual(ve.validate_generic_regression_evidence(evidence), [])
        del evidence["runner_version"]
        errors = ve.validate_generic_regression_evidence(evidence)
        self.assertTrue(any("immutable metadata runner_version" in error
                            for error in errors), errors)

    def test_neutral_execution_rejects_unsafe_skill_name(self):
        errors = ve.validate_generic_execution_evidence({
            "evidence_type": "execution",
            "protocol": "qualification",
            "harness": {"adapter_protocol": eha.ADAPTER_PROTOCOL},
            "skill": "../code-review",
            "case_id": 1,
        })
        self.assertTrue(any("safe skill name" in error for error in errors), errors)

    def test_neutral_runner_rejects_external_placebo_skill(self):
        args = argparse.Namespace(
            skill="code-review",
            case_id=5,
            protocol="confirmation",
            conditions=["target", "baseline", "placebo"],
            placebo_skill="/tmp/external-guidance",
            model=None,
            reps=3,
        )
        with self.assertRaisesRegex(ValueError, "invalid placebo skill name"):
            rhe.build_evidence(args, object())


class EvidenceValidationTests(unittest.TestCase):
    def tearDown(self):
        reset()

    def _cond(self, name, cid, sid, **over):
        rep_id = over.pop("repetition_id", None)
        cond = {
            "repetition_id": rep_id if rep_id is not None else str(uuid.uuid4()),
            "container_id": cid, "session_id": sid,
            "run_status": "success", "returncode": 0,
            "starting_task_hash": "sha256:seed", "ending_task_hash": "sha256:z",
            "starting_full_hash": f"sha256:full-{name}",
            "ending_full_hash": f"sha256:end-{name}",
            "skill_probe": "present" if name != "baseline" else "absent",
            "output": f"{name} output", "stderr": "",
            "activation_mechanism": ("kilo-command-skill"
                                     if name != "baseline" else "none"),
            "skill_context_probe": ("present" if name != "baseline"
                                      else "none"),
            "skill_command": (f"{name}:skill" if name != "baseline" else None),
            "skill_kilo_path": (f".kilo/skills/{name}"
                                if name != "baseline" else None),
            "skill_content_hash": (f"sha256:{name}guidance"
                                   if name != "baseline" else None),
            "skill_tool_invoked": False,
            "activation_events": [],
        }
        cond.update(over)
        return cond

    def _exec_evidence(self, **over_rep):
        skill = "code-review"
        skill_dir = os.path.join(ROOT, "skills", skill)
        evals_path = os.path.join(skill_dir, "evals", "evals.json")
        source = json.load(open(evals_path))
        case = next(c for c in source["evals"] if c["id"] == 1)
        fixture_hash = case["fixture"]["content_hash"]
        target_hash = ree.skill_tree_hash(skill_dir)
        rep_id = str(uuid.uuid4())
        target = self._cond(
            skill, "cg", "sg", skill_content_hash=target_hash,
            starting_task_hash=fixture_hash, repetition_id=rep_id)
        baseline = self._cond("baseline", "cb", "sb",
                              starting_task_hash=fixture_hash, repetition_id=rep_id)
        rep = {
            "rep": 1,
            "repetition_id": rep_id,
            "workspace_path": "/work/task",
            "canonical_task_seed_hash": fixture_hash,
            "natural_task_hash": hashlib.sha256(
                case["prompt"].encode()).hexdigest(),
            "natural_task_identical_across_conditions": True,
            "condition_workspace_ids": {"target": "ws-target-1",
                                        "baseline": "ws-baseline-1"},
            "conditions": {"target": target, "baseline": baseline},
            "distinct_containers": True, "distinct_sessions": True,
            "starting_task_hashes_match": True,
            "task_hashes_match_canonical_seed": True,
            "workspace_paths_differ": True,
        }
        rep.update(over_rep)
        return {"evidence_type": "execution",
                "canonical_task_seed_hash": fixture_hash,
                "expected_fixture_hash": fixture_hash,
                "runtime_treatment_paths": [".kilo/skills"],
                "activation_mechanism": "kilo-command-skill",
                "target_skill_kilo_path": f".kilo/skills/{skill}",
                "target_skill_content_hash": target_hash,
                "conditions": ["target", "baseline"],
                "skill": skill,
                "case_id": 1,
                "fixture_source_path": "skills/code-review/evals/evals.json",
                "fixture_path": "skills/code-review/evals/files/case-1",
                "fixture_source_hash": "sha256:" + hashlib.sha256(
                    open(evals_path, "rb").read()).hexdigest(),
                "target_skill_source_path": "skills/code-review",
                "repetitions": [rep]}

    def _cat_evidence(self, present_reps, absent_reps):
        evals = json.load(open(os.path.join(
            ROOT, "skills", "code-review", "evals", "evals.json")))
        prompt = next(c for c in evals["evals"] if c["id"] == 1)["prompt"]
        for name, reps, absent in (("target_present", present_reps, None),
                                   ("target_absent", absent_reps,
                                    "code-review")):
            catalog = rc.render_catalog(rc.build_catalog(absent))
            catalog_hash = hashlib.sha256(catalog.encode()).hexdigest()
            prompt_hash = hashlib.sha256(
                rc.build_prompt(catalog, prompt).encode()).hexdigest()
            for rep in reps:
                rep["catalog_hash"] = catalog_hash
                rep["prompt_hash"] = prompt_hash
        return {"evidence_type": "catalog-routing", "skill": "code-review",
                "case_id": 1, "conditions": {
            "target_present": {"repetitions": present_reps},
            "target_absent": {"repetitions": absent_reps}}}

    def test_execution_evidence_valid(self):
        self.assertEqual(ve.validate_execution_evidence(self._exec_evidence()), [])

    def test_execution_evidence_shared_container_fails(self):
        ev = self._exec_evidence()
        ev["repetitions"][0]["conditions"]["target"]["container_id"] = "cb"
        self.assertTrue(any("distinct containers" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_baseline_leak_fails(self):
        # Baseline must not receive the target runtime treatment (no .kilo/skills).
        ev = self._exec_evidence()
        ev["repetitions"][0]["conditions"]["baseline"]["skill_probe"] = "present"
        self.assertTrue(any("baseline: skill_probe" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_baseline_runtime_path_fails(self):
        ev = self._exec_evidence()
        ev["repetitions"][0]["conditions"]["baseline"]["skill_kilo_path"] = \
            ".kilo/skills/target"
        self.assertTrue(any("baseline: skill_kilo_path" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_task_hash_mismatch_fails(self):
        # Real task-state difference between conditions (not treatment files)
        # must be rejected: task-state hashes exclude the .kilo treatment tree.
        ev = self._exec_evidence()
        ev["repetitions"][0]["conditions"]["baseline"]["starting_task_hash"] = \
            "sha256:other"
        self.assertTrue(any("TASK hash" in e or "differ" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_failed_run_rejected(self):
        # A failed Docker/Kilo run cannot be valid evidence.
        ev = self._exec_evidence()
        ev["repetitions"][0]["conditions"]["target"]["run_status"] = "failed"
        ev["repetitions"][0]["conditions"]["target"]["returncode"] = 1
        ev["repetitions"][0]["conditions"]["target"]["output"] = ""
        self.assertTrue(any("run_status" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_shared_workspace_rejected(self):
        # Target and baseline must use independent workspace ids.
        ev = self._exec_evidence()
        ev["repetitions"][0]["condition_workspace_ids"]["baseline"] = "ws-target-1"
        self.assertTrue(any("workspace ids" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_missing_target_skill_kilo_path_fails(self):
        ev = self._exec_evidence()
        del ev["target_skill_kilo_path"]
        self.assertTrue(any("target_skill_kilo_path" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_target_not_activated_fails(self):
        # P0-D: skill merely PRESENT (probe ok, file on disk) but NOT activated
        # through the controlled mechanism must be rejected: activation is the
        # evaluator-forced skill-command, not file presence.
        ev = self._exec_evidence()
        t = ev["repetitions"][0]["conditions"]["target"]
        t["activation_mechanism"] = "none"
        t["skill_command"] = None
        self.assertTrue(any("activation_mechanism" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_target_probe_mismatch_fails(self):
        ev = self._exec_evidence()
        ev["repetitions"][0]["conditions"]["target"]["skill_probe"] = "absent"
        self.assertTrue(any("target: skill_probe" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_target_event_wrong_skill_fails(self):
        # Another skill's invocation must not count as the target's activation.
        ev = self._exec_evidence()
        t = ev["repetitions"][0]["conditions"]["target"]
        t["skill_tool_invoked"] = True
        t["activation_events"] = [
            {"tool": "skill", "skill_name": "other-skill", "timestamp": 1,
             "session_id": "sg"}]
        self.assertTrue(any("names skill" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_placebo_valid(self):
        ev = self._exec_evidence()
        ev["conditions"] = ["target", "baseline", "placebo"]
        ev["placebo_skill"] = "security-review"
        ev["placebo_skill_kilo_path"] = ".kilo/skills/security-review"
        ev["placebo_skill_content_hash"] = ree.skill_tree_hash(
            os.path.join(ROOT, "skills", "security-review"))
        ev["repetitions"][0]["condition_workspace_ids"]["placebo"] = "ws-placebo-1"
        ev["repetitions"][0]["conditions"]["placebo"] = self._cond(
            "security-review", "cp", "sp",
            skill_content_hash=ev["placebo_skill_content_hash"],
            starting_task_hash=ev["expected_fixture_hash"],
            repetition_id=ev["repetitions"][0]["repetition_id"])
        self.assertEqual(ve.validate_execution_evidence(ev), [])

    def test_execution_evidence_placebo_not_activated_fails(self):
        # P0-D: the placebo must be activated through the SAME mechanism as the
        # target; a discoverable-but-not-activated placebo is rejected.
        ev = self._exec_evidence()
        ev["conditions"] = ["target", "baseline", "placebo"]
        ev["placebo_skill"] = "placebo"
        ev["placebo_skill_kilo_path"] = ".kilo/skills/placebo"
        ev["placebo_skill_content_hash"] = "sha256:placeboguidance"
        ev["repetitions"][0]["condition_workspace_ids"]["placebo"] = "ws-placebo-1"
        ev["repetitions"][0]["conditions"]["placebo"] = self._cond(
            "placebo", "cp", "sp", activation_mechanism="none",
            skill_command=None, skill_probe="absent")
        self.assertTrue(any("placebo: activation_mechanism" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_placebo_missing_path_fails(self):
        ev = self._exec_evidence()
        ev["conditions"] = ["target", "baseline", "placebo"]
        ev["placebo_skill"] = "placebo"
        ev["placebo_skill_kilo_path"] = ".kilo/skills/placebo"
        ev["placebo_skill_content_hash"] = "sha256:placeboguidance"
        ev["repetitions"][0]["condition_workspace_ids"]["placebo"] = "ws-placebo-1"
        # No placebo condition entry in the repetition -> evidence is missing a
        # declared condition (a placebo that never ran cannot be evidence).
        self.assertTrue(any("missing condition" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_missing_runtime_treatment_paths_fails(self):
        # P0-B: the validator must know which runtime paths were excluded from
        # the task-state hash; omitting the list is an error.
        ev = self._exec_evidence()
        del ev["runtime_treatment_paths"]
        self.assertTrue(any("runtime_treatment_paths" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_catalog_routing_evidence_valid(self):
        ev = self._cat_evidence(
            [{"rep": 1, "status": "success", "decision":
              {"selected_skill": "code-review", "action": "apply"},
              "match": True}],
            [{"rep": 1, "status": "success", "decision":
              {"selected_skill": None, "action": "clarify"}, "match": True}])
        self.assertEqual(ve.validate_catalog_routing_evidence(ev), [])

    def test_catalog_routing_evidence_missing_condition(self):
        ev = {"evidence_type": "catalog-routing",
              "conditions": {"target_present": {"repetitions": []}}}
        self.assertTrue(any("missing" in e
                            for e in ve.validate_catalog_routing_evidence(ev)))

    def test_catalog_failed_model_cannot_pass(self):
        # A failed model invocation must NOT be a null-selection pass.
        ev = self._cat_evidence(
            [{"rep": 1, "status": "success", "decision":
              {"selected_skill": "code-review", "action": "apply"}, "match": True}],
            # Model failed but someone marked match=True -> must be flagged.
            [{"rep": 1, "status": "failed", "error": "kilo exited 1",
              "decision": None, "match": True}])
        self.assertTrue(any("false pass" in e
                            for e in ve.validate_catalog_routing_evidence(ev)))

    def test_catalog_failed_model_recorded_as_failure(self):
        # The legitimate representation of a failure: status failed, match False.
        ev = self._cat_evidence(
            [{"rep": 1, "status": "success", "decision":
              {"selected_skill": "code-review", "action": "apply"}, "match": True}],
            [{"rep": 1, "status": "failed", "error": "no parseable decision",
              "decision": None, "match": False}])
        self.assertEqual(ve.validate_catalog_routing_evidence(ev), [])

    def test_catalog_invalid_decision_rejected(self):
        # null selection with action apply is invalid.
        ev = self._cat_evidence(
            [{"rep": 1, "status": "success", "decision":
              {"selected_skill": None, "action": "apply"}, "match": False}],
            [{"rep": 1, "status": "success", "decision":
              {"selected_skill": None, "action": "clarify"}, "match": True}])
        self.assertTrue(any("action 'apply'" in e
                            for e in ve.validate_catalog_routing_evidence(ev)))

    def test_catalog_absent_selection_and_match_are_rechecked(self):
        ev = self._cat_evidence(
            [{"rep": 1, "status": "success", "decision":
              {"selected_skill": "code-review", "action": "apply"},
              "match": True}],
            [{"rep": 1, "status": "success", "decision":
              {"selected_skill": "code-review", "action": "apply"},
              "match": True}])
        errs = ve.validate_catalog_routing_evidence(ev)
        self.assertTrue(any("not in the target_absent catalog" in e
                            for e in errs), errs)
        self.assertTrue(any("match does not match" in e for e in errs), errs)

    def test_catalog_stale_catalog_hash_rejected(self):
        ev = self._cat_evidence(
            [{"rep": 1, "status": "success", "decision":
              {"selected_skill": "code-review", "action": "apply"},
              "match": True}],
            [{"rep": 1, "status": "success", "decision":
              {"selected_skill": None, "action": "clarify"}, "match": True}])
        ev["conditions"]["target_present"]["repetitions"][0][
            "catalog_hash"] = "0" * 64
        errs = ve.validate_catalog_routing_evidence(ev)
        self.assertTrue(any("catalog_hash" in e for e in errs), errs)


class EvidenceDirDispatchTests(unittest.TestCase):
    """Defect 4 / 14A / 14G: --check-evidence must really inspect files and must
    not silently skip unknown or malformed evidence."""

    def tearDown(self):
        reset()

    def _run_check(self, files):
        d = tempfile.mkdtemp()
        try:
            for name, content in files.items():
                open(os.path.join(d, name), "w").write(content)
            ve.check_evidence_dir(d)
            return list(ve.errors)
        finally:
            shutil.rmtree(d, ignore_errors=True)
            ve.EVALS_DIR = os.path.join(ROOT, "docs", "evaluations")

    def _case_set_evidence(self, source_rel, case_id, selected):
        source_path = os.path.join(ROOT, source_rel)
        source = json.load(open(source_path))
        source_key = "confusion_set" if "confusion_set" in source else "holdout"
        source_name = source[source_key]
        recorded_cases = []
        for case in source["cases"]:
            turns = case.get("turns")
            case_selected = selected if case["id"] == case_id else None
            if turns:
                turn_results = []
                for i, turn in enumerate(turns, 1):
                    expected = turn["expected_route"]
                    turn_selected = (case_selected if case_selected is not None
                                     else expected)
                    turn_results.append({
                        "turn": i, "status": "success",
                        "expected_route": expected,
                        "expected_route_declared": True,
                        "selected_skill": turn_selected,
                        "action": "apply" if turn_selected else "clarify",
                        "pass": turn_selected == expected,
                    })
                repetitions = [{"rep": 1, "turns": turn_results}]
            else:
                expected = case.get("expected_skill")
                plain_selected = (case_selected if case_selected is not None
                                  else expected)
                repetitions = [{
                    "rep": 1, "status": "success",
                    "decision": {"selected_skill": plain_selected,
                                 "action": "apply" if plain_selected
                                 else "clarify"},
                    "match": plain_selected == expected,
                }]
            recorded_cases.append({
                "id": case["id"], "case_type": case.get("case_type"),
                "expected_skill": case.get("expected_skill"), "turns": turns,
                "repetitions": repetitions,
            })
        canonical = json.dumps(source, sort_keys=True,
                               separators=(",", ":"), ensure_ascii=False).encode()
        evidence = {
            "evidence_type": ("confusion-set" if source_key == "confusion_set"
                               else "holdout"),
            source_key: source_name,
            "case_set_path": source_rel,
            "case_set_hash": "sha256:" + hashlib.sha256(canonical).hexdigest(),
            "skills": source["skills"], "cases": recorded_cases,
        }
        evidence["aggregate"] = rc.build_aggregate(
            evidence["cases"], evidence["skills"])
        return evidence

    def test_malformed_exec_evidence_fails(self):
        # A malformed execution evidence file must cause validator failure.
        errs = self._run_check({
            "exec-bad.json": '{"evidence_type":"execution", "conditions":'
                             '["target","baseline"], "repetitions":[{"rep":1,'
                             '"conditions":{"target":{"container_id":"g"},'
                             '"baseline":{"container_id":"g"}}}]}'})
        self.assertTrue(any("distinct containers" in e for e in errs),
                        f"expected distinct-container failure, got {errs}")

    def test_unknown_evidence_type_rejected(self):
        errs = self._run_check({
            "weird.json": '{"evidence_type":"mystery","repetitions":[]}'})
        self.assertTrue(any("unknown evidence_type" in e for e in errs),
                        f"expected unknown-type error, got {errs}")

    def test_catalog_evidence_validated_via_dispatch(self):
        good = {"evidence_type": "catalog-routing", "conditions": {
            "target_present": {"repetitions": [
                {"rep": 1, "status": "success", "decision":
                 {"selected_skill": "code-review", "action": "apply"},
                 "match": True}]},
            "target_absent": {"repetitions": [
                {"rep": 1, "status": "success", "decision":
                 {"selected_skill": None, "action": "clarify"}, "match": True}]}}}
        good.update({"skill": "code-review", "case_id": 1})
        prompt = json.load(open(os.path.join(
            ROOT, "skills", "code-review", "evals", "evals.json")))
        prompt = next(c for c in prompt["evals"] if c["id"] == 1)["prompt"]
        for name, absent in (("target_present", None),
                             ("target_absent", "code-review")):
            catalog = rc.render_catalog(rc.build_catalog(absent))
            for rep in good["conditions"][name]["repetitions"]:
                rep["catalog_hash"] = hashlib.sha256(
                    catalog.encode()).hexdigest()
                rep["prompt_hash"] = hashlib.sha256(
                    rc.build_prompt(catalog, prompt).encode()).hexdigest()
        errs = self._run_check({"catalog-routing-x.json": json.dumps(good)})
        self.assertEqual(errs, [], errs)

    def test_case_set_evidence_validated_via_dispatch(self):
        # Confusion-set/holdout runners emit cases + aggregate, not the
        # legacy target-present/target-absent conditions shape.
        good = self._case_set_evidence(
            "evaluations/holdout/review-discrim-1.json", 1, "code-review")
        errs = self._run_check({"holdout-x.json": json.dumps(good)})
        self.assertEqual(errs, [], errs)

    def test_workflow_case_set_evidence_validated_via_dispatch(self):
        good = self._case_set_evidence(
            "evaluations/confusion-sets/review-family.json", 13,
            "review-feedback-resolution")
        errs = self._run_check({"confusion-set-x.json": json.dumps(good)})
        self.assertEqual(errs, [], errs)

    def test_case_set_stale_aggregate_rejected(self):
        good = self._case_set_evidence(
            "evaluations/holdout/review-discrim-1.json", 1, "code-review")
        good["aggregate"]["observations"] = 99
        errs = self._run_check({"holdout-stale.json": json.dumps(good)})
        self.assertTrue(any("aggregate does not match" in e for e in errs),
                        errs)

    def test_case_set_out_of_catalog_selection_rejected(self):
        good = self._case_set_evidence(
            "evaluations/holdout/review-discrim-1.json", 1,
            "not-in-catalog")
        errs = self._run_check({"holdout-membership.json": json.dumps(good)})
        self.assertTrue(any("not in catalog skills" in e for e in errs), errs)

    def test_case_set_stale_source_hash_rejected(self):
        good = self._case_set_evidence(
            "evaluations/holdout/review-discrim-1.json", 1, "code-review")
        good["case_set_hash"] = "sha256:" + "0" * 64
        errs = self._run_check({"holdout-stale-source.json": json.dumps(good)})
        self.assertTrue(any("case_set_hash" in e for e in errs), errs)


class GeneratorSeedTests(unittest.TestCase):
    """Defect 2 / 14E: generator source must never be worker-visible."""

    def tearDown(self):
        reset()

    def test_generator_seed_excludes_source(self):
        tmp = tempfile.mkdtemp()
        try:
            gendir = os.path.join(tmp, "gen")
            os.makedirs(gendir)
            open(os.path.join(gendir, "setup.sh"), "w").write(
                "#!/usr/bin/env bash\nset -e\n"
                "echo '# answer key: the defect is in auth.py' > LEAK.txt\n")
            seed, h = eh.materialize_fixture_seed(gendir, "generator",
                                                  "setup.sh", "bash setup.sh")
            self.assertFalse(os.path.exists(os.path.join(seed, "setup.sh")),
                             "generator source leaked into worker seed")
            self.assertTrue(os.path.exists(os.path.join(seed, "LEAK.txt")),
                            "generated task state missing from seed")
            self.assertTrue(h)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)



class GeneratorTests(unittest.TestCase):
    def tearDown(self):
        reset()

    def test_nondeterministic_generator_fails(self):
        tmp = tempfile.mkdtemp()
        try:
            src = os.path.join(tmp, "setup.sh")
            open(src, "w").write(
                "#!/usr/bin/env bash\nset -e\n"
                "echo \"$RANDOM\" > out.txt\n")
            with self.assertRaises(ValueError):
                eh.verify_generator_deterministic(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_deterministic_generator_ok(self):
        tmp = tempfile.mkdtemp()
        try:
            src = os.path.join(tmp, "setup.sh")
            open(src, "w").write(
                "#!/usr/bin/env bash\nset -e\necho 'static content' > out.txt\n")
            h = eh.verify_generator_deterministic(tmp)
            self.assertTrue(h)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_generator_invocation_is_shell_free(self):
        tmp = tempfile.mkdtemp()
        work = None
        try:
            open(os.path.join(tmp, "setup.sh"), "w").write(
                "#!/usr/bin/env bash\necho static > out.txt\n")
            with unittest.mock.patch.object(eh.subprocess, "check_call") as check_call:
                work, _ = eh.run_generator(tmp)
            check_call.assert_called_once()
            argv = check_call.call_args.args[0]
            self.assertEqual(argv, ["bash", "setup.sh"])
            self.assertFalse(check_call.call_args.kwargs["shell"])
            with self.assertRaisesRegex(ValueError, "no shell syntax"):
                eh.run_generator(tmp, "setup.sh", "bash setup.sh && touch pwned")
        finally:
            if work:
                shutil.rmtree(work, ignore_errors=True)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_fixture_source_hash_mismatch_fails(self):
        # Item 4: a changed generator source without an updated source_hash fails.
        tmp = tempfile.mkdtemp()
        try:
            skill_root = os.path.join(tmp, "skill")
            fxdir = os.path.join(skill_root, "files")
            os.makedirs(os.path.join(skill_root, "evals"))
            os.makedirs(fxdir)
            open(os.path.join(fxdir, "setup.sh"), "w").write(
                "#!/usr/bin/env bash\nset -e\necho hi > a.txt\n")
            fx = {"status": "ready", "type": "generator", "path": fxdir,
                  "source_hash": "sha256:" + "0" * 64,
                  "output_hash": "sha256:" + "0" * 64,
                  "content_hash": "sha256:" + "0" * 64}
            c = {"id": 1, "evaluation_modes": ["routing"], "fixture": fx}
            fx["path"] = "files"
            ve.check_fixture(os.path.join(skill_root, "evals", "evals.json"),
                             "skill/evals/evals.json", c, "x case 1")
            self.assertTrue(any("source_hash mismatch" in e for e in ve.errors))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_fixture_path_cannot_escape_skill_root(self):
        fx = {
            "status": "ready",
            "type": "committed",
            "path": "../../outside-fixture",
            "content_hash": "sha256:" + "0" * 64,
        }
        ve.check_fixture(
            os.path.join(ROOT, "skills", "code-review", "evals", "evals.json"),
            "skills/code-review/evals/evals.json",
            {"id": 1, "evaluation_modes": ["execution"], "fixture": fx},
            "code-review case 1",
        )
        self.assertTrue(any("must remain under the skill directory" in error
                            for error in ve.errors), ve.errors)

    def test_generator_git_hash_includes_untracked(self):
        # Item 3: the content hash must cover the full working tree (untracked files
        # included), not just the committed HEAD tree.
        tmp = tempfile.mkdtemp()
        try:
            open(os.path.join(tmp, "setup.sh"), "w").write(
                "#!/usr/bin/env bash\nset -e\n"
                "git init -q .\n"
                "git config user.email e@e.com\n"
                "git config user.name n\n"
                "echo tracked > tracked.txt\n"
                "git add tracked.txt\n"
                "git commit -q -m init\n"
                "echo untracked > untracked.txt\n")
            work, h1 = eh.run_generator(tmp)
            os.remove(os.path.join(work, "untracked.txt"))
            h2 = eh._generator_output_hash(work)
            shutil.rmtree(work, ignore_errors=True)
            self.assertNotEqual(h1, h2, "git generator hash ignored untracked file")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_generator_does_not_inherit_host_identity(self):
        tmp = tempfile.mkdtemp()
        try:
            src = os.path.join(tmp, "setup.sh")
            open(src, "w").write(
                "#!/usr/bin/env bash\nset -e\n"
                "echo \"${GIT_AUTHOR_EMAIL:-}<${USER:-}>\" > whoami.txt\n")
            work, _ = eh.run_generator(tmp)
            content = open(os.path.join(work, "whoami.txt")).read().strip()
            shutil.rmtree(work, ignore_errors=True)
            self.assertEqual(content, "<>", "generator leaked host identity: %r" % content)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_catalog_md_leak_in_fixture(self):
        tmp = tempfile.mkdtemp()
        try:
            skill_root = os.path.join(tmp, "skill")
            files = os.path.join(skill_root, "files")
            os.makedirs(os.path.join(skill_root, "evals"))
            os.makedirs(files)
            open(os.path.join(files, "catalog.md"), "w").write("leak")
            open(os.path.join(files, "x.txt"), "w").write("ok")
            c = base_case(1, "matching", ["routing", "execution"],
                          routing_context=routing_ctx(),
                          routing=routing_exp(),
                          execution=exec_exp(),
                          fixture={"status": "ready", "type": "committed",
                                   "path": "files",
                                   "content_hash": "sha256:" + "0" * 64})
            ve.check_case(os.path.join(skill_root, "evals", "evals.json"),
                          "skill/evals/evals.json", c)
            self.assertTrue(any("catalog.md" in e for e in ve.errors))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class CatalogCoverageTests(unittest.TestCase):
    def tearDown(self):
        reset()

    def test_skill_without_eval_set(self):
        # scenario 15: a skill dir with SKILL.md but no evals/evals.json
        tmp = tempfile.mkdtemp()
        try:
            skilldir = os.path.join(tmp, "skills", "ghost-skill")
            os.makedirs(skilldir)
            open(os.path.join(skilldir, "SKILL.md"), "w").write("---\nname: ghost-skill\n")
            ve.check_skill_coverage(set(), base=tmp)
            self.assertTrue(any("ghost-skill" in e and "no evals" in e for e in ve.errors))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_orphan_eval_set(self):
        # scenario 16: an evals.json whose skill_name is not a real skill directory
        tmp = tempfile.mkdtemp()
        try:
            skilldir = os.path.join(tmp, "skills", "real-skill")
            os.makedirs(os.path.join(skilldir, "evals"))
            open(os.path.join(skilldir, "SKILL.md"), "w").write("---\nname: real-skill\n")
            d = {"skill_name": "real-skill", "evals": [
                base_case(i, "matching", ["routing", "execution"],
                          routing_context=routing_ctx("real-skill"),
                          routing=routing_exp("real-skill"), execution=exec_exp())
                for i in range(1, 6)]}
            json.dump(d, open(os.path.join(skilldir, "evals", "evals.json"), "w"))
            # An orphan evals.json whose skill_name does not match its directory.
            d2 = dict(d, skill_name="nonexistent-skill")
            orphan_dir = os.path.join(tmp, "skills", "real-skill", "evals")
            json.dump(d2, open(os.path.join(orphan_dir, "orphan.json"), "w"))
            orig_glob = ve.SKILLS_GLOB
            orig_root = ve.ROOT
            ve.SKILLS_GLOB = os.path.join(tmp, "skills", "*", "evals", "*.json")
            ve.ROOT = tmp
            try:
                ve.check_eval_files()
            finally:
                ve.SKILLS_GLOB = orig_glob
                ve.ROOT = orig_root
            self.assertTrue(any("nonexistent-skill" in e and "skill_name" in e for e in ve.errors))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class CatalogTests(unittest.TestCase):
    def test_minimal_yaml_folded_scalar(self):
        d = brc.load_frontmatter("name: foo\ndescription: >-\n  line one\n  line two\n")
        self.assertEqual(d["name"], "foo")
        self.assertEqual(d["description"], "line one line two")

    def test_minimal_yaml_literal_scalar(self):
        d = brc.load_frontmatter("name: foo\ndescription: |\n  a\n  b\n")
        self.assertEqual(d["description"], "a\nb\n")

    def test_parse_frontmatter_reads_file(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "SKILL.md")
            open(p, "w").write(
                "---\nname: bar\ndescription: >-\n  multi line\n  description here\n---\nbody\n")
            name, desc = brc.parse_frontmatter(p)
            self.assertEqual(name, "bar")
            self.assertEqual(desc, "multi line description here")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_build_target_absent_removes_skill(self):
        # target-absent must drop ONLY the target skill from the catalog.
        all_rows = brc.build()
        names = [n for n, _ in all_rows]
        self.assertIn("code-review", names)
        absent_rows = brc.build(target_absent="code-review")
        absent_names = [n for n, _ in absent_rows]
        self.assertNotIn("code-review", absent_names)
        self.assertEqual(len(names), len(absent_names) + 1)


class CatalogRoutingDecisionTests(unittest.TestCase):
    """Defect 1 / 14B: a malformed/partial catalog-routing decision must never
    become a valid null-selection, and a selection must be valid against the exact
    catalog actually presented to the model."""

    def _cat(self, names):
        return set(names)

    def test_missing_selected_skill_rejected(self):
        r = rc.extract_decision('{"action": "clarify"}', self._cat(["code-review"]))
        self.assertEqual(r["status"], "failed")
        self.assertIn("selected_skill field missing", r["error"])

    def test_missing_action_rejected(self):
        r = rc.extract_decision('{"selected_skill": null}', self._cat(["code-review"]))
        self.assertEqual(r["status"], "failed")
        self.assertIn("action field missing", r["error"])

    def test_null_clarify_accepted(self):
        r = rc.extract_decision('{"selected_skill": null, "action": "clarify"}',
                                self._cat(["code-review"]))
        self.assertEqual(r["status"], "success")
        self.assertEqual(r["decision"]["selected_skill"], None)
        self.assertEqual(r["decision"]["action"], "clarify")

    def test_null_like_strings_are_not_json_null(self):
        for value in ("null", "none", "None", ""):
            with self.subTest(value=value):
                raw = json.dumps({"selected_skill": value, "action": "clarify"})
                r = rc.extract_decision(raw, self._cat(["code-review"]))
                self.assertEqual(r["status"], "failed")
                self.assertIn("not in supplied catalog", r["error"])

    def test_non_string_selected_skill_is_rejected(self):
        for value in ([], {}):
            with self.subTest(value=value):
                raw = json.dumps({"selected_skill": value, "action": "clarify"})
                r = rc.extract_decision(raw, self._cat(["code-review"]))
                self.assertEqual(r["status"], "failed")
                self.assertIn("string or null", r["error"])

    def test_null_apply_rejected(self):
        r = rc.extract_decision('{"selected_skill": null, "action": "apply"}',
                                self._cat(["code-review"]))
        self.assertEqual(r["status"], "failed")
        self.assertIn("action 'apply'", r["error"])

    def test_skill_apply_accepted(self):
        r = rc.extract_decision('{"selected_skill": "code-review", "action": "apply"}',
                                self._cat(["code-review"]))
        self.assertEqual(r["status"], "success")

    def test_skill_clarify_rejected(self):
        r = rc.extract_decision('{"selected_skill": "code-review", "action": "clarify"}',
                                self._cat(["code-review"]))
        self.assertEqual(r["status"], "failed")
        self.assertIn("action 'clarify'", r["error"])

    def test_unknown_catalog_skill_rejected(self):
        r = rc.extract_decision('{"selected_skill": "ghost", "action": "apply"}',
                                self._cat(["code-review"]))
        self.assertEqual(r["status"], "failed")
        self.assertIn("not in supplied catalog", r["error"])

    def test_absent_target_returned_anyway_rejected(self):
        # target-absent catalog omits the target; selecting it is rejected.
        r = rc.extract_decision('{"selected_skill": "code-review", "action": "apply"}',
                                self._cat(["other-skill"]))
        self.assertEqual(r["status"], "failed")
        self.assertIn("not in supplied catalog", r["error"])

    def test_malformed_json_rejected(self):
        r = rc.extract_decision('{"selected_skill": }', self._cat(["code-review"]))
        self.assertEqual(r["status"], "failed")
        self.assertIn("malformed", r["error"])

    def test_empty_output_rejected(self):
        r = rc.extract_decision('', self._cat(["code-review"]))
        self.assertEqual(r["status"], "failed")
        self.assertIn("no JSON decision", r["error"])

    def test_unknown_action_rejected(self):
        r = rc.extract_decision('{"selected_skill": null, "action": "bogus"}',
                                self._cat(["code-review"]))
        self.assertEqual(r["status"], "failed")
        self.assertIn("invalid action", r["error"])

    def test_failed_kilo_invocation_cannot_match(self):
        # A failed model invocation (non-zero exit, empty parseable decision)
        # must be recorded as status failed with no decision, never a pass.
        import subprocess
        fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
        with unittest.mock.patch("subprocess.run", return_value=fake):
            meta = rc.run_kilo("prompt", "model", "/tmp", "kilo",
                               self._cat(["code-review"]))
        self.assertEqual(meta["status"], "failed")
        self.assertIsNone(meta["decision"])

    def test_verify_host_kilo_uses_resolved_path_for_version(self):
        resolved = "/opt/homebrew/bin/kilo"
        with unittest.mock.patch.object(rc, "_kilo_path", return_value=resolved), \
                unittest.mock.patch.object(rc.os.path, "exists", return_value=True), \
                unittest.mock.patch.object(rc, "_host_kilo_version",
                                           return_value="kilo 1") as version, \
                unittest.mock.patch.object(rc.subprocess, "check_output",
                                           return_value="model\n") as check:
            self.assertTrue(rc._verify_host_kilo("model"))
        version.assert_called_once_with(resolved)
        check.assert_called_once_with([resolved, "models"], text=True, timeout=120)


class GeneratorHashSemanticsTests(unittest.TestCase):
    """Defect 2 / 14E: source_hash vs worker-visible output_hash semantics."""

    def tearDown(self):
        reset()

    def _git(self, cwd, *args, env=None):
        run_env = os.environ.copy()
        run_env.update({
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
        })
        if env:
            run_env.update(env)
        return subprocess.run(["git", *args], cwd=cwd, env=run_env,
                              check=True, capture_output=True, text=True)

    def _git_fixture(self, parent):
        root = os.path.join(parent, "fixture")
        os.makedirs(root)
        self._git(root, "init", "-q", "-b", "main")
        self._git(root, "config", "user.name", "Eval Bot")
        self._git(root, "config", "user.email", "eval@example.com")
        with open(os.path.join(root, "tracked.txt"), "w") as handle:
            handle.write("base\n")
        self._git(root, "add", "tracked.txt")
        self._git(root, "commit", "-q", "-m", "base")
        main_sha = self._git(root, "rev-parse", "HEAD").stdout.strip()

        origin = os.path.join(root, ".origin.git")
        self._git(root, "init", "-q", "--bare", origin)
        self._git(root, "remote", "add", "origin", "./.origin.git")
        self._git(root, "push", "-q", "-u", "origin", "main")
        self._git(root, "checkout", "-q", "-b", "feature")
        with open(os.path.join(root, "feature.txt"), "w") as handle:
            handle.write("feature\n")
        self._git(root, "add", "feature.txt")
        self._git(root, "commit", "-q", "-m", "feature")
        feature_sha = self._git(root, "rev-parse", "HEAD").stdout.strip()
        self._git(root, "push", "-q", "-u", "origin", "feature")
        self._git(root, "checkout", "-q", "main")
        return root, origin, main_sha, feature_sha

    def test_bare_remote_branch_change_changes_hash(self):
        tmp = tempfile.mkdtemp()
        try:
            root, origin, main_sha, feature_sha = self._git_fixture(tmp)
            h1 = eh.hash_workspace(root)
            self._git(origin, "update-ref", "refs/heads/feature", main_sha)
            self.assertNotEqual(h1, eh.hash_workspace(root))
            self._git(origin, "update-ref", "refs/heads/feature", feature_sha)
            self._git(origin, "symbolic-ref", "HEAD", "refs/heads/feature")
            self.assertNotEqual(h1, eh.hash_workspace(root))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_detached_bare_remote_head_target_changes_hash(self):
        tmp = tempfile.mkdtemp()
        try:
            root, origin, main_sha, feature_sha = self._git_fixture(tmp)
            h1 = eh.hash_workspace(root)
            self._git(origin, "update-ref", "--no-deref", "HEAD", feature_sha)
            h2 = eh.hash_workspace(root)
            self.assertNotEqual(h1, h2)
            self._git(origin, "update-ref", "--no-deref", "HEAD", main_sha)
            self.assertNotEqual(h2, eh.hash_workspace(root))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_configured_bare_remote_name_is_discovered(self):
        tmp = tempfile.mkdtemp()
        try:
            root, origin, main_sha, _feature_sha = self._git_fixture(tmp)
            named_origin = os.path.join(root, "origin")
            os.rename(origin, named_origin)
            self._git(root, "remote", "set-url", "origin", "./origin")
            h1 = eh.hash_workspace(root)
            self._git(named_origin, "config", "core.precomposeUnicode", "true")
            self.assertEqual(h1, eh.hash_workspace(root))
            self._git(named_origin, "update-ref", "refs/heads/feature", main_sha)
            self.assertNotEqual(h1, eh.hash_workspace(root))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_bare_remote_branch_addition_and_removal_change_hash(self):
        tmp = tempfile.mkdtemp()
        try:
            root, origin, main_sha, _feature_sha = self._git_fixture(tmp)
            h1 = eh.hash_workspace(root)
            self._git(origin, "update-ref", "refs/heads/new-feature", main_sha)
            h2 = eh.hash_workspace(root)
            self.assertNotEqual(h1, h2)
            self._git(origin, "update-ref", "-d", "refs/heads/feature")
            h3 = eh.hash_workspace(root)
            self.assertNotEqual(h2, h3)
            self.assertNotEqual(h1, h3)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_bare_remote_tag_change_changes_hash(self):
        tmp = tempfile.mkdtemp()
        try:
            root, origin, main_sha, feature_sha = self._git_fixture(tmp)
            self._git(origin, "update-ref", "refs/tags/v1", main_sha)
            h1 = eh.hash_workspace(root)
            self._git(origin, "update-ref", "refs/tags/v1", feature_sha)
            self.assertNotEqual(h1, eh.hash_workspace(root))
            self._git(origin, "update-ref", "-d", "refs/tags/v1")
            self.assertNotEqual(h1, eh.hash_workspace(root))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_bare_remote_config_noise_does_not_change_hash(self):
        tmp = tempfile.mkdtemp()
        try:
            root, origin, _main_sha, _feature_sha = self._git_fixture(tmp)
            h1 = eh.hash_workspace(root)
            self._git(origin, "config", "core.precomposeUnicode", "true")
            self.assertEqual(h1, eh.hash_workspace(root))
            self._git(origin, "config", "fixture.irrelevant", "noise")
            self.assertEqual(h1, eh.hash_workspace(root))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_working_upstream_change_changes_hash(self):
        tmp = tempfile.mkdtemp()
        try:
            root, _origin, _main_sha, _feature_sha = self._git_fixture(tmp)
            h1 = eh.hash_workspace(root)
            self._git(root, "config", "branch.main.remote", "upstream")
            self.assertNotEqual(h1, eh.hash_workspace(root))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_fixture_local_absolute_remote_paths_normalize(self):
        tmp = tempfile.mkdtemp()
        try:
            root, _origin, _main_sha, _feature_sha = self._git_fixture(tmp)
            root_copy = os.path.join(tmp, "other-fixture")
            self._git(root, "remote", "set-url", "origin",
                      os.path.join(root, ".origin.git"))
            shutil.copytree(root, root_copy)
            self._git(root_copy, "remote", "set-url", "origin",
                      os.path.join(root_copy, ".origin.git"))
            self.assertEqual(eh.hash_workspace(root), eh.hash_workspace(root_copy))
            self.assertEqual(
                eh._normalize_fixture_remote_url(
                    "https://github.com/foo/bar.git", root),
                "https://github.com/foo/bar.git",
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_bare_remote_hash_is_repeatable(self):
        tmp = tempfile.mkdtemp()
        try:
            root, _origin, _main_sha, _feature_sha = self._git_fixture(tmp)
            self.assertEqual(eh.hash_workspace(root), eh.hash_workspace(root))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_setup_sh_absent_from_worker_seed(self):
        tmp = tempfile.mkdtemp()
        try:
            gendir = os.path.join(tmp, "gen")
            os.makedirs(gendir)
            open(os.path.join(gendir, "setup.sh"), "w").write(
                "#!/usr/bin/env bash\nset -e\n"
                "echo 'answer key' > LEAK.txt\n")
            seed, h = eh.materialize_fixture_seed(gendir, "generator",
                                                  "setup.sh", "bash setup.sh")
            self.assertFalse(os.path.exists(os.path.join(seed, "setup.sh")))
            self.assertTrue(os.path.exists(os.path.join(seed, "LEAK.txt")))
            self.assertTrue(h)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_source_hash_covering_setup_sh(self):
        tmp = tempfile.mkdtemp()
        try:
            gendir = os.path.join(tmp, "gen")
            os.makedirs(gendir)
            open(os.path.join(gendir, "setup.sh"), "w").write("echo hi > a.txt\n")
            sh = eh.source_hash_of(os.path.join(gendir, "setup.sh"))
            # Changing setup.sh must change the source hash.
            open(os.path.join(gendir, "setup.sh"), "w").write("echo bye > a.txt\n")
            sh2 = eh.source_hash_of(os.path.join(gendir, "setup.sh"))
            self.assertNotEqual(sh, sh2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_output_hash_excludes_setup_sh(self):
        tmp = tempfile.mkdtemp()
        try:
            gendir = os.path.join(tmp, "gen")
            os.makedirs(gendir)
            open(os.path.join(gendir, "setup.sh"), "w").write(
                "#!/usr/bin/env bash\nset -e\necho static > out.txt\n")
            seed, h = eh.materialize_fixture_seed(gendir, "generator",
                                                  "setup.sh", "bash setup.sh")
            # The hash must be derived from the worker-visible files only, so adding
            # (or here, the absence of) setup.sh in the seed is irrelevant because
            # it is already stripped; recompute via committed_hash of the seed.
            h2 = eh.committed_hash(seed)
            # canonical_hash(generator) must equal the worker-visible seed hash.
            ch = eh.canonical_hash(gendir, "generator", "setup.sh", "bash setup.sh")
            self.assertEqual(ch, h)
            self.assertEqual(ch, h2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_modifying_generated_output_changes_output_hash(self):
        tmp = tempfile.mkdtemp()
        try:
            gendir = os.path.join(tmp, "gen")
            os.makedirs(gendir)
            open(os.path.join(gendir, "setup.sh"), "w").write(
                "#!/usr/bin/env bash\nset -e\necho one > out.txt\n")
            h1 = eh.canonical_hash(gendir, "generator", "setup.sh", "bash setup.sh")
            open(os.path.join(gendir, "setup.sh"), "w").write(
                "#!/usr/bin/env bash\nset -e\necho two > out.txt\n")
            h2 = eh.canonical_hash(gendir, "generator", "setup.sh", "bash setup.sh")
            self.assertNotEqual(h1, h2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_deterministic_worker_seed_hash(self):
        tmp = tempfile.mkdtemp()
        try:
            gendir = os.path.join(tmp, "gen")
            os.makedirs(gendir)
            open(os.path.join(gendir, "setup.sh"), "w").write(
                "#!/usr/bin/env bash\nset -e\necho static > out.txt\n")
            h1 = eh.canonical_hash(gendir, "generator", "setup.sh", "bash setup.sh")
            h2 = eh.canonical_hash(gendir, "generator", "setup.sh", "bash setup.sh")
            self.assertEqual(h1, h2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_canonical_seed_equals_frozen_hash(self):
        # canonical_hash(generator) is what hash_fixtures.py records as the frozen
        # output_hash/content_hash; materialize_fixture_seed must reproduce it.
        tmp = tempfile.mkdtemp()
        try:
            gendir = os.path.join(tmp, "gen")
            os.makedirs(gendir)
            open(os.path.join(gendir, "setup.sh"), "w").write(
                "#!/usr/bin/env bash\nset -e\necho static > out.txt\n")
            frozen = eh.canonical_hash(gendir, "generator", "setup.sh", "bash setup.sh")
            seed, runtime = eh.materialize_fixture_seed(gendir, "generator",
                                                       "setup.sh", "bash setup.sh")
            self.assertEqual(runtime, frozen)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ExecutionEvidenceAnchorTests(unittest.TestCase):
    """Execution evidence must anchor to the frozen fixture hash, record the
    runtime-treatment exclusion list, and freeze the injected guidance tree."""

    def tearDown(self):
        reset()

    def _ev(self, **over):
        evals_path = os.path.join(ROOT, "skills", "code-review", "evals",
                                  "evals.json")
        source = json.load(open(evals_path))
        case = next(c for c in source["evals"] if c["id"] == 1)
        fixture_hash = case["fixture"]["content_hash"]
        target_hash = ree.skill_tree_hash(
            os.path.join(ROOT, "skills", "code-review"))
        source_hash = "sha256:" + hashlib.sha256(
            open(evals_path, "rb").read()).hexdigest()
        rep_id = str(uuid.uuid4())
        ev = {
            "evidence_type": "execution",
            "canonical_task_seed_hash": fixture_hash,
            "expected_fixture_hash": fixture_hash,
            "fixture_source_path": "skills/code-review/evals/evals.json",
            "fixture_path": "skills/code-review/evals/files/case-1",
            "fixture_source_hash": source_hash,
            "target_skill_source_path": "skills/code-review",
            "runtime_treatment_paths": [".kilo/skills"],
            "activation_mechanism": "kilo-command-skill",
            "target_skill_kilo_path": ".kilo/skills/code-review",
            "target_skill_content_hash": target_hash,
            "conditions": ["target", "baseline"],
            "skill": "code-review",
            "case_id": 1,
            "repetitions": [{
                "rep": 1,
                "repetition_id": rep_id,
                "canonical_task_seed_hash": fixture_hash,
                "natural_task_hash": hashlib.sha256(
                    case["prompt"].encode()).hexdigest(),
                "natural_task_identical_across_conditions": True,
                "condition_workspace_ids": {"target": "ws-target-1",
                                            "baseline": "ws-baseline-1"},
                "conditions": {
                    "target": {"repetition_id": rep_id, "container_id": "cg", "session_id": "sg",
                               "run_status": "success", "returncode": 0,
                               "skill_probe": "present",
                               "skill_context_probe": "present",
                               "starting_task_hash": fixture_hash,
                               "ending_task_hash": "sha256:g",
                               "starting_full_hash": "sha256:f1",
                               "ending_full_hash": "sha256:f2",
                               "output": "out", "stderr": "",
                               "activation_mechanism": "kilo-command-skill",
                               "skill_command": "code-review:skill",
                               "skill_kilo_path": ".kilo/skills/code-review",
                               "skill_content_hash": target_hash,
                               "skill_tool_invoked": False,
                               "activation_events": []},
                    "baseline": {"repetition_id": rep_id, "container_id": "cb", "session_id": "sb",
                                 "run_status": "success", "returncode": 0,
                                 "skill_probe": "absent",
                                 "skill_context_probe": "none",
                                 "starting_task_hash": fixture_hash,
                                 "ending_task_hash": "sha256:h",
                                 "starting_full_hash": "sha256:f3",
                                 "ending_full_hash": "sha256:f4",
                                 "output": "out", "stderr": "",
                                 "activation_mechanism": "none",
                                 "skill_command": None,
                                 "skill_kilo_path": None,
                                 "skill_content_hash": None,
                                 "skill_tool_invoked": False,
                                 "activation_events": []},
                },
                "distinct_containers": True, "distinct_sessions": True,
                "starting_task_hashes_match": True,
                "task_hashes_match_canonical_seed": True,
                "workspace_paths_differ": True,
            }],
        }
        ev.update(over)
        return ev

    def test_valid_with_anchored_hash(self):
        self.assertEqual(ve.validate_execution_evidence(self._ev()), [])

    def test_natural_task_hash_mismatch_rejected(self):
        ev = self._ev()
        ev["repetitions"][0]["natural_task_hash"] = "0" * 64
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("current source eval case prompt" in e
                            for e in errs), errs)

    def test_stale_natural_task_hash_rejected_after_prompt_change(self):
        # A hash from an older prompt must not remain valid merely because it is
        # well-formed; the validator anchors it to today's source eval case.
        ev = self._ev()
        ev["repetitions"][0]["natural_task_hash"] = hashlib.sha256(
            b"historical prompt text").hexdigest()
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("stale or mismatched task" in e for e in errs), errs)

    def test_missing_expected_fixture_hash_rejected(self):
        ev = self._ev()
        del ev["expected_fixture_hash"]
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("expected_fixture_hash" in e for e in errs), errs)

    def test_missing_runtime_treatment_paths_rejected(self):
        # P0-B: the validator must be able to prove WHICH paths the task-state
        # hash excluded; omitting the list is a schema error.
        ev = self._ev()
        del ev["runtime_treatment_paths"]
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("runtime_treatment_paths" in e for e in errs), errs)

    def test_runtime_treatment_paths_must_match_canonical_runner(self):
        for paths in ([".kilo/skills", "src"], [".kilo/skills", "tests"],
                      [".kilo"], []):
            with self.subTest(paths=paths):
                ev = self._ev(runtime_treatment_paths=paths)
                errs = ve.validate_execution_evidence(ev)
                self.assertTrue(any("runtime_treatment_paths" in e
                                    for e in errs), (paths, errs))

    def test_frozen_hash_mismatch_rejected(self):
        # The conditions start from identical task copies, but the canonical
        # seed does not match the frozen expected hash -> evidence rejected.
        ev = self._ev(expected_fixture_hash="sha256:wrong")
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("frozen" in e or "expected_fixture_hash" in e
                            for e in errs), errs)


class PreflightReferencesTests(unittest.TestCase):
    """Defect 4 / 14D: the docker references probe must fail when required
    references are missing."""

    def test_refs_expected_and_present(self):
        script = dip.probe_script("code-review", "abc", guidance_present=True,
                                  refs_expected=True)
        self.assertIn("references_present_if_required", script)
        # required + present -> the check succeeds inline (true)
        self.assertIn('references_present_if_required" true', script)

    def test_refs_expected_and_absent_fails(self):
        # When references are required, the absent branch must be compiled so that
        # a missing references directory fails (required=true).
        script = dip.probe_script("code-review", "abc", guidance_present=True,
                                  refs_expected=True)
        self.assertIn('[ "true" = "true" ]', script)
        self.assertNotIn("references_available", script)

    def test_refs_not_expected_and_absent_passes(self):
        script = dip.probe_script("code-review", "abc", guidance_present=True,
                                  refs_expected=False)
        # When references are not required, the absent branch must pass (true).
        self.assertIn('[ "false" = "true" ]', script)


class ConfusionSetAndHoldoutTests(unittest.TestCase):
    """Confusion sets + holdouts: schema, keyword-leak rejection, workflow
    transition turns, counterfactual placement."""

    def tearDown(self):
        reset()

    def _confusion(self, **over):
        d = {
            "confusion_set": "review-family",
            "cluster": "review",
            "skills": ["code-review", "security-review"],
            "cases": [
                {"id": 1, "case_type": "hard-negative",
                 "prompt": "This PR changes how access tokens are checked. "
                           "Is the change correct and mergeable?",
                 "expected_skill": "code-review"},
            ],
        }
        d.update(over)
        return d

    def _write(self, tmp, name, data):
        p = os.path.join(tmp, name)
        json.dump(data, open(p, "w"))
        return p

    def test_valid_confusion_set(self):
        tmp = tempfile.mkdtemp()
        try:
            p = self._write(tmp, "review.json", self._confusion())
            ve.check_confusion_set(p, "evaluations/confusion-sets/review.json")
            self.assertEqual(ve.errors, [], ve.errors)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_prompt_with_expected_skill_name_rejected(self):
        # The prompt contains "code-review" verbatim -> keyword leak.
        d = self._confusion()
        d["cases"][0]["prompt"] = "Please run code-review on this diff."
        tmp = tempfile.mkdtemp()
        try:
            p = self._write(tmp, "review.json", d)
            ve.check_confusion_set(p, "evaluations/confusion-sets/review.json")
            self.assertTrue(any("keyword leak" in e for e in ve.errors),
                            ve.errors)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_expected_skill_must_be_in_set(self):
        d = self._confusion()
        d["cases"][0]["expected_skill"] = "threat-modeling"
        tmp = tempfile.mkdtemp()
        try:
            p = self._write(tmp, "review.json", d)
            ve.check_confusion_set(p, "evaluations/confusion-sets/review.json")
            self.assertTrue(any("not in the confusion set" in e for e in ve.errors))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_workflow_transition_needs_turns(self):
        d = self._confusion()
        d["cases"][0]["case_type"] = "workflow-transition"
        tmp = tempfile.mkdtemp()
        try:
            p = self._write(tmp, "review.json", d)
            ve.check_confusion_set(p, "evaluations/confusion-sets/review.json")
            self.assertTrue(any("workflow-transition case must carry"
                                in e for e in ve.errors))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_nonworkflow_turns_rejected(self):
        d = self._confusion()
        d["cases"][0]["turns"] = [{"user": "follow-up",
                                    "expected_route": "code-review"}]
        tmp = tempfile.mkdtemp()
        try:
            p = self._write(tmp, "review.json", d)
            ve.check_confusion_set(p, "evaluations/confusion-sets/review.json")
            self.assertTrue(any("turns are only valid" in e for e in ve.errors),
                            ve.errors)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_workflow_transition_with_turns_ok(self):
        d = self._confusion()
        d["cases"] = [{
            "id": 1, "case_type": "workflow-transition",
            "prompt": "Look at this subsystem and tell me whether the design "
                      "is why every change touches the same five modules.",
            "turns": [
                {"user": "Can you tell me whether the design is the problem?",
                 "expected_route": "architecture-review"},
                {"user": "Option B sounds right. Plan the change.",
                 "expected_route": "implementation-planning"},
            ],
        }]
        d["skills"] = ["architecture-review", "implementation-planning"]
        d["cases"][0]["expected_skill"] = "architecture-review"
        tmp = tempfile.mkdtemp()
        try:
            p = self._write(tmp, "design.json", d)
            ve.check_confusion_set(p, "evaluations/confusion-sets/design.json")
            self.assertEqual(ve.errors, [], ve.errors)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_workflow_transition_route_not_in_skills_rejected(self):
        d = self._confusion()
        d["cases"] = [{
            "id": 1, "case_type": "workflow-transition",
            "prompt": "p",
            "turns": [
                {"user": "u1", "expected_route": "architecture-review"},
                {"user": "u2", "expected_route": "quality-hardening"},
            ],
        }]
        d["skills"] = ["architecture-review", "implementation-planning"]
        tmp = tempfile.mkdtemp()
        try:
            p = self._write(tmp, "design.json", d)
            ve.check_confusion_set(p, "evaluations/confusion-sets/design.json")
            self.assertTrue(any("not in the confusion set's skills" in e
                                for e in ve.errors), ve.errors)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_counterfactual_inside_skill_pack_rejected(self):
        # A counterfactual case must live in a confusion set, never in a
        # skill's own eval pack (its paired member would be visible there).
        c = base_case(1, "edge", ["catalog-routing"],
                      case_type="counterfactual",
                      counterfactual_pair="pair-1",
                      routing_context=routing_ctx(),
                      routing=routing_exp())
        ve.check_case(fake_path(), "skills/foo/evals/evals.json", c)
        self.assertTrue(any("must live in a confusion-set" in e
                            for e in ve.errors), ve.errors)

    def test_counterfactual_missing_pair_rejected(self):
        c = base_case(1, "edge", ["catalog-routing"],
                      case_type="counterfactual",
                      routing_context=routing_ctx(),
                      routing=routing_exp())
        ve.check_case("evaluations/confusion-sets/x.json",
                      "evaluations/confusion-sets/x.json", c)
        self.assertTrue(any("counterfactual_pair" in e for e in ve.errors))

    def test_counterfactual_in_confusion_set_ok(self):
        d = self._confusion()
        d["cases"] = [{
            "id": 1, "case_type": "counterfactual",
            "counterfactual_pair": "restructure-1",
            "prompt": "These modules have become tangled. Should we "
                      "restructure them?",
            "expected_skill": "architecture-review",
        }]
        d["skills"] = ["architecture-review", "implementation-planning"]
        tmp = tempfile.mkdtemp()
        try:
            p = self._write(tmp, "design.json", d)
            ve.check_confusion_set(p, "evaluations/confusion-sets/design.json")
            self.assertEqual(ve.errors, [], ve.errors)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_holdout_valid(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "review-holdout.json")
            json.dump({"holdout": "review-holdout-1", "skills": [
                "code-review", "architecture-review"
            ], "cases": [
                {"id": 1, "prompt": "Is this auth change correct?",
                 "expected_skill": "code-review"},
            ]}, open(p, "w"))
            ve.check_holdout(p, "evaluations/holdout/review-holdout.json")
            self.assertEqual(ve.errors, [], ve.errors)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_holdout_missing_expected_skill(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "h.json")
            json.dump({"holdout": "h", "cases": [
                {"id": 1, "prompt": "x"},
            ]}, open(p, "w"))
            ve.check_holdout(p, "evaluations/holdout/h.json")
            self.assertTrue(any("expected_skill" in e for e in ve.errors))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_confusion_set_null_expected_skill_ambiguous_ok(self):
        """ambiguous-natural cases may have expected_skill=null."""
        d = self._confusion()
        d["cases"][0] = {
            "id": 1, "case_type": "ambiguous-natural",
            "prompt": "Is this a security problem or just a bug? No way to tell.",
            "expected_skill": None,
        }
        tmp = tempfile.mkdtemp()
        try:
            p = self._write(tmp, "review.json", d)
            ve.check_confusion_set(p, "evaluations/confusion-sets/review.json")
            self.assertEqual(ve.errors, [], ve.errors)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_confusion_set_null_expected_skill_non_ambiguous_rejected(self):
        """expected_skill=null is only valid for ambiguous-natural cases."""
        d = self._confusion()
        d["cases"][0]["case_type"] = "hard-negative"
        d["cases"][0]["expected_skill"] = None
        d["cases"][0]["prompt"] = "A vague request with no clear owner."
        tmp = tempfile.mkdtemp()
        try:
            p = self._write(tmp, "review.json", d)
            ve.check_confusion_set(p, "evaluations/confusion-sets/review.json")
            self.assertTrue(any("null only valid for" in e for e in ve.errors))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_confusion_set_null_expected_skill_no_keyword_leak_check(self):
        """When expected_skill is null, the keyword-leak check must not crash."""
        d = self._confusion()
        d["cases"][0] = {
            "id": 1, "case_type": "ambiguous-natural",
            "prompt": "Too little evidence to decide.",
            "expected_skill": None,
        }
        tmp = tempfile.mkdtemp()
        try:
            p = self._write(tmp, "review.json", d)
            ve.check_confusion_set(p, "evaluations/confusion-sets/review.json")
            self.assertEqual(ve.errors, [], ve.errors)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_holdout_null_expected_skill_ambiguous_ok(self):
        """Holdout ambiguous-natural cases may have expected_skill=null."""
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "h.json")
            json.dump({"holdout": "h", "cases": [
                {"id": 1, "case_type": "ambiguous-natural",
                 "prompt": "Unclear what to do.", "expected_skill": None},
            ]}, open(p, "w"))
            ve.check_holdout(p, "evaluations/holdout/h.json")
            self.assertEqual(ve.errors, [], ve.errors)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_holdout_null_expected_skill_non_ambiguous_rejected(self):
        """Holdout: expected_skill=null only valid for ambiguous-natural."""
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "h.json")
            json.dump({"holdout": "h", "cases": [
                {"id": 1, "case_type": "hard-negative",
                 "prompt": "x", "expected_skill": None},
            ]}, open(p, "w"))
            ve.check_holdout(p, "evaluations/holdout/h.json")
            self.assertTrue(any("null only valid" in e for e in ve.errors))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class AssertionTypeTests(unittest.TestCase):
    """Assertions may be plain strings (legacy) or typed objects; typed
    assertions must declare behavioral/quality/presentation."""

    def tearDown(self):
        reset()

    def test_typed_assertions_valid(self):
        c = base_case(5, "edge", ["execution"],
                      execution={"expected_output": "out", "assertions": [
                          {"text": "did not merge", "type": "behavioral"},
                          {"text": "explains evidence clearly",
                           "type": "quality"},
                          {"text": "uses a matrix", "type": "presentation"},
                      ]})
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertEqual(ve.errors, [], ve.errors)

    def test_assertion_object_missing_type_rejected(self):
        c = base_case(5, "edge", ["execution"],
                      execution={"expected_output": "out", "assertions": [
                          {"text": "did not merge"},
                      ]})
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertTrue(any("missing 'type'" in e for e in ve.errors))

    def test_assertion_bad_type_rejected(self):
        c = base_case(5, "edge", ["execution"],
                      execution={"expected_output": "out", "assertions": [
                          {"text": "x", "type": "hard"},
                      ]})
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertTrue(any("bad assertion type" in e for e in ve.errors))

    def test_assertion_object_missing_text_rejected(self):
        c = base_case(5, "edge", ["execution"],
                      execution={"expected_output": "out", "assertions": [
                          {"type": "behavioral"},
                      ]})
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertTrue(any("missing 'text'" in e for e in ve.errors))

    def test_placeholder_guidance_only_for_designed_only(self):
        c = base_case(5, "edge", ["execution"],
                      execution={"expected_output": "out",
                                 "assertions": ["a"],
                                 "placeholder_guidance": "Tier-1 dev smoke: "
                                 "the worker has no fixture yet."},
                      fixture={"status": "designed_only"})
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertEqual(ve.errors, [], ve.errors)

    def test_placeholder_guidance_with_ready_fixture_rejected(self):
        c = base_case(5, "edge", ["execution"],
                      execution={"expected_output": "out",
                                 "assertions": ["a"],
                                 "placeholder_guidance": "not allowed here"},
                      fixture={"status": "ready", "type": "committed",
                               "path": "evals/files/x",
                               "content_hash": "sha256:" + "0" * 64})
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertTrue(any("placeholder_guidance" in e for e in ve.errors))


class CaseTypeTests(unittest.TestCase):
    def tearDown(self):
        reset()

    def _case(self, ctype, **extra):
        return base_case(1, "matching", ["catalog-routing"],
                         case_type=ctype,
                         routing_context=routing_ctx(),
                         routing=routing_exp(), **extra)

    def test_smoke_default_ok(self):
        # Legacy cases without case_type default to smoke.
        c = base_case(1, "matching", ["catalog-routing"],
                      routing_context=routing_ctx(), routing=routing_exp())
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertEqual(ve.errors, [], ve.errors)

    def test_discriminator_ok(self):
        ve.check_case(fake_path(), "x/evals.json", self._case("discriminator"))
        self.assertEqual(ve.errors, [], ve.errors)

    def test_misleading_keyword_ok(self):
        ve.check_case(fake_path(), "x/evals.json",
                      self._case("misleading-keyword"))
        self.assertEqual(ve.errors, [], ve.errors)

    def test_bad_case_type_rejected(self):
        ve.check_case(fake_path(), "x/evals.json", self._case("easy"))
        self.assertTrue(any("bad case_type" in e for e in ve.errors))

    def test_multi_turn_case_requires_workflow_type(self):
        c = self._case("discriminator", turns=[{"user": "hi"}])
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertTrue(any("workflow-transition" in e for e in ve.errors))

    def test_turn_missing_user_rejected(self):
        c = self._case("workflow-transition",
                       turns=[{"expected_route": "code-review"}])
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertTrue(any("turn 1" in e for e in ve.errors))


class ExecutionEvidenceV2Tests(unittest.TestCase):
    """Execution evidence: controlled activation mechanism, identical natural
    task, target/baseline/placebo conditions, task-vs-runtime hashing."""

    def tearDown(self):
        reset()

    def _evidence(self, **over):
        evals_path = os.path.join(ROOT, "skills", "code-review", "evals",
                                  "evals.json")
        source = json.load(open(evals_path))
        case = next(c for c in source["evals"] if c["id"] == 1)
        fixture_hash = case["fixture"]["content_hash"]
        target_hash = ree.skill_tree_hash(
            os.path.join(ROOT, "skills", "code-review"))
        source_hash = "sha256:" + hashlib.sha256(
            open(evals_path, "rb").read()).hexdigest()
        rep_id = str(uuid.uuid4())
        cond = {
            "repetition_id": rep_id,
            "container_id": "c", "session_id": "s",
            "run_status": "success", "returncode": 0,
            "skill_probe": "present",
            "skill_context_probe": "present",
            "starting_task_hash": fixture_hash,
            "ending_task_hash": "sha256:after",
            "starting_full_hash": "sha256:f1", "ending_full_hash": "sha256:f2",
                "output": "worker output", "stderr": "",
            "activation_mechanism": "kilo-command-skill",
            "skill_command": "code-review:skill",
            "skill_kilo_path": ".kilo/skills/code-review",
            "skill_content_hash": target_hash,
            "skill_tool_invoked": False, "activation_events": []}
        baseline = dict(cond, container_id="cb", session_id="sb",
                        repetition_id=rep_id,
                        skill_probe="absent", skill_context_probe="none",
                        starting_full_hash="sha256:f3",
                        ending_full_hash="sha256:f4",
                        activation_mechanism="none",
                        skill_command=None,
                        skill_kilo_path=None,
                        skill_content_hash=None,
                        skill_tool_invoked=False,
                        activation_events=[])
        placebo_skill = over.get('placebo_skill')
        placebo_hash = (ree.skill_tree_hash(
            os.path.join(ROOT, "skills", placebo_skill))
                        if placebo_skill else None)
        ev = {
            "evidence_type": "execution",
            "canonical_task_seed_hash": fixture_hash,
            "expected_fixture_hash": fixture_hash,
            "fixture_source_path": "skills/code-review/evals/evals.json",
            "fixture_path": "skills/code-review/evals/files/case-1",
            "fixture_source_hash": source_hash,
            "target_skill_source_path": "skills/code-review",
            "runtime_treatment_paths": [".kilo/skills"],
            "activation_mechanism": "kilo-command-skill",
            "target_skill_kilo_path": ".kilo/skills/code-review",
            "target_skill_content_hash": target_hash,
            "placebo_skill_kilo_path": (".kilo/skills/" + placebo_skill)
                if placebo_skill else None,
            "placebo_skill_content_hash":
                placebo_hash,
            "conditions": ["target", "baseline"],
            "placebo_skill": None,
            "skill": "code-review",
            "case_id": 1,
            "repetitions": [{
                "rep": 1,
                "repetition_id": rep_id,
                "canonical_task_seed_hash": fixture_hash,
                "natural_task_hash": hashlib.sha256(
                    case["prompt"].encode()).hexdigest(),
                "natural_task_identical_across_conditions": True,
                "condition_workspace_ids": {"target": "ws-t", "baseline": "ws-b"},
                "conditions": {"target": cond, "baseline": baseline},
                "distinct_containers": True, "distinct_sessions": True,
                "starting_task_hashes_match": True,
                "task_hashes_match_canonical_seed": True,
                "workspace_paths_differ": True,
            }],
        }
        ev.update(over)
        return ev

    def test_valid_v2(self):
        self.assertEqual(ve.validate_execution_evidence(self._evidence()), [])

    def test_task_hash_includes_no_treatment_paths_fails(self):
        # P0-B: the target's starting TASK hash must equal the canonical seed
        # even though the target workspace carries the .kilo treatment tree;
        # if someone hashed the treatment INTO the task hash, the evidence
        # cannot claim identical task state.
        ev = self._evidence()
        ev["repetitions"][0]["conditions"]["target"]["starting_task_hash"] = \
            "sha256:with-treatment"
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("TASK hash" in e or "differ" in e for e in errs),
                        errs)

    def test_missing_identical_task_hash_rejected(self):
        ev = self._evidence()
        del ev["repetitions"][0]["natural_task_hash"]
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("natural_task_hash" in e for e in errs), errs)

    def test_conditions_share_container_rejected(self):
        ev = self._evidence()
        ev["repetitions"][0]["conditions"]["baseline"]["container_id"] = "c"
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("distinct containers" in e for e in errs), errs)

    def test_baseline_treatment_present_rejected(self):
        ev = self._evidence()
        ev["repetitions"][0]["conditions"]["baseline"]["skill_probe"] = "present"
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("baseline: skill_probe" in e for e in errs), errs)

    def test_missing_condition_rejected(self):
        ev = self._evidence(conditions=["target", "baseline", "placebo"])
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("missing condition" in e for e in errs), errs)

    def test_placebo_requires_placebo_skill(self):
        ev = self._evidence(conditions=["target", "baseline", "placebo"])
        placebo = dict(ev["repetitions"][0]["conditions"]["target"],
                       container_id="cp", session_id="sp",
                       starting_full_hash="sha256:f5",
                       ending_full_hash="sha256:f6",
                       skill_command="security-review:skill",
                       skill_kilo_path=".kilo/skills/security-review",
                       skill_content_hash=ree.skill_tree_hash(
                           os.path.join(ROOT, "skills", "security-review")))
        ev["repetitions"][0]["conditions"]["placebo"] = placebo
        ev["repetitions"][0]["condition_workspace_ids"]["placebo"] = "ws-p"
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("placebo_skill" in e for e in errs), errs)

    def test_placebo_valid_with_skill(self):
        ev = self._evidence(conditions=["target", "baseline", "placebo"],
                            placebo_skill="security-review")
        placebo = dict(ev["repetitions"][0]["conditions"]["target"],
                       container_id="cp", session_id="sp",
                       starting_full_hash="sha256:f5",
                       ending_full_hash="sha256:f6",
                       skill_command="security-review:skill",
                       skill_kilo_path=".kilo/skills/security-review",
                       skill_content_hash=ree.skill_tree_hash(
                           os.path.join(ROOT, "skills", "security-review")))
        ev["repetitions"][0]["conditions"]["placebo"] = placebo
        ev["repetitions"][0]["condition_workspace_ids"]["placebo"] = "ws-p"
        self.assertEqual(ve.validate_execution_evidence(ev), [])

    def test_failed_condition_rejected(self):
        ev = self._evidence()
        ev["repetitions"][0]["conditions"]["target"]["run_status"] = "failed"
        ev["repetitions"][0]["conditions"]["target"]["returncode"] = 1
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("run_status" in e for e in errs), errs)


class ExecutionRunnerBoundaryTests(unittest.TestCase):
    """Runner-level treatment boundary: Kilo discovery-tree materialization,
    skill-command naming, and REAL activation-event parsing (not file reads)."""

    def test_conditions_arg_validation(self):
        self.assertEqual(ree._conditions_arg("target,baseline"),
                         ["target", "baseline"])
        self.assertEqual(ree._conditions_arg("target,baseline,placebo"),
                         ["target", "baseline", "placebo"])
        with self.assertRaises(argparse.ArgumentTypeError):
            ree._conditions_arg("target")
        with self.assertRaises(argparse.ArgumentTypeError):
            ree._conditions_arg("target,baseline,bogus")
        self.assertEqual(ree._conditions_arg("baseline,target,target"),
                         ["baseline", "target"])

    def test_skill_command_name(self):
        self.assertEqual(ree.skill_command_name("code-review"),
                         "code-review:skill")

    def test_kilo_command_placeholders_are_detected(self):
        tmp = tempfile.mkdtemp()
        try:
            skilldir = os.path.join(tmp, "skill")
            os.makedirs(skilldir)
            open(os.path.join(skilldir, "SKILL.md"), "w").write(
                "# Skill\nUse $ARGUMENTS, $1, $2, and $0.\n")
            self.assertEqual(ree.kilo_command_placeholders(skilldir),
                             ["$0", "$1", "$2", "$ARGUMENTS"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_kilo_command_placeholder_check_accepts_normal_skill(self):
        tmp = tempfile.mkdtemp()
        try:
            skilldir = os.path.join(tmp, "skill")
            os.makedirs(skilldir)
            open(os.path.join(skilldir, "SKILL.md"), "w").write(
                "# Skill\nUse the verification checklist.\n")
            self.assertEqual(ree.kilo_command_placeholders(skilldir), [])
            ree.validate_activation_sources(
                skilldir, "code-review", ["target", "baseline"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_materialized_seed_hash_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "launch workers"):
            ree.validate_materialized_seed_hash(
                "sha256:actual", "sha256:frozen")
        ree.validate_materialized_seed_hash("sha256:frozen", "sha256:frozen")

    def test_worker_seed_copy_is_writable_through_bind_mount(self):
        tmp = tempfile.mkdtemp()
        try:
            source = os.path.join(tmp, "source")
            os.makedirs(source)
            source_file = os.path.join(source, "README.md")
            open(source_file, "w").write("# task\n")
            os.chmod(source_file, 0o444)
            worker = ree._copy_seed(source)
            worker_file = os.path.join(worker, "README.md")
            self.assertEqual(os.stat(worker_file).st_mode & stat.S_IWOTH,
                             stat.S_IWOTH)
            self.assertEqual(os.stat(worker).st_mode & stat.S_IWOTH,
                             stat.S_IWOTH)
        finally:
            shutil.rmtree(ree.SHARED_TMP, ignore_errors=True)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_runner_refuses_command_placeholders_before_worker(self):
        tmp = tempfile.mkdtemp()
        try:
            fixture = os.path.join(tmp, "fixture")
            os.makedirs(fixture)
            open(os.path.join(fixture, "README.md"), "w").write("# task\n")
            skilldir = os.path.join(tmp, "skill")
            os.makedirs(skilldir)
            open(os.path.join(skilldir, "SKILL.md"), "w").write(
                "# Skill\nUse the supplied $ARGUMENTS and $1.\n")
            called = []

            def worker(**_kwargs):
                called.append(True)
                raise AssertionError("worker must not be launched")

            with self.assertRaisesRegex(ValueError, "placeholder"):
                ree.run_repetition(
                    0, ["target", "baseline"], "Fix the bug.", fixture,
                    "code-review", skilldir, None, None,
                    "kilo/tencent/hy3:free", "kilo-eval:local", worker)
            self.assertEqual(called, [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_materialize_kilo_skill_creates_discovery_dir(self):
        tmp = tempfile.mkdtemp()
        try:
            skilldir = os.path.join(tmp, "skill")
            os.makedirs(os.path.join(skilldir, "references"))
            open(os.path.join(skilldir, "SKILL.md"), "w").write("# S")
            open(os.path.join(skilldir, "references", "r.md"), "w").write("r")
            workspace = os.path.join(tmp, "ws")
            os.makedirs(workspace)
            path = ree.materialize_kilo_skill(skilldir, "code-review", workspace)
            self.assertEqual(os.path.join(workspace, ".kilo", "skills",
                                          "code-review"), path)
            self.assertTrue(os.path.exists(os.path.join(path, "SKILL.md")))
            self.assertTrue(os.path.exists(
                os.path.join(path, "references", "r.md")))
            # The SKILL.md body and references must be copied verbatim.
            self.assertEqual(open(os.path.join(path, "SKILL.md")).read(), "# S")
            self.assertEqual(
                open(os.path.join(path, "references", "r.md")).read(), "r")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_materialize_kilo_skill_placebo_contents_reach_discovery(self):
        # P0-C regression: the placebo SKILL.md must reach the runtime discovery
        # location. The old bug passed a staged neutral bundle shaped
        # <dir>/task/SKILL.md into the kilo materializer (which expects
        # <dir>/SKILL.md), creating .kilo/skills/<name>/ WITHOUT the SKILL.md.
        # Materializing from the canonical repository skill dir must never
        # produce an empty discovery tree.
        tmp = tempfile.mkdtemp()
        try:
            pdir = os.path.join(tmp, "placebo-skill")
            os.makedirs(pdir)
            placebo_body = ("---\nname: placebo-skill\ndescription: irrelevant\n"
                            "---\n# Placebo\nDo nothing special.\n")
            open(os.path.join(pdir, "SKILL.md"), "w").write(placebo_body)
            workspace = os.path.join(tmp, "ws")
            os.makedirs(workspace)
            tree = ree.materialize_kilo_skill(pdir, "placebo-skill", workspace)
            discovery_md = os.path.join(tree, "SKILL.md")
            self.assertTrue(os.path.exists(discovery_md),
                            "placebo SKILL.md missing at discovery location")
            self.assertEqual(open(discovery_md).read(), placebo_body)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_skill_tree_hash_deterministic_and_content_sensitive(self):
        tmp = tempfile.mkdtemp()
        try:
            skilldir = os.path.join(tmp, "skill")
            os.makedirs(skilldir)
            open(os.path.join(skilldir, "SKILL.md"), "w").write("# S")
            h1 = ree.skill_tree_hash(skilldir)
            h2 = ree.skill_tree_hash(skilldir)
            self.assertEqual(h1, h2)
            self.assertTrue(h1.startswith("sha256:"))
            open(os.path.join(skilldir, "SKILL.md"), "w").write("# S changed")
            self.assertNotEqual(h1, ree.skill_tree_hash(skilldir))
            self.assertIsNone(ree.skill_tree_hash(
                os.path.join(tmp, "missing")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_skill_tree_hash_excludes_non_discovery_files(self):
        # The frozen hash must cover EXACTLY what reaches a worker's discovery
        # tree (SKILL.md + references/**), never the evals/ fixture snapshot.
        tmp = tempfile.mkdtemp()
        try:
            skilldir = os.path.join(tmp, "skill")
            os.makedirs(os.path.join(skilldir, "references"))
            os.makedirs(os.path.join(skilldir, "evals"))
            open(os.path.join(skilldir, "SKILL.md"), "w").write("# S")
            open(os.path.join(skilldir, "references", "r.md"), "w").write("r")
            # The evals/ tree contains the expected output / answer key and must
            # not influence the frozen guidance hash.
            open(os.path.join(skilldir, "evals", "evals.json"), "w").write(
                '{"answer": "secret"}')
            frozen = ree.skill_tree_hash(skilldir)
            # Materializing into a workspace must produce an identical hash.
            workspace = os.path.join(tmp, "ws")
            os.makedirs(workspace)
            tree = ree.materialize_kilo_skill(skilldir, "code-review", workspace)
            self.assertEqual(
                open(os.path.join(tree, "SKILL.md")).read(), "# S")
            self.assertEqual(frozen, ree.skill_tree_hash(tree))
            # Mutating the evals/ snapshot must NOT change the frozen hash.
            open(os.path.join(skilldir, "evals", "evals.json"), "w").write(
                '{"answer": "changed"}')
            self.assertEqual(frozen, ree.skill_tree_hash(skilldir))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- P0-A: real Kilo activation events (structure verified against the
    # installed CLI 7.4.22 --format json output) ---

    def _realistic_skill_event(self, name, status="completed", ts=1787124430157,
                               session="ses_abc123"):
        return json.dumps({
            "type": "tool_use",
            "timestamp": ts,
            "sessionID": session,
            "part": {
                "id": "prt_x",
                "sessionID": session,
                "messageID": "msg_y",
                "type": "tool",
                "callID": "chatcmpl-tool-abc",
                "tool": "skill",
                "state": {
                    "status": status,
                    "input": {"name": name},
                    "output": f'<skill_content name="{name}">\n# Skill: {name}\n'
                              f'\n# Body\n\nBase directory for this skill: '
                              f'/work/task/.kilo/skills/{name}\n'
                              f'Relative paths in this skill are relative to '
                              f'this base directory.\nNote: file list is '
                              f'sampled.\n\n<skill_files>\n\n</skill_files>\n'
                              f'</skill_content>',
                    "title": f"Loaded skill: {name}",
                    "metadata": {
                        "name": name,
                        "dir": f"/work/task/.kilo/skills/{name}",
                        "truncated": False,
                        "approval": {"source": "global",
                                     "rule": {"permission": "*",
                                              "pattern": "*",
                                              "action": "allow"}}},
                    "time": {"start": ts, "end": ts + 42},
                },
                "metadata": {"openrouter": {"reasoning_details": []}},
            },
        })

    def test_extract_activation_events_detects_skill_invocation(self):
        # A REAL Kilo `skill` tool_use event must be detected.
        stdout = "\n".join([
            self._realistic_skill_event("code-review"),
            '{"type":"text","part":{"type":"text","text":"done"}}',
        ])
        events = ree.extract_activation_events(stdout, "code-review")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["tool"], "skill")
        self.assertEqual(events[0]["skill_name"], "code-review")
        self.assertEqual(events[0]["session_id"], "ses_abc123")
        self.assertEqual(events[0]["timestamp"], 1787124430157)
        self.assertIn(".kilo/skills/code-review", events[0]["dir"])

    def test_extract_activation_events_ignores_file_reads(self):
        # P0-A: a normal `read` of the SKILL.md file is NOT activation.
        stdout = "\n".join([
            json.dumps({"type": "tool_use", "timestamp": 1,
                        "part": {"tool": "read",
                                 "state": {"input": {
                                     "filePath": "/work/task/.kilo/skills/"
                                                 "code-review/SKILL.md"}}}}),
            '{"type":"text","part":{"type":"text","text":"ok"}}',
        ])
        self.assertEqual(
            ree.extract_activation_events(stdout, "code-review"), [])

    def test_extract_activation_events_requires_completed_content(self):
        # A tool name alone, or a completed event without the skill result, is
        # not proof that the guidance entered context.
        stdout = "\n".join([
            self._realistic_skill_event("code-review", status="running"),
            json.dumps({
                "type": "tool_use", "timestamp": 2,
                "sessionID": "ses_no_content",
                "part": {"type": "tool", "tool": "skill",
                         "state": {"status": "completed",
                                   "input": {"name": "code-review"},
                                   "output": ""}},
            }),
            json.dumps({
                "type": "tool_use", "timestamp": 3,
                "sessionID": "ses_open_only",
                "part": {"type": "tool", "tool": "skill",
                         "state": {"status": "completed",
                                   "input": {"name": "code-review"},
                                   "output": "<skill_content name=\"code-review\">"}},
            }),
        ])
        self.assertEqual(
            ree.extract_activation_events(stdout, "code-review"), [])

    def test_extract_activation_events_other_skill_not_counted(self):
        # P0-A: another skill's invocation must not count as this skill's.
        stdout = "\n".join([
            self._realistic_skill_event("security-review", session="ses_abc"),
        ])
        self.assertEqual(
            ree.extract_activation_events(stdout, "code-review"), [])

    def test_extract_activation_events_malformed_not_counted(self):
        # P0-A: malformed tool events (bad JSON, missing state, error status,
        # non-skill tool) must never count.
        stdout = "\n".join([
            "not json at all",
            '{"type":"tool_use"}',
            '{"type":"tool_use","part":{"tool":"skill"}}',
            self._realistic_skill_event("code-review", status="error",
                                        session="ses_bad"),
            '{"type":"tool_use","part":{"tool":"bash",'
            '"state":{"input":{"command":"cat .kilo/skills/code-review/'
            'SKILL.md"}}}}',
        ])
        self.assertEqual(
            ree.extract_activation_events(stdout, "code-review"), [])

    def test_extract_activation_events_file_presence_not_enough(self):
        # P0-A: mere skill-file presence in the workspace never produces
        # activation events by itself.
        tmp = tempfile.mkdtemp()
        try:
            workspace = os.path.join(tmp, "ws")
            os.makedirs(os.path.join(workspace, ".kilo", "skills", "code-review"))
            open(os.path.join(workspace, ".kilo", "skills", "code-review",
                              "SKILL.md"), "w").write("# present but inert")
            self.assertEqual(
                ree.extract_activation_events("", "code-review"), [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TaskStateHashRegressionTests(unittest.TestCase):
    """P0-B regression: evaluator treatment files must not invalidate seed
    equality; real task mutations still change the task-state hash."""

    def _make_fixture(self, tmp):
        fx = os.path.join(tmp, "fixture")
        os.makedirs(fx)
        open(os.path.join(fx, "main.py"), "w").write("print('hi')\n")
        open(os.path.join(fx, "README.md"), "w").write("# task\n")
        return fx

    def _make_skill(self, tmp, name, body):
        sd = os.path.join(tmp, f"skill-{name}")
        os.makedirs(sd)
        open(os.path.join(sd, "SKILL.md"), "w").write(body)
        return sd

    def test_treatment_paths_do_not_change_task_hash(self):
        tmp = tempfile.mkdtemp()
        try:
            fx = self._make_fixture(tmp)
            target_skill = self._make_skill(
                tmp, "code-review", "# target guidance body\n")
            placebo_skill = self._make_skill(
                tmp, "security-review", "# placebo guidance body\n")
            workspaces = {}
            for name in ("target", "baseline", "placebo"):
                ws = os.path.join(tmp, f"ws-{name}")
                shutil.copytree(fx, ws)
                workspaces[name] = ws
            # Treatment: target and placebo receive .kilo/skills trees;
            # baseline untouched.
            ree.materialize_kilo_skill(target_skill, "code-review",
                                       workspaces["target"])
            ree.materialize_kilo_skill(placebo_skill, "security-review",
                                       workspaces["placebo"])
            # Task-state hashes must be equal across all three conditions.
            task_hashes = {n: eh.hash_task_workspace(ws, ree.RUNTIME_TREATMENT_PATHS)
                           for n, ws in workspaces.items()}
            self.assertEqual(len(set(task_hashes.values())), 1,
                             f"task hashes must match: {task_hashes}")
            # Full-filesystem hashes (treatment included) MUST differ from the
            # baseline, and the target/placebo trees differ from each other.
            full_hashes = {n: eh.hash_workspace(ws) for n, ws in workspaces.items()}
            self.assertNotEqual(full_hashes["target"], full_hashes["baseline"])
            self.assertNotEqual(full_hashes["placebo"], full_hashes["baseline"])
            self.assertNotEqual(full_hashes["target"], full_hashes["placebo"])
            # A real task mutation changes the task hash.
            before = task_hashes["target"]
            open(os.path.join(workspaces["target"], "main.py"), "a").write(
                "# mutated\n")
            self.assertNotEqual(
                before, eh.hash_task_workspace(workspaces["target"],
                                               ree.RUNTIME_TREATMENT_PATHS))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_nested_kilo_fixture_content_still_hashed(self):
        # The exclusion is conservative: only a TOP-LEVEL .kilo root is
        # excluded; a fixture's own nested .kilo content still counts.
        tmp = tempfile.mkdtemp()
        try:
            fx = os.path.join(tmp, "fx")
            os.makedirs(os.path.join(fx, "sub", ".kilo"))
            open(os.path.join(fx, "sub", ".kilo", "config"), "w").write("x")
            open(os.path.join(fx, "a.txt"), "w").write("a")
            h1 = eh.hash_task_workspace(fx, ree.RUNTIME_TREATMENT_PATHS)
            open(os.path.join(fx, "sub", ".kilo", "config"), "w").write("y")
            h2 = eh.hash_task_workspace(fx, ree.RUNTIME_TREATMENT_PATHS)
            self.assertNotEqual(h1, h2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_project_kilo_config_remains_task_state(self):
        # Only the evaluator-owned project skill tree is excluded. A fixture's
        # project config under .kilo is part of the task and must affect its hash.
        tmp = tempfile.mkdtemp()
        try:
            fx = os.path.join(tmp, "fx")
            os.makedirs(os.path.join(fx, ".kilo", "skills"))
            open(os.path.join(fx, ".kilo", "config.jsonc"), "w").write(
                '{"agent":"code"}\n')
            h1 = eh.hash_task_workspace(fx, ree.RUNTIME_TREATMENT_PATHS)
            open(os.path.join(fx, ".kilo", "config.jsonc"), "w").write(
                '{"agent":"plan"}\n')
            h2 = eh.hash_task_workspace(fx, ree.RUNTIME_TREATMENT_PATHS)
            self.assertNotEqual(h1, h2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class LayerBProtocolIntegrationTests(unittest.TestCase):
    """P1: end-to-end Layer B protocol test.

    Exercises the REAL runner preparation -> condition workspace construction ->
    guidance activation setup -> evidence construction -> validator, with only
    the Kilo subprocess boundary mocked. Catches runner/validator
    incompatibilities that isolated unit tests miss.
    """

    def tearDown(self):
        reset()

    def _fixture(self, tmp):
        fx = os.path.join(tmp, "fixture")
        os.makedirs(fx)
        open(os.path.join(fx, "main.py"), "w").write(
            "def buggy():\n    return 1 / 0\n")
        open(os.path.join(fx, "README.md"), "w").write("# task\n")
        return fx

    def _skill(self, tmp, name, body):
        sd = os.path.join(tmp, f"skill-{name}")
        os.makedirs(sd)
        open(os.path.join(sd, "SKILL.md"), "w").write(body)
        return sd

    def _fake_run(self, condition_stdout):
        """Build a run_container()-shaped fake: returns canned metadata whose
        stdout carries REALISTIC Kilo JSONL (real skill tool_use event shape)."""
        def fake(image, model, prompt, fixture_dir, skill_command=None,
                 skill_md_hex=None, skill_probe_path=None):
            skill_name = None
            if skill_command:
                skill_name = skill_command.split(":")[0]
            if skill_name:
                probe = skill_probe_path.replace("/work/task", fixture_dir)
                if os.path.exists(probe) and skill_md_hex:
                    actual = hashlib.sha256(open(probe, "rb").read()).hexdigest()
                    probe_state = ("present" if actual == skill_md_hex
                                   else "hash_mismatch")
                elif os.path.exists(probe):
                    probe_state = "present"
                else:
                    probe_state = "absent"
            else:
                kilo_skills = os.path.join(fixture_dir, ".kilo", "skills")
                probe_state = "absent" if not os.path.exists(kilo_skills) \
                    else "present"
            return {
                "returncode": 0,
                "stdout": condition_stdout,
                "stderr": "",
                "container_id": "cid-" + (skill_name or "baseline"),
                "session_id": "ses-" + (skill_name or "baseline"),
                "output": "worker output",
                "skill_probe": probe_state,
                "skill_context_probe": "present" if skill_name else "none",
                "status": "success",
                "reason": None,
            }
        return fake

    def test_run_container_context_probe_parses_json_session_ids(self):
        # The real Docker shell must parse JSONL structurally; compact-JSON
        # regexes are brittle when Kilo emits whitespace after a colon.
        tmp = tempfile.mkdtemp()
        try:
            fixture = os.path.join(tmp, "fixture")
            os.makedirs(fixture)
            captured = {}

            def fake_subprocess_run(cmd, **kwargs):
                captured["cmd"] = cmd
                cidfile = cmd[cmd.index("--cidfile") + 1]
                open(cidfile, "w").write("cid-test")
                return unittest.mock.Mock(
                    returncode=0,
                    stdout=('{"type": "text", "sessionID": "ses spaced", '
                            '"part": {"type": "text", "text": "done"}}\n'
                            'SKILL_CONTEXT_PROBE:present\n'
                            'SKILL_PROBE:present\n'),
                    stderr="",
                )

            with unittest.mock.patch.object(ree.subprocess, "run",
                                            side_effect=fake_subprocess_run):
                meta = ree.run_container(
                    "kilo-eval:local", "kilo/tencent/hy3:free", "task",
                    fixture, skill_command="code-review:skill",
                    skill_md_hex="abc",
                    skill_probe_path="/work/task/.kilo/skills/code-review/"
                                      "SKILL.md")
            script = captured["cmd"][-1]
            self.assertIn("JSON.parse", script)
            self.assertIn('role===\"user\"', script)
            self.assertNotIn("sed -n", script)
            syntax = subprocess.run(["bash", "-n"], input=script,
                                    text=True, capture_output=True)
            self.assertEqual(syntax.returncode, 0, syntax.stderr)
            self.assertEqual(meta["session_id"], "ses spaced")
            self.assertEqual(meta["skill_context_probe"], "present")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @unittest.skipUnless(shutil.which("node"), "Node is required for export probe")
    def test_context_probe_parses_export_roles_and_rejects_assistant_echo(self):
        # Exercise the actual Node export parser with Kilo's observed
        # messages[].info.role shape, rather than only inspecting generated
        # shell text.
        tmp = tempfile.mkdtemp()
        try:
            export_path = os.path.join(tmp, "export.json")
            skill_path = os.path.join(tmp, "SKILL.md")
            body = "# Guidance\nUse the verification checklist."
            open(skill_path, "w").write(
                "---\nname: probe\ndescription: probe\n---\n" + body)

            def run_probe(messages):
                open(export_path, "w").write(json.dumps({"messages": messages}))
                return subprocess.run(
                    ["node", "-e", ree.CONTEXT_PROBE_NODE_SCRIPT,
                     export_path, skill_path],
                    text=True, capture_output=True, check=True).stdout

            self.assertEqual(run_probe([{
                "info": {"role": "assistant"},
                "parts": [{"type": "text", "text": body}],
            }]), "absent")
            self.assertEqual(run_probe([{
                "info": {"role": "user"},
                "parts": [{"type": "text", "text": body}],
            }]), "present")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _run_full_protocol(self, tmp, conditions, target_body, placebo_body,
                           fake_run=None):
        """Seed -> per-condition copies -> .kilo/skills placement -> fake
        workers -> evidence -> validator. Returns (evidence, errors)."""
        fx = os.path.join(tmp, "fixture")
        shutil.copytree(os.path.join(ROOT, "skills", "code-review", "evals",
                                     "files", "case-1"), fx)
        # Use canonical repository skill trees so the evidence source anchors are
        # checked against the same artifacts the production runner would use.
        target_skill = os.path.join(ROOT, "skills", "code-review")
        placebo_skill = os.path.join(ROOT, "skills", "security-review")
        seed, seed_hash = eh.materialize_fixture_seed(fx, "committed")
        expected_hash = ree.HASH_PREFIX + seed_hash
        canonical = ree.HASH_PREFIX + eh.hash_task_workspace(
            seed, ree.RUNTIME_TREATMENT_PATHS)
        # The pristine seed must be free of runtime treatment paths.
        self.assertEqual(canonical, ree.HASH_PREFIX + eh.hash_workspace(seed))

        target_stdout = "\n".join([
            self._realistic_skill_event("code-review"),
            '{"type":"text","part":{"type":"text","text":"target done"}}',
        ])
        placebo_stdout = "\n".join([
            self._realistic_skill_event("security-review"),
            '{"type":"text","part":{"type":"text","text":"placebo done"}}',
        ])
        baseline_stdout = ('{"type":"text","part":{"type":"text",'
                           '"text":"baseline done"}}')
        # Keyed by the SKILL name (what --command resolves); baseline has none.
        stdout_by_cond = {"code-review": target_stdout,
                          "security-review": placebo_stdout,
                          "baseline": baseline_stdout}

        def run_fn(image, model, prompt, fixture_dir, skill_command=None,
                   skill_md_hex=None, skill_probe_path=None):
            name = (skill_command.split(":")[0] if skill_command else "baseline")
            if fake_run is not None:
                return fake_run(image, model, prompt, fixture_dir,
                                skill_command, skill_md_hex, skill_probe_path)
            return self._fake_run(stdout_by_cond[name])(
                image, model, prompt, fixture_dir, skill_command,
                skill_md_hex, skill_probe_path)

        evals = json.load(open(os.path.join(
            ROOT, "skills", "code-review", "evals", "evals.json")))
        natural_task = next(c for c in evals["evals"] if c["id"] == 1)[
            "prompt"]
        rep, canonical, _ = ree.run_repetition(
            0, conditions, natural_task, seed,
            "code-review", target_skill,
            "security-review" if "placebo" in conditions else None,
            placebo_skill if "placebo" in conditions else None,
            "kilo/tencent/hy3:free", "kilo-eval:local", run_fn)
        evidence = {
            "evidence_type": "execution",
            "skill": "code-review", "case_id": 1,
            "model": "kilo/tencent/hy3:free", "image": "kilo-eval:local",
            "activation_mechanism": ree.ACTIVATION_MECHANISM,
            "runtime_treatment_paths": list(ree.RUNTIME_TREATMENT_PATHS),
            "target_skill_kilo_path": ".kilo/skills/code-review",
            "target_skill_content_hash": ree.skill_tree_hash(target_skill),
            "placebo_skill_kilo_path": (".kilo/skills/security-review"
                                        if "placebo" in conditions else None),
            "placebo_skill_content_hash": (ree.skill_tree_hash(placebo_skill)
                                           if "placebo" in conditions else None),
            "expected_fixture_hash": expected_hash,
            "fixture_source_path": "skills/code-review/evals/evals.json",
            "fixture_path": "skills/code-review/evals/files/case-1",
            "fixture_source_hash": "sha256:" + hashlib.sha256(open(
                os.path.join(ROOT, "skills", "code-review", "evals",
                             "evals.json"), "rb").read()).hexdigest(),
            "target_skill_source_path": "skills/code-review",
            "canonical_task_seed_hash": canonical,
            "conditions": conditions,
            "placebo_skill": ("security-review" if "placebo" in conditions
                              else None),
            "repetitions": [rep],
        }
        return evidence, ve.validate_execution_evidence(evidence)

    def _realistic_skill_event(self, name, status="completed", ts=1,
                               session="ses_abc"):
        return json.dumps({
            "type": "tool_use", "timestamp": ts, "sessionID": session,
            "part": {"type": "tool", "tool": "skill", "callID": "chatcmpl-x",
                     "state": {"status": status,
                               "input": {"name": name},
                    "output": (f"<skill_content name=\"{name}\">\n"
                               f"# {name} guidance\n"
                               "Use the loaded guidance.\n"
                               "</skill_content>"),
                               "title": f"Loaded skill: {name}",
                               "metadata": {"name": name,
                                            "dir": f"/work/task/.kilo/skills/"
                                                    f"{name}"},
                               "time": {"start": ts, "end": ts + 1}}},
        })

    def test_full_protocol_valid_target_baseline_placebo(self):
        tmp = tempfile.mkdtemp()
        try:
            ev, errs = self._run_full_protocol(
                tmp, ["target", "baseline", "placebo"],
                "# target guidance\nDo verification.\n",
                "# placebo guidance\nBe verbose.\n",
                fake_run=None)
            self.assertEqual(errs, [], f"validator errors: {errs}")
            rep = ev["repetitions"][0]
            starts = {n: rep["conditions"][n]["starting_task_hash"]
                      for n in ("target", "baseline", "placebo")}
            self.assertEqual(len(set(starts.values())), 1,
                             f"task hashes must match: {starts}")
            # Task hashes must equal the frozen fixture hash.
            self.assertEqual(rep["canonical_task_seed_hash"],
                             ev["expected_fixture_hash"])
            # Runtime treatment recorded separately and differs as expected.
            self.assertEqual(rep["conditions"]["target"]["activation_mechanism"],
                             "kilo-command-skill")
            self.assertEqual(rep["conditions"]["placebo"]["activation_mechanism"],
                             "kilo-command-skill")
            self.assertEqual(rep["conditions"]["baseline"]["activation_mechanism"],
                             "none")
            self.assertEqual(rep["conditions"]["target"]["skill_probe"],
                             "present")
            self.assertEqual(rep["conditions"]["placebo"]["skill_probe"],
                             "present")
            self.assertEqual(rep["conditions"]["baseline"]["skill_probe"],
                             "absent")
            self.assertNotEqual(
                rep["conditions"]["target"]["starting_full_hash"],
                rep["conditions"]["baseline"]["starting_full_hash"])
            # Distinct sessions/containers represented.
            self.assertTrue(rep["distinct_containers"])
            self.assertTrue(rep["distinct_sessions"])
            # Natural prompt byte-identical across conditions (single hash).
            self.assertTrue(rep["natural_task_identical_across_conditions"])
            # Native skill-tool activation events parsed from realistic JSONL.
            self.assertTrue(
                rep["conditions"]["target"]["skill_tool_invoked"])
            self.assertEqual(
                rep["conditions"]["target"]["activation_events"][0][
                    "skill_name"], "code-review")
            self.assertEqual(
                rep["conditions"]["placebo"]["activation_events"][0][
                    "skill_name"], "security-review")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_filesystem_snapshots_capture_worker_mutation(self):
        # The pre-snapshot must be captured before run_fn, not reconstructed
        # afterward. This is a runner-level regression, not only a hash check.
        tmp = tempfile.mkdtemp()
        try:
            fixture = self._fixture(tmp)
            target_skill = self._skill(
                tmp, "code-review", "# target guidance\nVerify changes.\n")
            stdout = '{"type":"text","part":{"type":"text",'
            stdout += '"text":"worker done"}}'

            def mutating_run(image, model, prompt, fixture_dir,
                             skill_command=None, skill_md_hex=None,
                             skill_probe_path=None):
                with open(os.path.join(fixture_dir, "README.md"), "a") as fh:
                    fh.write("# worker mutation\n")
                return self._fake_run(stdout)(
                    image, model, prompt, fixture_dir, skill_command,
                    skill_md_hex, skill_probe_path)

            rep, _, workspaces = ree.run_repetition(
                0, ["target", "baseline"], "Fix the bug.", fixture,
                "code-review", target_skill, None, None,
                "kilo/tencent/hy3:free", "kilo-eval:local", mutating_run)
            target = rep["conditions"]["target"]
            before = target["filesystem_snapshot_before"]
            after = target["filesystem_snapshot_after"]
            self.assertNotEqual(before["listing"]["README.md"],
                                after["listing"]["README.md"])
            self.assertNotEqual(target["starting_task_hash"],
                                target["ending_task_hash"])
            self.assertEqual(set(workspaces), {"target", "baseline"})
        finally:
            shutil.rmtree(ree.SHARED_TMP, ignore_errors=True)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_target_file_present_but_not_activated_rejected(self):
        # Negative 1: the target skill merely EXISTS (tree on disk, probe
        # present) but was never activated through the controlled mechanism.
        tmp = tempfile.mkdtemp()
        try:
            ev, errs = self._run_full_protocol(
                tmp, ["target", "baseline"],
                "# target guidance\nDo verification.\n", "", fake_run=None)
            t = ev["repetitions"][0]["conditions"]["target"]
            t["activation_mechanism"] = "none"
            t["skill_command"] = None
            errs = ve.validate_execution_evidence(ev)
            self.assertTrue(any("activation_mechanism" in e for e in errs),
                            errs)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_target_context_body_missing_rejected(self):
        tmp = tempfile.mkdtemp()
        try:
            ev, _ = self._run_full_protocol(
                tmp, ["target", "baseline"],
                "# target guidance\nDo verification.\n", "", fake_run=None)
            ev["repetitions"][0]["conditions"]["target"][
                "skill_context_probe"] = "absent"
            errs = ve.validate_execution_evidence(ev)
            self.assertTrue(any("skill_context_probe" in e for e in errs), errs)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_placebo_missing_skill_md_rejected(self):
        # Negative 2: the old P0-C staging bug — .kilo/skills/<placebo>/ exists
        # but the SKILL.md never reached it. The probe must report absent and
        # the validator must reject.
        tmp = tempfile.mkdtemp()
        try:
            ev, errs = self._run_full_protocol(
                tmp, ["target", "baseline", "placebo"],
                "# target guidance\nDo verification.\n",
                "# placebo guidance\nBe verbose.\n",
                fake_run=None)
            # Simulate the empty-discovery-tree defect: remove the placebo
            # SKILL.md from the workspace the evidence describes.
            ws_id = ev["repetitions"][0]["condition_workspace_ids"]["placebo"]
            ws_path = os.path.join(ree.SHARED_TMP, ws_id)
            os.remove(os.path.join(ws_path, ".kilo", "skills",
                                   "security-review", "SKILL.md"))
            p = ev["repetitions"][0]["conditions"]["placebo"]
            p["skill_probe"] = "absent"
            p["skill_content_hash"] = None
            errs = ve.validate_execution_evidence(ev)
            self.assertTrue(any("placebo: skill_probe" in e for e in errs),
                            errs)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_baseline_leaks_target_runtime_path_rejected(self):
        # Negative 3: the baseline workspace carries the target's .kilo/skills
        # tree (or records it) — a treatment leak.
        tmp = tempfile.mkdtemp()
        try:
            ev, errs = self._run_full_protocol(
                tmp, ["target", "baseline"],
                "# target guidance\nDo verification.\n", "", fake_run=None)
            b = ev["repetitions"][0]["conditions"]["baseline"]
            b["skill_kilo_path"] = ".kilo/skills/code-review"
            b["skill_probe"] = "present"
            errs = ve.validate_execution_evidence(ev)
            self.assertTrue(any("baseline: skill_kilo_path" in e
                                for e in errs), errs)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_task_hash_difference_before_run_rejected(self):
        # Negative 4: a REAL fixture mutation before the run (not a treatment
        # file) must make the evidence fail the identical-task requirement.
        tmp = tempfile.mkdtemp()
        try:
            def mutate():
                ws_id = ev["repetitions"][0]["condition_workspace_ids"][
                    "baseline"]
                ws = os.path.join(ree.SHARED_TMP, ws_id)
                open(os.path.join(ws, "README.md"), "a").write("# changed\n")

            ev = None
            fx = os.path.join(tmp, "fixture")
            shutil.copytree(os.path.join(ROOT, "skills", "code-review", "evals",
                                         "files", "case-1"), fx)
            target_skill = os.path.join(ROOT, "skills", "code-review")
            seed, seed_hash = eh.materialize_fixture_seed(fx, "committed")
            canonical = ree.HASH_PREFIX + eh.hash_task_workspace(
                seed, ree.RUNTIME_TREATMENT_PATHS)
            target_stdout = ("{\"type\":\"text\",\"part\":{\"type\":\"text\","
                             "\"text\":\"target done\"}}")
            stdout_by_cond = {"code-review": target_stdout,
                              "baseline": target_stdout}

            def run_fn(image, model, prompt, fixture_dir, skill_command=None,
                       skill_md_hex=None, skill_probe_path=None):
                name = (skill_command.split(":")[0] if skill_command
                        else "baseline")
                return self._fake_run(stdout_by_cond[name])(
                    image, model, prompt, fixture_dir, skill_command,
                    skill_md_hex, skill_probe_path)

            rep, canonical, _ = ree.run_repetition(
                0, ["target", "baseline"], "Fix the bug.", seed,
                "code-review", target_skill, None, None,
                "kilo/tencent/hy3:free", "kilo-eval:local", run_fn)
            ev = {
                "evidence_type": "execution",
                "skill": "code-review", "case_id": 1,
                "model": "kilo/tencent/hy3:free", "image": "kilo-eval:local",
                "activation_mechanism": ree.ACTIVATION_MECHANISM,
                "runtime_treatment_paths": list(ree.RUNTIME_TREATMENT_PATHS),
                "target_skill_kilo_path": ".kilo/skills/code-review",
                "target_skill_content_hash": ree.skill_tree_hash(target_skill),
                "expected_fixture_hash": ree.HASH_PREFIX + seed_hash,
                "fixture_source_path": "skills/code-review/evals/evals.json",
                "fixture_path": "skills/code-review/evals/files/case-1",
                "fixture_source_hash": "sha256:" + hashlib.sha256(open(
                    os.path.join(ROOT, "skills", "code-review", "evals",
                                 "evals.json"), "rb").read()).hexdigest(),
                "target_skill_source_path": "skills/code-review",
                "canonical_task_seed_hash": canonical,
                "conditions": ["target", "baseline"],
                "placebo_skill": None,
                "repetitions": [rep],
            }
            mutate()
            # Rewrite the starting_task_hash to what a broken runner would have
            # recorded if it had hashed AFTER the mutation.
            b = ev["repetitions"][0]["conditions"]["baseline"]
            ws = os.path.join(ree.SHARED_TMP,
                              ev["repetitions"][0][
                                  "condition_workspace_ids"]["baseline"])
            b["starting_task_hash"] = ree.HASH_PREFIX + eh.hash_task_workspace(
                ws, ree.RUNTIME_TREATMENT_PATHS)
            errs = ve.validate_execution_evidence(ev)
            self.assertTrue(any("TASK hash" in e or "differ" in e
                                for e in errs), errs)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_target_activation_event_names_other_skill_rejected(self):
        # Negative 5: the target's recorded activation event names a DIFFERENT
        # skill — that invocation must not count as target activation.
        tmp = tempfile.mkdtemp()
        try:
            ev, errs = self._run_full_protocol(
                tmp, ["target", "baseline"],
                "# target guidance\nDo verification.\n", "", fake_run=None)
            t = ev["repetitions"][0]["conditions"]["target"]
            t["skill_tool_invoked"] = True
            t["activation_events"] = [
                {"tool": "skill", "skill_name": "security-review",
                 "timestamp": 1, "session_id": "ses-x"}]
            errs = ve.validate_execution_evidence(ev)
            self.assertTrue(any("names skill" in e for e in errs), errs)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class LayerAAggregateTests(unittest.TestCase):
    """P2: Layer A aggregate confusion matrix + per-skill precision/recall."""

    def _case_results(self):
        return [
            {"id": 1, "expected_skill": "code-review",
             "repetitions": [
                 {"rep": 1, "status": "success", "decision":
                  {"selected_skill": "code-review"}},
                 {"rep": 2, "status": "success", "decision":
                  {"selected_skill": "security-review"}}]},
            {"id": 2, "expected_skill": "security-review",
             "repetitions": [
                 {"rep": 1, "status": "success", "decision":
                  {"selected_skill": "security-review"}},
                 {"rep": 2, "status": "failed", "error": "kilo exited 1",
                  "decision": None}]},
            {"id": 3, "expected_skill": None,
             "repetitions": [
                 {"rep": 1, "status": "success", "decision":
                  {"selected_skill": None}}]},
        ]

    def test_aggregate_matrix_and_metrics(self):
        agg = rc.build_aggregate(self._case_results(),
                                 ["code-review", "security-review"])
        self.assertEqual(agg["observations"], 4)  # failed rep not an observation
        self.assertEqual(agg["confusion_matrix"]["code-review"],
                         {"code-review": 1, "security-review": 1})
        self.assertEqual(agg["confusion_matrix"]["security-review"],
                         {"security-review": 1})
        self.assertEqual(agg["confusion_matrix"]["null"], {"null": 1})
        cr = agg["per_skill"]["code-review"]
        self.assertEqual((cr["tp"], cr["fp"], cr["fn"]), (1, 0, 1))
        self.assertEqual(cr["precision"], 1.0)
        self.assertEqual(cr["recall"], 0.5)
        sr = agg["per_skill"]["security-review"]
        self.assertEqual((sr["tp"], sr["fp"], sr["fn"]), (1, 1, 0))
        self.assertEqual(sr["precision"], 0.5)
        self.assertEqual(sr["recall"], 1.0)

    def test_aggregate_turn_observations(self):
        cases = [{
            "id": 1, "case_type": "workflow-transition",
            "expected_skill": "code-review",
            "turns": [{"user": "a", "expected_route": "code-review"},
                      {"user": "b", "expected_route": None}],
            "repetitions": [{"rep": 1, "turns": [
                {"status": "success", "expected_route": "code-review",
                 "selected_skill": "code-review"},
                {"status": "success", "expected_route": None,
                 "selected_skill": None}]}],
        }]
        agg = rc.build_aggregate(cases, ["code-review"])
        self.assertEqual(agg["observations"], 2)
        self.assertEqual(agg["confusion_matrix"]["code-review"],
                         {"code-review": 1})
        self.assertEqual(agg["confusion_matrix"]["null"], {"null": 1})

    def test_aggregate_nonworkflow_turns_follow_plain_runner_shape(self):
        # Non-workflow cases are executed as single-prompt cases by the
        # runner, even if malformed input happens to contain turns. Aggregate
        # must not reinterpret their plain decisions as per-turn observations.
        cases = [{
            "id": 1, "case_type": "smoke", "expected_skill": "code-review",
            "turns": [{"user": "not a workflow"}],
            "repetitions": [{"rep": 1, "status": "success",
                              "decision": {"selected_skill": "code-review"}}],
        }]
        agg = rc.build_aggregate(cases, ["code-review"])
        self.assertEqual(agg["observations"], 1)
        self.assertEqual(agg["confusion_matrix"],
                         {"code-review": {"code-review": 1}})

    def test_aggregate_undefined_metrics_are_null(self):
        agg = rc.build_aggregate(
            [{"id": 1, "expected_skill": "security-review",
              "repetitions": [{"rep": 1, "status": "success", "decision":
                               {"selected_skill": "code-review"}}]}],
            ["security-review", "code-review"])
        sr = agg["per_skill"]["security-review"]
        self.assertEqual(sr["tp"], 0)
        self.assertIsNone(sr["precision"])  # 0/0 is undefined, not 0
        self.assertEqual(sr["recall"], 0.0)

    def test_aggregate_deterministic(self):
        c = self._case_results()
        self.assertEqual(rc.build_aggregate(c, ["code-review",
                                                "security-review"]),
                         rc.build_aggregate(c, ["code-review",
                                                "security-review"]))


class HoldoutInvocationTests(unittest.TestCase):
    """P2: first-class holdout invocation path with distinct evidence source
    labels, and no confusion-set/holdout cross-contamination."""

    def tearDown(self):
        reset()

    def _fake_run(self, selected_skill):
        def fake(prompt, model, workdir, kilo_bin, catalog_names=None,
                 session_id=None):
            return {"status": "success", "error": None, "returncode": 0,
                    "stdout": "", "stderr": "",
                    "session_id": "ses-x" if not session_id else session_id,
                    "decision": {"selected_skill": selected_skill,
                                 "action": ("apply" if selected_skill else
                                            "clarify"),
                                 "rationale": "r"}}
        return fake

    def _run_set(self, path, args, runner, fake):
        with unittest.mock.patch.object(runner, "run_kilo", fake):
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                runner.run_case_set(path, args, "kilo")
        return buf.getvalue()

    def test_confusion_set_and_holdout_labeling(self):
        tmp = tempfile.mkdtemp()
        try:
            conf = os.path.join(tmp, "conf.json")
            hold = os.path.join(tmp, "hold.json")
            json.dump({"confusion_set": "review-family", "skills": ["code-review"],
                       "cases": [{"id": 1, "case_type": "hard-negative",
                                  "prompt": "p", "expected_skill": "code-review"}]},
                      open(conf, "w"))
            json.dump({"holdout": "review-discrim-1", "skills": ["code-review"],
                       "cases": [{"id": 1, "case_type": "hard-negative",
                                  "prompt": "p", "expected_skill": "code-review"}]},
                      open(hold, "w"))
            conf_out = os.path.join(tmp, "out-conf.json")
            hold_out = os.path.join(tmp, "out-hold.json")

            class A:
                reps = 1
                model = "kilo/tencent/hy3:free"
                out = conf_out

            class B:
                reps = 1
                model = "kilo/tencent/hy3:free"
                out = hold_out

            conf_fake = self._fake_run("code-review")
            hold_fake = self._fake_run("code-review")
            self._run_set(conf, A(), rc, conf_fake)
            self._run_set(hold, B(), rc, hold_fake)

            conf_ev = json.load(open(conf_out))
            hold_ev = json.load(open(hold_out))
            self.assertEqual(conf_ev["evidence_type"], "confusion-set")
            self.assertEqual(conf_ev["confusion_set"], "review-family")
            self.assertIsNone(conf_ev.get("holdout"))
            self.assertEqual(hold_ev["evidence_type"], "holdout")
            self.assertEqual(hold_ev["holdout"], "review-discrim-1")
            self.assertIsNone(hold_ev.get("confusion_set"))
            # Both carry the aggregate (Layer A metrics).
            self.assertIn("aggregate", conf_ev)
            self.assertIn("aggregate", hold_ev)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_unknown_case_set_file_rejected(self):
        tmp = tempfile.mkdtemp()
        try:
            bad = os.path.join(tmp, "bad.json")
            json.dump({"cases": []}, open(bad, "w"))
            with self.assertRaises(SystemExit):
                rc.run_case_set(bad, None, "kilo")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class CommittedEvaluationArtifactIntegrationTests(unittest.TestCase):
    """Exercise the repository's committed result files as a corpus."""

    def test_all_committed_artifacts_are_readable_and_validated(self):
        reset()
        result_dir = os.path.join(ROOT, "docs", "evaluations", "results")
        artifacts = sorted(glob.glob(os.path.join(result_dir, "*.md")))
        self.assertTrue(artifacts, "expected committed evaluation artifacts")

        original_evals_dir = ve.EVALS_DIR
        try:
            skill_names, case_index = ve.check_eval_files()
            ve.check_results(skill_names, case_index)
            parsed_blocks = 0
            for path in artifacts:
                text = open(path, encoding="utf-8",
                            errors="replace").read()
                blocks = ve.extract_result_json(text)
                if os.path.basename(path) not in ve.HISTORICAL:
                    self.assertTrue(
                        blocks,
                        f"non-historical artifact has no result-json: {path}")
                parsed_blocks += len(blocks)
                for block in blocks:
                    self.assertIsInstance(block, dict)
                    if block.get("evaluation_mode") == "regression":
                        self.assertTrue(block.get("case_revision"))
                        self.assertTrue(block.get("fixture_revision"))
            self.assertGreater(parsed_blocks, 0)
            self.assertEqual(ve.errors, [], ve.errors)
        finally:
            ve.EVALS_DIR = original_evals_dir
            reset()


class RegressionSemanticsTests(unittest.TestCase):
    def test_regression_labels_are_observations(self):
        self.assertEqual(
            ve.regression_status_for_verdict(True, False),
            ("candidate_only_pass", "observed_candidate_only_pass"),
        )
        self.assertEqual(
            ve.regression_status_for_verdict(False, True),
            ("reference_only_pass", "observed_reference_only_pass"),
        )
        self.assertEqual(
            ve.regression_status_for_verdict(True, True),
            ("both_pass", "observed_both_pass"),
        )
        self.assertEqual(
            ve.regression_status_for_verdict(False, False),
            ("both_fail", "observed_both_fail"),
        )


class ExpectedRouteNullTests(unittest.TestCase):
    """P1 schema: explicit expected_route null = 'no specialized skill
    expected'; missing route data is a schema error, never a null route."""

    def tearDown(self):
        reset()

    def test_explicit_null_route_accepted_in_confusion_set(self):
        ve.check_confusion_set(
            os.path.join(ROOT, "evaluations", "confusion-sets",
                         "design-change-family.json"),
            "evaluations/confusion-sets/design-change-family.json")
        self.assertEqual(ve.errors, [])

    def test_missing_expected_route_is_schema_error(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "cs.json")
            json.dump({"confusion_set": "x", "cluster": "review",
                       "skills": ["code-review", "security-review"],
                       "cases": [{"id": 1, "case_type": "workflow-transition",
                                  "prompt": "p",
                                  "turns": [{"user": "do it"}]}]},
                      open(path, "w"))
            ve.check_confusion_set(path, "evaluations/confusion-sets/x.json")
            self.assertTrue(any("expected_route" in e for e in ve.errors),
                            ve.errors)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_null_route_graded_as_no_specialized_skill(self):
        # The runner grades an explicit-null route as "the model must decline a
        # specialized skill" (selected == null), distinctly from a missing key
        # which is a malformed turn.
        from run_catalog_routing_eval import matches
        self.assertTrue(matches(None, None, []))
        self.assertFalse(matches("code-review", None, []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
