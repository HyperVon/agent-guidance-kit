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
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_hashing import (HASH_PREFIX, canonical_hash, source_hash_of,
                          verify_generator_deterministic)

try:
    import run_execution_eval as execution_runner
except ImportError:  # pragma: no cover - direct library import fallback
    execution_runner = None
try:
    import run_catalog_routing_eval as catalog_runner
except ImportError:  # pragma: no cover - direct library import fallback
    catalog_runner = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVALS_DIR = os.path.join(ROOT, "docs", "evaluations")
SKILLS_GLOB = os.path.join(ROOT, "skills", "*", "evals", "evals.json")
# Repository-level evaluation corpora (shared cross-skill cases and holdouts).
CONFUSION_GLOB = os.path.join(ROOT, "evaluations", "confusion-sets", "*.json")
HOLDOUT_GLOB = os.path.join(ROOT, "evaluations", "holdout", "*.json")

# Case classification: the design intent of a case, independent of its
# ``kind``. ``smoke`` cases are obvious sanity checks (keep them cheap, do not
# claim they prove robust routing); ``discriminator``-family cases are the
# difficult, high-evidence cases. ``counterfactual`` cases are members of a
# minimal pair (paired via ``counterfactual_pair``) and the paired member lives
# in the confusion set that owns the pair (never inside a skill's own eval set).
ALLOWED_CASE_TYPES = {
    "smoke", "discriminator", "counterfactual", "misleading-keyword",
    "hard-negative", "ambiguous-natural", "multi-intent",
    "workflow-transition", "harness-native",
}
# A counterfactual must declare a pair id; only the confusion-set owner may
# host counterfactual cases.
COUNTERFACTUAL_TYPES = {"counterfactual"}

ALLOWED_KINDS = {"matching", "neighboring", "ambiguous", "edge"}
# Three-layer model (see RUNBOOK.md / skills/skill-evaluation/SKILL.md):
#   * routing-family  : portable, harness-independent router selection
#       - "routing"           : legacy / harness-integrated routing
#       - "catalog-routing"   : Layer A — model-as-classifier over a neutral catalog
#       - "harness-routing"   : Layer C — optional harness-integration routing
#   * execution        : Layer B — Docker-isolated target vs baseline vs placebo efficacy
ROUTING_MODES = {"routing", "catalog-routing", "harness-routing"}
EXEC_MODES = {"execution"}
ALLOWED_MODES = ROUTING_MODES | EXEC_MODES
ALLOWED_FIXTURE_STATUS = {"ready", "designed_only"}
ALLOWED_FIXTURE_TYPES = {"committed", "generator"}
KIND_COUNTS = {"matching": 2, "neighboring": 1, "ambiguous": 1, "edge": 1}
ALLOWED_OUTCOME = {"skill_only_pass", "baseline_only_pass", "both_pass",
                   "both_fail", "non_discriminating", "invalid", "not_run"}
ALLOWED_MEASUREMENT = {"discriminating", "non_discriminating", "inconclusive"}
ALLOWED_PROTOCOL = {"valid", "limited", "contaminated", "invalid", "not_run"}
# Assertion types: hard behavioral invariants vs quality criteria vs
# presentation/process preferences. Soft preferences must not be graded as
# hard pass/fail correctness.
ALLOWED_ASSERTION_TYPES = {"behavioral", "quality", "presentation"}
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
    # Case type (design intent): distinguishes cheap smoke coverage from the
    # difficult discriminator cases. Defaults to "smoke" for legacy cases so old
    # packs remain valid while their honest classification is explicit.
    ctype = c.get("case_type", "smoke")
    if ctype not in ALLOWED_CASE_TYPES:
        err(f"{tag}: bad case_type '{ctype}'")
    if ctype in COUNTERFACTUAL_TYPES:
        # Counterfactual members must declare their pair and may only live in
        # the confusion set that owns the pair (they are NEVER inside a skill's
        # own eval pack — the paired case must not be visible there).
        pair = c.get("counterfactual_pair")
        if not (isinstance(pair, str) and pair.strip()):
            err(f"{tag}: counterfactual case missing counterfactual_pair id")
        if not rel.startswith(os.path.join("evaluations", "confusion-sets")):
            err(f"{tag}: counterfactual case must live in a confusion-set file "
                f"(not inside a skill's own eval pack)")
    is_routing = bool(set(modes) & ROUTING_MODES)
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
            if not isinstance(r.get("experiment"), str) or not r["experiment"].strip():
                err(f"{tag}: routing.experiment must be a non-empty string")
            for oracle_name in ("target_present", "target_absent"):
                oracle = r.get(oracle_name)
                if not isinstance(oracle, dict):
                    continue
                if "expected_selected_skill" not in oracle:
                    err(f"{tag}: routing.{oracle_name} missing "
                        "expected_selected_skill")
                elif oracle["expected_selected_skill"] is not None and \
                        not isinstance(oracle["expected_selected_skill"], str):
                    err(f"{tag}: routing.{oracle_name}.expected_selected_skill "
                        "must be a skill name or null")
                fallbacks = oracle.get("allowed_fallbacks", [])
                if not isinstance(fallbacks, list) or any(
                        not isinstance(x, str) for x in fallbacks):
                    err(f"{tag}: routing.{oracle_name}.allowed_fallbacks "
                        "must be a list of skill names")
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
            if not isinstance(a, list) or not a or not all(
                    isinstance(x, str) and x.strip()
                    or isinstance(x, dict) and isinstance(x.get("text"), str)
                    and x["text"].strip() for x in a):
                err(f"{tag}: execution.assertions invalid")
            check_assertion_types(ex, tag)
            # Placeholder guidance declaration: a case whose execution depends
            # on guidance the worker has not been given yet must say so instead
            # of claiming a runnable efficacy benchmark.
            ph = ex.get("placeholder_guidance")
            if ph is not None and not isinstance(ph, str):
                err(f"{tag}: execution.placeholder_guidance must be a string")
            if ph:
                if c.get("fixture", {}).get("status") != "designed_only":
                    err(f"{tag}: placeholder_guidance declared but fixture is ready "
                        f"(placeholder is only for designed-only cases)")
    else:
        if "execution" in c:
            err(f"{tag}: routing-only case must not carry an 'execution' block")

    # Multi-turn cases: ordered turns; each turn carries the user text and the
    # expected route; the whole case must not leak expectations into prompts.
    # ``expected_route`` is REQUIRED per turn: a skill name, or explicit null
    # meaning "no specialized skill expected" (ordinary unspecialized work must
    # not be encoded as any skill, including implementation-planning, which
    # explicitly stops before implementation). Missing route data is a schema
    # error, never silently treated as null.
    turns = c.get("turns")
    if turns is not None:
        if not isinstance(turns, list) or not turns:
            err(f"{tag}: 'turns' must be a non-empty ordered list")
        else:
            for i, t in enumerate(turns, 1):
                if not isinstance(t, dict) or not isinstance(t.get("user"), str) \
                        or not t["user"].strip():
                    err(f"{tag}: turn {i} missing non-empty 'user' text")
                if "expected_route" not in t:
                    err(f"{tag}: turn {i} missing 'expected_route' "
                        f"(null means 'no specialized skill expected')")
                elif t["expected_route"] is not None and \
                        not isinstance(t["expected_route"], str):
                    err(f"{tag}: turn {i} expected_route must be a skill name "
                        f"or null")
            if c.get("case_type") not in ("workflow-transition", "harness-native"):
                err(f"{tag}: multi-turn case must set case_type workflow-transition "
                    f"or harness-native")

    check_fixture(f, rel, c, tag)


