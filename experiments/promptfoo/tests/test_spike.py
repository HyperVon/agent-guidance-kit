"""Tests for the Promptfoo spike thin layer (corpus conversion, metrics,
protocol policy, workspace isolation, provenance)."""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKE = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(SPIKE))
sys.path.insert(0, REPO)

from experiments.promptfoo.assertions import protocol  # noqa: E402
from experiments.promptfoo.analysis.routing_metrics import build_aggregate  # noqa: E402
from experiments.promptfoo.generators import routing_cases  # noqa: E402
from experiments.promptfoo.lib.paths import (  # noqa: E402
    CONFUSION_SETS,
    GENERATED_DIR,
)
from experiments.promptfoo.lib.workspace import (  # noqa: E402
    install_skill_tree,
    materialize_skill_from_revision,
    workspace_path,
)


def make_row(case_id, rep, output=None, error=None, turns_json=None,
             expected="@null"):
    variables = {"case_id": case_id, "rep": rep,
                 "expected_skill": expected}
    if turns_json:
        variables["turns_json"] = turns_json
    response = {}
    if output is not None:
        response["output"] = output
    if error:
        response["error"] = error
    return {"vars": variables, "response": response,
            "error": error}


def decision_row(cid, rep, selected, expected):
    return make_row(cid, rep,
                    output=json.dumps({"selected_skill": selected}),
                    expected=expected)


class CorpusConversionTests(unittest.TestCase):
    def test_generated_tests_match_canonical_prompts(self):
        data = json.load(open(CONFUSION_SETS["review-family"]))
        skills = data["skills"]
        rows = routing_cases.build(None)
        kept = [r for r in rows if r[0] in set(skills)]
        catalog_text = routing_cases.render_catalog(kept)
        from scripts.run_catalog_routing_eval import build_confusion_prompt
        tests = json.load(open(os.path.join(
            GENERATED_DIR, "routing-review-family-tests.json")))
        by_desc = {t["description"]: t for t in tests}
        for case in data["cases"]:
            if case.get("turns"):
                continue
            expected_prompt = build_confusion_prompt(
                catalog_text, case["prompt"], skills)
            test = by_desc[f"case {case['id']} [{case['case_type']}] rep 1"]
            self.assertEqual(test["vars"]["prompt"], expected_prompt)
            expected = case.get("expected_skill")
            want = "@null" if expected is None else expected
            self.assertEqual(test["vars"]["expected_skill"], want)

    def test_generation_is_deterministic(self):
        path = os.path.join(GENERATED_DIR,
                            "routing-review-family-tests.json")
        before = open(path).read()
        routing_cases.generate("review-family", 3, path)
        after = open(path).read()
        self.assertEqual(before, after)


class FailureAccountingTests(unittest.TestCase):
    def test_failed_invocation_is_not_null(self):
        rows = [make_row(7, 1, error="kilo exited 1")]
        agg = build_aggregate(rows, ["code-review"])
        self.assertEqual(agg["attempted_decisions"], 1)
        self.assertEqual(agg["successful_decisions"], 0)
        self.assertEqual(len(agg["failed_decisions"]), 1)
        self.assertEqual(agg["null_decisions"], 0)
        self.assertEqual(agg["failed_decisions"][0]["case_id"], 7)

    def test_successful_null_is_not_failure(self):
        rows = [make_row(11, 1,
                         output=json.dumps({"selected_skill": None,
                                            "action": "clarify"}),
                         expected="@null")]
        agg = build_aggregate(rows, ["code-review"])
        self.assertEqual(agg["successful_decisions"], 1)
        self.assertEqual(len(agg["failed_decisions"]), 0)
        self.assertEqual(agg["null_decisions"], 1)

    def test_assertion_failure_with_valid_decision_is_observation(self):
        """A wrong-route row still carries a parseable decision in
        response.output; it must count as an incorrect observation, never as
        a failed invocation."""
        row = make_row(1, 2,
                       output=json.dumps({"selected_skill":
                                          "security-review"}),
                       expected="code-review")
        row["error"] = "expected='code-review' selected='security-review'"
        agg = build_aggregate(rows=[row], skills=["code-review",
                                                  "security-review"])
        self.assertEqual(agg["successful_decisions"], 1)
        self.assertEqual(len(agg["failed_decisions"]), 0)
        self.assertEqual(agg["correct_decisions"], 0)
        self.assertEqual(agg["confusion_matrix"]["code-review"],
                         {"security-review": 1})

    def test_attempted_invariant(self):
        rows = [
            decision_row(1, 1, "code-review", "code-review"),
            make_row(2, 1, error="timeout"),
            make_row(11, 1,
                     output=json.dumps({"selected_skill": None}),
                     expected="@null"),
        ]
        agg = build_aggregate(rows, ["code-review"])
        self.assertEqual(agg["attempted_decisions"],
                         agg["successful_decisions"]
                         + len(agg["failed_decisions"]))


