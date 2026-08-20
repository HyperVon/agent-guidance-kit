#!/usr/bin/env python3
"""Catalog-routing evaluation runner (portable, harness-independent layer A).

This runner implements the *catalog-routing* evaluation layer. It does NOT depend
on Kilo's internal/harness routing. Instead it:

  1. generates a neutral routing catalog from each skill's frontmatter
     (via scripts/build_routing_catalog.py, with optional --target-absent);
  2. issues a fresh, independent Kilo model call per repetition with a neutral
     routing instruction that embeds the catalog + the user request;
  3. captures the structured decision ``{"selected_skill": ..., "action": ...}``;
  4. compares the captured selection against the case's routing expectation.

Each repetition is a brand-new Kilo session run from a fresh, isolated, empty
workdir (never a continuation, never the repo), so there is no cross-rep
contamination and the model cannot inspect the repository.

Validity rules: a model invocation that fails (non-zero exit, no parseable
decision, or an invalid decision structure) is recorded as ``status="failed"``
and is explicitly NOT a successful null-selection. A null ``selected_skill``
(clarify) is only valid when the model call succeeded AND produced a well-formed
decision that EXPLICITLY contains both ``selected_skill`` and ``action``: a
MISSING field is never treated as an explicit null. A non-null ``selected_skill``
must name a skill that was actually present in the catalog supplied to the model
for that condition (a target-absent catalog omits the target, so selecting it is
rejected).

Usage:
    python3 scripts/run_catalog_routing_eval.py \
        --skill code-review --case-id 1 \
        --model kilo/tencent/hy3:free --reps 3 \
        --out .eval-evidence/catalog-routing-code-review-case1.json
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_CATALOG = os.path.join(ROOT, "scripts", "build_routing_catalog.py")

DEFAULT_MODEL = "kilo/tencent/hy3:free"
KILO_BIN = "kilo"


def _kilo_path():
    """Resolve the kilo executable (not always on PATH in non-interactive shells)."""
    import shutil
    p = shutil.which(KILO_BIN)
    if p:
        return p
    for cand in ("/opt/homebrew/bin/kilo", "/usr/local/bin/kilo"):
        if os.path.exists(cand):
            return cand
    return KILO_BIN


def require_free_model(model, allow_paid):
    if allow_paid:
        return
    if not model.endswith(":free"):
        print(f"refusing to run catalog-routing eval on non-free model '{model}'. "
              f"This is a cost-safety gate (not a methodology rule): both "
              f"conditions must use the identical model. Use --allow-paid-model to "
              f"opt in, or a free model id (e.g. {DEFAULT_MODEL}).", file=sys.stderr)
        sys.exit(2)


def _host_kilo_version(kilo_bin=KILO_BIN):
    try:
        out = subprocess.check_output([kilo_bin, "--version"],
                                      text=True, timeout=60).strip()
        return out.splitlines()[0] if out else None
    except Exception:
        return None


def _verify_host_kilo(model):
    """Fail early if the host Kilo CLI or model is unusable."""
    kilo = _kilo_path()
    if not os.path.exists(kilo):
        print(f"kilo executable not found ({kilo})", file=sys.stderr)
        sys.exit(2)
    if not _host_kilo_version(kilo):
        print("kilo --version failed on host", file=sys.stderr)
        sys.exit(2)
    try:
        models = subprocess.check_output([kilo, "models"],
                                        text=True, timeout=120)
        listed = model in models
    except Exception:
        listed = None
    return listed


def build_catalog(target_absent):
    cmd = [sys.executable, BUILD_CATALOG, "--format", "tsv"]
    if target_absent:
        cmd += ["--target-absent", target_absent]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                         check=True).stdout
    rows = []
    for line in out.splitlines():
        if not line.strip():
            continue
        name, _, desc = line.partition("\t")
        rows.append((name.strip(), desc.strip()))
    return rows


def render_catalog(rows):
    lines = ["Available skills (name — one-line purpose):"]
    for name, desc in rows:
        lines.append(f"- {name} — {desc}")
    return "\n".join(lines)


def build_prompt(catalog_text, user_request):
    return (
        "You are a neutral skill router. You will receive (1) a catalog of "
        "available skills and (2) a user request. Choose the single best skill "
        "for the request. If no skill clearly fits, return selected_skill=null "
        "and action=\"clarify\".\n\n"
        "Respond with ONLY a single JSON object and no other text, of the form:\n"
        "{\"selected_skill\": \"<skill name or null>\", "
        "\"action\": \"apply\"|\"clarify\", \"rationale\": \"<one sentence>\"}\n\n"
        f"=== CATALOG ===\n{catalog_text}\n\n"
        f"=== USER REQUEST ===\n{user_request}\n"
    )


def _extract_session(text):
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("sessionID"):
            return obj["sessionID"]
    return None


def _collect_text(stdout):
    parts = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") == "text":
            parts.append(obj.get("part", {}).get("text", ""))
    return "".join(parts)


def extract_decision(text, catalog_names=None):
    """Parse and strictly validate a raw model routing decision.

    Returns ``{"status": "success", "decision": {...}}`` or
    ``{"status": "failed", "error": <reason>, "decision": None}``.

    CRITICAL: a MISSING field is NOT the same as an explicit ``null``. The raw
    parsed object must explicitly contain both ``selected_skill`` and ``action``;
    omitting either is a malformed decision and is rejected (it can never become a
    valid null-selection pass). A non-null ``selected_skill`` must additionally
    name a skill that was actually present in the catalog supplied to the model
    for this condition. Unknown action values are rejected.
    """
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {"status": "failed", "error": "no JSON decision object in output",
                "decision": None}
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return {"status": "failed", "error": "malformed JSON decision",
                "decision": None}
    if not isinstance(obj, dict):
        return {"status": "failed", "error": "decision is not a JSON object",
                "decision": None}
    # Missing field != explicit null.
    if "selected_skill" not in obj:
        return {"status": "failed", "error": "selected_skill field missing",
                "decision": None}
    if "action" not in obj:
        return {"status": "failed", "error": "action field missing",
                "decision": None}
    sel = obj["selected_skill"]
    action = obj["action"]
    if action not in ("apply", "clarify"):
        return {"status": "failed",
                "error": f"invalid action {action!r}", "decision": None}
    if sel is not None and not isinstance(sel, str):
        return {"status": "failed",
                "error": "selected_skill must be a string or null",
                "decision": None}
    # The selected skill must be one of the skills actually presented in the
    # catalog for this condition (a target-absent catalog omits the target).
    if sel is not None and catalog_names is not None and sel not in catalog_names:
        return {"status": "failed",
                "error": f"selected skill {sel!r} not in supplied catalog",
                "decision": None}
    # Cross-field validity.
    if sel is None and action == "apply":
        return {"status": "failed",
                "error": "null selected_skill with action 'apply'", "decision": None}
    if sel is not None and action == "clarify":
        return {"status": "failed",
                "error": "non-null selected_skill with action 'clarify'",
                "decision": None}
    return {"status": "success",
            "decision": {"selected_skill": sel, "action": action,
                         "rationale": obj.get("rationale")}}


def run_kilo(prompt, model, workdir, kilo_bin=KILO_BIN, catalog_names=None):
    """Run one model call. Returns structured metadata distinguishing a failed
    invocation from a valid null-selection decision."""
    cmd = [kilo_bin, "run", "--model", model, "--variant", "high",
           "--format", "json", "--pure", prompt]
    try:
        proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                              timeout=600)
    except Exception as e:
        return {"status": "failed", "error": f"invocation error: {e}",
                "returncode": None, "stdout": "", "stderr": "",
                "session_id": None, "decision": None}

    raw = proc.stdout or ""
    text = _collect_text(raw)
    parsed = extract_decision(text, catalog_names)
    session = _extract_session(raw)

    status = parsed["status"]
    error = parsed.get("error")
    if proc.returncode != 0:
        status = "failed"
        error = f"kilo exited {proc.returncode}"
    return {"status": status, "error": error, "returncode": proc.returncode,
            "stdout": raw, "stderr": proc.stderr, "session_id": session,
            "decision": parsed.get("decision")}


def matches(selected, expected, fallbacks):
    fallbacks = fallbacks or []
    if expected is not None:
        return selected == expected or selected in fallbacks
    return selected is None or selected in fallbacks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True)
    ap.add_argument("--case-id", type=int, required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--allow-paid-model", action="store_true",
                    help="allow a non-free model (cost-safety opt-in)")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--evals-json",
                    default=os.path.join(ROOT, "skills", "{skill}",
                                         "evals", "evals.json"))
    ap.add_argument("--out", help="path to write the captured evidence JSON")
    args = ap.parse_args()
    require_free_model(args.model, args.allow_paid_model)

    kilo_bin = _kilo_path()
    model_listed = _verify_host_kilo(args.model)
    kilo_version = _host_kilo_version(kilo_bin)

    evals_path = args.evals_json.format(skill=args.skill)
    if not os.path.exists(evals_path):
        print(f"evals.json not found: {evals_path}", file=sys.stderr)
        sys.exit(2)
    data = json.load(open(evals_path))
    case = next((c for c in data["evals"] if c.get("id") == args.case_id), None)
    if case is None:
        print(f"case {args.case_id} not found in {evals_path}", file=sys.stderr)
        sys.exit(2)
    modes = case.get("evaluation_modes", [])
    # Both the legacy "routing" mode and the Layer-A "catalog-routing" mode are
    # valid for the catalog-routing runner. Existing case files may use either;
    # this preserves compatibility while preferring the explicit catalog-routing
    # label for new cases.
    if not any(m in ("routing", "catalog-routing") for m in modes):
        print(f"case {args.case_id} is not a routing/catalog-routing case "
              f"(modes={modes})", file=sys.stderr)
        sys.exit(2)

    user_request = case["prompt"]
    exp = (case.get("routing") or {})
    target_skill = exp.get("target_skill") or args.skill
    exp_present = (exp.get("target_present") or {}).get("expected_selected_skill")
    exp_absent = (exp.get("target_absent") or {}).get("expected_selected_skill")
    fallbacks = (exp.get("target_absent") or {}).get("allowed_fallbacks") or []

    present_rows = build_catalog(None)
    absent_rows = build_catalog(target_skill)
    catalog_present = render_catalog(present_rows)
    catalog_absent = render_catalog(absent_rows)
    # The exact catalog names actually presented to the model for each condition.
    # A target-absent catalog omits the target skill, so a model that "selects"
    # the target anyway is rejecting against the real supplied catalog.
    names_present = {name for name, _ in present_rows}
    names_absent = {name for name, _ in absent_rows}
    prompt_present = build_prompt(catalog_present, user_request)
    prompt_absent = build_prompt(catalog_absent, user_request)

    results = {
        "evidence_type": "catalog-routing",
        "skill": args.skill, "case_id": args.case_id, "model": args.model,
        "kilo_version": kilo_version, "model_listed": model_listed,
        "repetitions": args.reps, "conditions": {},
    }

    def run_condition(name, prompt, catalog_text, expected, catalog_names):
        reps = []
        catalog_hash = hashlib.sha256(catalog_text.encode()).hexdigest()
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        for i in range(args.reps):
            # Fresh, isolated, empty workdir per call; deleted afterwards.
            workdir = tempfile.mkdtemp(prefix="kilo-routing-")
            try:
                meta = run_kilo(prompt, args.model, workdir, kilo_bin,
                               catalog_names)
            finally:
                shutil.rmtree(workdir, ignore_errors=True)
            dec = meta["decision"]
            sel = dec.get("selected_skill") if dec else None
            act = dec.get("action") if dec else None
            ok = False
            if meta["status"] == "success":
                ok = matches(sel, expected, fallbacks if expected is None else
                             (exp.get("target_present") or {}).get("allowed_fallbacks") or [])
            reps.append({
                "rep": i + 1,
                "status": meta["status"],
                "error": meta.get("error"),
                "returncode": meta["returncode"],
                "session_id": meta["session_id"],
                "stderr": meta["stderr"],
                "catalog_hash": catalog_hash,
                "prompt_hash": prompt_hash,
                "output_hash": hashlib.sha256(
                    (meta["stdout"] or "").encode()).hexdigest(),
                "decision": {"selected_skill": sel, "action": act,
                             "rationale": dec.get("rationale") if dec else None},
                "match": ok,
            })
        passed = sum(1 for r in reps if r["match"])
        results["conditions"][name] = {
            "expected_selected_skill": expected,
            "repetitions": reps,
            "passed": passed,
            "total": args.reps,
        }

    run_condition("target_present", prompt_present, catalog_present, exp_present,
                  names_present)
    run_condition("target_absent", prompt_absent, catalog_absent, exp_absent,
                  names_absent)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        json.dump(results, open(args.out, "w"), indent=2)
        print(f"wrote evidence: {args.out}")

    for name, cond in results["conditions"].items():
        print(f"[{name}] expected={cond['expected_selected_skill']!r} "
              f"passed {cond['passed']}/{cond['total']}")
        for r in cond["repetitions"]:
            print(f"   rep{r['rep']}: status={r['status']} "
                  f"selected={r['decision']['selected_skill']!r} "
                  f"action={r['decision']['action']!r} match={r['match']}")


if __name__ == "__main__":
    main()
