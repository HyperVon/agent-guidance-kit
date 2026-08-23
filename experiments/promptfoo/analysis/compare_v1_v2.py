"""Compare existing evaluator (v1) evidence with the Promptfoo spike (v2).

Produces a decision-oriented discrepancy report for the overlapping
representative cases. Every meaningful difference is classified as one of:

    expected engine difference | Promptfoo limitation |
    existing-evaluator limitation | prototype bug |
    model nondeterminism | provider/harness difference | unknown

Usage (routing):
    python3 analysis/compare_v1_v2.py routing \
        --v1 ../../.eval-evidence/layerA-review-family-v4.json \
        --v2 .results/routing-dev.json \
        --corpus ../../evaluations/confusion-sets/review-family.json \
        --out .results/compare-routing.md

Usage (holdout): same with the holdout files and label=holdout.
"""
import argparse
import hashlib
import json
import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from experiments.promptfoo.analysis.routing_metrics import (  # noqa: E402
    build_aggregate,
    classify_row,
    extract_observations,
    load_rows,
)

CLASSIFICATIONS = (
    "expected engine difference",
    "Promptfoo limitation",
    "existing-evaluator limitation",
    "prototype bug",
    "model nondeterminism",
    "provider/harness difference",
    "unknown",
)


def canonical_case_hash(path):
    data = json.load(open(path))
    return "sha256:" + hashlib.sha256(json.dumps(
        data, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode()).hexdigest()


NULL_LABEL = "null"


def _show(value):
    return NULL_LABEL if value is None else value


def v1_case_map(v1):
    out = {}
    for case in v1.get("cases", []):
        cid = case.get("id")
        entries = []
        if case.get("turns") and case.get("case_type") in (
                "workflow-transition", "harness-native"):
            for rep in case.get("repetitions", []):
                for t in rep.get("turns", []):
                    entries.append({
                        "rep": rep.get("rep"), "turn": t.get("turn"),
                        "status": t.get("status"),
                        "selected": t.get("selected_skill"),
                        "expected": t.get("expected_route"),
                        "error": t.get("error"),
                    })
        else:
            for rep in case.get("repetitions", []):
                dec = rep.get("decision") or {}
                entries.append({
                    "rep": rep.get("rep"), "turn": None,
                    "status": rep.get("status"),
                    "selected": dec.get("selected_skill"),
                    "expected": case.get("expected_skill"),
                    "error": rep.get("error"),
                })
        out[cid] = entries
    return out


def v2_case_map(rows):
    """Build per-(case, rep, turn) entries from exported rows.

    Multi-turn rows contribute one entry PER TURN (matching v1's per-turn
    recording); single-turn rows one entry per rep.
    """
    observations, failures = extract_observations(rows)
    out = {}
    for row in rows:
        variables = row.get("vars") or {}
        cid = variables.get("case_id")
        failed = classify_row(row) == "failed"
        if variables.get("turns_json"):
            if failed:
                out.setdefault(cid, []).append({
                    "rep": variables.get("rep"), "turn": None,
                    "status": "failed", "selected": None,
                    "expected": None,
                    "error": (row.get("response") or {}).get("error")})
                continue
            try:
                payload = json.loads((row.get("response") or {}).get("output")
                                     or "")
                turns = payload.get("turns", [])
            except Exception:
                turns = []
            expected_turns = json.loads(variables["turns_json"])
            for exp, got in zip(expected_turns, turns):
                ok = got.get("status") == "success"
                out.setdefault(cid, []).append({
                    "rep": variables.get("rep"), "turn": got.get("turn"),
                    "status": "success" if ok else "failed",
                    "selected": got.get("selected_skill"),
                    "expected": exp.get("expected_route"),
                    "error": got.get("error")})
            continue
        selected = None
        if not failed:
            try:
                decision = json.loads((row.get("response") or {}).get("output")
                                      or "")
                selected = decision.get("selected_skill")
            except Exception:
                pass
        out.setdefault(cid, []).append({
            "rep": variables.get("rep"), "turn": None,
            "status": "failed" if failed else "success",
            "selected": None if failed else selected,
            "expected": variables.get("expected_skill"),
            "error": (row.get("response") or {}).get("error")})
    return out, len(observations), failures


def classify_diff(v1_entry, v2_entry):
    """Heuristic classification of one rep-level difference."""
    if v1_entry["status"] != "success" or v2_entry["status"] != "success":
        return "provider/harness difference"
    return "model nondeterminism"


def compare_routing(v1_path, v2_path, corpus_path, label):
    v1 = json.load(open(v1_path))
    rows = load_rows(v2_path)
    skills = json.load(open(corpus_path)).get("skills") or []
    agg = build_aggregate(rows, skills)
    v1_cases = v1_case_map(v1)
    v2_cases, n_obs, v2_failures = v2_case_map(rows)

    lines = [f"# v1 vs Promptfoo comparison — {label}", ""]
    lines.append("## Provenance")
    lines.append(f"- v1 evidence: `{os.path.basename(v1_path)}` "
                 f"(case_set_hash {v1.get('case_set_hash', 'n/a')[:19]}..., "
                 f"model {v1.get('model')}, kilo {v1.get('kilo_version')}, "
                 f"reps {v1.get('repetitions')})")
    lines.append(f"- v2 export: `{os.path.relpath(v2_path)}` "
                 f"(engine promptfoo 0.122.0, provider kilo-cli, "
                 f"same model family as v1)")
    lines.append(f"- corpus: `{os.path.relpath(corpus_path)}` "
                 f"(canonical hash {canonical_case_hash(corpus_path)[:19]}...)")
    same_corpus = v1.get("case_set_hash") == canonical_case_hash(corpus_path)
    lines.append(f"- v1 case_set_hash matches current corpus: **{same_corpus}**")
    lines.append("")

    lines.append("## Accounting")
    lines.append("| metric | v1 | v2 (promptfoo) |")
    lines.append("|---|---|---|")
    v1_agg = v1.get("aggregate", {})
    v1_failed = v1_agg.get("failed_decisions") or []
    lines.append(f"| attempted | {v1_agg.get('attempted_decisions')} | "
                 f"{agg['attempted_decisions']} |")
    lines.append(f"| successful | {v1_agg.get('successful_decisions')} | "
                 f"{agg['successful_decisions']} |")
    lines.append(f"| failed | {len(v1_failed)} | {len(v2_failures)} |")
    null_v1 = sum(1 for c in v1_cases.values() for e in c
                  if e["status"] == "success" and e["selected"] is None)
    lines.append(f"| null selections | {null_v1} | "
                 f"{agg['null_decisions']} |")
    lines.append(f"| accuracy over successful | "
                 f"{v1_accuracy(v1_agg):.3f} | "
                 f"{agg['accuracy_over_successful']:.3f} |")
    lines.append("")

    lines.append("## Per-case routes (rep-level)")
    lines.append("| case | expected | v1 selections | v2 selections | diff? |")
    lines.append("|---|---|---|---|---|")
    diffs = 0
    for cid in sorted(set(v1_cases) | set(v2_cases), key=lambda x: (x is None, x)):
        v1_sel = [(_show(e['selected']) if e["status"] == "success"
                   else "FAILED")
                  for e in sorted(v1_cases.get(cid, []),
                                  key=lambda e: (e["rep"], e["turn"] or 0))]
        v2_sel = [(_show(e['selected']) if e["status"] == "success"
                   else "FAILED")
                  for e in sorted(v2_cases.get(cid, []),
                                  key=lambda e: (e["rep"], e["turn"] or 0))]
        raw_expected = next((e["expected"] for e in
                             v1_cases.get(cid, []) + v2_cases.get(cid, [])
                             if e["expected"] not in (None, "@null")), None)
        expected = _show(raw_expected)
        differs = sorted(map(str, v1_sel)) != sorted(map(str, v2_sel))
        diffs += int(differs)
        lines.append(f"| {cid} | {expected} | {'; '.join(v1_sel)} | "
                     f"{'; '.join(v2_sel)} | "
                     f"{'DIFFERENT' if differs else 'same'} |")
    lines.append("")
    lines.append(f"Cases with any rep-level selection difference: **{diffs}** "
                 f"— classified per-rep below.")
    lines.append("")
    lines.append("## Rep-level difference classifications")
    classified = {}
    for cid in sorted(set(v1_cases) & set(v2_cases)):
        v1_by_key = {(e["rep"], e["turn"]): e
                     for e in v1_cases[cid]}
        for e in sorted(v2_cases[cid], key=lambda x: (x["rep"],
                                                      x["turn"] or 0)):
            twin = v1_by_key.get((e["rep"], e["turn"]))
            if not twin:
                continue
            same = (twin["status"] == e["status"]
                    and _show(twin["selected"]) == _show(e["selected"]))
            if same:
                continue
            cls = classify_diff(twin, e)
            classified.setdefault(cls, []).append(
                f"case {cid} rep {e['rep']} turn {e['turn']}: "
                f"v1={twin['selected']!r}/{twin['status']} vs "
                f"v2={e['selected']!r}/{e['status']}")
    if not classified:
        lines.append("No rep-level status/selection differences detected.")
    for cls in CLASSIFICATIONS:
        items = classified.get(cls)
        if items:
            lines.append(f"- **{cls}** ({len(items)}):")
            lines.extend(f"  - {item}" for item in items)
    lines.append("")

    lines.append("## Confusion behavior (successful decisions)")
    lines.append(f"- v2 confusion matrix: `{json.dumps(agg['confusion_matrix'])}`")
    lines.append(f"- v1 confusion matrix: "
                 f"`{json.dumps(v1_agg.get('confusion_matrix'))}`")
    lines.append("")
    lines.append("## Failure accounting")
    lines.append(f"- invariant attempted == successful + failed holds in v2: "
                 f"**{agg['attempted_decisions'] == agg['successful_decisions'] + len(v2_failures)}**")
    for failure in v2_failures:
        lines.append(f"- v2 failed: {failure}")
    for failure in v1_failed:
        lines.append(f"- v1 failed: {failure}")
    return "\n".join(lines) + "\n", agg


def v1_accuracy(v1_agg):
    successful = v1_agg.get("successful_decisions") or 0
    matrix = v1_agg.get("confusion_matrix") or {}
    correct = sum(count for intended, row in matrix.items()
                  for sel, count in row.items() if intended == sel)
    return (correct / successful) if successful else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["routing"])
    ap.add_argument("--v1", required=True)
    ap.add_argument("--v2", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--label", default="development")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    report, agg = compare_routing(args.v1, args.v2, args.corpus, args.label)
    print(report)
    if args.out:
        with open(args.out, "w") as f:
            f.write(report)
        base = os.path.splitext(args.out)[0]
        with open(base + "-metrics.json", "w") as f:
            json.dump(agg, f, indent=2)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