class RoutingMetricsTests(unittest.TestCase):
    def test_confusion_matrix_and_per_skill(self):
        rows = [
            decision_row(1, 1, "code-review", "code-review"),
            decision_row(1, 2, "security-review", "code-review"),
            decision_row(2, 1, "threat-modeling", "threat-modeling"),
            decision_row(11, 1, None, "@null"),
        ]
        agg = build_aggregate(rows, ["code-review", "security-review",
                                     "threat-modeling"])
        matrix = agg["confusion_matrix"]
        self.assertEqual(matrix["code-review"],
                         {"code-review": 1, "security-review": 1})
        self.assertEqual(matrix["null"], {"null": 1})
        cr = agg["per_skill"]["code-review"]
        self.assertEqual((cr["tp"], cr["fp"], cr["fn"]), (1, 0, 1))
        self.assertAlmostEqual(cr["precision"], 1.0)
        self.assertAlmostEqual(cr["recall"], 0.5)
        tm = agg["per_skill"]["threat-modeling"]
        self.assertEqual((tm["tp"], tm["fp"], tm["fn"]), (1, 0, 0))

    def test_precision_recall_null_when_denominator_zero(self):
        rows = [decision_row(3, 1, "documentation-review",
                              "documentation-review")]
        agg = build_aggregate(rows, ["code-review"])
        cr = agg["per_skill"]["code-review"]
        self.assertIsNone(cr["precision"])
        self.assertIsNone(cr["recall"])

    def test_multi_turn_aggregation(self):
        turns_json = json.dumps([
            {"prompt": "p1", "expected_route": "review-feedback-resolution"},
            {"prompt": "p2", "expected_route": "review-feedback-resolution"},
        ])
        output = json.dumps({"turns": [
            {"turn": 1, "status": "success", "selected_skill":
             "review-feedback-resolution"},
            {"turn": 2, "status": "success", "selected_skill":
             "implementation-planning"},
        ]})
        row = make_row(13, 1, output=output, turns_json=turns_json,
                       expected="review-feedback-resolution")
        row["vars"]["expected_skill"] = "review-feedback-resolution"
        agg = build_aggregate([row], ["review-feedback-resolution",
                                      "implementation-planning"])
        self.assertEqual(agg["observations"], 2)
        self.assertEqual(agg["correct_decisions"], 1)
        self.assertIn(13, agg["multi_turn_cases"])

    def test_ambiguous_case_recorded(self):
        rows = [decision_row(11, 1, None, "@null")]
        agg = build_aggregate(rows, ["code-review"])
        self.assertIn(11, agg["ambiguous_null_cases"])


