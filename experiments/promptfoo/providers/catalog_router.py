"""Layer A catalog-routing provider for Promptfoo.

Thin transformation layer: Promptfoo owns orchestration/repetition/assertions;
this provider only (1) optionally chains multi-turn sessions and (2) delegates
model invocation to the same ``kilo`` CLI the existing evaluator uses, parsing
decisions with the canonical ``scripts.run_catalog_routing_eval``
implementation so failure semantics are byte-for-byte comparable with v1.

Expected vars:
    request            single-turn user request (plain cases)
    turns_json         JSON list of {prompt, expected_route} for
                       workflow-transition cases (multi-turn chaining)
    catalog_names_json JSON list of skill names present in the supplied catalog

Returns ProviderResponse dict; an invocation/parse failure sets ``error``
(never a silent null selection).
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.run_catalog_routing_eval import (  # noqa: E402
    _collect_text,
    _extract_session,
    extract_decision,
)

DEFAULT_MODEL = "kilo/tencent/hy3:free"


def _run_kilo(prompt, model, workdir, timeout_s):
    cmd = ["kilo", "run", "--model", model, "--variant", "high",
           "--format", "json", "--pure", prompt]
    child_env = dict(os.environ, PWD=workdir)
    proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          timeout=timeout_s, env=child_env)
    return proc


def call_api(prompt, options, context):
    cfg = options.get("config", {})
    model = cfg.get("model", DEFAULT_MODEL)
    timeout_s = int(cfg.get("timeout_s", 600))
    variables = context.get("vars", {})
    turns_json = variables.get("turns_json")
    catalog_names = None
    if variables.get("catalog_names_json"):
        catalog_names = set(json.loads(variables["catalog_names_json"]))

    workdir = tempfile.mkdtemp(prefix="pf-routing-")
    try:
        if turns_json:
            return _run_multi_turn(json.loads(turns_json), model, workdir,
                                   timeout_s)
        return _run_single(prompt, model, workdir, timeout_s, catalog_names)
    except subprocess.TimeoutExpired:
        return {"output": "", "error": f"kilo invocation timed out after "
                                       f"{timeout_s}s"}
    except Exception as exc:
        return {"output": "", "error": f"invocation error: {exc}"}
    finally:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)


def _decision_payload(decision):
    return {
        "selected_skill": decision.get("selected_skill"),
        "action": decision.get("action"),
        "rationale": decision.get("rationale"),
    }


def _run_single(prompt, model, workdir, timeout_s, catalog_names):
    proc = _run_kilo(prompt, model, workdir, timeout_s)
    raw = proc.stdout or ""
    text = _collect_text(raw)
    parsed = extract_decision(text, catalog_names)
    status = parsed["status"]
    error = parsed.get("error")
    if proc.returncode != 0:
        status = "failed"
        error = f"kilo exited {proc.returncode}: {(proc.stderr or '')[:200]}"
    meta = {
        "layer": "A",
        "experiment": "catalog-routing",
        "status": status,
        "model": model,
        "returncode": proc.returncode,
        "session_id": _extract_session(raw),
        "prompt_hash": hashlib.sha256((prompt or "").encode()).hexdigest(),
        "output_hash": hashlib.sha256(raw.encode()).hexdigest(),
        "engine": "promptfoo",
        "provider_impl": "kilo-cli",
    }
    if status != "success":
        meta["error_detail"] = error
        return {"output": text or "", "error": error, "metadata": meta}
    return {
        "output": json.dumps(_decision_payload(parsed["decision"])),
        "metadata": meta,
    }


def _run_multi_turn(turns, model, workdir, timeout_s):
    results = []
    session_id = None
    failed = False
    error = None
    for i, turn in enumerate(turns, 1):
        cmd = ["kilo", "run", "--model", model, "--variant", "high",
               "--format", "json", "--pure", turn["prompt"]]
        if session_id:
            cmd += ["--session", session_id, "--continue"]
        try:
            child_env = dict(os.environ, PWD=workdir)
            proc = subprocess.run(cmd, cwd=workdir, capture_output=True,
                                  text=True, stdin=subprocess.DEVNULL,
                                  timeout=timeout_s, env=child_env)
        except Exception as exc:
            failed = True
            error = f"turn {i} invocation error: {exc}"
            break
        raw = proc.stdout or ""
        text = _collect_text(raw)
        parsed = extract_decision(text, None)
        status = parsed["status"]
        terr = parsed.get("error")
        if proc.returncode != 0:
            status = "failed"
            terr = f"turn {i}: kilo exited {proc.returncode}"
        new_session = _extract_session(raw)
        if new_session:
            session_id = new_session
        entry = {
            "turn": i,
            "session_id": session_id,
            "expected_route": turn.get("expected_route"),
            "status": status,
            "error": terr,
        }
        if status == "success":
            entry.update(_decision_payload(parsed["decision"]))
        else:
            failed = True
            error = terr
            results.append(entry)
            break
        results.append(entry)
    meta = {
        "layer": "A",
        "experiment": "catalog-routing",
        "status": "failed" if failed else "success",
        "model": model,
        "session_id": session_id,
        "turn_count": len(results),
        "engine": "promptfoo",
        "provider_impl": "kilo-cli",
    }
    if failed:
        return {
            "output": json.dumps({"turns": results}),
            "error": error,
            "metadata": meta,
        }
    return {"output": json.dumps({"turns": results}), "metadata": meta}


def build_routing_prompt(catalog_text, user_request):
    """Expose the exact neutral-router prompt used by the spike (same bytes
    as scripts.run_catalog_routing_eval.build_confusion_prompt)."""
    from scripts.run_catalog_routing_eval import build_confusion_prompt
    return build_confusion_prompt(catalog_text, user_request)
