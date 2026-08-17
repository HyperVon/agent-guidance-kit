#!/usr/bin/env python3
"""Execution-efficacy evaluation runner (Docker-isolated layer B).

For each repetition, runs TWO fresh, independent Docker containers:

  * guided   : fixture + target skill guidance mounted read-only into the
               workspace; the worker is told the skill is available.
  * baseline : fixture ONLY (no skill guidance, no skill mention); the worker
               receives the same natural task.

Both use the same hosted free model through anonymous Kilo Gateway access, so
the only systematic difference is whether the target guidance is present. The
runner records container IDs, captured output, and a mount-presence proof so a
later validation step can confirm the baseline genuinely lacked the guidance.

Each container is disposable (--rm) and isolated per isolation-protocol.md.

Usage:
    python3 scripts/run_execution_eval.py \
        --skill code-review --case-id 5 \
        --model kilo/tencent/hy3:free --reps 1 \
        --out .eval-evidence/exec-code-review-case5.json
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_hashing import canonical_hash, source_hash_of

IMAGE = "kilo-eval:local"
# The evaluation must run on a pinned, anonymous FREE model so that cost/account
# binding never varies between the guided and baseline workers (which would
# confound the comparison). This is the single source of truth for the model.
# The free-model catalog changes over time; update this id when the current
# free model is retired. For the same reason --auto below is ONLY permission
# auto-approval for the headless container, never model selection.
DEFAULT_MODEL = "kilo/tencent/hy3:free"


def require_free_model(model):
    # Guard against accidentally running the eval on a paid/account-bound model,
    # which would break the fairness assumption between guided and baseline.
    if not model.endswith(":free"):
        print(f"refusing to run execution eval on non-free model '{model}'. "
              f"The evaluation requires an anonymous free model (id ending in "
              f"':free', e.g. {DEFAULT_MODEL}) so both workers use identical, "
              f"cost-neutral inference.", file=sys.stderr)
        sys.exit(2)

# Docker Desktop on macOS only bind-mounts paths under its shared roots (e.g. the
# project, which lives under /Users). system temp dirs like /var/folders are NOT
# shared and silently appear empty inside the container. Materialize anything that
# gets mounted (fixtures, guidance) under this repo-relative dir instead.
SHARED_TMP = os.path.join(ROOT, ".docker-tmp")


def _mkdtemp(prefix):
    os.makedirs(SHARED_TMP, exist_ok=True)
    d = tempfile.mkdtemp(prefix=prefix, dir=SHARED_TMP)
    os.chmod(d, 0o755)
    return d


def materialize_guidance(skill_dir, skill_name):
    """Build a temp dir with ONLY the guidance (SKILL.md + references/).

    The runner mounts this read-only at /work/guidance/<skill_name>. Crucially
    it EXCLUDES the evals/ tree (which contains the fixture snapshot), so the
    guided worker can never see the expected output it is supposed to produce.
    """
    dst = tempfile.mkdtemp(prefix="kilo-guidance-")
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if os.path.exists(skill_md):
        shutil.copy(skill_md, os.path.join(dst, "SKILL.md"))
    refs = os.path.join(skill_dir, "references")
    if os.path.isdir(refs):
        shutil.copytree(refs, os.path.join(dst, "references"))
    return dst


def materialize_fixture(skill_dir, case):
    fx = case["fixture"]
    src = os.path.join(skill_dir, fx["path"])
    dst = _mkdtemp(prefix="kilo-fixture-")
    if fx.get("type") == "generator":
        # Run the generator into a fresh copy so the host fixture is untouched.
        shutil.copytree(src, dst, dirs_exist_ok=True)
        inv = fx.get("invocation", "bash setup.sh")
        subprocess.run(inv, shell=True, cwd=dst, check=True,
                       capture_output=True, text=True)
    else:
        shutil.copytree(src, dst, dirs_exist_ok=True)
    return dst


def run_container(image, model, prompt, fixture_dir, guidance_dir, skill_name):
    """Run one worker container. Returns (stdout_text, container_id, has_skill_mount).

    guidance_dir, when provided, is the *guidance only* path (SKILL.md +
    references/), mounted read-only at /work/guidance/<name>. Mounting only the
    guidance (never the whole skill dir, which includes the fixture snapshot)
    is what keeps the baseline container free of target guidance.
    """
    cidfile = tempfile.mktemp(suffix=".cid")
    cmd = ["docker", "run", "--rm", "--cidfile", cidfile,
           "-v", f"{fixture_dir}:/work/input",
           "-v", f"{fixture_dir}:/work/output"]
    has_skill = False
    if guidance_dir:
        cmd += ["-v", f"{guidance_dir}:/work/guidance/{skill_name}:ro"]
        has_skill = True
    cmd += [image, "run", "--model", model, "--variant", "high",
            "--format", "json", "--pure", "--auto", "--dir", "/work/input", prompt]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    cid = open(cidfile).read().strip() if os.path.exists(cidfile) else None
    return proc.stdout, cid, has_skill


def collect_text(stdout):
    parts = []
    session = None
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if session is None and obj.get("sessionID"):
            session = obj["sessionID"]
        if obj.get("type") == "text":
            parts.append(obj.get("part", {}).get("text", ""))
    return "".join(parts), session


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True)
    ap.add_argument("--case-id", type=int, required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--image", default=IMAGE)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--out")
    args = ap.parse_args()
    require_free_model(args.model)

    skill_dir = os.path.join(ROOT, "skills", args.skill)
    evals_path = os.path.join(skill_dir, "evals", "evals.json")
    data = json.load(open(evals_path))
    case = next((c for c in data["evals"] if c.get("id") == args.case_id), None)
    if case is None or "execution" not in case.get("evaluation_modes", []):
        print(f"case {args.case_id} is not an execution case", file=sys.stderr)
        sys.exit(2)

    natural_task = case["prompt"]
    # Guidance-only path: SKILL.md (+ references/) — never the whole skill dir,
    # which would pull in the evals/ fixture snapshot.
    guidance_src = materialize_guidance(skill_dir, args.skill)
    skill_hash = source_hash_of(os.path.join(skill_dir, "SKILL.md"))
    evidence = {"skill": args.skill, "case_id": args.case_id, "model": args.model,
                "image": args.image, "repetitions": [], "fixtures": {}}

    try:
        for i in range(args.reps):
            fx = materialize_fixture(skill_dir, case)
            fx_hash = canonical_hash(fx, "committed")
            # Guided worker: guidance available at /work/guidance/<name>.
            g_prompt = (natural_task + "\n\nA skill named '" + args.skill +
                        "' is available at /work/guidance/" + args.skill +
                        "/SKILL.md; read it and follow its guidance.")
            g_out, g_cid, _ = run_container(args.image, args.model, g_prompt, fx,
                                            guidance_src, args.skill)
            g_text, g_sess = collect_text(g_out)
            # Baseline worker: no guidance mounted, no skill mention.
            b_prompt = natural_task
            b_out, b_cid, _ = run_container(args.image, args.model, b_prompt, fx,
                                            None, args.skill)
            b_text, b_sess = collect_text(b_out)
            rep = {
                "rep": i + 1,
                "guided": {"container_id": g_cid, "session_id": g_sess,
                           "skill_mounted": True, "skill_hash": skill_hash,
                           "fixture_hash": fx_hash, "output": g_text},
                "baseline": {"container_id": b_cid, "session_id": b_sess,
                             "skill_mounted": False,
                             "guidance_absent_proof": "runner mounted no guidance "
                             "dir (guidance_dir=None); baseline container had no "
                             "/work/guidance mount",
                             "fixture_hash": fx_hash, "output": b_text},
            }
            # Contamination guard: the guided and baseline workers must run in
            # distinct containers over an identical fixture.
            rep["distinct_containers"] = (g_cid != b_cid)
            evidence["repetitions"].append(rep)
            shutil.rmtree(fx, ignore_errors=True)
    finally:
        shutil.rmtree(guidance_src, ignore_errors=True)
        shutil.rmtree(SHARED_TMP, ignore_errors=True)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        json.dump(evidence, open(args.out, "w"), indent=2)
        print(f"wrote evidence: {args.out}")

    for r in evidence["repetitions"]:
        print(f"rep{r['rep']}: guided_cid={r['guided']['container_id'][:12]} "
              f"baseline_cid={r['baseline']['container_id'][:12]} "
              f"distinct={r['distinct_containers']}")
        print(f"  guided output ({len(r['guided']['output'])} chars), "
              f"baseline output ({len(r['baseline']['output'])} chars)")


if __name__ == "__main__":
    main()
