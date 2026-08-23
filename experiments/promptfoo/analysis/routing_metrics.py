"""AGK routing metrics computed from a Promptfoo results export.

Preserves the existing evaluator's experimental semantics:

* one observation per successful model decision;
* workflow-transition turns each contribute one observation with
  ``expected_route`` as the intended class;
* explicit null selections are the literal ``"null"`` class;
* failed invocations are NOT observations: they are recorded per
  case/rep/turn in ``failed_decisions`` and never inflate or deflate the
  matrix;
* attempted_decisions = successful_decisions + failed_decisions;
* precision/recall are null (not 0) when the denominator is zero.

Usage:
    python3 analysis/routing_metrics.py --results .results/routing-dev.json \
        [--out .results/routing-dev-metrics.json]
"""
import argparse
import json

NULL_LABEL = "null"


def classify_row(row):
    """Classify one exported row into AGK decision-accounting states.

    A FAILED INVOCATION is a row where the provider reported an error
    (``response.error``) or produced no response at all. An ASSERTION FAILURE
    (wrong route) also sets the top-level ``error`` field on the exported row,
    but its ``response.output`` still contains a well-formed decision, so it
    remains a SUCCESSFUL decision observation.
    """
    response = row.get("response") or {}
    if response.get("error") or not response.get("output"):
        return "failed"
    return "success"


def parse_decision(row):
    import json as _json
    output = (row.get("response") or {}).get("output")
    if not output:
        return None
    try:
        obj = _json.loads(output)
    except Exception:
        return None
    if not isinstance(obj, dict) or "selected_skill" not in obj:
        return None
    return obj


def extract_observations(rows):
    """Yield (case_id, rep, turn_or_None, intended, selected) for successful
    decisions; collect failure records for failed invocations."""
    observations = []
    failures = []
    for row in rows:
        variables = row.get("vars") or {}
        case_id = variables.get("case_id")
        rep = variables.get("rep")
        if classify_row(row) == "failed":
            error = (row.get("response") or {}).get("error") \
                or row.get("error") or "no response output"
            failures.append({"case_id": case_id, "rep": rep,
                             "turn": None,
                             "error": str(error)[:300]})
            continue
        if variables.get("turns_json"):
            try:
                payload = json.loads((row.get("response") or {}).get("output")
                                     or "")
            except Exception:
                failures.append({"case_id": case_id, "rep": rep,
                                 "turn": None,
                                 "error": "unparseable turns payload"})
                continue
            turns = payload.get("turns", []) if isinstance(payload, dict) \
                else []
            expected_turns = json.loads(variables["turns_json"])
            if len(turns) != len(expected_turns):
                failures.append({"case_id": case_id, "rep": rep,
                                 "turn": None,
                                 "error": f"incomplete turn chain "
                                          f"({len(turns)} of "
                                          f"{len(expected_turns)})"})
                continue
            for exp, got in zip(expected_turns, turns):
                if got.get("status") != "success":
                    failures.append({"case_id": case_id, "rep": rep,
                                     "turn": got.get("turn"),
                                     "error": got.get("error")})
                    continue
                intended = exp.get("expected_route")
                intended = NULL_LABEL if intended is None else intended
                sel = got.get("selected_skill")
                sel = NULL_LABEL if sel is None else sel
                observations.append((case_id, rep, got.get("turn"),
                                     intended, sel))
            continue
        decision = parse_decision(row)
        if decision is None:
            failures.append({"case_id": case_id, "rep": rep, "turn": None,
                             "error": "unparseable decision output"})
            continue
        selected = decision.get("selected_skill")
        expected = variables.get("expected_skill")
        if expected == "@null":
            expected = None
        intended = NULL_LABEL if expected is None else expected
        sel = NULL_LABEL if selected is None else selected
        observations.append((case_id, rep, None, intended, sel))
    return observations, failures


def build_aggregate(rows, skills):
    """AGK aggregate over an exported Promptfoo run."""
    observations, failures = extract_observations(rows)
    attempted = len(observations) + len(failures)
    matrix = {}
    for _c, _r, _t, intended, selected in observations:
        row_map = matrix.setdefault(intended, {})
        row_map[selected] = row_map.get(selected, 0) + 1

    correct = sum(1 for o in observations if o[3] == o[4])
    incorrect = len(observations) - correct
    null_selections = sum(1 for o in observations
                          if o[4] == NULL_LABEL)

    per_skill = {}
    for skill in skills:
        tp = sum(1 for o in observations if o[3] == skill and o[4] == skill)
        fp = sum(1 for o in observations if o[3] != skill and o[4] == skill)
        fn = sum(1 for o in observations if o[3] == skill and o[4] != skill)
        precision = (tp / (tp + fp)) if (tp + fp) else None
        recall = (tp / (tp + fn)) if (tp + fn) else None
        f1 = None
        if precision and recall:
            f1 = 2 * precision * recall / (precision + recall)
        per_skill[skill] = {"tp": tp, "fp": fp, "fn": fn,
                            "precision": precision, "recall": recall,
                            "f1": f1}

    ambiguous_ids = {o[0] for o in observations
                     if o[3] == NULL_LABEL}
    multi_turn_cases = sorted({(o[0]) for o in observations if o[2] is not None})

    return {
        "rule": ("one observation per successful model decision; "
                 "workflow-transition turns contribute one observation each; "
                 "explicit null selections are the literal 'null' class; "
                 "precision/recall/f1 are null when denominators are zero; "
                 "attempted_decisions = successful + failed"),
        "observations": len(observations),
        "attempted_decisions": attempted,
        "successful_decisions": len(observations),
        "failed_decisions": failures,
        "correct_decisions": correct,
        "incorrect_decisions": incorrect,
        "null_decisions": null_selections,
        "accuracy_over_successful": (correct / len(observations))
        if observations else None,
        "accuracy_over_attempted": (correct / attempted) if attempted else None,
        "confusion_matrix": matrix,
        "per_skill": per_skill,
        "ambiguous_null_cases": sorted(ambiguous_ids),
        "multi_turn_cases": multi_turn_cases,
    }


def load_rows(results_path):
    data = json.load(open(results_path))
    if isinstance(data, dict):
        return data["results"]["results"]
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--skills", nargs="*", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    rows = load_rows(args.results)
    skills = args.skills
    if not skills:
        seen = []
        for row in rows:
            for side in ("expected_skill",):
                value = (row.get("vars") or {}).get(side)
                if value and value != "@null" and value not in seen:
                    seen.append(value)
            decision = parse_decision(row)
            if decision and decision.get("selected_skill") \
                    and decision["selected_skill"] not in seen:
                seen.append(decision["selected_skill"])
        skills = seen
    agg = build_aggregate(rows, skills)
    print(json.dumps({
        k: v for k, v in agg.items() if k not in ("rule",)}, indent=2)[:2400])
    print(f"\nattempted={agg['attempted_decisions']} "
          f"successful={agg['successful_decisions']} "
          f"failed={len(agg['failed_decisions'])} "
          f"(invariant ok: "
          f"{agg['attempted_decisions'] == agg['successful_decisions'] + len(agg['failed_decisions'])})")
    print(f"correct={agg['correct_decisions']} "
          f"incorrect={agg['incorrect_decisions']} "
          f"null={agg['null_decisions']} "
          f"acc(successful)={agg['accuracy_over_successful']}")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(agg, f, indent=2)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
