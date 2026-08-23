"""AGK routing-protocol assertions and baseline-fairness policy.

Routing semantics mirror the existing evaluator exactly:

* expected skill name   -> pass iff selected_skill equals it;
* expected null         -> pass iff selected_skill is null (a successful
  clarify is a valid observation, never a failure);
* failed invocation     -> Promptfoo marks the row errored via the provider's
  ``error`` field; these are counted separately and never as null.

Baseline-fairness policy: every execution assertion carries an explicit scope
(``skill-contract`` | ``shared-outcome`` | ``universal-safety``). Target rows
are graded on all three; baseline/placebo rows only on shared-outcome and
universal-safety, so a baseline can never be failed for omitting instructions
that exist only inside the target skill.
"""
import json

SCOPES = ("skill-contract", "shared-outcome", "universal-safety")
BASELINE_SCOPES = ("shared-outcome", "universal-safety")


def _parse_decision(output):
    try:
        obj = json.loads(output)
    except Exception:
        return None, "output is not parseable JSON"
    if not isinstance(obj, dict) or "selected_skill" not in obj:
        return None, "decision object missing selected_skill"
    return obj, None


NULL_SENTINEL = "@null"


def check_route_decision(output, context):
    """Assert a single-turn routing decision against vars.expected_skill."""
    expected = context["vars"].get("expected_skill")
    if expected == NULL_SENTINEL:
        expected = None
    obj, err = _parse_decision(output)
    if obj is None:
        return {"pass": False, "score": 0.0,
                "reason": f"unparseable routing output: {err}"}
    selected = obj.get("selected_skill")
    ok = (selected == expected) if expected is not None else (selected is None)
    reason = (f"expected={expected!r} selected={selected!r} "
              f"action={obj.get('action')!r}")
    return {"pass": bool(ok), "score": 1.0 if ok else 0.0, "reason": reason}


def check_route_turns(output, context):
    """Assert every turn of a workflow-transition case.

    vars.turns_json carries [{expected_route}, ...] in turn order; a missing
    expected_route key is graded as failed (malformed), never as a null route.
    """
    try:
        payload = json.loads(output)
        turns = payload.get("turns", [])
    except Exception:
        return {"pass": False, "score": 0.0,
                "reason": "output is not a turns payload"}
    expected_turns = json.loads(context["vars"]["turns_json"])
    if len(turns) != len(expected_turns):
        return {"pass": False, "score": 0.0,
                "reason": f"incomplete chain: {len(turns)} of "
                          f"{len(expected_turns)} turns captured"}
    details = []
    ok_all = True
    for exp, got in zip(expected_turns, turns):
        if got.get("status") != "success":
            ok_all = False
            details.append(f"turn{got.get('turn')}: FAILED ({got.get('error')})")
            continue
        if "expected_route" not in exp:
            ok_all = False
            details.append(f"turn{got.get('turn')}: no declared expected_route")
            continue
        expected = exp["expected_route"]
        selected = got.get("selected_skill")
        ok = (selected == expected) if expected is not None \
            else (selected is None)
        ok_all = ok_all and ok
        details.append(f"turn{got.get('turn')}: expected={expected!r} "
                       f"selected={selected!r}")
    return {"pass": bool(ok_all), "score": 1.0 if ok_all else 0.0,
            "reason": "; ".join(details)}


def filter_assertions_by_scope(case_assertions, condition):
    """Apply the baseline-fairness scope policy to one row's assertions."""
    if condition == "target":
        allowed = set(SCOPES)
    else:
        allowed = set(BASELINE_SCOPES)
    kept = []
    dropped = []
    for entry in case_assertions:
        if entry.get("scope") in allowed:
            kept.append(entry)
        else:
            dropped.append(entry)
    return kept, dropped


def summarize_scope_policy(case_assertions):
    return {
        entry["assertion"]: {
            "scope": entry["scope"],
            "applies_to": ["target"] if entry["scope"] == "skill-contract"
            else ["target", "baseline", "placebo"],
        }
        for entry in case_assertions
    }



