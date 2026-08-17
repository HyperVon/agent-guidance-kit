#!/usr/bin/env python3
"""Unit tests for the evaluation validator.

Run from repo root:  python3 scripts/test_validate_evaluations.py

Tests the validator's failure detection directly (no network / no real runs).
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_routing_catalog as brc
import docker_isolation_preflight as dip
import eval_hashing as eh
import run_catalog_routing_eval as rc
import validate_evaluations as ve


# Helper to reset the shared error/warning lists between tests.
def reset():
    ve.errors.clear()
    ve.warnings.clear()


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

    def test_execution_no_assertions(self):
        c = base_case(5, "edge", ["execution"],
                      execution={"expected_output": "out", "assertions": []})
        ve.check_case(fake_path(), "x/evals.json", c)
        self.assertTrue(any("execution.assertions invalid" in e for e in ve.errors))


class ResultFailureTests(unittest.TestCase):
    def tearDown(self):
        reset()

    def _result(self, mode="execution", **over):
        res = {
            "skill": "code-review",
            "evaluation_mode": mode,
            "method": "prompt-injection-approximation",
            "case_revision": "sha256:a",
            "fixture_revision": "sha256:b",
            "target_skill_revision": "sha256:c",
            "runtime": {"harness": "kilo", "harness_version": "unknown",
                        "model": "m", "reasoning_effort": "high",
                        "tool_policy": "sandbox", "network_policy": "none",
                        "isolation_method": "instruction-only (limited)"},
            "protocol": {"status": "limited", "worker_isolation_verified": True,
                         "target_loaded_in_guided": "ev", "target_absent_in_baseline": "ev",
                         "guided_skill_hash": "sha256:g", "baseline_guidance_absent": "ev",
                         "contamination": "none", "routing_mechanism": None},
            "runs": {"guided": {"session_id": "g1", "container_id": "cg1", "output_hash": "h",
                                "selected_skill": "code-review"},
                     "baseline": {"session_id": "b1", "container_id": "cb1", "output_hash": "h"}},
            "cases": [{
                "case_id": 1,
                "outcome": {"category": "skill_only_pass",
                            "measurement_status": "discriminating",
                            "protocol_status": "limited"},
                "verdict": {"guided_pass": True, "baseline_pass": False},
                "assertions": [{"assertion": "frozen", "guided": {"pass": True, "evidence": "e"},
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
        res["runs"]["guided"].pop("selected_skill")
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("selected_skill" in e for e in ve.errors))

    def test_execution_missing_baseline_absence(self):
        res = self._result()
        res["protocol"].pop("target_absent_in_baseline")
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("target_absent_in_baseline" in e for e in ve.errors))

    def test_passed_assertion_no_evidence(self):
        res = self._result()
        res["cases"][0]["assertions"][0]["guided"]["evidence"] = ""
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("passing guided assertion has no evidence" in e for e in ve.errors))

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
                      "target_loaded_in_guided": None,
                      "target_absent_in_baseline": None, "contamination": "none"},
            runs={"guided": {"session_id": "g1", "output_hash": "h",
                             "selected_skill": present},
                  "baseline": {"session_id": "b1", "output_hash": "h",
                               "selected_skill": absent}},
            cases=[{
                "case_id": 1,
                "outcome": {"category": "both_pass",
                            "measurement_status": "discriminating",
                            "protocol_status": "limited"},
                "verdict": {"guided_pass": True, "baseline_pass": True},
                "runs": {"guided": {"selected_skill": present},
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

    # --- new Docker execution evidence checks (mode == execution) ---
    def test_execution_shared_container_id_fails(self):
        res = self._result()
        res["runs"]["guided"]["container_id"] = "cb1"  # same as baseline
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("share a container_id" in e for e in ve.errors))

    def test_execution_missing_skill_hash_fails(self):
        res = self._result()
        res["protocol"].pop("guided_skill_hash")
        ve.check_one_result("r.md", res, {"code-review"}, {})
        self.assertTrue(any("guided_skill_hash" in e for e in ve.errors))

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
                      "target_loaded_in_guided": None,
                      "target_absent_in_baseline": None,
                      "guided_skill_hash": None, "baseline_guidance_absent": None,
                      "contamination": "none"},
            runs={"guided": {"session_id": "g1", "container_id": "cg1",
                             "output_hash": "h", "selected_skill": "code-review"},
                  "baseline": {"session_id": "b1", "container_id": "cb1",
                               "output_hash": "h", "selected_skill": None}},
            cases=[{
                "case_id": 1,
                "outcome": {"category": "both_pass",
                            "measurement_status": "discriminating",
                            "protocol_status": "limited"},
                "verdict": {"guided_pass": True, "baseline_pass": True},
                "runs": {"guided": {"selected_skill": "code-review"},
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


class EvidenceValidationTests(unittest.TestCase):
    def tearDown(self):
        reset()

    def _exec_evidence(self, **over_rep):
        rep = {
            "rep": 1,
            "workspace_path": "/work/task",
            "canonical_seed_hash": "sha256:seed",
            "guided_workspace_id": "ws-guided-1",
            "baseline_workspace_id": "ws-baseline-1",
            "guided": {
                "container_id": "cg", "session_id": "sg",
                "run_status": "success", "returncode": 0,
                "skill_mounted": True, "skill_hash": "sha256:skill",
                "guidance_verified": True, "guidance_probe": "present",
                "starting_fixture_hash": "sha256:seed", "ending_fixture_hash": "sha256:g",
                "output": "guided output", "stderr": ""},
            "baseline": {
                "container_id": "cb", "session_id": "sb",
                "run_status": "success", "returncode": 0,
                "skill_mounted": False,
                "guidance_verified_absent": True, "guidance_probe": "absent",
                "starting_fixture_hash": "sha256:seed", "ending_fixture_hash": "sha256:h",
                "output": "baseline output", "stderr": ""},
            "distinct_containers": True, "distinct_sessions": True,
            "starting_fixture_hashes_match": True, "workspace_paths_differ": True,
        }
        rep.update(over_rep)
        return {"evidence_type": "execution",
                "canonical_seed_hash": "sha256:seed",
                "expected_fixture_hash": "sha256:seed",
                "guidance_bundle_hash": "sha256:bundle",
                "repetitions": [rep]}

    def _cat_evidence(self, present_reps, absent_reps):
        return {"evidence_type": "catalog-routing", "conditions": {
            "target_present": {"repetitions": present_reps},
            "target_absent": {"repetitions": absent_reps}}}

    def test_execution_evidence_valid(self):
        self.assertEqual(ve.validate_execution_evidence(self._exec_evidence()), [])

    def test_execution_evidence_shared_container_fails(self):
        ev = self._exec_evidence()
        ev["repetitions"][0]["guided"]["container_id"] = "cb"
        self.assertTrue(any("distinct containers" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_baseline_leak_fails(self):
        ev = self._exec_evidence()
        ev["repetitions"][0]["baseline"]["guidance_verified_absent"] = False
        self.assertTrue(any("guidance_verified_absent" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_fixture_mismatch_fails(self):
        ev = self._exec_evidence()
        ev["repetitions"][0]["baseline"]["starting_fixture_hash"] = "sha256:other"
        self.assertTrue(any("starting fixture hashes differ" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_failed_run_rejected(self):
        # Defect 3/9: a failed Docker/Kilo run cannot be valid evidence.
        ev = self._exec_evidence()
        ev["repetitions"][0]["guided"]["run_status"] = "failed"
        ev["repetitions"][0]["guided"]["returncode"] = 1
        ev["repetitions"][0]["guided"]["guidance_verified"] = False
        ev["repetitions"][0]["guided"]["output"] = ""
        self.assertTrue(any("run_status" in e
                            for e in ve.validate_execution_evidence(ev)))

    def test_execution_evidence_shared_workspace_rejected(self):
        # Defect 1: guided and baseline must use independent workspace ids.
        ev = self._exec_evidence()
        ev["repetitions"][0]["baseline_workspace_id"] = "ws-guided-1"
        self.assertTrue(any("workspace ids" in e
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
        # Defect 5/14B: a failed model invocation must NOT be a null-selection pass.
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

    def test_malformed_exec_evidence_fails(self):
        # A malformed execution evidence file must cause validator failure.
        errs = self._run_check({
            "exec-bad.json": '{"evidence_type":"execution", "repetitions":[{"rep":1,'
                             '"guided":{"container_id":"g"},'
                             '"baseline":{"container_id":"g"}}]}'})
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
        errs = self._run_check({"catalog-routing-x.json": json.dumps(good)})
        self.assertEqual(errs, [], errs)


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

    def test_fixture_source_hash_mismatch_fails(self):
        # Item 4: a changed generator source without an updated source_hash fails.
        tmp = tempfile.mkdtemp()
        try:
            fxdir = os.path.join(tmp, "files")
            os.makedirs(fxdir)
            open(os.path.join(fxdir, "setup.sh"), "w").write(
                "#!/usr/bin/env bash\nset -e\necho hi > a.txt\n")
            fx = {"status": "ready", "type": "generator", "path": fxdir,
                  "source_hash": "sha256:" + "0" * 64,
                  "output_hash": "sha256:" + "0" * 64,
                  "content_hash": "sha256:" + "0" * 64}
            c = {"id": 1, "evaluation_modes": ["routing"], "fixture": fx}
            ve.check_fixture("x/evals.json", "x/evals.json", c, "x case 1")
            self.assertTrue(any("source_hash mismatch" in e for e in ve.errors))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

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
            os.makedirs(os.path.join(tmp, "files"))
            open(os.path.join(tmp, "files", "catalog.md"), "w").write("leak")
            open(os.path.join(tmp, "files", "x.txt"), "w").write("ok")
            c = base_case(1, "matching", ["routing", "execution"],
                          routing_context=routing_ctx(),
                          routing=routing_exp(),
                          execution=exec_exp(),
                          fixture={"status": "ready", "type": "committed",
                                   "path": os.path.join(tmp, "files"),
                                   "content_hash": "sha256:" + "0" * 64})
            ve.check_case(fake_path(), "x/evals.json", c)
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


class GeneratorHashSemanticsTests(unittest.TestCase):
    """Defect 2 / 14E: source_hash vs worker-visible output_hash semantics."""

    def tearDown(self):
        reset()

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
    """Defect 3 / 14C: execution evidence must anchor to the frozen fixture hash
    and freeze the injected guidance bundle."""

    def tearDown(self):
        reset()

    def _ev(self, **over):
        ev = {
            "evidence_type": "execution",
            "canonical_seed_hash": "sha256:seed",
            "expected_fixture_hash": "sha256:seed",
            "guidance_bundle_hash": "sha256:bundle",
            "repetitions": [{
                "rep": 1,
                "canonical_seed_hash": "sha256:seed",
                "guided_workspace_id": "ws-guided-1",
                "baseline_workspace_id": "ws-baseline-1",
                "guided": {"container_id": "cg", "session_id": "sg",
                           "run_status": "success", "returncode": 0,
                           "skill_mounted": True, "skill_hash": "sha256:skill",
                           "guidance_verified": True, "guidance_probe": "present",
                           "starting_fixture_hash": "sha256:seed",
                           "ending_fixture_hash": "sha256:g", "output": "out",
                           "stderr": ""},
                "baseline": {"container_id": "cb", "session_id": "sb",
                             "run_status": "success", "returncode": 0,
                             "skill_mounted": False,
                             "guidance_verified_absent": True,
                             "guidance_probe": "absent",
                             "starting_fixture_hash": "sha256:seed",
                             "ending_fixture_hash": "sha256:h", "output": "out",
                             "stderr": ""},
                "distinct_containers": True, "distinct_sessions": True,
                "starting_fixture_hashes_match": True,
                "workspace_paths_differ": True,
            }],
        }
        ev.update(over)
        return ev

    def test_valid_with_anchored_hash(self):
        self.assertEqual(ve.validate_execution_evidence(self._ev()), [])

    def test_missing_expected_fixture_hash_rejected(self):
        ev = self._ev()
        del ev["expected_fixture_hash"]
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("expected_fixture_hash" in e for e in errs), errs)

    def test_missing_guidance_bundle_rejected(self):
        ev = self._ev()
        del ev["guidance_bundle_hash"]
        errs = ve.validate_execution_evidence(ev)
        self.assertTrue(any("guidance_bundle_hash" in e for e in errs), errs)

    def test_frozen_hash_mismatch_rejected(self):
        # Guided and baseline start from identical copies, but the canonical seed
        # does not match the frozen expected hash -> evidence must be rejected.
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
