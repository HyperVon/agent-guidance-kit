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

Each repetition is a brand-new Kilo session (never a continuation), so there is
no cross-rep contamination. The model is used purely as a classifier here; no
filesystem access, no tools, no repo are involved.

Usage:
    python3 scripts/run_catalog_routing_eval.py \
        --skill code-review --case-id 1 \
        --model kilo/tencent/hy3:free --reps 3 \
        --out .eval-evidence/catalog-routing-code-review-case1.json
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_CATALOG = os.path.join(ROOT, "scripts", "build_routing_catalog.py")

DEFAULT_MODEL = "kilo/tencent/hy3:free"
KILO_BIN = "kilo"


def require_free_model(model):
    # Guard against accidentally running the eval on a paid/account-bound model,
    # which would break the fairness assumption (both conditions must use the
    # identical, cost-neutral inference).
    if not model.endswith(":free"):
        print(f"refusing to run catalog-routing eval on non-free model '{model}'. "
              f"The evaluation requires an anonymous free model (id ending in "
              f"':free', e.g. {DEFAULT_MODEL}).", file=sys.stderr)
        sys.exit(2)


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


def run_kilo(prompt, model, workdir):
    cmd = [KILO_BIN, "run", "--model", model, "--variant", "high",
           "--format", "json", "--pure", prompt]
    proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                         timeout=600)
    parts = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") == "text":
            parts.append(obj.get("part", {}).get("text", ""))
    return "".join(parts), proc.stderr


def extract_decision(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    sel = obj.get("selected_skill")
    if sel in ("", "null", "none", "None"):
        sel = None
    return {
        "selected_skill": sel,
        "action": obj.get("action"),
        "rationale": obj.get("rationale"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True)
    ap.add_argument("--case-id", type=int, required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--evals-json",
                    default=os.path.join(ROOT, "skills", "{skill}",
                                         "evals", "evals.json"))
    ap.add_argument("--out", help="path to write the captured evidence JSON")
    args = ap.parse_args()
    require_free_model(args.model)

    evals_path = args.evals_json.format(skill=args.skill)
    if not os.path.exists(evals_path):
        print(f"evals.json not found: {evals_path}", file=sys.stderr)
        sys.exit(2)
    data = json.load(open(evals_path))
    case = next((c for c in data["evals"] if c.get("id") == args.case_id), None)
    if case is None:
        print(f"case {args.case_id} not found in {evals_path}", file=sys.stderr)
        sys.exit(2)
    if "routing" not in case.get("evaluation_modes", []):
        print(f"case {args.case_id} is not a routing case", file=sys.stderr)
        sys.exit(2)

    user_request = case["prompt"]
    exp = (case.get("routing") or {})
    target_skill = exp.get("target_skill") or args.skill
    exp_present = (exp.get("target_present") or {}).get("expected_selected_skill")
    exp_absent = (exp.get("target_absent") or {}).get("expected_selected_skill")
    fallbacks = (exp.get("target_absent") or {}).get("allowed_fallbacks") or []

    # Target-present condition == guided worker sees the target in the catalog.
    present_rows = build_catalog(None)
    # Target-absent condition == baseline worker; the target is omitted.
    absent_rows = build_catalog(target_skill)

    prompt_present = build_prompt(render_catalog(present_rows), user_request)
    prompt_absent = build_prompt(render_catalog(absent_rows), user_request)

    results = {"skill": args.skill, "case_id": args.case_id, "model": args.model,
               "repetitions": args.reps, "conditions": {}}
    workdir = tempfile.mkdtemp(prefix="kilo-routing-")

    def run_condition(name, prompt, expected):
        reps = []
        for i in range(args.reps):
            raw, err = run_kilo(prompt, args.model, workdir)
            dec = extract_decision(raw)
            sel = dec.get("selected_skill") if dec else None
            ok = matches(sel, expected, fallbacks if expected is None else
                         (exp.get("target_present") or {}).get("allowed_fallbacks") or [])
            reps.append({"rep": i + 1, "selected_skill": sel,
                         "action": dec.get("action") if dec else None,
                         "rationale": dec.get("rationale") if dec else None,
                         "match": ok, "raw": raw})
        passed = sum(1 for r in reps if r["match"])
        results["conditions"][name] = {
            "expected_selected_skill": expected,
            "repetitions": reps,
            "passed": passed,
            "total": args.reps,
        }

    run_condition("target_present", prompt_present, exp_present)
    run_condition("target_absent", prompt_absent, exp_absent)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        json.dump(results, open(args.out, "w"), indent=2)
        print(f"wrote evidence: {args.out}")

    # Console summary
    for name, cond in results["conditions"].items():
        print(f"[{name}] expected={cond['expected_selected_skill']!r} "
              f"passed {cond['passed']}/{cond['total']}")
        for r in cond["repetitions"]:
            print(f"   rep{r['rep']}: selected={r['selected_skill']!r} "
                  f"action={r['action']!r} match={r['match']}")


def matches(selected, expected, fallbacks):
    fallbacks = fallbacks or []
    if expected is not None:
        return selected == expected or selected in fallbacks
    return selected is None or selected in fallbacks


if __name__ == "__main__":
    main()
