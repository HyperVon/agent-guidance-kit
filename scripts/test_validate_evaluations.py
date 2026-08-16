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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_routing_catalog as brc
import eval_hashing as eh
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
                         "contamination": "none", "routing_mechanism": None},
            "runs": {"guided": {"session_id": "g1", "output_hash": "h",
                                "selected_skill": "code-review"},
                     "baseline": {"session_id": "b1", "output_hash": "h"}},
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
