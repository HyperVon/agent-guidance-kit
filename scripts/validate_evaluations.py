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
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_hashing import (HASH_PREFIX, canonical_hash, source_hash_of,
                          verify_generator_deterministic)
from evaluation_protocols import (ALLOWED_ASSERTION_SCOPES, PROTOCOL_NAMES,
                                  REGRESSION_STATUSES, get_protocol,
                                  is_safe_skill_name, legacy_protocol_name,
                                  protocol_name, resolve_path_within,
                                  validate_declaration)

try:
    import run_execution_eval as execution_runner
except ImportError:  # pragma: no cover - direct library import fallback
    execution_runner = None
try:
    import evaluation_harness as harness_runner
except ImportError:  # pragma: no cover - direct library import fallback
    harness_runner = None
try:
    import run_catalog_routing_eval as catalog_runner
except ImportError:  # pragma: no cover - direct library import fallback
    catalog_runner = None
try:
    import run_skill_regression_eval as regression_runner
except ImportError:  # pragma: no cover - direct library import fallback
    regression_runner = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVALS_DIR = os.path.join(ROOT, "docs", "evaluations")
SKILLS_GLOB = os.path.join(ROOT, "skills", "*", "evals", "evals.json")
# Repository-level evaluation corpora (shared cross-skill cases and holdouts).
CONFUSION_GLOB = os.path.join(ROOT, "evaluations", "confusion-sets", "*.json")
HOLDOUT_GLOB = os.path.join(ROOT, "evaluations", "holdout", "*.json")