class ProtocolPolicyTests(unittest.TestCase):
    def route_ctx(self, expected):
        return {"vars": {"expected_skill": expected}}

    def test_decision_match_mismatch_null(self):
        ok = protocol.check_route_decision(
            json.dumps({"selected_skill": "code-review"}),
            self.route_ctx("code-review"))
        self.assertTrue(ok["pass"])
        wrong = protocol.check_route_decision(
            json.dumps({"selected_skill": "security-review"}),
            self.route_ctx("code-review"))
        self.assertFalse(wrong["pass"])
        null_ok = protocol.check_route_decision(
            json.dumps({"selected_skill": None}),
            self.route_ctx("@null"))
        self.assertTrue(null_ok["pass"])
        null_wrong = protocol.check_route_decision(
            json.dumps({"selected_skill": "code-review"}),
            self.route_ctx("@null"))
        self.assertFalse(null_wrong["pass"])

    def test_turns_incomplete_chain_fails(self):
        ctx = {"vars": {"turns_json": json.dumps([
            {"expected_route": "review-feedback-resolution"}])}}
        result = protocol.check_route_turns(json.dumps({"turns": []}), ctx)
        self.assertFalse(result["pass"])

    def test_baseline_excludes_skill_contract(self):
        entries = [
            {"assertion": "a", "scope": "skill-contract"},
            {"assertion": "b", "scope": "shared-outcome"},
            {"assertion": "c", "scope": "universal-safety"},
        ]
        kept, dropped = protocol.filter_assertions_by_scope(entries,
                                                            "baseline")
        self.assertEqual([e["scope"] for e in kept],
                         ["shared-outcome", "universal-safety"])
        self.assertEqual(dropped, [entries[0]])
        kept_t, _ = protocol.filter_assertions_by_scope(entries, "target")
        self.assertEqual(len(kept_t), 3)


class WorkspaceIsolationTests(unittest.TestCase):
    def test_target_and_baseline_paths_differ(self):
        a = workspace_path("exec", "code-review-c5", "target", 1)
        b = workspace_path("exec", "code-review-c5", "baseline", 1)
        self.assertNotEqual(a, b)

    def test_install_skill_tree_returns_hash(self):
        tmp = tempfile.mkdtemp(prefix="pf-test-skill-")
        ws = tempfile.mkdtemp(prefix="pf-test-ws-")
        try:
            src = os.path.join(tmp, "code-review")
            os.makedirs(src)
            with open(os.path.join(src, "SKILL.md"), "w") as f:
                f.write("---\nname: code-review\n---\nbody")
            h1 = install_skill_tree(ws, "code-review", src)
            installed = os.path.join(ws, ".kilo", "skills", "code-review",
                                     "SKILL.md")
            self.assertTrue(os.path.exists(installed))
            with open(os.path.join(src, "SKILL.md"), "w") as f:
                f.write("---\nname: code-review\n---\nbody2")
            h2 = install_skill_tree(ws, "code-review", src)
            self.assertNotEqual(h1, h2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(ws, ignore_errors=True)

    def test_revision_materialization_differs_between_revisions(self):
        cand_dir, cand_hash = materialize_skill_from_revision(
            "deeebfe1678e015b7f32de93833f01f544a21fcf", "code-review")
        ref_dir, ref_hash = materialize_skill_from_revision(
            "8adc094f203f8c09f44e7953b093912a31f36bd2", "code-review")
        try:
            self.assertNotEqual(cand_hash, ref_hash)
            self.assertTrue(os.path.exists(
                os.path.join(cand_dir, "SKILL.md")))
        finally:
            shutil.rmtree(os.path.dirname(cand_dir), ignore_errors=True)
            shutil.rmtree(os.path.dirname(ref_dir), ignore_errors=True)


class ProvenanceTests(unittest.TestCase):
    def test_regression_meta_records_shas(self):
        meta = json.load(open(os.path.join(
            GENERATED_DIR, "regression-tests.json.meta.json")))
        self.assertEqual(meta["candidate_git_sha"],
                         "deeebfe1678e015b7f32de93833f01f544a21fcf")
        self.assertEqual(meta["reference_git_sha"],
                         "8adc094f203f8c09f44e7953b093912a31f36bd2")

    def test_execution_meta_documents_architecture_gap(self):
        meta = json.load(open(os.path.join(
            GENERATED_DIR, "execution-tests.json.meta.json")))
        self.assertIn("designed_only", meta["architecture_review_note"])

    def test_fixture_hashes_stable_across_regeneration(self):
        m1 = os.path.join(GENERATED_DIR,
                          "routing-review-family-tests.json.meta.json")
        h_before = open(m1).read()
        routing_cases.generate("review-family", 3, os.path.join(
            GENERATED_DIR, "routing-review-family-tests.json"))
        self.assertEqual(h_before, open(m1).read())


if __name__ == "__main__":
    unittest.main()