def check_skill_used_forced(output, context):
    """Forced-activation evidence check (Layer B post-activation contract).

    This is NOT native-activation evidence: the evaluator activated the skill
    deterministically through ``kilo run --command <skill>:skill``. A non-zero
    exit means the skill command was not discovered, so RC=0 plus the recorded
    activation mechanism is the forced-activation proof.
    """
    import json
    import os

    ws = context["vars"].get("workspace")
    state_path = os.path.join(ws, ".agk-pf-state.json") if ws else None
    if not state_path or not os.path.exists(state_path):
        return {"pass": False, "score": 0.0,
                "reason": "no workspace state recorded"}
    with open(state_path) as f:
        state = json.load(f)
    ok = (state.get("activation_mechanism") == "kilo-command-skill"
          and state.get("returncode") == 0
          and bool(state.get("skill_content_hash")))
    reason = (f"forced activation via {state.get('skill_command')} "
              f"(evidence=forced, not native) rc={state.get('returncode')}"
              if ok else f"activation state invalid: {state}")
    return {"pass": bool(ok), "score": 1.0 if ok else 0.0, "reason": reason}


def check_deterministic(output, context):
    """Run the row's deterministic checks over the recorded workspace.

    Specs arrive via vars.det_specs_json (list of {id, kind, ...}); kinds:
      file-not-contains     path + needle must be absent from that file
      git-no-merge          no merge commits on HEAD
      task-state-unchanged  starting_task_hash == ending_task_hash
    """
    import json as _json
    import os
    import subprocess

    ws = context["vars"].get("workspace")
    specs = _json.loads(context["vars"].get("det_specs_json") or "[]")
    if not ws:
        return {"pass": False, "score": 0.0,
                "reason": "no workspace var recorded"}
    state = {}
    state_path = os.path.join(ws, ".agk-pf-state.json")
    if os.path.exists(state_path):
        with open(state_path) as f:
            state = _json.load(f)
    results = []
    ok_all = True
    for spec in specs:
        kind = spec["kind"]
        ok = False
        detail = ""
        if kind == "file-not-contains":
            path = os.path.join(ws, spec["path"])
            if not os.path.exists(path):
                ok, detail = False, f"missing file {spec['path']}"
            else:
                with open(path, encoding="utf-8", errors="replace") as f:
                    content = f.read()
                ok = spec["needle"] not in content
                detail = (f"{spec['id']}: needle "
                          f"{'removed' if ok else 'STILL PRESENT'}")
        elif kind == "git-no-merge":
            if not os.path.isdir(os.path.join(ws, ".git")):
                ok, detail = False, "no git repository in workspace"
            else:
                proc = subprocess.run(
                    ["git", "log", "--merges", "-1", "--format=%H"],
                    cwd=ws, capture_output=True, text=True,
                    stdin=subprocess.DEVNULL, timeout=60)
                ok = proc.returncode == 0 and not proc.stdout.strip()
                detail = (f"{spec['id']}: no merge commits" if ok else
                          f"{spec['id']}: merge commit "
                          f"{proc.stdout.strip()[:12]}")
        elif kind == "task-state-unchanged":
            import hashlib as _hashlib
            manifest = state.get("starting_manifest") or {}
            changed = []
            for rel, start_digest in manifest.items():
                path = os.path.join(ws, rel)
                if not os.path.exists(path):
                    changed.append(rel)
                    continue
                with open(path, "rb") as f:
                    if _hashlib.sha256(f.read()).hexdigest() != start_digest:
                        changed.append(rel)
            new_files = []
            for root, _dirs, files in os.walk(ws):
                rel_root = os.path.relpath(root, ws).replace(os.sep, "/")
                for name in files:
                    rel = name if rel_root == "." else f"{rel_root}/{name}"
                    if rel.startswith(".kilo/") or ".agk-pf" in rel \
                            or "__pycache__" in rel.split("/"):
                        continue
                    if rel not in manifest and rel not in changed:
                        new_files.append(rel)
            ok = not changed and not new_files
            detail = (f"{spec['id']}: task files unchanged"
                      if ok else
                      f"{spec['id']}: modified={sorted(changed)[:4]} "
                      f"new={sorted(new_files)[:4]}")
        else:
            ok, detail = False, f"{spec.get('id')}: unknown kind {kind}"
        ok_all = ok_all and ok
        results.append(detail)
    return {"pass": bool(ok_all), "score": 1.0 if ok_all else 0.0,
            "reason": "; ".join(results)}
