#!/usr/bin/env python3
"""Validation gate for the skill evaluation artifacts.

Checks:
  * case-set schema (split routing/execution oracles, 5 cases per skill,
    kind distribution, no leaked catalog, generator hashes);
  * personal-data / target-leak patterns in fixtures and results;
  * markdown link integrity;
  * result files (historical pilots stay exploratory/invalid; any other result
    file is validated against docs/evaluations/result-schema.md);
  * validation-matrix / SUMMARY consistency with discovered data;
  * no overload of `valid`/`✓` where the underlying result is invalid.

Run from the repo root:  python3 scripts/validate_evaluations.py
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_hashing import (HASH_PREFIX, canonical_hash, source_hash_of,
                          verify_generator_deterministic)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVALS_DIR = os.path.join(ROOT, "docs", "evaluations")
SKILLS_GLOB = os.path.join(ROOT, "skills", "*", "evals", "evals.json")

ALLOWED_KINDS = {"matching", "neighboring", "ambiguous", "edge"}
ALLOWED_MODES = {"routing", "execution"}
ALLOWED_FIXTURE_STATUS = {"ready", "designed_only"}
ALLOWED_FIXTURE_TYPES = {"committed", "generator"}
KIND_COUNTS = {"matching": 2, "neighboring": 1, "ambiguous": 1, "edge": 1}
ALLOWED_OUTCOME = {"skill_only_pass", "baseline_only_pass", "both_pass",
                   "both_fail", "invalid", "not_run"}
ALLOWED_MEASUREMENT = {"discriminating", "non_discriminating", "inconclusive"}
ALLOWED_PROTOCOL = {"valid", "limited", "contaminated", "invalid", "not_run"}
# Isolation methods that are NOT valid production isolation. A run claiming
# protocol.status == "valid" must use real OS-level isolation (container/gvisor/
# sandbox with a verified boundary), not instruction-only / prompt-only wording.
LIMITED_ISOLATION = ("instruction-only", "prompt-only", "no sandbox", "none",
                     "n/a", "unknown")
HISTORICAL = {"code-review.md", "git-github-workflow.md",
              "review-feedback-resolution.md", "security-review.md"}

# Personal / secret patterns that must never appear in committed fixtures/results.
LEAK_PATTERNS = [
    r"cvonness", r"charlesv", r"hypervon", r"gmail\.com",
    r"/Users/\w+", r"github\.com/HyperVon",
    r"cvonness@",
]

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


# --------------------------------------------------------------------------
# Case-set schema
# --------------------------------------------------------------------------
def check_skill_shape(evals, rel):
    """Per-skill case-set shape checks (5 cases, ids, kind distribution)."""
    if not isinstance(evals, list) or len(evals) != 5:
        err(f"{rel}: expected exactly 5 cases, got {len(evals) if isinstance(evals,list) else 'none'}")
        return
    ids = [c.get("id") for c in evals]
    if ids != [1, 2, 3, 4, 5]:
        err(f"{rel}: case ids must be [1,2,3,4,5], got {ids}")
    kind_counts = {}
    for c in evals:
        kind_counts[c.get("kind")] = kind_counts.get(c.get("kind"), 0) + 1
    for k, n in KIND_COUNTS.items():
        if kind_counts.get(k, 0) != n:
            err(f"{rel}: expected {n} '{k}' cases, found {kind_counts.get(k,0)}")


def check_eval_files():
    paths = sorted(glob.glob(SKILLS_GLOB))
    skill_names = set()
    case_index = {}  # skill -> {id: case}
    for f in paths:
        rel = os.path.relpath(f, ROOT)
        try:
            d = json.load(open(f))
        except Exception as e:
            err(f"{rel}: JSON parse error: {e}")
            continue
        if "skill_name" not in d:
            err(f"{rel}: missing skill_name")
            continue
        skill = d["skill_name"]
        skill_names.add(skill)
        expected = os.path.basename(os.path.dirname(os.path.dirname(f)))
        if skill != expected:
            err(f"{rel}: skill_name '{skill}' != dir name '{expected}'")
        evals = d.get("evals")
        if not isinstance(evals, list):
            err(f"{rel}: evals missing/empty")
            continue
        check_skill_shape(evals, rel)
        if len(evals) != 5:
            continue
        case_index[skill] = {c.get("id"): c for c in evals}
        for c in evals:
            check_case(f, rel, c)
    # No skill directory may ship without an eval set.
    check_skill_coverage(skill_names, ROOT)
    return skill_names, case_index


def check_skill_coverage(skill_names, base=ROOT):
    for sk in sorted(glob.glob(os.path.join(base, "skills", "*", "SKILL.md"))):
        name = os.path.basename(os.path.dirname(sk))
        if name not in skill_names:
            err(f"skill '{name}' has no evals/evals.json")


def check_case(f, rel, c):
    cid = c.get("id")
    tag = f"{rel} case {cid}"
    if "requires_catalog" in c:
        err(f"{tag}: legacy 'requires_catalog' must be removed (use routing_context)")
    modes = c.get("evaluation_modes")
    if not isinstance(modes, list) or not modes or not set(modes) <= ALLOWED_MODES:
        err(f"{tag}: bad evaluation_modes {modes}")
        modes = []
    if c.get("kind") not in ALLOWED_KINDS:
        err(f"{tag}: bad kind '{c.get('kind')}'")
    if not isinstance(c.get("prompt"), str) or not c["prompt"].strip():
        err(f"{tag}: empty prompt")
    is_routing = "routing" in modes
    is_exec = "execution" in modes

    if is_routing:
        rc = c.get("routing_context")
        if not isinstance(rc, dict) or rc.get("catalog_required") is not True:
            err(f"{tag}: routing case missing routing_context.catalog_required=true")
        else:
            if rc.get("comparison") not in ("target-present-vs-target-absent",
                                            "description-regression"):
                err(f"{tag}: routing_context.comparison invalid: {rc.get('comparison')}")
            if rc.get("catalog_source") != "generated-from-current-catalog":
                err(f"{tag}: routing_context.catalog_source must be 'generated-from-current-catalog'")
            if rc.get("target_skill") != skill_of(f):
                err(f"{tag}: routing_context.target_skill must equal the skill name")
        r = c.get("routing")
        if not isinstance(r, dict):
            err(f"{tag}: routing case missing 'routing' expectation")
        else:
            for key in ("experiment", "target_skill", "target_present", "target_absent"):
                if key not in r:
                    err(f"{tag}: routing expectation missing '{key}'")
            if r.get("target_skill") != skill_of(f):
                err(f"{tag}: routing.target_skill must equal the skill name")
            if c.get("kind") == "neighboring" and "allowed_behavior" not in r:
                err(f"{tag}: neighboring routing expectation needs allowed_behavior")
    else:
        if "routing" in c or "routing_context" in c:
            err(f"{tag}: execution-only case must not carry routing/routing_context")

    if is_exec:
        ex = c.get("execution")
        if not isinstance(ex, dict):
            err(f"{tag}: execution case missing 'execution' expectation")
        else:
            if not isinstance(ex.get("expected_output"), str) or not ex["expected_output"]:
                err(f"{tag}: execution.expected_output empty")
            a = ex.get("assertions")
            if not isinstance(a, list) or not a or not all(isinstance(x, str) and x.strip() for x in a):
                err(f"{tag}: execution.assertions invalid")
    else:
        if "execution" in c:
            err(f"{tag}: routing-only case must not carry an 'execution' block")

    check_fixture(f, rel, c, tag)


def skill_of(f):
    return os.path.basename(os.path.dirname(os.path.dirname(f)))


def check_fixture(f, rel, c, tag):
    fx = c.get("fixture")
    if not isinstance(fx, dict) or fx.get("status") not in ALLOWED_FIXTURE_STATUS:
        err(f"{tag}: bad fixture.status")
        return
    if fx["status"] == "designed_only":
        if "path" in fx:
            warn(f"{tag}: designed_only fixture has a path")
        return
    ftype = fx.get("type")
    if ftype not in ALLOWED_FIXTURE_TYPES:
        err(f"{tag}: ready fixture missing/invalid type")
        return
    p = fx.get("path")
    if not p:
        err(f"{tag}: ready fixture missing path")
        return
    fpath = os.path.join(os.path.dirname(os.path.dirname(f)), p)
    if not os.path.exists(fpath):
        err(f"{tag}: fixture path missing: {p}")
        return
    # No catalog.md may live inside a task fixture (routing surface leak).
    if any(name == "catalog.md" for _, _, names in os.walk(fpath) for name in names):
        err(f"{tag}: fixture contains catalog.md (routing surface must not live in the task fixture)")
    ch = fx.get("content_hash", "")
    if not (isinstance(ch, str) and ch.startswith(HASH_PREFIX) and len(ch) > len(HASH_PREFIX)):
        err(f"{tag}: fixture missing/invalid content_hash")
        return
    if ftype == "generator":
        src = fx.get("source", "setup.sh")
        src_path = os.path.join(fpath, src)
        if not fx.get("source_hash", "").startswith(HASH_PREFIX):
            err(f"{tag}: generator missing source_hash")
        if not fx.get("output_hash", "").startswith(HASH_PREFIX):
            err(f"{tag}: generator missing output_hash")
        if not os.path.exists(src_path):
            err(f"{tag}: generator source missing: {src}")
            return
        # Real source-hash validation: the recorded source_hash must match the
        # generator source on disk. A changed setup.sh without an updated
        # source_hash must fail.
        try:
            sh = source_hash_of(src_path)
        except Exception as e:
            err(f"{tag}: cannot read generator source: {e}")
            return
        if HASH_PREFIX + sh != fx.get("source_hash"):
            err(f"{tag}: source_hash mismatch (generator source '{src}' changed "
                f"without updating source_hash)")
        # Real output-hash validation with a deterministic double-run: the generator
        # must produce the SAME output on two independent runs, and that output must
        # match the recorded content_hash / output_hash.
        inv = fx.get("invocation", "bash setup.sh")
        try:
            computed = verify_generator_deterministic(fpath, src, inv)
        except ValueError as e:
            err(f"{tag}: {e}")
            return
        except Exception as e:
            err(f"{tag}: generator could not run: {e}")
            return
        if HASH_PREFIX + computed != fx["content_hash"]:
            err(f"{tag}: generator content_hash mismatch (recorded {ch[:10]}.. computed {HASH_PREFIX+computed[:10]}..)")
        if HASH_PREFIX + computed != fx.get("output_hash"):
            err(f"{tag}: generator output_hash does not match generated output")
    else:
        computed = canonical_hash(fpath, "committed")
        if HASH_PREFIX + computed != ch:
            err(f"{tag}: fixture hash mismatch (recorded {ch[:10]}.. computed {HASH_PREFIX+computed[:10]}..)")


# --------------------------------------------------------------------------
# Leaks
# --------------------------------------------------------------------------
def check_leaks():
    targets = []
    for ext in ("md", "json"):
        targets += glob.glob(os.path.join(ROOT, "docs", "evaluations", "**", f"*.{ext}"), recursive=True)
        targets += glob.glob(os.path.join(ROOT, "skills", "*", "evals", "**", f"*.{ext}"), recursive=True)
    targets += glob.glob(os.path.join(ROOT, "skills", "*", "evals", "files", "**", "*"), recursive=True)
    for t in set(targets):
        if os.path.isdir(t):
            continue
        try:
            text = open(t, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for pat in LEAK_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                err(f"LEAK {os.path.relpath(t, ROOT)}: matches /{pat}/")


# --------------------------------------------------------------------------
# Links
# --------------------------------------------------------------------------
def check_links():
    md_files = glob.glob(os.path.join(ROOT, "docs", "evaluations", "**", "*.md"), recursive=True)
    md_files += glob.glob(os.path.join(ROOT, "skills", "skill-evaluation", "**", "*.md"), recursive=True)
    for mf in md_files:
        text = open(mf, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
            link = m.group(2)
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            if link.startswith("#"):
                continue
            anchor = ""
            if "#" in link:
                link, anchor = link.split("#", 1)
            if not link:
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(mf), link))
            if not os.path.exists(target):
                err(f"{os.path.relpath(mf, ROOT)}: broken link {link}")


# --------------------------------------------------------------------------
# Result files
# --------------------------------------------------------------------------
def extract_result_json(text):
    out = []
    for m in re.finditer(r"```result-json\s*\n(.*?)```", text, re.DOTALL):
        try:
            out.append(json.loads(m.group(1)))
        except Exception:
            pass
    return out


def check_results(skill_names, case_index):
    res_dir = os.path.join(EVALS_DIR, "results")
    if not os.path.isdir(res_dir):
        return
    for rf in sorted(glob.glob(os.path.join(res_dir, "*.md"))):
        base = os.path.basename(rf)
        text = open(rf, encoding="utf-8", errors="replace").read()
        if base in HISTORICAL:
            check_historical_result(base, text)
            continue
        check_real_result(base, text, skill_names, case_index)


def check_historical_result(base, text):
    if "protocol_status: invalid" not in text and "exploratory" not in text.lower():
        err(f"{base}: historical pilot must be marked exploratory/invalid")
    if "✓" in text:
        err(f"{base}: must not present an overloaded ✓ validation")
    if "authoritative" in text.lower():
        err(f"{base}: must not use 'authoritative' for a single pilot")


def check_real_result(base, text, skill_names, case_index):
    blocks = extract_result_json(text)
    if not blocks:
        err(f"{base}: a real run result must contain a ```result-json block with the required metadata")
        return
    for res in blocks:
        check_one_result(base, res, skill_names, case_index)


def check_one_result(base, res, skill_names, case_index):
    skill = res.get("skill")
    if skill not in skill_names:
        err(f"{base}: result skill '{skill}' not in discovered skills")
    mode = res.get("evaluation_mode")
    if mode not in ALLOWED_MODES:
        err(f"{base}: evaluation_mode '{mode}' invalid")
    for key in ("method", "case_revision", "fixture_revision", "target_skill_revision"):
        if not res.get(key):
            err(f"{base}: missing identity field '{key}'")
    rt = res.get("runtime") or {}
    for key in ("harness", "model", "reasoning_effort", "tool_policy",
               "network_policy", "isolation_method"):
        if not rt.get(key):
            err(f"{base}: missing runtime field '{key}'")
    if rt.get("harness_version") is None and False:
        pass  # harness_version may be 'unknown'
    pr = res.get("protocol") or {}
    status = pr.get("status")
    if status not in ALLOWED_PROTOCOL:
        err(f"{base}: protocol.status '{status}' invalid")
    if not isinstance(pr.get("worker_isolation_verified"), bool):
        err(f"{base}: protocol.worker_isolation_verified must be boolean")
    if status == "valid" and pr.get("worker_isolation_verified") is not True:
        err(f"{base}: valid run requires worker_isolation_verified=true")
    if status == "valid":
        im = (rt.get("isolation_method") or "").lower()
        if any(kw in im for kw in LIMITED_ISOLATION):
            err(f"{base}: valid run requires OS-level isolation, but isolation_method "
                f"is '{rt.get('isolation_method')}' (limited-grade only)")
    if mode == "execution":
        if not pr.get("target_loaded_in_guided"):
            err(f"{base}: execution result missing target_loaded_in_guided evidence")
        if not pr.get("target_absent_in_baseline"):
            err(f"{base}: execution result missing target_absent_in_baseline evidence (target absence unverified)")
    if mode == "routing":
        if not pr.get("routing_mechanism"):
            err(f"{base}: routing result missing routing_mechanism (selected skill unverified)")
    # Worker / run identity
    runs = res.get("runs") or {}
    g = runs.get("guided") or {}
    b = runs.get("baseline") or {}
    if not g.get("session_id") or not b.get("session_id"):
        err(f"{base}: result must record distinct guided/baseline session_ids")
    elif g["session_id"] == b["session_id"]:
        err(f"{base}: guided and baseline share a session_id (contamination)")
    # Protocol-validity gates: invalid/contaminated cannot produce success.
    if status in ("invalid", "contaminated"):
        for cs in res.get("cases", []):
            cat = (cs.get("outcome") or {}).get("category")
            if cat in ("skill_only_pass", "baseline_only_pass", "both_pass"):
                err(f"{base} case {cs.get('case_id')}: {status} result cannot claim a success outcome ({cat})")
    for cs in res.get("cases", []):
        check_result_case(base, cs, skill, mode, case_index)


def check_result_case(base, cs, skill, mode, case_index):
    cid = cs.get("case_id")
    if not isinstance(cid, int):
        err(f"{base}: case_id must be integer")
        return
    oc = cs.get("outcome") or {}
    cat = oc.get("category")
    if cat not in ALLOWED_OUTCOME:
        err(f"{base} case {cid}: outcome.category '{cat}' invalid")
    if oc.get("measurement_status") not in ALLOWED_MEASUREMENT:
        err(f"{base} case {cid}: outcome.measurement_status invalid")
    if oc.get("protocol_status") not in ALLOWED_PROTOCOL:
        err(f"{base} case {cid}: outcome.protocol_status invalid")
    # outcome <-> verdict consistency (verdict booleans are required for every mode)
    verdict = cs.get("verdict") or {}
    gp = verdict.get("guided_pass")
    bp = verdict.get("baseline_pass")
    if not isinstance(gp, bool) or not isinstance(bp, bool):
        err(f"{base} case {cid}: missing verdict.guided_pass/baseline_pass booleans")
        return
    expect = None
    if gp and not bp:
        expect = "skill_only_pass"
    elif bp and not gp:
        expect = "baseline_only_pass"
    elif gp and bp:
        expect = "both_pass"
    elif not gp and not bp:
        expect = "both_fail"
    if expect and cat != expect:
        err(f"{base} case {cid}: outcome.category '{cat}' inconsistent with verdict (expected {expect})")

    if mode == "routing":
        check_routing_result_case(base, cs, skill, case_index, cid, gp, bp)
    else:
        check_exec_result_case(base, cs, skill, case_index, cid)


def _routing_match(selected, expected, fallbacks):
    """Whether a captured selection satisfies the routing expectation.

    For a target-absent expectation (expected is None) a null selection or any
    allowed fallback is acceptable; for a target-present expectation the selected
    skill must equal the expected skill or be an allowed fallback.
    """
    fallbacks = fallbacks or []
    if expected is not None:
        return selected == expected or selected in fallbacks
    return selected is None or selected in fallbacks


def check_routing_result_case(base, cs, skill, case_index, cid, gp, bp):
    """Routing results grade harness selection evidence, not worker output.

    Requires both routing conditions (target-present == runs.guided, target-absent
    == runs.baseline) to be present, and verifies the captured selected skills
    against the case's routing expectation. No execution assertions are graded.
    """
    rn = cs.get("runs") or {}
    g = rn.get("guided") or {}
    b = rn.get("baseline") or {}
    # target-present condition evidence (a concrete selected skill must exist)
    sel_p = g.get("selected_skill")
    if not sel_p:
        err(f"{base} case {cid}: routing result missing target-present selected_skill "
            f"evidence (captured harness selection is required)")
    # target-absent condition evidence (selected skill or explicit null selection)
    if "baseline" not in rn:
        err(f"{base} case {cid}: routing result missing target-absent condition "
            f"(runs.baseline must be present)")
        return
    if "selected_skill" not in b:
        err(f"{base} case {cid}: routing result missing target-absent selected_skill "
            f"evidence (captured selection or explicit null is required)")
        return
    sel_a = b.get("selected_skill")

    exp = {}
    if skill in case_index and cid in case_index[skill]:
        exp = case_index[skill][cid].get("routing") or {}
    tp = exp.get("target_present") or {}
    ta = exp.get("target_absent") or {}
    exp_present = tp.get("expected_selected_skill")
    exp_absent = ta.get("expected_selected_skill")
    fallbacks = ta.get("allowed_fallbacks") or []

    guided_ok = _routing_match(sel_p, exp_present, tp.get("allowed_fallbacks") or [])
    baseline_ok = _routing_match(sel_a, exp_absent, fallbacks)
    # The verdict must reflect the actual captured selection: a routing result may
    # not claim success on a condition whose captured selection does not match.
    if exp and (gp != guided_ok or bp != baseline_ok):
        err(f"{base} case {cid}: routing verdict (guided_pass={gp}, baseline_pass={bp}) "
            f"does not match captured selection (present={sel_p!r}->{exp_present!r}, "
            f"absent={sel_a!r}->{exp_absent!r}, fallbacks={fallbacks!r})")


def check_exec_result_case(base, cs, skill, case_index, cid):
    """Execution results grade frozen assertions with evidence on both conditions."""
    assertions = cs.get("assertions") or []
    if not isinstance(assertions, list) or not assertions:
        err(f"{base} case {cid}: execution result must grade at least one assertion")
        return
    frozen = []
    if skill in case_index and cid in case_index[skill]:
        frozen = case_index[skill][cid].get("execution", {}).get("assertions", [])
    graded_texts = [a.get("assertion") for a in assertions]
    for fa in frozen:
        if fa not in graded_texts:
            err(f"{base} case {cid}: frozen assertion missing from graded result: {fa[:60]}")
    for a in assertions:
        for cond in ("guided", "baseline"):
            g = a.get(cond) or {}
            if not isinstance(g.get("pass"), bool):
                err(f"{base} case {cid}: assertion missing {cond}.pass")
            elif g["pass"] is True and not str(g.get("evidence", "")).strip():
                err(f"{base} case {cid}: passing {cond} assertion has no evidence")


# --------------------------------------------------------------------------
# Matrix / summary consistency
# --------------------------------------------------------------------------
def check_matrix_sync(skill_names):
    matrix = os.path.join(EVALS_DIR, "validation-matrix.md")
    if not os.path.exists(matrix):
        return
    text = open(matrix, encoding="utf-8", errors="replace").read()
    for sn in skill_names:
        if f"skills/{sn}/evals/evals.json" not in text:
            err(f"matrix missing row for skill '{sn}'")
    # result links must resolve
    for m in re.finditer(r"\]\((results/[^)]+)\)", text):
        tgt = os.path.join(EVALS_DIR, m.group(1))
        if not os.path.exists(tgt):
            err(f"matrix broken result link {m.group(1)}")
    # Per-row agreement between the matrix and the linked result file.
    res_dir = os.path.join(EVALS_DIR, "results")
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 8:
            continue
        # cells: ['', skill, cases, fixtures, routing, execution, protocol, repeats, result]
        skill_cell = cells[1]
        routing_cell = cells[4].lower()
        execution_cell = cells[5].lower()
        proto_cell = cells[6].lower()
        result_cell = cells[8] if len(cells) > 8 else (cells[7] if len(cells) > 7 else "")
        m = re.search(r"\((results/[^)]+)\)", result_cell)
        if not m:
            continue
        rpath = os.path.join(EVALS_DIR, m.group(1))
        if not os.path.exists(rpath):
            continue
        rtext = open(rpath, encoding="utf-8", errors="replace").read()
        base = os.path.basename(rpath)
        is_invalid = ("protocol_status: invalid" in rtext) or \
                    (base in HISTORICAL and "exploratory" in rtext.lower())
        if is_invalid:
            # A matrix cell must not claim `valid` for an invalid result.
            for label, cell in (("routing", routing_cell), ("execution", execution_cell),
                                ("protocol", proto_cell)):
                if cell == "valid":
                    err(f"matrix row '{skill_cell}': {label} 'valid' but linked result is invalid")
        # A routing cell may only be 'valid' when a routing result carries
        # captured selected-skill evidence.
        if routing_cell == "valid":
            blocks = extract_result_json(rtext)
            has_routing_evidence = any(
                (b.get("evaluation_mode") == "routing") and
                ((b.get("runs") or {}).get("guided") or {}).get("selected_skill")
                for b in blocks
            )
            if not has_routing_evidence:
                err(f"matrix row '{skill_cell}': routing 'valid' without captured routing evidence")


def check_summary(skill_names):
    summary = os.path.join(EVALS_DIR, "SUMMARY.md")
    if not os.path.exists(summary):
        return
    text = open(summary, encoding="utf-8", errors="replace").read()
    if str(len(skill_names)) not in text:
        err("SUMMARY.md does not mention the discovered skill count")
    if "130" not in text:
        err("SUMMARY.md does not mention 130 cases")
    if "4/26" not in text and "4 / 26" not in text:
        warn("SUMMARY.md does not mention fixtures frozen for 4/26 skills")


# --------------------------------------------------------------------------
def main():
    print("=== Evaluating skill eval artifacts ===")
    skill_names, case_index = check_eval_files()
    check_leaks()
    check_links()
    check_results(skill_names, case_index)
    check_matrix_sync(skill_names)
    check_summary(skill_names)

    print(f"\nSkills with evals.json: {len(skill_names)}")
    print(f"Hard errors: {len(errors)}")
    print(f"Warnings:   {len(warnings)}")
    for w in warnings:
        print("  WARN:", w)
    for e in errors:
        print("  ERR :", e)
    if errors:
        print("\nVALIDATION FAILED")
        sys.exit(1)
    print("\nVALIDATION PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