def _git_commit_exists(value):
    """Return whether a resolved SHA names a commit in the current repo."""

    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        return False
    try:
        subprocess.run(
            ["git", "-C", ROOT, "cat-file", "-e", f"{value}^{{commit}}"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def _skill_hash_at_revision(revision, skill):
    """Materialize one revision's skill tree and return its guidance hash."""

    if regression_runner is None or harness_runner is None:
        raise ValueError("Git regression hashing helpers are unavailable")
    root, _resolved = regression_runner.materialize_skill_revision(
        revision, skill)
    try:
        return harness_runner.skill_tree_hash(
            os.path.join(root, "skills", skill))
    finally:
        shutil.rmtree(root, ignore_errors=True)

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
#   * execution        : Layer B — post-activation condition comparison
ROUTING_MODES = {"routing", "catalog-routing", "harness-routing"}
EXEC_MODES = {"execution"}
REGRESSION_MODES = {"regression"}
ALLOWED_MODES = ROUTING_MODES | EXEC_MODES | REGRESSION_MODES
ALLOWED_FIXTURE_STATUS = {"ready", "designed_only"}
ALLOWED_FIXTURE_TYPES = {"committed", "generator"}
KIND_COUNTS = {"matching": 2, "neighboring": 1, "ambiguous": 1, "edge": 1}
ALLOWED_OUTCOME = {"skill_only_pass", "baseline_only_pass", "both_pass",
                   "both_fail", "placebo_only_pass", "non_discriminating",
                   "candidate_only_pass", "reference_only_pass",
                   "single_condition_pass", "single_condition_fail",
                   "invalid", "not_run"}
ALLOWED_MEASUREMENT = {"discriminating", "non_discriminating", "inconclusive"}
ALLOWED_PROTOCOL = {"valid", "limited", "contaminated", "invalid", "not_run"}
# Assertion types: hard behavioral invariants vs quality criteria vs
# presentation/process preferences. Soft preferences must not be graded as
# hard pass/fail correctness.
ALLOWED_ASSERTION_TYPES = {"behavioral", "quality", "presentation"}
ALLOWED_ASSERTION_SCOPES = set(ALLOWED_ASSERTION_SCOPES)
# Isolation methods that are NOT valid production isolation. A run claiming
# protocol.status == "valid" must use real OS-level isolation (container/gvisor/
# sandbox with a verified boundary), not instruction-only / prompt-only wording.
LIMITED_ISOLATION = ("instruction-only", "prompt-only", "no sandbox", "none",
                     "n/a", "unknown")
ISOLATION_ATTESTATION_PROTOCOL = (
    "agent-guidance-kit.isolation-attestation/v1")
EXECUTION_ATTESTATION_PROTOCOL = (
    "agent-guidance-kit.execution-attestation/v1")


def _case_supports_mode(case, mode):
    """Whether an authoritative eval case can support the result mode."""
    modes = case.get("evaluation_modes") if isinstance(case, dict) else None
    if not isinstance(modes, list):
        return False
    if mode in modes:
        return True
    # Revision comparisons reuse the execution case and change only the
    # guidance condition (candidate vs reference).
    if mode in REGRESSION_MODES:
        return "execution" in modes
    # Catalog- and harness-routing are routing-family variants; existing eval
    # catalogs may declare their shared mode simply as ``routing``.
    return mode in ROUTING_MODES and "routing" in modes


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
            scope = a.get("scope", "shared-outcome")
            if scope not in ALLOWED_ASSERTION_SCOPES:
                err(f"{tag}: bad assertion scope '{scope}'")


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
    skill_root = os.path.dirname(os.path.dirname(f))
    fpath = resolve_path_within(skill_root, p)
    if fpath is None:
        err(f"{tag}: fixture path must remain under the skill directory: {p}")
        return
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
        src_path = resolve_path_within(fpath, src)
        if src_path is None:
            err(f"{tag}: generator source path must remain under the fixture: {src}")
            return
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
        if not isinstance(res, dict):
            err(f"{base}: result-json block must contain an object")
            continue
        check_one_result(base, res, skill_names, case_index)


def _validate_isolation_attestation(base, res, cases, status):
    """Require structured, raw-evidence-bound isolation for valid comparisons."""

    if (status != "valid" or
            res.get("evaluation_mode") not in (EXEC_MODES | REGRESSION_MODES)):
        return
    protocol = res.get("protocol") or {}
    attestation = protocol.get("isolation_attestation")
    if not isinstance(attestation, dict):
        err(f"{base}: valid comparison requires isolation_attestation")
        return
    if attestation.get("protocol") != ISOLATION_ATTESTATION_PROTOCOL:
        err(f"{base}: isolation_attestation protocol is unsupported")
    if attestation.get("status") != "verified":
        err(f"{base}: isolation_attestation must be verified")
    if attestation.get("verification_mode") != "independent":
        err(f"{base}: isolation_attestation must use independent verification")
    if attestation.get("boundary") != "os-level":
        err(f"{base}: valid comparison requires an os-level isolation boundary")
    if attestation.get("worker_isolation_verified") is not True:
        err(f"{base}: isolation_attestation must verify worker isolation")
    runtime = res.get("runtime") or {}
    if attestation.get("isolation_method") != runtime.get("isolation_method"):
        err(f"{base}: isolation_attestation does not match isolation_method")
    evidence_hashes = attestation.get("evidence_hashes")
    if not isinstance(evidence_hashes, dict):
        err(f"{base}: isolation_attestation must bind raw evidence hashes")
        return
    expected_case_keys = {str(case.get("case_id")) for case in cases
                          if isinstance(case, dict)}
    if set(evidence_hashes) != expected_case_keys:
        err(f"{base}: isolation_attestation evidence hashes do not cover every case")
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id"))
        raw_hash = case.get("raw_evidence_hash")
        if not isinstance(raw_hash, str) or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", raw_hash):
            err(f"{base} case {case.get('case_id')}: valid comparison requires raw_evidence_hash")
        elif evidence_hashes.get(case_id) != raw_hash:
            err(f"{base} case {case.get('case_id')}: isolation_attestation raw hash does not match case evidence")


def check_one_result(base, res, skill_names, case_index):
    skill = res.get("skill")
    if skill not in skill_names:
        err(f"{base}: result skill '{skill}' not in discovered skills")
    mode = res.get("evaluation_mode")
    if mode not in ALLOWED_MODES:
        err(f"{base}: evaluation_mode '{mode}' invalid")
    identity_keys = ["method", "case_revision", "fixture_revision"]
    if mode in REGRESSION_MODES:
        identity_keys.extend(["candidate_skill_revision", "reference_skill_revision"])
    else:
        identity_keys.append("target_skill_revision")
    for key in identity_keys:
        if not res.get(key):
            err(f"{base}: missing identity field '{key}'")
    method = res.get("method")
    if method not in {"docker-isolated", "harness-adapter", "harness-routing"}:
        err(f"{base}: method '{method}' invalid; expected harness-adapter, docker-isolated, or harness-routing")
    rt = res.get("runtime")
    if rt is None:
        rt = {}
    elif not isinstance(rt, dict):
        err(f"{base}: result runtime must be an object")
        rt = {}
    for key in ("harness", "model", "reasoning_effort", "tool_policy",
                "network_policy", "isolation_method"):
        if not rt.get(key):
            err(f"{base}: missing runtime field '{key}'")
    pr = res.get("protocol")
    if pr is None:
        pr = {}
    elif not isinstance(pr, dict):
        err(f"{base}: result protocol must be an object")
        pr = {}
    cases = res.get("cases")
    if not isinstance(cases, list):
        err(f"{base}: result cases must be a list")
        cases = []
    runs = res.get("runs")
    if runs is None:
        runs = {}
    elif not isinstance(runs, dict):
        err(f"{base}: result runs must be an object")
        runs = {}
    for condition in ("target", "baseline", "placebo", "candidate", "reference"):
        if condition in runs and not isinstance(runs[condition], dict):
            err(f"{base}: top-level runs.{condition} must be an object")
    status = pr.get("status")
    _validate_isolation_attestation(base, res, cases, status)
    if status not in ALLOWED_PROTOCOL:
        err(f"{base}: protocol.status '{status}' invalid")
    if status == "valid" and not cases:
        err(f"{base}: valid result must contain at least one case")
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
        smoke_protocol = pr.get("name") == "smoke"
        if not smoke_protocol and not pr.get("target_absent_in_baseline"):
            err(f"{base}: execution result missing target_absent_in_baseline evidence (target absence unverified)")
        if not pr.get("target_guidance_hash"):
            err(f"{base}: execution result missing target_guidance_hash (mounted guidance unverified)")
        if not smoke_protocol and not pr.get("baseline_guidance_absent"):
            err(f"{base}: execution result missing baseline_guidance_absent evidence (baseline received no guidance)")
        # A strict adapter must provide distinct worker boundaries; the legacy
        # Docker path reports these as container IDs.
        # Top-level container IDs: for multi-case with per-case reps, top-level is optional
        has_per_case_reps_early = False
        if res.get("evaluation_mode") == "execution":
            for cs in cases:
                if isinstance(cs, dict) and isinstance(
                        cs.get("repetitions"), list) and cs.get("repetitions"):
                    has_per_case_reps_early = True
                    break
        if not has_per_case_reps_early:
            target_run = runs.get("target")
            baseline_run = runs.get("baseline")
            if target_run is None:
                target_run = {}
            if baseline_run is None:
                baseline_run = {}
            if not isinstance(target_run, dict) or not isinstance(
                    baseline_run, dict):
                err(f"{base}: execution target/baseline runs must be objects")
                g_worker = b_worker = None
            else:
                g_worker = target_run.get("worker_id") or target_run.get("container_id")
                b_worker = baseline_run.get("worker_id") or baseline_run.get("container_id")
            if smoke_protocol:
                if not g_worker:
                    err(f"{base}: smoke execution result must record a target worker_id/container_id")
            elif not g_worker or not b_worker:
                err(f"{base}: execution result must record distinct target/baseline worker_id or container_id")
            elif g_worker == b_worker:
                err(f"{base}: target and baseline share a container_id/worker_id (contamination)")
    if mode in REGRESSION_MODES:
        for key in ("candidate_guidance_present", "reference_guidance_present",
                    "candidate_guidance_hash", "reference_guidance_hash"):
            if status == "valid" and not pr.get(key):
                err(f"{base}: regression result missing {key} evidence")
    explicit_protocol = protocol_name(pr)
    legacy_protocol = legacy_protocol_name(pr, mode)
    selected_protocol = explicit_protocol or legacy_protocol
    if explicit_protocol is not None and explicit_protocol not in PROTOCOL_NAMES:
        err(f"{base}: unknown evaluation protocol {explicit_protocol!r}")
    if (status == "valid" and explicit_protocol in PROTOCOL_NAMES and
            res.get("result_schema_version") != 2):
        err(f"{base}: protocol-declared valid results must set result_schema_version=2")
    if mode in REGRESSION_MODES and status == "valid" and explicit_protocol != "regression":
        err(f"{base}: valid regression result must declare protocol.name='regression'")
    if mode in EXEC_MODES and status == "valid" and explicit_protocol is None and legacy_protocol is None:
        err(f"{base}: new valid execution results must declare protocol.name; only the legacy strict confirmation shape may omit it")

    strict_comparison = mode in (EXEC_MODES | REGRESSION_MODES) and status == "valid"
    if selected_protocol in PROTOCOL_NAMES:
        required_conditions = tuple(get_protocol(selected_protocol).required_conditions)
    elif mode in REGRESSION_MODES:
        required_conditions = ("candidate", "reference")
    else:
        required_conditions = ("target", "baseline")
    declared_repeats = None
    global_identity = (
        {"repetition_id": set(), "session_id": set(), "container_id": set(),
         "worker_id": set()}
        if strict_comparison else None)
    if mode in (EXEC_MODES | REGRESSION_MODES):
        declared_conditions = pr.get("conditions")
        if strict_comparison and selected_protocol in PROTOCOL_NAMES:
            for protocol_error in validate_declaration(
                    selected_protocol, declared_conditions, pr.get("repeats")):
                err(f"{base}: {protocol_error}")
            if isinstance(declared_conditions, list):
                required_conditions = tuple(
                    condition for condition in declared_conditions
                    if isinstance(condition, str)
                )
        elif strict_comparison:
            if not isinstance(declared_conditions, list):
                err(f"{base}: valid comparison result must declare protocol.conditions")
            else:
                non_string = [condition for condition in declared_conditions
                               if not isinstance(condition, str)]
                if non_string:
                    err(f"{base}: protocol.conditions must contain only "
                        f"condition names, got {non_string!r}")
                else:
                    unknown = set(declared_conditions) - {
                        "target", "baseline", "placebo", "candidate", "reference"}
                    if unknown:
                        err(f"{base}: protocol.conditions contains unknown "
                            f"condition(s) {sorted(unknown)!r}")
                    if not set(declared_conditions) >= set(required_conditions):
                        err(f"{base}: protocol.conditions is missing required "
                            f"condition(s) {sorted(set(required_conditions) - set(declared_conditions))!r}")
                    required_conditions = tuple(declared_conditions)
            declared_repeats = pr.get("repeats")
            if not isinstance(declared_repeats, int) or isinstance(
                    declared_repeats, bool) or declared_repeats < 1:
                err(f"{base}: valid comparison result must declare a positive "
                    "integer protocol.repeats")
                declared_repeats = None
        else:
            declared_conditions = pr.get("conditions")
            if isinstance(declared_conditions, list) and "placebo" in declared_conditions:
                required_conditions += ("placebo",)
        # A committed case may still carry placebo data even when an older
        # result omitted protocol.conditions. Treat that as a declared placebo
        # for strict verdict validation rather than silently dropping it.
        if strict_comparison and mode in EXEC_MODES and "placebo" not in required_conditions:
            has_placebo = False
            for c in cases:
                if not isinstance(c, dict):
                    continue
                verdict = c.get("verdict")
                if isinstance(verdict, dict) and "placebo" in verdict:
                    has_placebo = True
                    break
                assertions = c.get("assertions")
                if isinstance(assertions, list) and any(
                        isinstance(assertion, dict) and "placebo" in assertion
                        for assertion in assertions):
                    has_placebo = True
                    break
                repetitions = c.get("repetitions")
                if isinstance(repetitions, list) and any(
                        isinstance(repetition, dict) and
                        isinstance(repetition.get("runs"), dict) and
                        "placebo" in repetition["runs"]
                        for repetition in repetitions):
                    has_placebo = True
                    break
            if has_placebo:
                required_conditions += ("placebo",)
    if mode in ROUTING_MODES:
        if not pr.get("routing_mechanism"):
            err(f"{base}: routing result missing routing_mechanism (selected skill unverified)")
    # Worker / run identity: for single-case backward compat a top-level
    # runs block is allowed, but for multi-case results the per-case/per-repetition
    # runs are authoritative. If per-case repetitions are present, top-level is optional.
    # Detect if this is a multi-case result with per-case repetitions
    has_per_case_reps = False
    if res.get("evaluation_mode") in (EXEC_MODES | REGRESSION_MODES):
        for cs in cases:
            if isinstance(cs, dict) and isinstance(
                    cs.get("repetitions"), list) and cs.get("repetitions"):
                has_per_case_reps = True
                break
    if has_per_case_reps:
        # Per-case repetitions are authoritative; top-level is optional alias
        # If top-level is present, it must still be distinct if used, but we don't
        # require it and we don't treat it as an independent execution for uniqueness
        g = runs.get("target")
        b = runs.get("baseline")
        if g is not None and b is not None and (
                not isinstance(g, dict) or not isinstance(b, dict)):
            err(f"{base}: top-level target/baseline runs must be objects")
        elif isinstance(g, dict) and isinstance(b, dict):
            if g.get("session_id") and b.get("session_id") and g["session_id"] == b["session_id"]:
                err(f"{base}: top-level target and baseline share a session_id (contamination)")
    else:
        left_name, right_name = (("candidate", "reference")
                                 if mode in REGRESSION_MODES
                                 else ("target", "baseline"))
        g = runs.get(left_name)
        b = runs.get(right_name)
        if g is None:
            g = {}
        if b is None:
            b = {}
        if not isinstance(g, dict) or not isinstance(b, dict):
            err(f"{base}: top-level {left_name}/{right_name} runs must be objects")
        elif not g.get("session_id") or not b.get("session_id"):
            err(f"{base}: result must record distinct {left_name}/{right_name} session_ids")
        elif g["session_id"] == b["session_id"]:
            err(f"{base}: {left_name} and {right_name} share a session_id (contamination)")
    # Multi-case execution results must use per-case natural_task_hash; a single
    # top-level protocol.natural_task_hash cannot represent several different prompts.
    if mode in (EXEC_MODES | REGRESSION_MODES) and status == "valid":
        has_top_task_hash = "natural_task_hash" in pr
        top_task_hash = pr.get("natural_task_hash")
        if len(cases) > 1 and has_top_task_hash:
            err(f"{base}: multi-case execution result has ambiguous top-level protocol.natural_task_hash; use per-case cases[].natural_task_hash instead (top-level must be absent for multi-case)")
        elif len(cases) == 1 and has_top_task_hash:
            case_task_hash = (cases[0].get("natural_task_hash")
                              if isinstance(cases[0], dict) else None)
            if not isinstance(top_task_hash, str) or not isinstance(
                    case_task_hash, str) or \
                    top_task_hash.removeprefix("sha256:") != \
                    case_task_hash.removeprefix("sha256:"):
                err(f"{base}: single-case protocol.natural_task_hash must "
                    "match cases[].natural_task_hash")
    # Protocol-validity gates: invalid/contaminated cannot produce success.
    if status in ("invalid", "contaminated"):
        for cs in cases:
            if not isinstance(cs, dict):
                continue
            outcome = cs.get("outcome")
            cat = (outcome.get("category")
                   if isinstance(outcome, dict) else None)
            if cat in ("skill_only_pass", "baseline_only_pass", "both_pass",
                       "candidate_only_pass", "reference_only_pass"):
                err(f"{base} case {cs.get('case_id')}: {status} result cannot claim a success outcome ({cat})")
    for cs in cases:
        check_result_case(
            base, cs, skill, mode, case_index,
            strict_execution=strict_comparison,
            protocol_name=selected_protocol,
            require_authoritative_case=(status == "valid"),
            protocol_status=status,
            required_conditions=required_conditions,
            declared_repeats=declared_repeats,
            global_identity=global_identity,
        )


def check_result_case(base, cs, skill, mode, case_index, *,
                      strict_execution=False,
                      protocol_name=None,
                      require_authoritative_case=False,
                      protocol_status=None,
                      required_conditions=("target", "baseline"),
                      declared_repeats=None,
                      global_identity=None):
    if not isinstance(cs, dict):
        err(f"{base}: result case must be an object")
        return
    cid = cs.get("case_id")
    if not isinstance(cid, int) or isinstance(cid, bool):
        err(f"{base}: case_id must be integer")
        return
    oc = cs.get("outcome")
    if oc is None:
        oc = {}
    elif not isinstance(oc, dict):
        err(f"{base} case {cid}: outcome must be an object")
        oc = {}
    cat = oc.get("category")
    if cat not in ALLOWED_OUTCOME:
        err(f"{base} case {cid}: outcome.category '{cat}' invalid")
    if oc.get("measurement_status") not in ALLOWED_MEASUREMENT:
        err(f"{base} case {cid}: outcome.measurement_status invalid")
    if oc.get("protocol_status") not in ALLOWED_PROTOCOL:
        err(f"{base} case {cid}: outcome.protocol_status invalid")
    elif protocol_status in ALLOWED_PROTOCOL and oc.get("protocol_status") != protocol_status:
        err(f"{base} case {cid}: outcome.protocol_status must match "
            f"top-level protocol.status ({protocol_status!r})")
    # Outcome <-> verdict consistency. Legacy routing/execution results use
    # target/baseline(/placebo); revision results use candidate/reference; a
    # smoke may intentionally contain only the target condition.
    verdict = cs.get("verdict")
    if verdict is None:
        verdict = {}
    elif not isinstance(verdict, dict):
        err(f"{base} case {cid}: verdict must be an object")
        verdict = {}
    if mode in REGRESSION_MODES:
        gp = verdict.get("candidate_pass")
        bp = verdict.get("reference_pass")
        if not isinstance(gp, bool) or not isinstance(bp, bool):
            err(f"{base} case {cid}: regression verdict requires candidate_pass/reference_pass booleans")
            return
        if gp and not bp:
            expect = "candidate_only_pass"
            regression_status = "improved"
        elif bp and not gp:
            expect = "reference_only_pass"
            regression_status = "regressed"
        elif gp and bp:
            expect = "both_pass"
            regression_status = "equivalent"
        else:
            expect = "both_fail"
            regression_status = "inconclusive"
        if cat != expect:
            err(f"{base} case {cid}: outcome.category '{cat}' inconsistent with regression verdict (expected {expect})")
        if oc.get("regression_status") not in REGRESSION_STATUSES:
            err(f"{base} case {cid}: regression result requires outcome.regression_status")
        elif oc.get("regression_status") != regression_status:
            err(f"{base} case {cid}: regression_status '{oc.get('regression_status')}' does not match observed candidate/reference verdict (expected {regression_status})")
    else:
        gp = verdict.get("target_pass")
        bp = verdict.get("baseline_pass")
        pp = verdict.get("placebo_pass")
        requires_baseline = "baseline" in required_conditions
        requires_placebo = "placebo" in required_conditions
        if not isinstance(gp, bool):
            err(f"{base} case {cid}: missing verdict.target_pass boolean")
            return
        if requires_baseline and not isinstance(bp, bool):
            err(f"{base} case {cid}: missing verdict.baseline_pass boolean")
            return
        if requires_placebo and not isinstance(pp, bool):
            err(f"{base} case {cid}: valid placebo comparison requires verdict.placebo_pass boolean")
        if not requires_baseline:
            if cat != ("single_condition_pass" if gp else "single_condition_fail"):
                err(f"{base} case {cid}: smoke result category must describe its single target condition")
        else:
            expect = None
            if gp and not bp:
                if pp is False or (pp is None and not requires_placebo):
                    expect = "skill_only_pass"
                elif pp is True:
                    expect = "non_discriminating"
            elif bp and not gp:
                expect = "baseline_only_pass"
            elif gp and bp:
                if pp is True:
                    expect = "non_discriminating"
                elif pp is False or (pp is None and not requires_placebo):
                    expect = "both_pass"
            elif not gp and not bp:
                if pp is False or (pp is None and not requires_placebo):
                    expect = "both_fail"
                elif pp is True:
                    expect = "placebo_only_pass"
            if expect and cat != expect:
                err(f"{base} case {cid}: outcome.category '{cat}' inconsistent with verdict (expected {expect})")

        if mode in EXEC_MODES:
            measurement = oc.get("measurement_status")
            if not requires_baseline:
                if measurement == "discriminating":
                    err(f"{base} case {cid}: a single-condition smoke cannot claim a discriminating comparison")
            else:
                controls = [bp]
                if requires_placebo:
                    controls.append(pp)
                if measurement == "discriminating":
                    if gp is not True or any(control is not False for control in controls):
                        err(f"{base} case {cid}: discriminating measurement requires target_pass=true and every declared control to fail")
                elif measurement == "non_discriminating":
                    if gp is True and all(control is False for control in controls):
                        err(f"{base} case {cid}: non_discriminating measurement cannot claim a unique target advantage")

    if require_authoritative_case:
        authoritative = case_index.get(skill, {}).get(cid)
        if authoritative is None:
            err(f"{base} case {cid}: case_id is not present in the current "
                f"{skill} evals; valid provenance must reference an "
                "authoritative case")
        elif not _case_supports_mode(authoritative, mode):
            err(f"{base} case {cid}: authoritative eval case does not support "
                f"evaluation_mode {mode!r}")

    if mode in ROUTING_MODES:
        check_routing_result_case(base, cs, skill, case_index, cid, gp, bp)
    else:
        check_exec_result_case(
            base, cs, skill, case_index, cid,
            strict=strict_execution,
            protocol_name=protocol_name,
            required_conditions=required_conditions,
            declared_repeats=declared_repeats,
            global_identity=global_identity,
        )


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
    rn = cs.get("runs")
    if rn is None:
        rn = {}
    elif not isinstance(rn, dict):
        err(f"{base} case {cid}: routing runs must be an object")
        return
    g = rn.get("target") or {}
    b = rn.get("baseline") or {}
    if not isinstance(g, dict) or not isinstance(b, dict):
        err(f"{base} case {cid}: routing target/baseline runs must be objects")
        return
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


def _assertion_text(assertion):
    if isinstance(assertion, str):
        return assertion
    if isinstance(assertion, dict):
        return assertion.get("text") or assertion.get("assertion")
    return None


def _assertion_scope(assertion):
    """Legacy strings and unscoped objects are safe shared-outcome criteria."""
    if isinstance(assertion, dict):
        return assertion.get("scope", "shared-outcome")
    return "shared-outcome"


def check_exec_result_case(base, cs, skill, case_index, cid, *, strict=False,
                           protocol_name=None,
                           required_conditions=("target", "baseline"),
                           declared_repeats=None,
                           global_identity=None):
    """Grade execution or revision assertions and enforce scope fairness."""
    # Per-case provenance is mandatory for protocol-valid execution results.
    # Limited/invalid records may remain compact, but any fields they do carry
    # are still checked. This keeps historical records readable without allowing
    # a valid claim to omit its provenance.
    import hashlib
    from eval_hashing import HASH_PREFIX
    # Validate per-case natural_task_hash against authoritative prompt (when case is known)
    if skill in case_index and cid in case_index[skill]:
        case = case_index[skill][cid]
        prompt = case.get("prompt", "")
        expected_hex = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        expected_prefixed = HASH_PREFIX + expected_hex
        actual = cs.get("natural_task_hash")
        if strict and (not isinstance(actual, str) or not actual.strip()):
            err(f"{base} case {cid}: missing cases[].natural_task_hash (per-case prompt hash required)")
        elif isinstance(actual, str) and actual.strip() and actual not in (
                expected_hex, expected_prefixed):
            err(f"{base} case {cid}: natural_task_hash does not match current source prompt (expected {expected_prefixed[:16]}.., got {actual[:16] if isinstance(actual,str) else actual!r})")
        # Fixture hash is mandatory for valid execution and, when present on a
        # non-valid record, must still match the frozen source.
        expected_fixture = None
        fx = case.get("fixture") or {}
        if fx.get("type") == "generator":
            expected_fixture = fx.get("output_hash") or fx.get("content_hash")
        else:
            expected_fixture = fx.get("content_hash")
        if strict and not expected_fixture:
            err(f"{base} case {cid}: authoritative frozen fixture hash is missing")
        if strict and (not isinstance(cs.get("fixture_hash"), str) or
                       not cs.get("fixture_hash", "").strip()):
            err(f"{base} case {cid}: missing cases[].fixture_hash "
                "(per-case frozen fixture hash required)")
        if "fixture_hash" in cs and cs.get("fixture_hash") is not None:
            fh = cs.get("fixture_hash")
            if expected_fixture and fh != expected_fixture:
                err(f"{base} case {cid}: fixture_hash does not match frozen fixture hash")
        raw_hash = cs.get("raw_evidence_hash")
        if strict and (not isinstance(raw_hash, str) or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", raw_hash)):
            err(f"{base} case {cid}: valid comparison requires raw_evidence_hash")
        elif raw_hash is not None and not re.fullmatch(
                r"sha256:[0-9a-f]{64}", str(raw_hash)):
            err(f"{base} case {cid}: raw_evidence_hash must be a SHA-256 digest")
    else:
        # Unknown cases cannot be hash-checked against the current source, but a
        # limited/invalid execution result may still carry the field for later
        # auditing without being checked against the current source.
        if strict and (not isinstance(cs.get("natural_task_hash"), str) or
                       not cs.get("natural_task_hash", "").strip()):
            err(f"{base} case {cid}: missing cases[].natural_task_hash (per-case prompt hash required)")
        if strict and (not isinstance(cs.get("fixture_hash"), str) or
                       not cs.get("fixture_hash", "").strip()):
            err(f"{base} case {cid}: missing cases[].fixture_hash "
                "(per-case frozen fixture hash required)")
        raw_hash = cs.get("raw_evidence_hash")
        if strict and (not isinstance(raw_hash, str) or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", raw_hash)):
            err(f"{base} case {cid}: valid comparison requires raw_evidence_hash")
        elif raw_hash is not None and not re.fullmatch(
                r"sha256:[0-9a-f]{64}", str(raw_hash)):
            err(f"{base} case {cid}: raw_evidence_hash must be a SHA-256 digest")
    # Repetitions provenance: a valid execution case must carry the declared
    # number of complete repetitions. Non-valid records may omit this block.
    reps = cs.get("repetitions")
    if reps is None:
        if strict:
            err(f"{base} case {cid}: missing cases[].repetitions (per-case/per-repetition execution identity required)")
    elif not isinstance(reps, list):
        err(f"{base} case {cid}: cases[].repetitions must be a list")
    elif not reps and strict:
        err(f"{base} case {cid}: cases[].repetitions must be a non-empty list")
    elif isinstance(reps, list):
        expected_repeats = declared_repeats if strict else None
        if strict and expected_repeats is not None and len(reps) != expected_repeats:
            err(f"{base} case {cid}: cases[].repetitions must contain "
                f"{expected_repeats} complete repetitions (found {len(reps)})")
        # Check each repetition structure and uniqueness
        seen_rep_ids = set()
        seen_sids = set()
        seen_cids = set()
        rep_indices = []
        for r in reps:
            if not isinstance(r, dict):
                err(f"{base} case {cid}: repetition is not an object")
                continue
            rid = r.get("repetition_id")
            if not isinstance(rid, str) or not rid.strip():
                err(f"{base} case {cid} rep{r.get('rep')}: missing repetition_id (stable per-repetition identity required)")
            elif rid in seen_rep_ids:
                err(f"{base} case {cid} rep{r.get('rep')}: duplicate repetition_id {rid!r}")
            else:
                seen_rep_ids.add(rid)
            rep_idx = r.get("rep")
            if not isinstance(rep_idx, int) or isinstance(rep_idx, bool):
                err(f"{base} case {cid}: repetition missing integer rep index")
            else:
                rep_indices.append(rep_idx)
            runs = r.get("runs") or {}
            if not isinstance(runs, dict):
                err(f"{base} case {cid} rep{rep_idx}: runs must be an object")
                continue
            # Each rep must contain every condition declared by the result.
            conditions_to_check = list(required_conditions)
            if "placebo" not in conditions_to_check and "placebo" in runs:
                conditions_to_check.append("placebo")
            for cond in conditions_to_check:
                if cond not in runs:
                    err(f"{base} case {cid} rep{rep_idx}: missing runs.{cond}")
                    continue
                cr = runs.get(cond) or {}
                if not isinstance(cr, dict):
                    err(f"{base} case {cid} rep{rep_idx} {cond}: run must be an object")
                    continue
                sid = cr.get("session_id")
                worker_id = cr.get("worker_id") or cr.get("container_id")
                cid_ = cr.get("container_id")
                if not isinstance(sid, str) or not sid.strip():
                    err(f"{base} case {cid} rep{rep_idx} {cond}: missing session_id")
                elif sid in seen_sids:
                    err(f"{base} case {cid} rep{rep_idx} {cond}: duplicate session_id {sid!r} (spliced or shared execution)")
                else:
                    seen_sids.add(sid)
                    if global_identity is not None:
                        if sid in global_identity["session_id"]:
                            err(f"{base} case {cid} rep{rep_idx} {cond}: duplicate session_id {sid!r} across cases")
                        global_identity["session_id"].add(sid)
                if not isinstance(worker_id, str) or not worker_id.strip():
                    err(f"{base} case {cid} rep{rep_idx} {cond}: missing worker_id/container_id")
                elif worker_id in seen_cids:
                    err(f"{base} case {cid} rep{rep_idx} {cond}: duplicate worker_id/container_id {worker_id!r} (spliced or shared execution)")
                else:
                    seen_cids.add(worker_id)
                    if global_identity is not None:
                        if worker_id in global_identity["worker_id"]:
                            err(f"{base} case {cid} rep{rep_idx} {cond}: duplicate worker_id/container_id {worker_id!r} across cases")
                        global_identity["worker_id"].add(worker_id)
                        if cid_:
                            if cid_ in global_identity["container_id"]:
                                err(f"{base} case {cid} rep{rep_idx} {cond}: duplicate container_id {cid_!r} across cases")
                            global_identity["container_id"].add(cid_)
            if strict and isinstance(rid, str) and rid.strip() and \
                    global_identity is not None:
                if rid in global_identity["repetition_id"]:
                    err(f"{base} case {cid} rep{rep_idx}: duplicate repetition_id "
                        f"{rid!r} across cases")
                global_identity["repetition_id"].add(rid)
        if strict and expected_repeats is not None:
            expected_indices = list(range(1, expected_repeats + 1))
            if sorted(rep_indices) != expected_indices:
                err(f"{base} case {cid}: repetition rep indices must be "
                    f"{expected_indices!r}")
        # Cross-rep duplicate detection already done via seen sets
    assertions = cs.get("assertions") or []
    if not isinstance(assertions, list) or not assertions:
        err(f"{base} case {cid}: execution result must grade at least one assertion")
        return
    frozen = []
    if skill in case_index and cid in case_index[skill]:
        frozen = case_index[skill][cid].get("execution", {}).get("assertions", [])
    frozen_by_text = {
        text: assertion for assertion in frozen
        if (text := _assertion_text(assertion))
    }
    graded_texts = [_assertion_text(a) for a in assertions
                    if isinstance(a, dict)]
    for fa in frozen:
        fa_text = _assertion_text(fa)
        if fa_text not in graded_texts:
            err(f"{base} case {cid}: frozen assertion missing from graded result: {str(fa_text)[:60]}")
    if strict and frozen:
        seen_graded = set()
        for graded_text in graded_texts:
            if graded_text in seen_graded:
                err(f"{base} case {cid}: duplicate assertion in graded result: {str(graded_text)[:60]}")
            seen_graded.add(graded_text)
            if graded_text not in frozen_by_text:
                err(f"{base} case {cid}: assertion is not declared by the authoritative case: {str(graded_text)[:60]}")
    condition_names = tuple(required_conditions)
    scored_assertions = []
    for a in assertions:
        if not isinstance(a, dict):
            err(f"{base} case {cid}: assertion entry must be an object")
            continue
        text = _assertion_text(a)
        expected = frozen_by_text.get(text)
        scope = _assertion_scope(a)
        if scope not in ALLOWED_ASSERTION_SCOPES:
            err(f"{base} case {cid}: invalid assertion scope {scope!r}")
        elif expected is not None and scope != _assertion_scope(expected):
            err(f"{base} case {cid}: assertion scope for {str(text)[:60]!r} does not match the frozen case definition")
        if protocol_name == "qualification" and scope in get_protocol("qualification").scored_scopes:
            scored_assertions.append(a)
        for cond in condition_names:
            if cond not in a:
                err(f"{base} case {cid}: assertion missing {cond} grade")
        for cond in condition_names:
            if cond not in a:
                continue
            g = a.get(cond)
            if g is None:
                g = {}
            elif not isinstance(g, dict):
                err(f"{base} case {cid}: assertion {cond} grade must be an object")
                continue
            if not isinstance(g.get("pass"), bool):
                err(f"{base} case {cid}: assertion missing {cond}.pass")
            elif g["pass"] is True and not str(g.get("evidence", "")).strip():
                err(f"{base} case {cid}: passing {cond} assertion has no evidence")

    # Qualification verdicts are recomputed from only common-denominator
    # assertions. A target-only contract assertion is retained for the
    # contract report but can never make the baseline lose marginal-value
    # credit.
    if protocol_name == "qualification":
        if not scored_assertions:
            err(f"{base} case {cid}: qualification must contain at least one shared-outcome or universal-safety assertion")
        else:
            shared_passes = {}
            for cond in ("target", "baseline"):
                grades = [a.get(cond, {}).get("pass") for a in scored_assertions
                          if isinstance(a.get(cond), dict)]
                if grades and all(isinstance(value, bool) for value in grades):
                    shared_passes[cond] = all(grades)
            verdict = cs.get("verdict") or {}
            for cond in ("target", "baseline"):
                key = f"{cond}_pass"
                if cond in shared_passes and verdict.get(key) != shared_passes[cond]:
                    err(f"{base} case {cid}: {key} must be calculated from shared-outcome assertions; skill-contract assertions cannot change marginal-value scoring")
        repeats = declared_repeats
        early_stop = cs.get("early_stop")
        measurement = (cs.get("outcome") or {}).get("measurement_status")
        if repeats == 1 and measurement == "non_discriminating":
            if not isinstance(early_stop, dict) or early_stop.get("stopped") is not True:
                err(f"{base} case {cid}: n=1 non_discriminating qualification must record early_stop.stopped=true")
            elif not str(early_stop.get("reason", "")).strip():
                err(f"{base} case {cid}: early_stop.reason is required")
        elif early_stop is not None:
            if not isinstance(early_stop, dict) or not isinstance(early_stop.get("stopped"), bool):
                err(f"{base} case {cid}: early_stop must contain a boolean stopped field")


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
    if not is_safe_skill_name(skill):
        errs.append("execution evidence skill must be a single safe skill name")
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


def validate_generic_execution_evidence(evidence):
    """Validate execution evidence emitted through the neutral adapter."""

    errs = []
    if evidence.get("evidence_type") != "execution":
        errs.append(f"expected evidence_type 'execution', got {evidence.get('evidence_type')!r}")
    protocol = evidence.get("protocol")
    protocol_name_value = (protocol.get("name") if isinstance(protocol, dict)
                           else protocol)
    if protocol_name_value not in {"smoke", "qualification", "confirmation"}:
        errs.append("neutral execution evidence must declare smoke, qualification, or confirmation protocol")
    harness = evidence.get("harness")
    if not isinstance(harness, dict) or harness.get("adapter_protocol") != (
            "agent-guidance-kit.harness-adapter/v1"):
        errs.append("neutral execution evidence must identify the harness adapter protocol")
    anchor = _execution_source_anchor_generic(evidence, errs)
    if anchor is None:
        return errs
    repetitions = evidence.get("repetitions") or []
    conditions = evidence.get("conditions")
    for error in validate_declaration(protocol_name_value, conditions,
                                      len(repetitions)):
        errs.append(error)
    if not isinstance(conditions, list):
        return errs
    allowed = {"target", "baseline", "placebo"}
    unknown = set(conditions) - allowed
    if unknown:
        errs.append(f"neutral execution evidence has unknown condition(s): {sorted(unknown)!r}")
    expected_fixture = anchor["expected_fixture_hash"]
    seed = evidence.get("canonical_task_seed_hash")
    if not seed:
        errs.append("neutral execution evidence missing canonical_task_seed_hash")
    elif expected_fixture and seed != expected_fixture:
        errs.append("neutral execution canonical seed does not match frozen fixture")
    runtime_paths = evidence.get("runtime_treatment_paths")
    if (harness_runner is None or
            runtime_paths != list(harness_runner.RUNTIME_TREATMENT_PATHS)):
        errs.append("neutral execution runtime_treatment_paths do not match the neutral evaluator paths")
    if not anchor["expected_fixture_hash"]:
        errs.append("execution evidence current fixture has no frozen content/output hash")
    elif not isinstance(evidence.get("expected_fixture_hash"), str) or not evidence.get("expected_fixture_hash").strip():
        errs.append("execution evidence missing expected_fixture_hash for frozen content/output hash")
    elif evidence.get("expected_fixture_hash") != anchor["expected_fixture_hash"]:
        errs.append("execution evidence expected_fixture_hash does not match current frozen fixture hash")
    if not evidence.get("target_guidance_hash"):
        errs.append("neutral execution evidence missing target_guidance_hash")
    elif evidence.get("target_skill_content_hash") != evidence.get("target_guidance_hash"):
        errs.append("neutral execution target guidance hash does not match target skill content hash")
    if "baseline" in conditions:
        if not evidence.get("target_absent_in_baseline"):
            errs.append("neutral execution evidence missing target_absent_in_baseline")
        if not evidence.get("baseline_guidance_absent"):
            errs.append("neutral execution evidence missing baseline_guidance_absent")
    if "placebo" in conditions:
        for key in ("placebo_skill", "placebo_skill_content_hash",
                    "placebo_guidance_path"):
            if not evidence.get(key):
                errs.append(f"neutral execution evidence missing {key}")
        placebo = evidence.get("placebo_skill")
        if placebo == evidence.get("skill"):
            errs.append("neutral execution placebo skill must differ from target")
        if not is_safe_skill_name(placebo):
            errs.append("neutral execution placebo skill must be a single safe skill name")
        elif harness_runner is not None and isinstance(placebo, str):
            placebo_path = os.path.join(ROOT, "skills", placebo)
            current_placebo_hash = harness_runner.skill_tree_hash(placebo_path)
            if evidence.get("placebo_skill_content_hash") != current_placebo_hash:
                errs.append("neutral execution placebo skill hash does not match the current skill")

    seen_repetitions = set()
    seen_workers = set()
    seen_sessions = set()
    expected_task_hash = hashlib.sha256(
        anchor["case"].get("prompt", "").encode()).hexdigest()
    for repetition in repetitions:
        tag = f"rep{repetition.get('rep')}"
        rid = repetition.get("repetition_id")
        if not isinstance(rid, str) or not rid.strip():
            errs.append(f"{tag}: missing repetition_id")
        elif rid in seen_repetitions:
            errs.append(f"{tag}: duplicate repetition_id")
        else:
            seen_repetitions.add(rid)
        if repetition.get("natural_task_hash") != expected_task_hash:
            errs.append(f"{tag}: natural_task_hash does not match current case prompt")
        if repetition.get("natural_task_identical_across_conditions") is not True:
            errs.append(f"{tag}: natural_task_identical_across_conditions must be true")
        cmap = repetition.get("conditions") or {}
        if set(cmap) != set(conditions):
            errs.append(f"{tag}: condition evidence does not match declared conditions")
            continue
        starts = []
        workers = []
        sessions = []
        activation_mechanisms = []
        workspaces = (repetition.get("condition_workspace_ids") or {}).values()
        if len(set(workspaces)) != len(conditions):
            errs.append(f"{tag}: condition workspace ids are not distinct")
        receipt_hashes = repetition.get("condition_workspace_receipt_hashes")
        if (not isinstance(receipt_hashes, dict) or
                set(receipt_hashes) != set(conditions)):
            errs.append(f"{tag}: condition workspace receipt hashes are incomplete")
            receipt_hashes = {}
        if (repetition.get("workspace_receipt_path") !=
                getattr(harness_runner, "WORKSPACE_RECEIPT_PATH", None)):
            errs.append(f"{tag}: workspace receipt path is not the neutral receipt path")
        for name in conditions:
            cmeta = cmap.get(name) or {}
            ctag = f"{tag} {name}"
            if cmeta.get("repetition_id") != rid:
                errs.append(f"{ctag}: repetition_id does not match parent repetition")
            for key in ("worker_id", "session_id", "run_status", "returncode",
                        "starting_task_hash", "ending_task_hash",
                        "starting_full_hash", "ending_full_hash",
                        "guidance_probe", "guidance_context_probe",
                        "guidance_path", "guidance_content_hash",
                        "workspace_receipt", "workspace_receipt_path",
                        "workspace_receipt_hash", "attestation_nonce",
                        "execution_request_hash", "execution_observation_hash",
                        "execution_attestation"):
                if key not in cmeta:
                    errs.append(f"{ctag}: missing {key}")
            _validate_workspace_receipt(
                cmeta, receipt_hashes.get(name), ctag, errs)
            _validate_execution_attestation(
                cmeta, receipt_hashes.get(name), ctag, errs)
            if cmeta.get("run_status") != "success" or cmeta.get("returncode") != 0:
                errs.append(f"{ctag}: failed condition is not evidence")
            if not (cmeta.get("output") or "").strip():
                errs.append(f"{ctag}: empty model output")
            if expected_fixture and cmeta.get("starting_task_hash") != expected_fixture:
                errs.append(f"{ctag}: starting task hash does not match frozen seed")
            starts.append(cmeta.get("starting_task_hash"))
            worker = cmeta.get("worker_id")
            session = cmeta.get("session_id")
            workers.append(worker)
            sessions.append(session)
            if not worker or not session:
                errs.append(f"{ctag}: worker_id and session_id are required")
            if worker in seen_workers:
                errs.append(f"{ctag}: duplicate worker_id across repetitions")
            if session in seen_sessions:
                errs.append(f"{ctag}: duplicate session_id across repetitions")
            if worker:
                seen_workers.add(worker)
            if session:
                seen_sessions.add(session)
            guided = name != "baseline"
            if guided:
                expected_hash = (evidence.get("target_guidance_hash")
                                 if name == "target" else
                                 evidence.get("placebo_skill_content_hash"))
                expected_path = (evidence.get("target_guidance_path")
                                 if name == "target" else
                                 evidence.get("placebo_guidance_path"))
                if cmeta.get("guidance_probe") != "present":
                    errs.append(f"{ctag}: guidance probe did not confirm a present tree")
                if cmeta.get("guidance_context_probe") != "present":
                    errs.append(f"{ctag}: guidance context probe did not confirm activation")
                if cmeta.get("guidance_content_hash") != expected_hash:
                    errs.append(f"{ctag}: guidance content hash does not match the frozen skill")
                if cmeta.get("guidance_path") != expected_path:
                    errs.append(f"{ctag}: guidance path does not match the neutral runtime path")
                if not isinstance(cmeta.get("activation_mechanism"), str) or not cmeta.get("activation_mechanism"):
                    errs.append(f"{ctag}: activation_mechanism is missing")
                else:
                    activation_mechanisms.append(cmeta["activation_mechanism"])
            else:
                if cmeta.get("guidance_probe") not in {"absent", None}:
                    errs.append(f"{ctag}: baseline guidance probe must be absent")
                if cmeta.get("guidance_context_probe") not in {"none", "absent", None}:
                    errs.append(f"{ctag}: baseline guidance context probe must be none/absent")
                if cmeta.get("guidance_path") is not None:
                    errs.append(f"{ctag}: baseline must not have a guidance path")
                if cmeta.get("guidance_content_hash") is not None:
                    errs.append(f"{ctag}: baseline must not have a guidance content hash")
        if len(set(workers)) != len(conditions):
            errs.append(f"{tag}: conditions do not have distinct worker_ids")
        if len(set(sessions)) != len(conditions):
            errs.append(f"{tag}: conditions do not have distinct session_ids")
        if len(set(starts)) != 1:
            errs.append(f"{tag}: condition starting task hashes differ")
        if len(set(activation_mechanisms)) > 1:
            errs.append(f"{tag}: guided conditions use different activation_mechanisms")
    return errs


def _execution_source_anchor_generic(evidence, errs):
    """Resolve common current-source anchors without a harness-specific hash."""

    skill = evidence.get("skill")
    case_id = evidence.get("case_id")
    if not isinstance(skill, str) or not skill:
        errs.append("execution evidence missing skill")
        return None
    if not is_safe_skill_name(skill):
        errs.append("execution evidence skill must be a single safe skill name")
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
    except (OSError, ValueError) as exc:
        errs.append(f"execution source evals unreadable: {exc}")
        return None
    case = next((item for item in source.get("evals", [])
                 if item.get("id") == case_id), None)
    if case is None:
        errs.append("execution evidence case_id is not present in the current skill evals")
        return None
    if "execution" not in case.get("evaluation_modes", []):
        errs.append("execution evidence case is not an execution case")
    fixture = case.get("fixture") or {}
    expected = (fixture.get("output_hash")
                if fixture.get("type") == "generator"
                else fixture.get("content_hash"))
    evals_rel = os.path.relpath(evals_path, ROOT)
    skill_rel = os.path.dirname(os.path.dirname(evals_rel))
    fixture_rel = os.path.normpath(
        os.path.join(skill_rel, fixture.get("path", "")))
    source_hash = HASH_PREFIX + hashlib.sha256(
        open(evals_path, "rb").read()).hexdigest()
    if evidence.get("fixture_source_path") != evals_rel:
        errs.append("execution evidence fixture_source_path does not match current evals path")
    if evidence.get("fixture_path") != fixture_rel:
        errs.append("execution evidence fixture_path does not match current fixture path")
    if evidence.get("fixture_source_hash") != source_hash:
        errs.append("execution evidence fixture_source_hash does not match current evals.json")
    if not expected:
        errs.append("execution evidence current fixture has no frozen content/output hash")
    elif evidence.get("expected_fixture_hash") != expected:
        errs.append("execution evidence expected_fixture_hash does not match current frozen fixture hash")
    expected_skill_path = os.path.join("skills", skill)
    if evidence.get("target_skill_source_path") != expected_skill_path:
        errs.append("execution evidence target_skill_source_path does not match the target skill")
    if harness_runner is not None:
        current_hash = harness_runner.skill_tree_hash(os.path.join(ROOT, skill_rel))
        if evidence.get("target_skill_content_hash") != current_hash:
            errs.append("execution evidence target_skill_content_hash does not match the current target skill")
    return {"skill": skill, "case_id": case_id, "case": case,
            "fixture": fixture, "expected_fixture_hash": expected,
            "evals_path": evals_path, "evals_rel": evals_rel,
            "fixture_rel": fixture_rel, "source_hash": source_hash}


def _validate_workspace_receipt(cmeta, expected_hash, ctag, errs):
    """Require the adapter to return the random receipt from this workspace."""

    expected_path = (harness_runner.WORKSPACE_RECEIPT_PATH
                     if harness_runner is not None else None)
    if cmeta.get("workspace_receipt_path") != expected_path:
        errs.append(f"{ctag}: workspace receipt path is not the neutral receipt path")
    receipt = cmeta.get("workspace_receipt")
    if not isinstance(receipt, str) or not receipt:
        errs.append(f"{ctag}: adapter did not return a workspace receipt")
        return
    if cmeta.get("workspace_receipt_hash") != expected_hash:
        errs.append(f"{ctag}: workspace receipt hash is not bound to its condition")
    actual_hash = HASH_PREFIX + hashlib.sha256(receipt.encode()).hexdigest()
    if actual_hash != expected_hash:
        errs.append(f"{ctag}: workspace receipt does not match the evaluator receipt")


def _validate_execution_attestation(cmeta, expected_receipt_hash, ctag, errs):
    """Require a worker-sourced attestation bound to all neutral evidence."""

    attestation = cmeta.get("execution_attestation")
    if not isinstance(attestation, dict):
        errs.append(f"{ctag}: missing execution_attestation")
        return
    if attestation.get("protocol") != EXECUTION_ATTESTATION_PROTOCOL:
        errs.append(f"{ctag}: execution_attestation protocol is unsupported")
    if attestation.get("status") != "verified":
        errs.append(f"{ctag}: execution_attestation is not verified")
    if attestation.get("verification_mode") != "independent":
        errs.append(f"{ctag}: execution_attestation is not independently verified")
    if attestation.get("source") != "worker":
        errs.append(f"{ctag}: execution_attestation source is not the worker")
    for key in ("worker_id", "session_id", "nonce", "request_hash",
                "workspace_receipt_hash", "output_hash", "returncode"):
        if key not in attestation:
            errs.append(f"{ctag}: execution_attestation missing {key}")
    for key in ("worker_id", "session_id", "nonce"):
        value = attestation.get(key)
        if not isinstance(value, str) or not value.strip():
            errs.append(f"{ctag}: execution_attestation {key} must be non-empty")
    for key in ("request_hash", "workspace_receipt_hash", "output_hash",
                "observation_hash"):
        value = attestation.get(key)
        if not isinstance(value, str) or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", value):
            errs.append(f"{ctag}: execution_attestation {key} must be a SHA-256 digest")
    if attestation.get("worker_id") != cmeta.get("worker_id"):
        errs.append(f"{ctag}: execution_attestation worker_id is not bound")
    if attestation.get("session_id") != cmeta.get("session_id"):
        errs.append(f"{ctag}: execution_attestation session_id is not bound")
    if attestation.get("nonce") != cmeta.get("attestation_nonce"):
        errs.append(f"{ctag}: execution_attestation nonce is not bound")
    if attestation.get("request_hash") != cmeta.get("execution_request_hash"):
        errs.append(f"{ctag}: execution_attestation request is not bound")
    expected_observation_hash = None
    if harness_runner is not None:
        expected_observation_hash = harness_runner.attestation_observation_hash(
            cmeta)
    if cmeta.get("execution_observation_hash") != expected_observation_hash:
        errs.append(f"{ctag}: execution observation is not evaluator-bound")
    if attestation.get("observation_hash") != expected_observation_hash:
        errs.append(f"{ctag}: execution_attestation observation is not bound")
    if attestation.get("workspace_receipt_hash") != expected_receipt_hash:
        errs.append(f"{ctag}: execution_attestation receipt is not bound")
    if (not isinstance(attestation.get("returncode"), int) or
            isinstance(attestation.get("returncode"), bool)):
        errs.append(f"{ctag}: execution_attestation returncode must be an integer")
    elif attestation.get("returncode") != cmeta.get("returncode"):
        errs.append(f"{ctag}: execution_attestation returncode is not bound")
    output = cmeta.get("output")
    if not isinstance(output, str):
        errs.append(f"{ctag}: execution_attestation cannot bind non-text output")
    else:
        output_hash = HASH_PREFIX + hashlib.sha256(output.encode()).hexdigest()
        if attestation.get("output_hash") != output_hash:
            errs.append(f"{ctag}: execution_attestation output is not bound")


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
    harness = evidence.get("harness")
    if (isinstance(harness, dict) and
            harness.get("adapter_protocol") == "agent-guidance-kit.harness-adapter/v1"):
        return validate_generic_execution_evidence(evidence)

    errs = []
    et = evidence.get("evidence_type")
    if et != "execution":
        errs.append(f"expected evidence_type 'execution', got {et!r}")
    source_anchor = _execution_source_anchor(evidence, errs)
    if source_anchor is not None:
        _placebo_source_anchor(evidence, source_anchor, errs)
    expected_natural_task_hash = None
    if source_anchor is not None:
        expected_natural_task_hash = hashlib.sha256(
            source_anchor["case"]["prompt"].encode()).hexdigest()
    reps = evidence.get("repetitions") or []
    if not reps:
        errs.append("execution evidence has no repetitions")
        return errs
    conds = evidence.get("conditions") or ["target", "baseline"]
    raw_protocol = evidence.get("protocol")
    evidence_protocol = (
        raw_protocol.get("name") if isinstance(raw_protocol, dict)
        else raw_protocol if isinstance(raw_protocol, str) else None
    )
    if evidence_protocol is not None:
        for protocol_error in validate_declaration(
                evidence_protocol, conds, len(reps)):
            errs.append(protocol_error)
        protocol_def = get_protocol(evidence_protocol)
        required_conditions = set(protocol_def.required_conditions) if protocol_def else {"target", "baseline"}
    else:
        # Existing local evidence predates protocol.name and is retained under
        # the old target/baseline(/placebo) contract.
        required_conditions = {"target", "baseline"}
    if not set(conds) >= required_conditions:
        errs.append(f"execution evidence conditions {conds!r} do not include "
                    f"required condition(s) {sorted(required_conditions)!r}")
        return errs
    for extra in set(conds) - {"target", "baseline", "placebo"}:
        errs.append(f"unknown condition {extra!r} in evidence")
    # Repetition identity and integrity: each repetition is an atomic experimental unit
    seen_rep_ids = set()
    seen_cids_global = set()
    seen_sids_global = set()
    for r in reps:
        rid = r.get("repetition_id")
        if not isinstance(rid, str) or not rid.strip():
            errs.append(f"rep{r.get('rep')}: missing repetition_id (stable per-repetition identity required)")
        elif rid in seen_rep_ids:
            errs.append(f"rep{r.get('rep')}: duplicate repetition_id {rid!r} (repetition identity must be unique)")
        else:
            seen_rep_ids.add(rid)
        # Cross-repetition splicing detection via container/session IDs
        cmap = r.get("conditions") or {}
        for name in conds:
            cmeta = cmap.get(name) or {}
            # Per-condition repetition_id must match the parent rep's ID (proves the three conditions were generated together)
            crid = cmeta.get("repetition_id")
            if not isinstance(crid, str) or not crid.strip():
                errs.append(f"rep{r.get('rep')} {name}: missing repetition_id (per-condition repetition identity required)")
            elif crid != rid:
                errs.append(f"rep{r.get('rep')} {name}: repetition_id {crid!r} does not match parent rep {rid!r} (spliced condition)")
            cid = cmeta.get("container_id")
            sid = cmeta.get("session_id")
            if isinstance(cid, str) and cid:
                if cid in seen_cids_global:
                    errs.append(f"rep{r.get('rep')} {name}: duplicate container_id {cid!r} across repetitions (spliced or shared execution)")
                else:
                    seen_cids_global.add(cid)
            if isinstance(sid, str) and sid:
                if sid in seen_sids_global:
                    errs.append(f"rep{r.get('rep')} {name}: duplicate session_id {sid!r} across repetitions (spliced or shared execution)")
                else:
                    seen_sids_global.add(sid)
        # A failed condition invalidates the entire repetition
        has_failed = any((cmap.get(n) or {}).get("run_status") != "success" for n in conds if n in cmap)
        if has_failed:
            errs.append(f"rep{r.get('rep')}: has failed condition(s); entire repetition must be discarded and replaced with a complete fresh target/baseline/placebo triplet (do not splice)")
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
    elif execution_runner is not None:
        expected_runtime_paths = list(execution_runner.RUNTIME_TREATMENT_PATHS)
        if runtime_paths != expected_runtime_paths:
            errs.append(
                "execution evidence runtime_treatment_paths must exactly "
                f"match the canonical runner list {expected_runtime_paths!r}")
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
        elif expected_natural_task_hash and th != expected_natural_task_hash:
            errs.append(f"{tag}: natural_task_hash does not match the current "
                        f"source eval case prompt (stale or mismatched task)")
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
        if "baseline" in conds:
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


def validate_regression_evidence(evidence):
    """Validate candidate/reference raw evidence without treating either as baseline."""

    harness = evidence.get("harness")
    if (isinstance(harness, dict) and
            harness.get("adapter_protocol") == "agent-guidance-kit.harness-adapter/v1"):
        return validate_generic_regression_evidence(evidence)

    errs = []
    if evidence.get("evidence_type") != "regression":
        errs.append(f"expected evidence_type 'regression', got {evidence.get('evidence_type')!r}")
    if evidence.get("protocol") not in ("regression", {"name": "regression"}):
        errs.append("regression evidence must declare protocol 'regression'")
    skill = evidence.get("skill")
    case_id = evidence.get("case_id")
    if not isinstance(skill, str) or not skill:
        errs.append("regression evidence missing skill")
        return errs
    if not isinstance(case_id, int):
        errs.append("regression evidence missing integer case_id")
        return errs
    evals_path = os.path.join(ROOT, "skills", skill, "evals", "evals.json")
    if not os.path.isfile(evals_path):
        errs.append(f"regression evidence skill evals not found: {skill}")
        return errs
    try:
        source = json.load(open(evals_path, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errs.append(f"regression source evals unreadable: {exc}")
        return errs
    case = next((item for item in source.get("evals", [])
                 if item.get("id") == case_id), None)
    if case is None:
        errs.append("regression evidence case_id is not present in current skill evals")
        return errs
    if "execution" not in case.get("evaluation_modes", []):
        errs.append("regression evidence case is not an execution case")
    fixture = case.get("fixture") or {}
    expected_fixture = (fixture.get("output_hash") if fixture.get("type") == "generator"
                        else fixture.get("content_hash"))
    evals_rel = os.path.relpath(evals_path, ROOT)
    skill_rel = os.path.dirname(os.path.dirname(evals_rel))
    fixture_rel = os.path.normpath(os.path.join(skill_rel, fixture.get("path", "")))
    source_hash = HASH_PREFIX + hashlib.sha256(open(evals_path, "rb").read()).hexdigest()
    if evidence.get("fixture_source_path") != evals_rel:
        errs.append("regression evidence fixture_source_path does not match current evals path")
    if evidence.get("fixture_path") != fixture_rel:
        errs.append("regression evidence fixture_path does not match current fixture path")
    if evidence.get("fixture_source_hash") != source_hash:
        errs.append("regression evidence fixture_source_hash does not match current evals.json")
    if expected_fixture and evidence.get("expected_fixture_hash") != expected_fixture:
        errs.append("regression evidence expected_fixture_hash does not match frozen fixture hash")
    for key in ("candidate_revision", "reference_revision",
                "candidate_skill_content_hash", "reference_skill_content_hash"):
        if not isinstance(evidence.get(key), str) or not evidence[key].strip():
            errs.append(f"regression evidence missing {key}")
    for key in ("candidate_revision", "reference_revision"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(evidence.get(key, ""))):
            errs.append(f"regression evidence {key} must be a resolved Git commit SHA")
    expected_skill_source = f"skills/{skill}"
    for key in ("candidate_skill_source_path", "reference_skill_source_path"):
        if evidence.get(key) != expected_skill_source:
            errs.append(f"regression evidence {key} does not match the current skill")
    conditions = evidence.get("conditions")
    if conditions != ["candidate", "reference"]:
        errs.append(f"regression evidence conditions must be ['candidate', 'reference'], got {conditions!r}")
    repetitions = evidence.get("repetitions") or []
    for error in validate_declaration("regression", conditions, len(repetitions)):
        errs.append(error)
    expected_task_hash = hashlib.sha256(case.get("prompt", "").encode()).hexdigest()
    expected_seed = evidence.get("expected_fixture_hash")
    seed = evidence.get("canonical_task_seed_hash")
    if not seed:
        errs.append("regression evidence missing canonical_task_seed_hash")
    elif expected_seed and seed != expected_seed:
        errs.append("regression canonical_task_seed_hash does not match frozen fixture")
    runtime_paths = evidence.get("runtime_treatment_paths")
    if execution_runner is not None and runtime_paths != list(execution_runner.RUNTIME_TREATMENT_PATHS):
        errs.append("regression evidence runtime_treatment_paths do not match the canonical runner")

    seen_repetitions = set()
    seen_sessions = set()
    seen_containers = set()
    for repetition in repetitions:
        tag = f"rep{repetition.get('rep')}"
        rid = repetition.get("repetition_id")
        if not isinstance(rid, str) or not rid.strip():
            errs.append(f"{tag}: missing repetition_id")
        elif rid in seen_repetitions:
            errs.append(f"{tag}: duplicate repetition_id")
        else:
            seen_repetitions.add(rid)
        if repetition.get("natural_task_hash") != expected_task_hash:
            errs.append(f"{tag}: natural_task_hash does not match current case prompt")
        if repetition.get("natural_task_identical_across_conditions") is not True:
            errs.append(f"{tag}: natural_task_identical_across_conditions must be true")
        cmap = repetition.get("conditions") or {}
        if set(cmap) != {"candidate", "reference"}:
            errs.append(f"{tag}: candidate/reference condition evidence is incomplete")
            continue
        starts = []
        workspaces = []
        for name in ("candidate", "reference"):
            cmeta = cmap.get(name) or {}
            ctag = f"{tag} {name}"
            if cmeta.get("repetition_id") != rid:
                errs.append(f"{ctag}: repetition_id does not match parent repetition")
            for key in ("container_id", "session_id", "run_status", "returncode",
                        "starting_task_hash", "ending_task_hash",
                        "starting_full_hash", "ending_full_hash",
                        "skill_probe", "skill_context_probe"):
                if key not in cmeta:
                    errs.append(f"{ctag}: missing {key}")
            if cmeta.get("run_status") != "success" or cmeta.get("returncode") != 0:
                errs.append(f"{ctag}: failed condition is not evidence")
            if not (cmeta.get("output") or "").strip():
                errs.append(f"{ctag}: empty model output")
            if expected_seed and cmeta.get("starting_task_hash") != expected_seed:
                errs.append(f"{ctag}: starting task hash does not match frozen seed")
            starts.append(cmeta.get("starting_task_hash"))
            workspaces.append((cmeta.get("container_id"), cmeta.get("session_id"),
                               cmeta.get("skill_kilo_path")))
            expected_hash_key = f"{name}_skill_content_hash"
            if cmeta.get("activation_mechanism") != "kilo-command-skill":
                errs.append(f"{ctag}: guidance was not activated through kilo-command-skill")
            if cmeta.get("skill_command") != f"{skill}:skill":
                errs.append(f"{ctag}: skill command does not match the compared skill")
            if cmeta.get("skill_kilo_path") != f".kilo/skills/{skill}":
                errs.append(f"{ctag}: skill discovery path is incorrect")
            if cmeta.get("skill_content_hash") != evidence.get(expected_hash_key):
                errs.append(f"{ctag}: skill content hash does not match the revision anchor")
            if cmeta.get("skill_probe") != "present":
                errs.append(f"{ctag}: skill probe did not confirm a present tree")
            if cmeta.get("skill_context_probe") != "present":
                errs.append(f"{ctag}: skill context probe did not confirm activation")
        if len({item[0] for item in workspaces}) != 2:
            errs.append(f"{tag}: candidate/reference containers are not distinct")
        if len({item[1] for item in workspaces}) != 2:
            errs.append(f"{tag}: candidate/reference sessions are not distinct")
        if len({item[2] for item in workspaces}) != 1:
            errs.append(f"{tag}: candidate/reference discovery paths differ unexpectedly")
        if len(set(starts)) != 1:
            errs.append(f"{tag}: candidate/reference starting task hashes differ")
        workspace_ids = (repetition.get("condition_workspace_ids") or {}).values()
        if len(set(workspace_ids)) != 2:
            errs.append(f"{tag}: candidate/reference workspace ids are not distinct")
        for cmeta in cmap.values():
            sid = cmeta.get("session_id")
            cid = cmeta.get("container_id")
            if sid in seen_sessions:
                errs.append(f"{tag}: duplicate session_id across repetitions")
            if cid in seen_containers:
                errs.append(f"{tag}: duplicate container_id across repetitions")
            if sid:
                seen_sessions.add(sid)
            if cid:
                seen_containers.add(cid)
    return errs


def validate_generic_regression_evidence(evidence):
    """Validate regression evidence from a harness-neutral adapter.

    Unlike the historical Docker evidence path, this validator requires only
    worker/session identity and adapter-provided guidance/context probes.  A
    container, image, CLI name, or provider is optional and may be recorded as
    adapter metadata when available.
    """

    errs = []
    if evidence.get("evidence_type") != "regression":
        errs.append(f"expected evidence_type 'regression', got {evidence.get('evidence_type')!r}")
    protocol = evidence.get("protocol")
    protocol_name_value = (protocol.get("name") if isinstance(protocol, dict)
                           else protocol)
    if protocol_name_value != "regression":
        errs.append("regression evidence must declare protocol 'regression'")
    harness = evidence.get("harness")
    if not isinstance(harness, dict) or harness.get("adapter_protocol") != (
            "agent-guidance-kit.harness-adapter/v1"):
        errs.append("regression evidence must identify the harness adapter protocol")
    skill = evidence.get("skill")
    case_id = evidence.get("case_id")
    if not isinstance(skill, str) or not skill:
        errs.append("regression evidence missing skill")
        return errs
    if not is_safe_skill_name(skill):
        errs.append("regression evidence skill must be a single safe skill name")
        return errs
    if not isinstance(case_id, int):
        errs.append("regression evidence missing integer case_id")
        return errs
    evals_path = os.path.join(ROOT, "skills", skill, "evals", "evals.json")
    if not os.path.isfile(evals_path):
        errs.append(f"regression evidence skill evals not found: {skill}")
        return errs
    try:
        source = json.load(open(evals_path, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errs.append(f"regression source evals unreadable: {exc}")
        return errs
    case = next((item for item in source.get("evals", [])
                 if item.get("id") == case_id), None)
    if case is None:
        errs.append("regression evidence case_id is not present in current skill evals")
        return errs
    if "execution" not in case.get("evaluation_modes", []):
        errs.append("regression evidence case is not an execution case")
    fixture = case.get("fixture") or {}
    expected_fixture = (fixture.get("output_hash")
                        if fixture.get("type") == "generator"
                        else fixture.get("content_hash"))
    evals_rel = os.path.relpath(evals_path, ROOT)
    skill_rel = os.path.dirname(os.path.dirname(evals_rel))
    fixture_rel = os.path.normpath(
        os.path.join(skill_rel, fixture.get("path", "")))
    source_hash = HASH_PREFIX + hashlib.sha256(
        open(evals_path, "rb").read()).hexdigest()
    if evidence.get("fixture_source_path") != evals_rel:
        errs.append("regression evidence fixture_source_path does not match current evals path")
    if evidence.get("fixture_path") != fixture_rel:
        errs.append("regression evidence fixture_path does not match current fixture path")
    if evidence.get("fixture_source_hash") != source_hash:
        errs.append("regression evidence fixture_source_hash does not match current evals.json")
    if not expected_fixture:
        errs.append("regression evidence current fixture has no frozen content/output hash")
    elif not isinstance(evidence.get("expected_fixture_hash"), str) or not evidence.get("expected_fixture_hash").strip():
        errs.append("regression evidence missing expected_fixture_hash for frozen content/output hash")
    elif evidence.get("expected_fixture_hash") != expected_fixture:
        errs.append("regression evidence expected_fixture_hash does not match frozen fixture hash")
    for key in ("candidate_revision", "reference_revision",
                "candidate_skill_content_hash", "reference_skill_content_hash"):
        if not isinstance(evidence.get(key), str) or not evidence[key].strip():
            errs.append(f"regression evidence missing {key}")
    expected_skill_source = f"skills/{skill}"
    for key in ("candidate_skill_source_path", "reference_skill_source_path"):
        if evidence.get(key) != expected_skill_source:
            errs.append(f"regression evidence {key} does not match the current skill")
    for key in ("candidate_revision", "reference_revision"):
        if not _git_commit_exists(evidence.get(key)):
            errs.append(f"regression evidence {key} must be an existing Git commit SHA")
    revision_hashes = {}
    for revision_key, hash_key in (
            ("candidate_revision", "candidate_skill_content_hash"),
            ("reference_revision", "reference_skill_content_hash")):
        revision = evidence.get(revision_key)
        if not _git_commit_exists(revision):
            continue
        if revision not in revision_hashes:
            try:
                revision_hashes[revision] = _skill_hash_at_revision(
                    revision, skill)
            except Exception as exc:  # fail closed with anchored evidence error
                errs.append(f"regression evidence {revision_key} could not hash the Git revision: {exc}")
                revision_hashes[revision] = None
        if revision_hashes[revision] != evidence.get(hash_key):
            errs.append(f"regression evidence {hash_key} does not match the materialized Git revision")
    conditions = evidence.get("conditions")
    if conditions != ["candidate", "reference"]:
        errs.append("regression evidence conditions must be ['candidate', 'reference']")
    repetitions = evidence.get("repetitions") or []
    for error in validate_declaration("regression", conditions, len(repetitions)):
        errs.append(error)
    expected_task_hash = hashlib.sha256(
        case.get("prompt", "").encode()).hexdigest()
    expected_seed = evidence.get("expected_fixture_hash")
    seed = evidence.get("canonical_task_seed_hash")
    if not seed:
        errs.append("regression evidence missing canonical_task_seed_hash")
    elif expected_seed and seed != expected_seed:
        errs.append("regression canonical_task_seed_hash does not match frozen fixture")
    runtime_paths = evidence.get("runtime_treatment_paths")
    if (harness_runner is None or
            runtime_paths != list(harness_runner.RUNTIME_TREATMENT_PATHS)):
        errs.append("regression evidence runtime_treatment_paths do not match the neutral evaluator paths")

    seen_repetitions = set()
    seen_workers = set()
    seen_sessions = set()
    for repetition in repetitions:
        tag = f"rep{repetition.get('rep')}"
        rid = repetition.get("repetition_id")
        if not isinstance(rid, str) or not rid.strip():
            errs.append(f"{tag}: missing repetition_id")
        elif rid in seen_repetitions:
            errs.append(f"{tag}: duplicate repetition_id")
        else:
            seen_repetitions.add(rid)
        if repetition.get("natural_task_hash") != expected_task_hash:
            errs.append(f"{tag}: natural_task_hash does not match current case prompt")
        if repetition.get("natural_task_identical_across_conditions") is not True:
            errs.append(f"{tag}: natural_task_identical_across_conditions must be true")
        cmap = repetition.get("conditions") or {}
        if set(cmap) != {"candidate", "reference"}:
            errs.append(f"{tag}: candidate/reference condition evidence is incomplete")
            continue
        starts = []
        workspace_ids = (repetition.get("condition_workspace_ids") or {}).values()
        if len(set(workspace_ids)) != 2:
            errs.append(f"{tag}: candidate/reference workspace ids are not distinct")
        receipt_hashes = repetition.get("condition_workspace_receipt_hashes")
        if (not isinstance(receipt_hashes, dict) or
                set(receipt_hashes) != {"candidate", "reference"}):
            errs.append(f"{tag}: condition workspace receipt hashes are incomplete")
            receipt_hashes = {}
        if (repetition.get("workspace_receipt_path") !=
                getattr(harness_runner, "WORKSPACE_RECEIPT_PATH", None)):
            errs.append(f"{tag}: workspace receipt path is not the neutral receipt path")
        activation_mechanisms = []
        for name in ("candidate", "reference"):
            cmeta = cmap.get(name) or {}
            ctag = f"{tag} {name}"
            if cmeta.get("repetition_id") != rid:
                errs.append(f"{ctag}: repetition_id does not match parent repetition")
            for key in ("worker_id", "session_id", "run_status", "returncode",
                        "starting_task_hash", "ending_task_hash",
                        "starting_full_hash", "ending_full_hash",
                        "guidance_probe", "guidance_context_probe",
                        "guidance_path", "guidance_content_hash",
                        "workspace_receipt", "workspace_receipt_path",
                        "workspace_receipt_hash", "attestation_nonce",
                        "execution_request_hash", "execution_observation_hash",
                        "execution_attestation"):
                if key not in cmeta:
                    errs.append(f"{ctag}: missing {key}")
            _validate_workspace_receipt(
                cmeta, receipt_hashes.get(name), ctag, errs)
            _validate_execution_attestation(
                cmeta, receipt_hashes.get(name), ctag, errs)
            if cmeta.get("run_status") != "success" or cmeta.get("returncode") != 0:
                errs.append(f"{ctag}: failed condition is not evidence")
            if not (cmeta.get("output") or "").strip():
                errs.append(f"{ctag}: empty model output")
            if expected_seed and cmeta.get("starting_task_hash") != expected_seed:
                errs.append(f"{ctag}: starting task hash does not match frozen seed")
            starts.append(cmeta.get("starting_task_hash"))
            worker_id = cmeta.get("worker_id")
            session_id = cmeta.get("session_id")
            if not worker_id or not session_id:
                errs.append(f"{ctag}: worker_id and session_id are required")
            if worker_id in seen_workers:
                errs.append(f"{ctag}: duplicate worker_id across repetitions")
            if session_id in seen_sessions:
                errs.append(f"{ctag}: duplicate session_id across repetitions")
            if worker_id:
                seen_workers.add(worker_id)
            if session_id:
                seen_sessions.add(session_id)
            expected_hash_key = f"{name}_skill_content_hash"
            if cmeta.get("skill_content_hash") not in (None, cmeta.get("guidance_content_hash")):
                errs.append(f"{ctag}: legacy skill_content_hash disagrees with guidance_content_hash")
            if cmeta.get("guidance_content_hash") != evidence.get(expected_hash_key):
                errs.append(f"{ctag}: guidance content hash does not match the revision anchor")
            expected_path = evidence.get(f"{name}_guidance_path")
            if expected_path and cmeta.get("guidance_path") != expected_path:
                errs.append(f"{ctag}: guidance path does not match the neutral runtime path")
            if cmeta.get("guidance_probe") != "present":
                errs.append(f"{ctag}: guidance probe did not confirm a present tree")
            if cmeta.get("guidance_context_probe") != "present":
                errs.append(f"{ctag}: guidance context probe did not confirm activation")
            if not isinstance(cmeta.get("activation_mechanism"), str) or not cmeta.get("activation_mechanism"):
                errs.append(f"{ctag}: activation_mechanism must be recorded by the adapter")
            else:
                activation_mechanisms.append(cmeta["activation_mechanism"])
        if len(set(starts)) != 1:
            errs.append(f"{tag}: candidate/reference starting task hashes differ")
        if len(set(activation_mechanisms)) > 1:
            errs.append(f"{tag}: candidate/reference use different activation_mechanisms")
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
        elif et == "regression":
            for e in validate_regression_evidence(data):
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
        # Support both old 8-col and new 9-col (with Measurement) formats.
        # New: ['', skill, cases, fixtures, routing, execution, measurement, protocol, repeats, result]
        # Old: ['', skill, cases, fixtures, routing, execution, protocol, repeats, result]
        has_measurement = len(cells) >= 11
        if has_measurement:
            # 9-col format
            skill_cell = cells[1]
            routing_cell = cells[4].lower()
            execution_cell = cells[5].lower()
            measurement_cell = cells[6].lower()
            proto_cell = cells[7].lower()
            result_cell = cells[9] if len(cells) > 9 else (cells[8] if len(cells) > 8 else "")
        else:
            skill_cell = cells[1]
            routing_cell = cells[4].lower()
            execution_cell = cells[5].lower()
            measurement_cell = ""
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
                                ("measurement", measurement_cell), ("protocol", proto_cell)):
                if cell == "valid" or "discriminating" in cell:
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
