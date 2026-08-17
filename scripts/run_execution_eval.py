#!/usr/bin/env python3
"""Execution-efficacy evaluation runner (Docker-isolated layer B).

For each repetition, runs TWO fresh, independent Docker containers:

  * guided   : an independent COPY of the pristine fixture + target skill
               guidance mounted read-only; the worker is told the skill exists.
  * baseline : a SEPARATE independent COPY of the same pristine fixture, NO
               skill guidance, NO skill mention; the same natural task.

Crucial correctness properties (see docs/evaluations/isolation-protocol.md):

  * The guided and baseline workers never share a mutable fixture. Each gets its
    own copy made from one pristine seed; we verify both copies hash-identically
    BEFORE the run and record both starting and ending hashes.
  * Generator source (e.g. ``setup.sh``) is evaluator-only. It is run under a
    sanitized environment by ``eval_hashing.materialize_fixture_seed`` and then
    STRIPPED from the seed the worker sees.
  * A failed Docker/Kilo invocation (non-zero return code, missing container,
    unparseable/empty model output, missing session) is recorded as
    ``run_status="failed"`` and can never masquerade as valid evidence. The
    validator rejects any repetition whose guided or baseline worker failed.
  * The guidance boundary is verified INSIDE the container by a probe that checks
    ``/work/guidance/<skill>/SKILL.md`` presence (guided) / absence (baseline).

Both workers use the same pinned, anonymous free model (cost-safety gate), so the
only systematic difference is whether the target guidance is present.

Usage:
    python3 scripts/run_execution_eval.py \
        --skill code-review --case-id 5 \
        --model kilo/tencent/hy3:free --reps 1 \
        --out .eval-evidence/exec-code-review-case5.json
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_hashing import (canonical_hash, source_hash_of, hash_workspace,
                          materialize_fixture_seed)

IMAGE = "kilo-eval:local"
# The evaluation runs on a pinned, anonymous FREE model by default. This is a
# COST-SAFETY gate (accidental spend protection), NOT a scientific requirement:
# guided and baseline simply must use the identical resolved model/runtime. Pass
# --allow-paid-model to use a non-free model deliberately.
DEFAULT_MODEL = "kilo/tencent/hy3:free"

# Docker Desktop on macOS only bind-mounts paths under its shared roots (the
# project, which lives under /Users). system temp dirs like /var/folders are NOT
# shared and silently appear empty inside the container. Materialize anything that
# gets mounted (fixtures, guidance, prompt files) under this repo-relative dir.
SHARED_TMP = os.path.join(ROOT, ".docker-tmp")


def require_free_model(model, allow_paid):
    if allow_paid:
        return
    if not model.endswith(":free"):
        print(f"refusing to run execution eval on non-free model '{model}'. "
              f"This is a cost-safety gate (not a methodology rule): both workers "
              f"must use the identical model. Use --allow-paid-model to opt in, or "
              f"a free model id (e.g. {DEFAULT_MODEL}).", file=sys.stderr)
        sys.exit(2)


def _mkdtemp(prefix):
    os.makedirs(SHARED_TMP, exist_ok=True)
    d = tempfile.mkdtemp(prefix=prefix, dir=SHARED_TMP)
    os.chmod(d, 0o755)
    return d


def materialize_guidance(skill_dir, skill_name):
    """Build a temp dir with ONLY the guidance (SKILL.md + references/).

    Mounted read-only at /work/guidance/<skill_name>. Crucially it EXCLUDES the
    evals/ tree (which contains the fixture snapshot), so the guided worker can
    never see the expected output it is supposed to produce.
    """
    dst = _mkdtemp(prefix="kilo-guidance-")
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if os.path.exists(skill_md):
        shutil.copy(skill_md, os.path.join(dst, "SKILL.md"))
    refs = os.path.join(skill_dir, "references")
    if os.path.isdir(refs):
        shutil.copytree(refs, os.path.join(dst, "references"))
    return dst


def _snapshot(workspace):
    """Capture a deterministic pre/post task-state snapshot of a workspace."""
    git = os.path.join(workspace, ".git")
    if os.path.isdir(git):
        def _git(*a):
            return subprocess.run(["git", "-C", workspace] + list(a),
                                  capture_output=True, text=True).stdout
        head = None
        try:
            head = subprocess.check_output(
                ["git", "-C", workspace, "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL, text=True).strip()
        except Exception:
            head = None
        return {"vcs": "git", "head": head,
                "status": _git("status", "--porcelain=v1"),
                "diff": _git("diff", "--no-color")}
    files = {}
    for root, _, names in os.walk(workspace):
        for n in names:
            full = os.path.join(root, n)
            rel = os.path.relpath(full, workspace)
            if rel.split(os.sep)[0] == ".git":
                continue
            try:
                files[rel] = hashlib.sha256(open(full, "rb").read()).hexdigest()[:16]
            except Exception:
                pass
    return {"vcs": "files", "listing": files}


def _copy_seed(src):
    dst = _mkdtemp(prefix="kilo-workspace-")
    shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)
    return dst


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


def _verify_runtime(image, model):
    """Pre-flight: confirm the Docker image, Kilo CLI, and model are reachable.

    Returns a dict recorded in the evidence. A missing image or a Kilo CLI that
    will not start is fatal (exit). Model reachability is checked best-effort
    (free gateway models may not be enumerated by `kilo models`); the actual runs
    are the authoritative proof of model access, and any failure there is
    recorded as failed evidence rather than silently accepted.
    """
    out = {"image": image, "model": model}
    try:
        out["image_id"] = subprocess.check_output(
            ["docker", "inspect", "--format", "{{.Id}}", image],
            text=True).strip()
    except Exception as e:
        print(f"image {image} not found or docker unavailable: {e}", file=sys.stderr)
        sys.exit(2)
    try:
        out["image_digest"] = subprocess.check_output(
            ["docker", "inspect", "--format",
             "{{join .RepoDigests \",\"}}", image],
            text=True).strip() or None
    except Exception:
        out["image_digest"] = None
    try:
        kv = subprocess.check_output(
            ["docker", "run", "--rm", "--entrypoint", "kilo", image, "--version"],
            text=True, timeout=120).strip()
        out["kilo_version"] = kv.splitlines()[0] if kv else None
    except Exception as e:
        print(f"kilo --version failed inside image {image}: {e}", file=sys.stderr)
        sys.exit(2)
    try:
        out["node_version"] = subprocess.check_output(
            ["docker", "run", "--rm", "--entrypoint", "node", image, "--version"],
            text=True, timeout=60).strip()
    except Exception:
        out["node_version"] = None
    try:
        models = subprocess.check_output(
            ["docker", "run", "--rm", "--entrypoint", "kilo", image, "models"],
            text=True, timeout=120)
        out["model_listed"] = (model in models)
    except Exception:
        out["model_listed"] = None
    return out


def run_container(image, model, prompt, fixture_dir, guidance_dir, skill_name):
    """Run one worker container; return structured execution metadata.

    {
      "returncode": int|None, "stdout": str, "stderr": str,
      "container_id": str|None, "session_id": str|None,
      "output": str, "guidance_probe": "present"|"absent"|None,
      "status": "success"|"failed", "reason": str|None
    }

    A run is successful ONLY if: docker/Kilo returned 0, a container id exists,
    the output was parsed, a session id exists, and model text was produced.
    """
    cidfile = tempfile.mktemp(suffix=".cid", dir=SHARED_TMP)
    promptfile = tempfile.mktemp(suffix=".prompt.txt", dir=SHARED_TMP)
    open(promptfile, "w").write(prompt)
    cmd = ["docker", "run", "--rm", "--cidfile", cidfile,
           "-v", f"{fixture_dir}:/work/task",
           "-v", f"{promptfile}:/work/prompt.txt:ro"]
    if guidance_dir:
        cmd += ["-v", f"{guidance_dir}:/work/guidance/{skill_name}:ro"]
    # ENTRYPOINT is `kilo`; override to bash so we can run kilo then a boundary
    # probe that records whether the guidance path is actually present/absent.
    script = (
        "set +e\n"
        f"kilo run --model {model} --variant high --format json --pure --auto "
        "--dir /work/task \"$(cat /work/prompt.txt)\" < /dev/null "
        "> /tmp/kilo.out 2> /tmp/kilo.err\n"
        "KILO_RC=$?\n"
        "cat /tmp/kilo.out\n"
        "cat /tmp/kilo.err >&2\n"
        f"if [ -e \"/work/guidance/{skill_name}/SKILL.md\" ]; then "
        "echo GUIDANCE_PROBE:present; else echo GUIDANCE_PROBE:absent; fi\n"
        "exit $KILO_RC\n"
    )
    cmd += ["--entrypoint", "bash", image, "-c", script]

    meta = {"returncode": None, "stdout": "", "stderr": "",
            "container_id": None, "session_id": None, "output": "",
            "guidance_probe": None, "status": "failed", "reason": None}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    except Exception as e:
        meta["reason"] = f"docker invocation error: {e}"
        os.path.exists(promptfile) and os.remove(promptfile)
        return meta

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    cid = open(cidfile).read().strip() if os.path.exists(cidfile) else None
    os.path.exists(promptfile) and os.remove(promptfile)
    os.path.exists(cidfile) and os.remove(cidfile)

    session = _extract_session(stdout)
    text = _collect_text(stdout)
    probe = None
    for line in stdout.splitlines():
        if line.strip().startswith("GUIDANCE_PROBE:"):
            probe = line.strip().split(":", 1)[1]

    meta.update({"returncode": proc.returncode, "stdout": stdout,
                 "stderr": stderr, "container_id": cid, "session_id": session,
                 "output": text, "guidance_probe": probe})

    if proc.returncode != 0:
        meta["reason"] = f"kilo/docker exited {proc.returncode}"
    elif not cid:
        meta["reason"] = "no container id (container never started)"
    elif not session:
        meta["reason"] = "no session id in model output"
    elif not text.strip():
        meta["reason"] = "empty model response (no text produced)"
    else:
        meta["status"] = "success"
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True)
    ap.add_argument("--case-id", type=int, required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--image", default=IMAGE)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--allow-paid-model", action="store_true",
                    help="allow a non-free model (cost-safety opt-in)")
    ap.add_argument("--out")
    args = ap.parse_args()
    require_free_model(args.model, args.allow_paid_model)

    skill_dir = os.path.join(ROOT, "skills", args.skill)
    evals_path = os.path.join(skill_dir, "evals", "evals.json")
    data = json.load(open(evals_path))
    case = next((c for c in data["evals"] if c.get("id") == args.case_id), None)
    if case is None or "execution" not in case.get("evaluation_modes", []):
        print(f"case {args.case_id} is not an execution case", file=sys.stderr)
        sys.exit(2)

    fx = case["fixture"]
    ftype = fx.get("type")
    fx_src = os.path.join(skill_dir, fx["path"])
    source = fx.get("source", "setup.sh")
    invocation = fx.get("invocation", "bash setup.sh")

    runtime = _verify_runtime(args.image, args.model)

    natural_task = case["prompt"]
    guidance_src = materialize_guidance(skill_dir, args.skill)
    skill_hash = source_hash_of(os.path.join(skill_dir, "SKILL.md"))

    evidence = {
        "evidence_type": "execution",
        "skill": args.skill, "case_id": args.case_id, "model": args.model,
        "image": args.image, "kilo_version": runtime.get("kilo_version"),
        "image_id": runtime.get("image_id"),
        "image_digest": runtime.get("image_digest"),
        "node_version": runtime.get("node_version"),
        "model_listed": runtime.get("model_listed"),
        "skill_hash": skill_hash,
        "canonical_seed_hash": None,  # filled in after the first seed is materialized
        "repetitions": [],
    }

    try:
        for i in range(args.reps):
            # One pristine seed; two independent worker copies.
            seed, seed_hash = materialize_fixture_seed(
                fx_src, ftype, source, invocation)
            evidence["canonical_seed_hash"] = seed_hash
            g_fx = _copy_seed(seed)
            b_fx = _copy_seed(seed)
            g_before = hash_workspace(g_fx)
            b_before = hash_workspace(b_fx)

            g_prompt = (natural_task + "\n\nA skill named '" + args.skill +
                        "' is available at /work/guidance/" + args.skill +
                        "/SKILL.md; read it and follow its guidance.")
            b_prompt = natural_task

            # Pre-run snapshots (before the worker mutates the mounted copy).
            g_snap_before, b_snap_before = _snapshot(g_fx), _snapshot(b_fx)

            g_meta = run_container(args.image, args.model, g_prompt, g_fx,
                                   guidance_src, args.skill)
            b_meta = run_container(args.image, args.model, b_prompt, b_fx,
                                   None, args.skill)

            g_after = hash_workspace(g_fx)
            b_after = hash_workspace(b_fx)

            # Post-run snapshots (after the worker mutated the mounted copy).
            g_snap_after, b_snap_after = _snapshot(g_fx), _snapshot(b_fx)

            rep = {
                "rep": i + 1,
                "workspace_path": "/work/task",
                "canonical_seed_hash": seed_hash,
                "guided_workspace_id": os.path.basename(g_fx),
                "baseline_workspace_id": os.path.basename(b_fx),
                "guided": {
                    "container_id": g_meta["container_id"],
                    "session_id": g_meta["session_id"],
                    "run_status": g_meta["status"],
                    "returncode": g_meta["returncode"],
                    "skill_mounted": True,
                    "skill_hash": skill_hash,
                    "guidance_verified": (g_meta["guidance_probe"] == "present"),
                    "guidance_probe": g_meta["guidance_probe"],
                    "starting_fixture_hash": g_before,
                    "ending_fixture_hash": g_after,
                    "output": g_meta["output"],
                    "stderr": g_meta["stderr"],
                    "filesystem_snapshot_before": g_snap_before,
                    "filesystem_snapshot_after": g_snap_after,
                    "reason": g_meta["reason"],
                },
                "baseline": {
                    "container_id": b_meta["container_id"],
                    "session_id": b_meta["session_id"],
                    "run_status": b_meta["status"],
                    "returncode": b_meta["returncode"],
                    "skill_mounted": False,
                    "guidance_verified_absent": (b_meta["guidance_probe"] == "absent"),
                    "guidance_probe": b_meta["guidance_probe"],
                    "starting_fixture_hash": b_before,
                    "ending_fixture_hash": b_after,
                    "output": b_meta["output"],
                    "stderr": b_meta["stderr"],
                    "filesystem_snapshot_before": b_snap_before,
                    "filesystem_snapshot_after": b_snap_after,
                    "reason": b_meta["reason"],
                },
                "distinct_containers": (g_meta["container_id"]
                                        and g_meta["container_id"]
                                        != b_meta["container_id"]),
                "distinct_sessions": (g_meta["session_id"]
                                      and g_meta["session_id"]
                                      != b_meta["session_id"]),
                "starting_fixture_hashes_match": (g_before == b_before == seed_hash),
                "workspace_paths_differ": (os.path.basename(g_fx)
                                           != os.path.basename(b_fx)),
            }
            evidence["repetitions"].append(rep)

            shutil.rmtree(g_fx, ignore_errors=True)
            shutil.rmtree(b_fx, ignore_errors=True)
            shutil.rmtree(seed, ignore_errors=True)
    finally:
        shutil.rmtree(guidance_src, ignore_errors=True)
        shutil.rmtree(SHARED_TMP, ignore_errors=True)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        json.dump(evidence, open(args.out, "w"), indent=2)
        print(f"wrote evidence: {args.out}")

    for r in evidence["repetitions"]:
        g, b = r["guided"], r["baseline"]
        print(f"rep{r['rep']}: guided[{g['run_status']}] cids "
              f"{str(g['container_id'])[:12]}/{str(b['container_id'])[:12]} "
              f"distinct={r['distinct_containers']} "
              f"start_match={r['starting_fixture_hashes_match']}")
        print(f"  guided output ({len(g['output'])} chars, "
              f"after-hash {g['ending_fixture_hash'][:10]}), "
              f"baseline output ({len(b['output'])} chars, "
              f"after-hash {b['ending_fixture_hash'][:10]})")


if __name__ == "__main__":
    main()