def check_assertion_types(ex, tag):
    """Assertions are either plain strings (legacy, treated as behavioral) or
    objects with an explicit ``type``. Soft presentation/process preferences
    must never be graded as hard behavioral pass/fail, so a case that uses
    typed assertions must say which is which."""
    for a in ex.get("assertions", []):
        if isinstance(a, dict):
            if "text" not in a or not isinstance(a["text"], str) or not a["text"].strip():
                err(f"{tag}: assertion object missing 'text'")
            at = a.get("type")
            if at is None:
                err(f"{tag}: assertion object missing 'type'")
            elif at not in ALLOWED_ASSERTION_TYPES:
                err(f"{tag}: bad assertion type '{at}'")


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
    method = res.get("method")
    if method not in {"docker-isolated", "harness-routing"}:
        err(f"{base}: method '{method}' invalid; expected docker-isolated or harness-routing")
    rt = res.get("runtime") or {}
    for key in ("harness", "model", "reasoning_effort", "tool_policy",
                "network_policy", "isolation_method"):
        if not rt.get(key):
            err(f"{base}: missing runtime field '{key}'")
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
    if mode in EXEC_MODES:
        if not pr.get("target_guidance_present"):
            err(f"{base}: execution result missing target_guidance_present evidence")
        if not pr.get("target_absent_in_baseline"):
            err(f"{base}: execution result missing target_absent_in_baseline evidence (target absence unverified)")
        if not pr.get("target_guidance_hash"):
            err(f"{base}: execution result missing target_guidance_hash (mounted guidance unverified)")
        if not pr.get("baseline_guidance_absent"):
            err(f"{base}: execution result missing baseline_guidance_absent evidence (baseline received no guidance)")
        # Docker execution: the target and baseline workers must run in distinct
        # fresh containers, not a shared process.
        runs = res.get("runs") or {}
        g_cid = (runs.get("target") or {}).get("container_id")
        b_cid = (runs.get("baseline") or {}).get("container_id")
        if not g_cid or not b_cid:
            err(f"{base}: execution result must record distinct target/baseline container_ids")
        elif g_cid == b_cid:
            err(f"{base}: target and baseline share a container_id (contamination)")
    if mode in ROUTING_MODES:
        if not pr.get("routing_mechanism"):
            err(f"{base}: routing result missing routing_mechanism (selected skill unverified)")
    # Worker / run identity
    runs = res.get("runs") or {}
    g = runs.get("target") or {}
    b = runs.get("baseline") or {}
    if not g.get("session_id") or not b.get("session_id"):
        err(f"{base}: result must record distinct target/baseline session_ids")
    elif g["session_id"] == b["session_id"]:
        err(f"{base}: target and baseline share a session_id (contamination)")
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
    gp = verdict.get("target_pass")
    bp = verdict.get("baseline_pass")
    pp = verdict.get("placebo_pass")
    if not isinstance(gp, bool) or not isinstance(bp, bool):
        err(f"{base} case {cid}: missing verdict.target_pass/baseline_pass booleans")
        return
    expect = None
    if gp and not bp:
        # skill_only_pass requires placebo to fail (or not be run)
        if pp is False or pp is None:
            expect = "skill_only_pass"
    elif bp and not gp:
        # baseline_only_pass: placebo status doesn't change the category
        expect = "baseline_only_pass"
    elif gp and bp:
        # target and baseline both pass: non_discriminating when placebo also
        # passes (every condition wins, benchmark is ceiling-effected); otherwise
        # both_pass (benchmark at least separates real guidance from placebo).
        if pp is True:
            expect = "non_discriminating"
        else:
            expect = "both_pass"
    elif not gp and not bp:
        # both_fail requires placebo to fail (or not be run); if placebo passes
        # while target/baseline fail, the outcome is undefined in the schema.
        if pp is False or pp is None:
            expect = "both_fail"
        else:
            # pp is True but target/baseline both fail: not a defined category.
            # Reject as inconsistent — placebo should not outperform both.
            expect = "both_fail"  # still flag as inconsistent below
    if expect and cat != expect:
        err(f"{base} case {cid}: outcome.category '{cat}' inconsistent with verdict (expected {expect})")

    if mode in ROUTING_MODES:
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

    Requires both routing conditions (target-present == runs.target, target-absent
    == runs.baseline) to be present, and verifies the captured selected skills
    against the case's routing expectation. No execution assertions are graded.
    """
    rn = cs.get("runs") or {}
    g = rn.get("target") or {}
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

    target_ok = _routing_match(sel_p, exp_present, tp.get("allowed_fallbacks") or [])
    baseline_ok = _routing_match(sel_a, exp_absent, fallbacks)
    # The verdict must reflect the actual captured selection: a routing result may
    # not claim success on a condition whose captured selection does not match.
    if exp and (gp != target_ok or bp != baseline_ok):
        err(f"{base} case {cid}: routing verdict (target_pass={gp}, baseline_pass={bp}) "
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
        for cond in ("target", "baseline", "placebo"):
            if cond not in a:
                continue
            g = a.get(cond) or {}
            if not isinstance(g.get("pass"), bool):
                err(f"{base} case {cid}: assertion missing {cond}.pass")
            elif g["pass"] is True and not str(g.get("evidence", "")).strip():
                err(f"{base} case {cid}: passing {cond} assertion has no evidence")


# --------------------------------------------------------------------------
# Evidence-file validation (local .eval-evidence/*.json from the runners)
# --------------------------------------------------------------------------
# Worker-visible text that must never appear in an execution run's prompt.
# "target" is excluded because it is a common English word; the conditions are
# proven independent by the identical-task-hash invariant, not by forbidding a
# word.
LEAKY_PROMPT_TOKENS = ("baseline", "placebo", "eval", "evaluation",
                       "experiment", "condition")


def _execution_source_anchor(evidence, errs):
    """Resolve the current execution case and its frozen source hashes."""
    skill = evidence.get("skill")
    case_id = evidence.get("case_id")
    if not isinstance(skill, str) or not skill:
        errs.append("execution evidence missing skill")
        return None
    if not isinstance(case_id, int):
        errs.append("execution evidence missing integer case_id")
        return None
    evals_path = os.path.join(ROOT, "skills", skill, "evals", "evals.json")
    if not os.path.isfile(evals_path):
        errs.append(f"execution evidence skill evals not found: {skill}")
        return None
    try:
        source = json.load(open(evals_path, encoding="utf-8"))
    except (OSError, TypeError, ValueError) as exc:
        errs.append(f"execution source evals unreadable: {exc}")
        return None
    case = next((c for c in source.get("evals", [])
                 if c.get("id") == case_id), None)
    if case is None:
        errs.append("execution evidence case_id is not present in the current "
                    "skill evals")
        return None
    if "execution" not in case.get("evaluation_modes", []):
        errs.append("execution evidence case is not an execution case in the "
                    "current skill evals")
        return None
    fx = case.get("fixture") or {}
    expected = (fx.get("output_hash") if fx.get("type") == "generator"
                else fx.get("content_hash"))
    evals_rel = os.path.relpath(evals_path, ROOT)
    skill_rel = os.path.dirname(os.path.dirname(evals_rel))
    fixture_rel = os.path.normpath(os.path.join(
        skill_rel, fx.get("path", "")))
    source_hash = HASH_PREFIX + hashlib.sha256(
        open(evals_path, "rb").read()).hexdigest()
    if evidence.get("fixture_source_path") != evals_rel:
        errs.append("execution evidence fixture_source_path does not match "
                    "the current skill evals path")
    if evidence.get("fixture_path") != fixture_rel:
        errs.append("execution evidence fixture_path does not match the current "
                    "fixture path")
    if evidence.get("fixture_source_hash") != source_hash:
        errs.append("execution evidence fixture_source_hash does not match the "
                    "current evals.json")
    if expected and evidence.get("expected_fixture_hash") != expected:
        errs.append("execution evidence expected_fixture_hash does not match "
                    "the current frozen fixture hash")
    expected_skill_path = os.path.join("skills", skill)
    if evidence.get("target_skill_source_path") != expected_skill_path:
        errs.append("execution evidence target_skill_source_path does not match "
                    "the target skill")
    if execution_runner is not None:
        current_skill_hash = execution_runner.skill_tree_hash(
            os.path.join(ROOT, "skills", skill))
        if evidence.get("target_skill_content_hash") != current_skill_hash:
            errs.append("execution evidence target_skill_content_hash does not "
                        "match the current target skill discovery tree")
    return {"skill": skill, "case_id": case_id, "case": case,
            "fixture": fx, "expected_fixture_hash": expected,
            "evals_path": evals_path, "evals_rel": evals_rel,
            "fixture_rel": fixture_rel, "source_hash": source_hash}


def _placebo_source_anchor(evidence, anchor, errs):
    """Check that a placebo hash refers to the current canonical skill tree."""
    placebo = evidence.get("placebo_skill")
    if not isinstance(placebo, str) or not placebo:
        return
    if placebo == anchor["skill"]:
        errs.append("execution evidence placebo_skill must differ from skill")
        return
    placebo_path = os.path.join(ROOT, "skills", placebo)
    if not os.path.isfile(os.path.join(placebo_path, "SKILL.md")):
        errs.append(f"execution evidence placebo skill not found: {placebo}")
        return
    if execution_runner is not None:
        current_hash = execution_runner.skill_tree_hash(placebo_path)
        if evidence.get("placebo_skill_content_hash") != current_hash:
            errs.append("execution evidence placebo_skill_content_hash does not "
                        "match the current placebo skill discovery tree")


def validate_execution_evidence(evidence):
    """Validate a Docker execution-evidence file from run_execution_eval.py.

    Local-only check (the .eval-evidence/ dir is gitignored). Confirms the
    condition workers were genuinely independent, started from identical
    pristine TASK-state copies, received the byte-identical natural task (never
    a prompt naming the skill/condition/evaluation), and that the intended
    guidance treatment actually entered context through the controlled
    activation mechanism. A failed run can never masquerade as valid evidence.
    Returns a list of error strings (empty == valid).

    Activation model (Layer B is POST-activation): the evaluator activates the
    target/placebo guidance deterministically via ``kilo run --command
    <skill>:skill``, which resolves against the ``.kilo/skills/<skill>/SKILL.md``
    discovery tree in the worker workspace and injects the skill body into
    context at session start; an unresolvable command makes kilo exit non-zero
    ("Command not found"), so a successful run (returncode 0) proves the skill
    was discovered and injected. The baseline runs without ``--command`` and
    must have no ``.kilo/skills`` tree. Native ``skill`` tool calls are recorded
    as supplementary ``activation_events``; mere file presence is never
    activation. Task-state hashes (``starting_task_hash``) EXCLUDE the
    evaluator runtime treatment paths (``.kilo/skills``), so the target/placebo
    treatment trees cannot invalidate seed equality; the full-filesystem hashes
    are recorded separately.
    """
    errs = []
    et = evidence.get("evidence_type")
    if et != "execution":
        errs.append(f"expected evidence_type 'execution', got {et!r}")
    source_anchor = _execution_source_anchor(evidence, errs)
    if source_anchor is not None:
        _placebo_source_anchor(evidence, source_anchor, errs)
    reps = evidence.get("repetitions") or []
    if not reps:
        errs.append("execution evidence has no repetitions")
        return errs
    conds = evidence.get("conditions") or ["target", "baseline"]
    if not set(conds) >= {"target", "baseline"}:
        errs.append(f"execution evidence conditions {conds!r} must include "
                    f"'target' and 'baseline' (placebo optional)")
        return errs
    for extra in set(conds) - {"target", "baseline", "placebo"}:
        errs.append(f"unknown condition {extra!r} in evidence")
    seed = evidence.get("canonical_task_seed_hash")
    expected = evidence.get("expected_fixture_hash")
    # The executed task must be the EXACT frozen fixture, not merely a consistent
    # (but wrong) one. The runtime canonical task seed must equal the frozen hash.
    if "expected_fixture_hash" not in evidence:
        errs.append("execution evidence missing expected_fixture_hash "
                    "(frozen fixture hash not anchored)")
    # The runtime treatment must be recorded separately from the task hash, and
    # the treatment paths excluded from the task hash must be explicit.
    runtime_paths = evidence.get("runtime_treatment_paths")
    if not isinstance(runtime_paths, list) or not runtime_paths:
        errs.append("execution evidence missing runtime_treatment_paths "
                    "(task-state hash exclusion list not recorded)")
    else:
        if ".kilo/skills" not in runtime_paths:
            errs.append("execution evidence runtime_treatment_paths must include "
                        "'.kilo/skills' (the evaluator-owned discovery tree)")
        if ".kilo" in runtime_paths:
            errs.append("execution evidence must not exclude the entire '.kilo' "
                        "root from task hashing")
    if evidence.get("activation_mechanism") != "kilo-command-skill":
        errs.append("execution evidence missing activation_mechanism "
                    "'kilo-command-skill' (controlled post-activation model)")
    if not evidence.get("target_skill_kilo_path"):
        errs.append("execution evidence missing target_skill_kilo_path "
                    "(target skill not placed for Kilo discovery)")
    if not evidence.get("target_skill_content_hash"):
        errs.append("execution evidence missing target_skill_content_hash "
                    "(frozen target guidance tree not anchored)")
    if "placebo" in conds:
        if not evidence.get("placebo_skill"):
            errs.append("placebo condition present but placebo_skill not "
                        "recorded")
        if not evidence.get("placebo_skill_kilo_path"):
            errs.append("execution evidence missing placebo_skill_kilo_path "
                        "(placebo skill not placed for Kilo discovery)")
        if not evidence.get("placebo_skill_content_hash"):
            errs.append("execution evidence missing placebo_skill_content_hash "
                        "(frozen placebo guidance tree not anchored)")
    if not seed:
        errs.append("execution evidence missing canonical_task_seed_hash")
    if seed and expected and seed != expected:
        errs.append(f"canonical task seed hash {seed!r} does not match the "
                    f"frozen expected_fixture_hash {expected!r}")
    # Per-repetition anchor: the worker's starting TASK state must be the frozen
        # one. Treatment trees (``.kilo/skills``) are excluded from these hashes and are
    # verified separately below.
    for r in reps:
        tag = f"rep{r.get('rep')}"
        if expected and r.get("canonical_task_seed_hash") != expected:
            errs.append(f"{tag}: repetition canonical_task_seed_hash does not "
                        f"match the frozen expected_fixture_hash")
        # The natural task must be byte-identical across conditions. When the
        # runner records the task hash per repetition, all conditions must share
        # it; if the runner leaks condition/identity tokens into a prompt, the
        # evidence would not carry an identical task hash to check, so a missing
        # hash is itself an error.
        th = r.get("natural_task_hash")
        if not (isinstance(th, str) and len(th) >= 16):
            errs.append(f"{tag}: missing natural_task_hash (identical-task "
                        f"evidence required)")
        elif r.get("natural_task_identical_across_conditions") is not True:
            errs.append(f"{tag}: natural_task_identical_across_conditions != true")

        cmap = r.get("conditions") or {}
        missing = [n for n in conds if n not in cmap]
        if missing:
            errs.append(f"{tag}: missing condition(s) {missing}")
            continue
        for name in conds:
            cmeta = cmap.get(name) or {}
            ctag = f"{tag} {name}"
            for key in ("container_id", "session_id", "run_status", "returncode",
                        "starting_task_hash", "ending_task_hash",
                        "starting_full_hash", "ending_full_hash",
                        "skill_context_probe"):
                if key not in cmeta:
                    errs.append(f"{ctag}: missing {key}")
            if cmeta.get("run_status") != "success":
                errs.append(f"{ctag}: run_status={cmeta.get('run_status')!r} "
                            f"(failed/invalid evidence)")
            if cmeta.get("returncode") != 0:
                errs.append(f"{ctag}: returncode={cmeta.get('returncode')!r}")
            if not (cmeta.get("output") or "").strip() \
                    and not cmeta.get("ending_task_hash"):
                errs.append(f"{ctag}: no model output and no task-state evidence")
            if seed and cmeta.get("starting_task_hash") != seed:
                errs.append(f"{ctag}: starting TASK hash does not match "
                            f"canonical task seed hash (task state differs "
                            f"across conditions or from the frozen fixture)")
        # Activation boundary, per condition. Layer B is a POST-ACTIVATION
        # experiment: the evaluator must have ACTIVATED the target/placebo
        # guidance through the controlled skill-command mechanism, and the
        # baseline must have no treatment at all. The discovery-path probe
        # (presence + content hash) and the command resolution (returncode 0)
        # are the machine-verifiable activation evidence; native skill tool
        # calls are recorded as supplementary events.
        t = cmap.get("target") or {}
        if t.get("activation_mechanism") != "kilo-command-skill":
            errs.append(f"{tag} target: activation_mechanism != "
                        f"'kilo-command-skill' (target guidance was not "
                        f"activated through the controlled mechanism)")
        if t.get("skill_kilo_path") != evidence.get("target_skill_kilo_path"):
            errs.append(f"{tag} target: skill_kilo_path does not match "
                        f"target_skill_kilo_path (target skill not discoverable "
                        f"in worker workspace)")
        if t.get("skill_command") != f"{evidence.get('skill')}:skill":
            errs.append(f"{tag} target: skill_command {t.get('skill_command')!r} "
                        f"!= '<skill>:skill' (command must resolve the skill)")
        if t.get("skill_content_hash") != evidence.get("target_skill_content_hash"):
            errs.append(f"{tag} target: skill_content_hash does not match the "
                        f"frozen target guidance tree hash")
        if t.get("skill_probe") != "present":
            errs.append(f"{tag} target: skill_probe != 'present' "
                            f"(discovery path SKILL.md absent or content-hash "
                            f"mismatch inside the container)")
        if t.get("skill_context_probe") != "present":
            errs.append(f"{tag} target: skill_context_probe != 'present' "
                        f"(the exported Kilo session did not prove that the "
                        f"full guidance body entered context)")
        if t.get("skill_tool_invoked"):
            events = t.get("activation_events") or []
            if not events:
                errs.append(f"{tag} target: skill_tool_invoked but no "
                            f"activation_events recorded")
            for e in events:
                if e.get("skill_name") != evidence.get("skill"):
                    errs.append(f"{tag} target: activation event names skill "
                                f"{e.get('skill_name')!r}, not the target "
                            f"skill {evidence.get('skill')!r}")
        elif t.get("activation_events"):
            errs.append(f"{tag} target: activation_events present while "
                        f"skill_tool_invoked is false")
        b = cmap.get("baseline") or {}
        if b.get("activation_mechanism") != "none":
            errs.append(f"{tag} baseline: activation_mechanism != 'none' "
                        f"(baseline must not have activated guidance)")
        if b.get("skill_kilo_path"):
            errs.append(f"{tag} baseline: skill_kilo_path is set "
                        f"(baseline must not receive the target skill)")
        if b.get("skill_probe") != "absent":
            errs.append(f"{tag} baseline: skill_probe != 'absent' "
                            f"(baseline leaked a .kilo/skills treatment tree)")
        if b.get("skill_context_probe") != "none":
            errs.append(f"{tag} baseline: skill_context_probe != 'none' "
                        f"(baseline must not export activated guidance)")
        if b.get("skill_tool_invoked"):
            errs.append(f"{tag} baseline: skill_tool_invoked is true "
                        f"(baseline must have no skill activation)")
        if b.get("activation_events"):
            errs.append(f"{tag} baseline: activation_events present "
                        f"(baseline must have no skill activation)")
        if "placebo" in conds:
            p = cmap.get("placebo") or {}
            if p.get("activation_mechanism") != "kilo-command-skill":
                errs.append(f"{tag} placebo: activation_mechanism != "
                            f"'kilo-command-skill' (placebo guidance must be "
                            f"activated through the SAME mechanism as target)")
            if p.get("skill_kilo_path") != evidence.get("placebo_skill_kilo_path"):
                errs.append(f"{tag} placebo: skill_kilo_path does not match "
                            f"placebo_skill_kilo_path")
            if p.get("skill_command") != f"{evidence.get('placebo_skill')}:skill":
                errs.append(f"{tag} placebo: skill_command "
                            f"{p.get('skill_command')!r} != "
                            f"'<placebo-skill>:skill'")
            if p.get("skill_content_hash") != evidence.get(
                    "placebo_skill_content_hash"):
                errs.append(f"{tag} placebo: skill_content_hash does not match "
                            f"the frozen placebo guidance tree hash")
            if p.get("skill_probe") != "present":
                errs.append(f"{tag} placebo: skill_probe != 'present' "
                            f"(discovery path SKILL.md absent or content-hash "
                            f"mismatch inside the container)")
            if p.get("skill_context_probe") != "present":
                errs.append(f"{tag} placebo: skill_context_probe != 'present' "
                            f"(the exported Kilo session did not prove that "
                            f"the full placebo body entered context)")
            if p.get("skill_tool_invoked"):
                events = p.get("activation_events") or []
                if not events:
                    errs.append(f"{tag} placebo: skill_tool_invoked but no "
                                f"activation_events recorded")
                for e in events:
                    if e.get("skill_name") != evidence.get("placebo_skill"):
                        errs.append(f"{tag} placebo: activation event names "
                                    f"skill {e.get('skill_name')!r}, not the "
                                    f"placebo skill "
                                    f"{evidence.get('placebo_skill')!r}")
            elif p.get("activation_events"):
                errs.append(f"{tag} placebo: activation_events present while "
                            f"skill_tool_invoked is false")

        # Cross-condition isolation.
        cids = [cmap[n].get("container_id") for n in conds]
        sids = [cmap[n].get("session_id") for n in conds]
        starts = [cmap[n].get("starting_task_hash") for n in conds]
        if not (all(cids) and len(set(cids)) == len(cids)):
            errs.append(f"{tag}: conditions not in distinct containers")
        if not (all(sids) and len(set(sids)) == len(sids)):
            errs.append(f"{tag}: conditions not in distinct sessions")
        if not (starts and len(set(starts)) == 1):
            errs.append(f"{tag}: condition starting TASK hashes differ "
                        f"(not identical task seed)")
        full_starts = [cmap[n].get("starting_full_hash") for n in conds]
        if not (all(full_starts) and len(set(full_starts)) == len(conds)):
            errs.append(f"{tag}: condition starting FULL hashes do not differ "
                        f"as expected for separate runtime treatments")
        wids = (r.get("condition_workspace_ids") or {}).values()
        if not wids or len(set(wids)) != len(conds):
            errs.append(f"{tag}: condition workspace ids not distinct "
                        f"(shared mutable fixture)")
    return errs


def validate_catalog_routing_evidence(evidence):
    """Validate a catalog-routing evidence file from run_catalog_routing_eval.py.

    Confirms both routing conditions (target-present, target-absent) were run,
    each repetition carries a status, and a FAILED model invocation is never
    recorded as a successful null-selection pass. Returns a list of error strings
    (empty == valid).
    """
    errs = []
    et = evidence.get("evidence_type")
    if et != "catalog-routing":
        errs.append(f"expected evidence_type 'catalog-routing', got {et!r}")
    conds = evidence.get("conditions") or {}
    if "target_present" not in conds or "target_absent" not in conds:
        errs.append("catalog-routing evidence missing one or both conditions")
        return errs

    skill = evidence.get("skill")
    case_id = evidence.get("case_id")
    evals_path = os.path.join(ROOT, "skills", str(skill), "evals",
                              "evals.json")
    source_case = None
    if not isinstance(skill, str) or not skill:
        errs.append("catalog-routing evidence missing skill")
    elif not isinstance(case_id, int):
        errs.append("catalog-routing evidence missing integer case_id")
    elif not os.path.exists(evals_path):
        errs.append(f"catalog-routing evidence skill evals not found: {skill}")
    else:
        try:
            source = json.load(open(evals_path))
            source_case = next((c for c in source.get("evals", [])
                                if c.get("id") == case_id), None)
        except (OSError, TypeError, ValueError) as exc:
            errs.append(f"catalog-routing source evals unreadable: {exc}")
    if source_case is None and isinstance(case_id, int):
        errs.append("catalog-routing evidence case_id is not present in the "
                    "current skill evals")

    expected_by_condition = {}
    fallbacks_by_condition = {}
    target_skill = skill
    if source_case is not None:
        routing = source_case.get("routing") or {}
        target_skill = routing.get("target_skill") or skill
        for name in ("target_present", "target_absent"):
            oracle = routing.get(name) or {}
            expected_by_condition[name] = oracle.get("expected_selected_skill")
            fallbacks_by_condition[name] = oracle.get("allowed_fallbacks") or []
            if name not in routing:
                errs.append(f"catalog-routing source case missing {name} oracle")
        if target_skill != skill:
            errs.append("catalog-routing evidence skill does not match the "
                        "source routing target_skill")

    all_skills = {os.path.basename(os.path.dirname(p)) for p in glob.glob(
        os.path.join(ROOT, "skills", "*", "SKILL.md"))}
    catalogs = {
        "target_present": all_skills,
        "target_absent": all_skills - {target_skill},
    }
    catalog_hashes = {}
    prompt_hashes = {}
    if catalog_runner is not None and source_case is not None:
        prompt = source_case.get("prompt", "")
        for name, absent in (("target_present", None),
                             ("target_absent", target_skill)):
            rows = catalog_runner.build_catalog(absent)
            text = catalog_runner.render_catalog(rows)
            catalog_hashes[name] = hashlib.sha256(text.encode()).hexdigest()
            prompt_hashes[name] = hashlib.sha256(
                catalog_runner.build_prompt(text, prompt).encode()).hexdigest()
    valid_actions = ("apply", "clarify")
    for name, cond in conds.items():
        reps = cond.get("repetitions") or []
        if not reps:
            errs.append(f"{name}: no repetitions captured")
            continue
        for r in reps:
            rep_tag = f"{name} rep{r.get('rep')}"
            if name in catalog_hashes and r.get("catalog_hash") != \
                    catalog_hashes[name]:
                errs.append(f"{rep_tag}: catalog_hash does not match the "
                            f"current {name} catalog")
            if name in prompt_hashes and r.get("prompt_hash") != \
                    prompt_hashes[name]:
                errs.append(f"{rep_tag}: prompt_hash does not match the "
                            "current case and catalog")
            status = r.get("status")
            if status != "success":
                # A failed model invocation must NOT be recorded as a pass.
                if r.get("match") is True:
                    errs.append(f"{rep_tag}: failed model invocation recorded as "
                                f"match=True (false pass)")
                continue
            decision = r.get("decision") or {}
            if "selected_skill" not in decision:
                errs.append(f"{rep_tag}: success but decision missing "
                            f"'selected_skill'")
                continue
            if decision.get("action") not in valid_actions:
                errs.append(f"{rep_tag}: invalid action {decision.get('action')!r}")
            sel = decision.get("selected_skill")
            act = decision.get("action")
            if sel is not None and sel not in catalogs.get(name, set()):
                errs.append(f"{rep_tag}: selected_skill {sel!r} is not in the "
                            f"{name} catalog")
            if sel is None and act == "apply":
                errs.append(f"{rep_tag}: null selected_skill with action 'apply'")
            if sel is not None and act == "clarify":
                errs.append(f"{rep_tag}: non-null selected_skill with 'clarify'")
            if not isinstance(r.get("match"), bool):
                errs.append(f"{rep_tag}: match not boolean")
            if name in expected_by_condition:
                expected = expected_by_condition[name]
                fallbacks = fallbacks_by_condition[name]
                expected_match = ((sel == expected or sel in fallbacks)
                                  if expected is not None
                                  else (sel is None or sel in fallbacks))
                if r.get("match") is not expected_match:
                    errs.append(f"{rep_tag}: match does not match the current "
                                f"{name} oracle")
    return errs


def _recompute_case_set_aggregate(cases, skills):
    """Recompute case-set metrics from captured successful decisions."""
    observations = []
    workflow_types = ("workflow-transition", "harness-native")
    for case in cases:
        if not isinstance(case, dict):
            continue
        turns = case.get("turns")
        is_workflow = bool(turns) and case.get("case_type") in workflow_types
        if is_workflow:
            for rep in case.get("repetitions", []):
                if not isinstance(rep, dict):
                    continue
                for turn in rep.get("turns", []):
                    if not isinstance(turn, dict):
                        continue
                    if turn.get("status") != "success":
                        continue
                    intended = turn.get("expected_route")
                    selected = turn.get("selected_skill")
                    observations.append((
                        intended if intended is not None else "null",
                        selected if selected is not None else "null",
                    ))
        else:
            for rep in case.get("repetitions", []):
                if not isinstance(rep, dict):
                    continue
                if rep.get("status") != "success":
                    continue
                decision = rep.get("decision") or {}
                intended = case.get("expected_skill")
                selected = decision.get("selected_skill")
                observations.append((
                    intended if intended is not None else "null",
                    selected if selected is not None else "null",
                ))

    matrix = {}
    for intended, selected in observations:
        row = matrix.setdefault(intended, {})
        row[selected] = row.get(selected, 0) + 1

    per_skill = {}
    for skill in skills:
        tp = sum(1 for i, s in observations if i == skill and s == skill)
        fp = sum(1 for i, s in observations if i != skill and s == skill)
        fn = sum(1 for i, s in observations if i == skill and s != skill)
        per_skill[skill] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": (tp / (tp + fp)) if tp + fp else None,
            "recall": (tp / (tp + fn)) if tp + fn else None,
        }
    return {
        "rule": ("one observation per successful model decision; "
                 "workflow-transition/harness-native turns each contribute one "
                 "observation; explicit null selections are the literal "
                 "'null' class; precision/recall are null (not 0) when the "
                 "denominator is zero"),
        "observations": len(observations),
        "confusion_matrix": matrix,
        "per_skill": per_skill,
    }


def _case_set_source_anchor(evidence, errs):
    """Resolve case-set evidence to the canonical checked-in source file."""
    et = evidence.get("evidence_type")
    source_name_key = "confusion_set" if et == "confusion-set" else "holdout"
    source_dir = ("evaluations/confusion-sets" if et == "confusion-set"
                  else "evaluations/holdout")
    source_name = evidence.get(source_name_key)
    path = evidence.get("case_set_path")
    if not isinstance(source_name, str) or not source_name:
        errs.append(f"case-set evidence missing {source_name_key} source name")
        return None
    expected_path = os.path.join(source_dir, f"{source_name}.json")
    if path != expected_path:
        errs.append("case-set evidence case_set_path does not match the "
                    "canonical source name")
        return None
    source_path = os.path.join(ROOT, path)
    if not os.path.isfile(source_path):
        errs.append(f"case-set evidence source file not found: {path}")
        return None
    try:
        source = json.load(open(source_path, encoding="utf-8"))
    except (OSError, TypeError, ValueError) as exc:
        errs.append(f"case-set source unreadable: {exc}")
        return None
    canonical = json.dumps(source, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode()
    source_hash = HASH_PREFIX + hashlib.sha256(canonical).hexdigest()
    if evidence.get("case_set_hash") != source_hash:
        errs.append("case-set evidence case_set_hash does not match the "
                    "current canonical source")
    if source.get(source_name_key) != source_name:
        errs.append(f"case-set source {source_name_key} does not match evidence")
    if evidence.get("skills") != source.get("skills"):
        errs.append("case-set evidence skills do not match the canonical source")
    source_cases = source.get("cases") or []
    recorded_cases = evidence.get("cases") or []
    if len(recorded_cases) != len(source_cases):
        errs.append("case-set evidence case count does not match the canonical "
                    "source")
    for index, source_case in enumerate(source_cases):
        if index >= len(recorded_cases):
            break
        recorded = recorded_cases[index]
        if not isinstance(recorded, dict):
            continue
        for key in ("id", "case_type", "expected_skill"):
            if recorded.get(key) != source_case.get(key):
                errs.append(f"case {recorded.get('id')}: {key} does not match "
                            "the canonical source")
        if recorded.get("turns") != source_case.get("turns"):
            errs.append(f"case {recorded.get('id')}: turns do not match the "
                        "canonical source")
    return source


def validate_case_set_routing_evidence(evidence):
    """Validate confusion-set/holdout evidence emitted by ``run_case_set``.

    Case-set runs use a top-level ``cases``/``aggregate`` shape rather than
    the legacy target-present/target-absent ``conditions`` shape. Keep the two
    schemas explicit so a successful case-set run cannot be rejected as an
    unrelated legacy artifact or silently skipped by the evidence gate.
    """
    errs = []
    et = evidence.get("evidence_type")
    if et not in ("confusion-set", "holdout"):
        errs.append(f"expected case-set evidence type, got {et!r}")
    _case_set_source_anchor(evidence, errs)
    skills = evidence.get("skills")
    if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
        errs.append("case-set evidence missing a valid skills list")
        skills = []
    cases = evidence.get("cases")
    if not isinstance(cases, list) or not cases:
        errs.append("case-set evidence missing non-empty cases")
        return errs
    aggregate = evidence.get("aggregate")
    if not isinstance(aggregate, dict):
        errs.append("case-set evidence missing aggregate")
    else:
        for key in ("observations", "confusion_matrix", "per_skill"):
            if key not in aggregate:
                errs.append(f"case-set aggregate missing {key}")
        expected_aggregate = _recompute_case_set_aggregate(
            cases, skills)
        if aggregate != expected_aggregate:
            errs.append("case-set aggregate does not match captured cases")

    valid_actions = ("apply", "clarify")
    workflow_types = ("workflow-transition", "harness-native")
    for case in cases:
        if not isinstance(case, dict):
            errs.append("case-set evidence contains a non-object case")
            continue
        cid = case.get("id")
        tag = f"case {cid}"
        case_type = case.get("case_type")
        turns = case.get("turns")
        is_workflow = bool(turns) and case_type in workflow_types
        reps = case.get("repetitions")
        if not isinstance(reps, list) or not reps:
            errs.append(f"{tag}: no repetitions captured")
            continue

        if turns and not is_workflow:
            errs.append(f"{tag}: turns are only valid for workflow-transition "
                        "or harness-native cases")
            continue

        for rep in reps:
            if not isinstance(rep, dict):
                errs.append(f"{tag}: repetition is not an object")
                continue
            rep_tag = f"{tag} rep{rep.get('rep')}"
            if is_workflow:
                turn_results = rep.get("turns")
                if not isinstance(turn_results, list) or not turn_results:
                    errs.append(f"{rep_tag}: no turn results captured")
                    continue
                for turn in turn_results:
                    if not isinstance(turn, dict):
                        errs.append(f"{rep_tag}: turn is not an object")
                        continue
                    turn_tag = f"{rep_tag} turn{turn.get('turn')}"
                    if turn.get("status") != "success":
                        if turn.get("pass") is True:
                            errs.append(f"{turn_tag}: failed turn recorded as "
                                        "pass=True")
                        continue
                    if turn.get("expected_route_declared") is not True:
                        errs.append(f"{turn_tag}: expected route was not "
                                    "explicitly declared")
                    if "selected_skill" not in turn:
                        errs.append(f"{turn_tag}: missing selected_skill")
                    selected = turn.get("selected_skill")
                    if selected is not None and selected not in skills:
                        errs.append(f"{turn_tag}: selected_skill {selected!r} "
                                    "not in catalog skills")
                    if turn.get("action") not in valid_actions:
                        errs.append(f"{turn_tag}: invalid action "
                                    f"{turn.get('action')!r}")
                    if not isinstance(turn.get("pass"), bool):
                        errs.append(f"{turn_tag}: pass not boolean")
                    expected = turn.get("expected_route")
                    expected_pass = (selected == expected
                                     if expected is not None
                                     else selected is None)
                    if turn.get("pass") is not expected_pass:
                        errs.append(f"{turn_tag}: pass does not match "
                                    "expected_route and selected_skill")
            else:
                status = rep.get("status")
                if status != "success":
                    if rep.get("match") is True:
                        errs.append(f"{rep_tag}: failed model invocation "
                                    "recorded as match=True (false pass)")
                    continue
                decision = rep.get("decision") or {}
                if "selected_skill" not in decision:
                    errs.append(f"{rep_tag}: success but decision missing "
                                "'selected_skill'")
                    continue
                if decision.get("action") not in valid_actions:
                    errs.append(f"{rep_tag}: invalid action "
                                f"{decision.get('action')!r}")
                selected = decision.get("selected_skill")
                action = decision.get("action")
                if selected is not None and selected not in skills:
                    errs.append(f"{rep_tag}: selected_skill {selected!r} not in "
                                "catalog skills")
                if selected is None and action == "apply":
                    errs.append(f"{rep_tag}: null selected_skill with action "
                                "'apply'")
                if selected is not None and action == "clarify":
                    errs.append(f"{rep_tag}: non-null selected_skill with "
                                "'clarify'")
                if not isinstance(rep.get("match"), bool):
                    errs.append(f"{rep_tag}: match not boolean")
                expected = case.get("expected_skill")
                expected_match = (selected == expected
                                  if expected is not None
                                  else selected is None)
                if rep.get("match") is not expected_match:
                    errs.append(f"{rep_tag}: match does not match expected_skill "
                                "and selected_skill")
    return errs


def check_evidence_dir(ev_dir=None):
    """Optional gate for local .eval-evidence/ files (not committed).

    Dispatches on the top-level ``evidence_type`` field (filename convention is
    only a secondary hint). Unknown or malformed evidence is treated as an error
    so it cannot be silently skipped.
    """
    ev_dir = ev_dir or os.path.join(ROOT, ".eval-evidence")
    if not os.path.isdir(ev_dir):
        return
    for f in sorted(glob.glob(os.path.join(ev_dir, "*.json"))):
        rel = os.path.relpath(f, ROOT)
        try:
            data = json.load(open(f))
        except Exception as e:
            err(f"{rel}: unreadable/malformed evidence: {e}")
            continue
        if not isinstance(data, dict):
            err(f"{rel}: evidence is not a JSON object")
            continue
        et = data.get("evidence_type")
        basename = os.path.basename(f)
        if et == "execution":
            for e in validate_execution_evidence(data):
                err(f"{rel}: {e}")
        elif et in ("confusion-set", "holdout"):
            # Case-set evidence has a top-level cases/aggregate schema. The
            # source label distinguishes development data from holdout output.
            for e in validate_case_set_routing_evidence(data):
                err(f"{rel}: {e}")
        elif et == "catalog-routing":
            for e in validate_catalog_routing_evidence(data):
                err(f"{rel}: {e}")
        elif basename.startswith("exec-"):
            # Legacy fallback (pre-conditions evidence): trust filename only
            # when type is absent. Old target/baseline-shaped files are still
            # checked for cross-condition isolation; new files must use the
            # conditions shape.
            for e in validate_execution_evidence(data):
                err(f"{rel}: {e}")
        elif basename.startswith("catalog-routing-"):
            for e in validate_catalog_routing_evidence(data):
                err(f"{rel}: {e}")
        else:
            err(f"{rel}: unknown evidence_type {et!r} (not validated)")


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
                ((b.get("runs") or {}).get("target") or {}).get("selected_skill")
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
# Confusion sets and holdouts (repository-level evaluation corpora)
# --------------------------------------------------------------------------
def check_confusion_set(path, rel):
    """Validate one evaluations/confusion-sets/<name>.json file.

    A confusion set groups cases whose candidate skills are deliberately
    confusable, so the summary can report intended-vs-selected confusion
    patterns instead of isolated per-skill pass rates. Each case's prompt must
    not contain the expected skill's name (that would measure keyword matching,
    not discrimination).
    """
    try:
        d = json.load(open(path))
    except Exception as e:
        err(f"{rel}: JSON parse error: {e}")
        return
    if not isinstance(d, dict):
        err(f"{rel}: confusion set must be a JSON object")
        return
    if "confusion_set" not in d or not isinstance(d["confusion_set"], str) \
            or not d["confusion_set"].strip():
        err(f"{rel}: missing 'confusion_set' name")
    if not isinstance(d.get("cluster"), str) or not d["cluster"].strip():
        err(f"{rel}: missing 'cluster' name")
    skills = d.get("skills")
    if not isinstance(skills, list) or len(skills) < 2 \
            or not all(isinstance(s, str) and s for s in skills):
        err(f"{rel}: 'skills' must list at least two skill names")
        return
    cases = d.get("cases")
    if not isinstance(cases, list) or not cases:
        err(f"{rel}: 'cases' must be a non-empty list")
        return
    ids = [c.get("id") for c in cases]
    if len(ids) != len(set(ids)):
        err(f"{rel}: duplicate case ids in confusion set")
    for c in cases:
        tag = f"{rel} case {c.get('id')}"
        if not isinstance(c.get("id"), int):
            err(f"{tag}: id must be an integer")
        ctype = c.get("case_type")
        if ctype not in ALLOWED_CASE_TYPES:
            err(f"{tag}: bad case_type '{ctype}'")
            continue
        prompt = c.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            err(f"{tag}: empty prompt")
            continue
        if ctype in COUNTERFACTUAL_TYPES:
            pair = c.get("counterfactual_pair")
            if not (isinstance(pair, str) and pair.strip()):
                err(f"{tag}: counterfactual case missing counterfactual_pair")
        # The oracle is the dominant requested job. ``expected_skill`` may be
        # null for genuinely ambiguous cases (the router should clarify).
        exp = c.get("expected_skill")
        if exp is None:
            if ctype != "ambiguous-natural":
                err(f"{tag}: expected_skill null only valid for "
                    f"ambiguous-natural cases")
        elif not isinstance(exp, str) or not exp.strip():
            err(f"{tag}: missing expected_skill (or null for ambiguous)")
        elif exp not in skills:
            err(f"{tag}: expected_skill {exp!r} not in the "
                f"confusion set's skills")
        # No worker-visible prompt may recite the expected skill's name: that
        # would measure keyword matching instead of discrimination. Prompt text
        # is lowercased and matched on word boundaries. Skip when there is no
        # expected skill (ambiguous cases).
        if exp is not None and isinstance(exp, str) and exp.strip():
            low = prompt.lower()
            if re.search(rf"\b{re.escape(exp.lower())}\b", low):
                err(f"{tag}: prompt contains the expected skill name "
                    f"{exp!r} (keyword leak)")
        turns = c.get("turns", [])
        if turns and ctype not in ("workflow-transition", "harness-native"):
            err(f"{tag}: turns are only valid for workflow-transition or "
                "harness-native cases")
        for t in turns:
            if not isinstance(t, dict) or not isinstance(t.get("user"), str) \
                    or not t["user"].strip():
                err(f"{tag}: turn missing non-empty 'user' text")
            # ``expected_route`` is REQUIRED: a skill name in the set, or
            # explicit null meaning "no specialized skill expected". Missing
            # route data is a schema error, never silently treated as null.
            if "expected_route" not in t:
                err(f"{tag}: turn missing 'expected_route' "
                    f"(null means 'no specialized skill expected')")
            else:
                route = t["expected_route"]
                if route is not None and not isinstance(route, str):
                    err(f"{tag}: turn expected_route must be a skill name or null")
                elif route is not None and route not in skills:
                    err(f"{tag}: turn expected_route {route!r} not in the "
                        f"confusion set's skills")
        if ctype == "workflow-transition" and not c.get("turns"):
            err(f"{tag}: workflow-transition case must carry ordered 'turns'")
        if c.get("notes") is not None and not isinstance(c.get("notes"), str):
            err(f"{tag}: notes must be a string")


def check_holdout(path, rel):
    """Validate one evaluations/holdout/<name>.json file.

    Holdout cases are stored outside the skill directories so ordinary skill
    editing does not consume them. They are NOT secret (this is an open
    repository) — the guarantee is workflow separation, and results must
    distinguish development-case performance from holdout performance.
    """
    try:
        d = json.load(open(path))
    except Exception as e:
        err(f"{rel}: JSON parse error: {e}")
        return
    if not isinstance(d, dict) or "holdout" not in d:
        err(f"{rel}: holdout file must contain a 'holdout' name")
    skills = set(d.get("skills") or [])
    cases = d.get("cases")
    if not isinstance(cases, list) or not cases:
        err(f"{rel}: 'cases' must be a non-empty list")
        return
    ids = [c.get("id") for c in cases]
    if len(ids) != len(set(ids)):
        err(f"{rel}: duplicate case ids in holdout")
    for c in cases:
        tag = f"{rel} case {c.get('id')}"
        if not isinstance(c.get("id"), int):
            err(f"{tag}: id must be an integer")
        if not isinstance(c.get("prompt"), str) or not c["prompt"].strip():
            err(f"{tag}: empty prompt")
            continue
        prompt = c["prompt"]
        ctype = c.get("case_type", "smoke")
        if ctype not in ALLOWED_CASE_TYPES:
            err(f"{tag}: bad case_type '{ctype}'")
            continue
        exp = c.get("expected_skill")
        if exp is None:
            if ctype != "ambiguous-natural":
                err(f"{tag}: expected_skill null only valid for "
                    f"ambiguous-natural cases")
        elif not isinstance(exp, str) or not exp.strip():
            err(f"{tag}: missing expected_skill")
        elif exp not in skills:
            err(f"{tag}: expected_skill {exp!r} not in the holdout's skills")
        if ctype == "counterfactual" and not c.get("counterfactual_pair"):
            err(f"{tag}: counterfactual case missing counterfactual_pair")
        # Keyword leak check: no worker-visible prompt may recite the expected
        # skill's name — that would measure keyword matching instead of
        # discrimination. Skip when there is no expected skill.
        if exp is not None and isinstance(exp, str) and exp.strip():
            low = prompt.lower()
            if re.search(rf"\b{re.escape(exp.lower())}\b", low):
                err(f"{tag}: prompt contains the expected skill name "
                    f"{exp!r} (keyword leak)")
        turns = c.get("turns", [])
        if turns and ctype not in ("workflow-transition", "harness-native"):
            err(f"{tag}: turns are only valid for workflow-transition or "
                "harness-native cases")
        for t in turns:
            if not isinstance(t, dict) or not isinstance(t.get("user"), str) \
                    or not t["user"].strip():
                err(f"{tag}: turn missing non-empty 'user' text")
            # ``expected_route`` is REQUIRED: a skill name in the set, or
            # explicit null meaning "no specialized skill expected". Missing
            # route data is a schema error, never silently treated as null.
            if "expected_route" not in t:
                err(f"{tag}: turn missing 'expected_route' "
                    f"(null means 'no specialized skill expected')")
            else:
                route = t["expected_route"]
                if route is not None and not isinstance(route, str):
                    err(f"{tag}: turn expected_route must be a skill name or null")
                elif route is not None and route not in skills:
                    err(f"{tag}: turn expected_route {route!r} not in the "
                        f"holdout's skills")


def check_confusion_sets_and_holdouts():
    for f in sorted(glob.glob(CONFUSION_GLOB)):
        check_confusion_set(f, os.path.relpath(f, ROOT))
    for f in sorted(glob.glob(HOLDOUT_GLOB)):
        check_holdout(f, os.path.relpath(f, ROOT))


# --------------------------------------------------------------------------
def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-evidence", action="store_true",
                    help="also validate local .eval-evidence/*.json (Docker run outputs)")
    args = ap.parse_args()

    print("=== Evaluating skill eval artifacts ===")
    skill_names, case_index = check_eval_files()
    check_confusion_sets_and_holdouts()
    check_leaks()
    check_links()
    check_results(skill_names, case_index)
    check_matrix_sync(skill_names)
    check_summary(skill_names)
    if args.check_evidence:
        print("=== Validating local .eval-evidence/ (Docker run outputs) ===")
        check_evidence_dir()

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
