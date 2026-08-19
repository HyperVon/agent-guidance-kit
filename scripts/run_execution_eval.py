#!/usr/bin/env python3
"""Execution-efficacy evaluation runner (Docker-isolated layer B).

For each repetition, runs fresh, independent Docker containers — one per
condition. The supported conditions are:

  * ``target``: an independent COPY of the pristine fixture plus
    the target guidance mounted read-only at a NEUTRAL path; the worker
    receives ONLY the natural task.
  * ``baseline`` (harness/default): a SEPARATE independent COPY of the same
                           pristine fixture, NO guidance; the SAME natural task.
  * ``placebo`` (optional): a SEPARATE independent COPY of the same pristine
                           fixture plus IRRELEVANT, similarly-sized guidance
                           (a different skill) mounted at the SAME neutral
                           path; the SAME natural task.

TREATMENT-BOUNDARY CONTRACT (see skills/skill-evaluation/SKILL.md and
docs/evaluations/RUNBOOK.md):

  * The natural user task text is BYTE-IDENTICAL across all conditions. The
    target/baseline/placebo workers must not be told that an evaluation is
    happening, which condition they are in, the target skill's canonical name,
    the expected outcome, the scoring rubric, or that another condition exists.
  * The guidance is exposed at a NEUTRAL path — ``/work/guidance/task/SKILL.md``
    — that never encodes the skill name, the condition, a case id, or the
    evaluation purpose. The worker-visible prompt is the natural task only.
  * The only way a worker learns guidance exists is by its runtime environment
    (the mounted read-only guidance tree). No prompt text names it.
  * The placebo condition receives an irrelevant skill's guidance at the SAME
    neutral path, so "presence of extra procedural guidance" is controlled for.

Crucial correctness properties (see docs/evaluations/isolation-protocol.md):

  * The conditions never share a mutable fixture. Each gets its own copy made
    from one pristine seed; we verify all copies hash-identically BEFORE the
    run and record starting and ending hashes.
  * Generator source (e.g. ``setup.sh``) is evaluator-only. It is run under a
    sanitized environment by ``eval_hashing.materialize_fixture_seed`` and then
    STRIPPED from the seed the worker sees.
  * A failed Docker/Kilo invocation (non-zero return code, missing container,
    unparseable/empty model output, missing session) is recorded as
    ``run_status="failed"`` and can never masquerade as valid evidence. The
    validator rejects any repetition whose worker failed.
  * The guidance boundary is verified INSIDE the container by a probe that
    checks ``/work/guidance/task/SKILL.md`` presence (target/placebo) /
    absence (baseline).

All workers use the same pinned, anonymous free model (cost-safety gate), so
the only systematic difference between conditions is the mounted guidance.

Usage:
    python3 scripts/run_execution_eval.py \
        --skill code-review --case-id 5 \
        --model kilo/tencent/hy3:free --reps 1 \
        --conditions target baseline \
        --out .eval-evidence/exec-code-review-case5.json

    # Strong-efficacy run with the placebo control:
    python3 scripts/run_execution_eval.py \
        --skill code-review --case-id 5 \
        --placebo-skill security-review \
        --conditions target baseline placebo \
        --out .eval-evidence/exec-code-review-case5-placebo.json
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
from eval_hashing import (source_hash_of, hash_workspace,
                           materialize_fixture_seed, HASH_PREFIX)

IMAGE = "kilo-eval:local"
# The evaluation runs on a pinned, anonymous FREE model by default. This is a
# COST-SAFETY gate (accidental spend protection), NOT a scientific requirement:
# The target, baseline, and placebo conditions simply must use the identical
# resolved model/runtime. Pass
# --allow-paid-model to use a non-free model deliberately.
DEFAULT_MODEL = "kilo/tencent/hy3:free"

# Neutral worker-visible guidance mount. It deliberately does NOT encode the
# skill name, the condition, a case id, or the evaluation purpose. In a real
# harness the equivalent is the harness's own guidance-loading surface, which
# is part of the runtime condition and identical across conditions.
GUIDANCE_MOUNT = "/work/guidance/task"
WORKSPACE_MOUNT = "/work/task"

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

    Mounted read-only at the NEUTRAL path ``/work/guidance/task`` (see
    GUIDANCE_MOUNT). The directory is always staged as ``task/`` so the mount
    target is identical for the target and placebo conditions, and never
    encodes the skill name, the condition, or the evaluation purpose.
    Crucially it EXCLUDES the evals/ tree (which contains the fixture
    snapshot), so the target worker can never see the expected output it is
    supposed to produce.
    """
    dst = _mkdtemp(prefix="kilo-guidance-")
    task = os.path.join(dst, "task")
    os.makedirs(task)
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if os.path.exists(skill_md):
        shutil.copy(skill_md, os.path.join(task, "SKILL.md"))
    refs = os.path.join(skill_dir, "references")
    if os.path.isdir(refs):
        shutil.copytree(refs, os.path.join(task, "references"))
    return dst


def materialize_skill_for_kilo(skill_dir, skill_name, workspace):
    """Create ``.kilo/skills/<skill-name>/`` in the worker's workspace so Kilo
    discovers the skill through its normal startup scan.

    This is the activation mechanism for Layer B.  Merely mounting a
    ``SKILL.md`` at an arbitrary neutral path does not cause Kilo to load the
    skill into the worker's context.  Kilo discovers skills from
    ``.kilo/skills/`` (project-level) in the working directory at session
    start; once discovered, the agent may read the ``SKILL.md`` into context
    when it decides the task matches the skill description.

    The placebo condition gets the same mechanism with an irrelevant skill.
    The baseline receives no ``.kilo/skills/`` directory at all.
    """
    kilo_skills = os.path.join(workspace, ".kilo", "skills", skill_name)
    os.makedirs(kilo_skills, exist_ok=True)
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if os.path.exists(skill_md):
        shutil.copy(skill_md, os.path.join(kilo_skills, "SKILL.md"))
    refs = os.path.join(skill_dir, "references")
    if os.path.isdir(refs):
        shutil.copytree(refs, os.path.join(kilo_skills, "references"),
                        dirs_exist_ok=True)
    return kilo_skills


def extract_skill_loads(stdout, skill_name, workspace_path):
    """Detect whether the agent actually loaded a skill by reading its SKILL.md.

    Returns a list of ``{path, timestamp}`` dicts for each detected load event
    in the Kilo JSONL output.  A skill is considered ``loaded`` when the agent
    issues a ``read`` tool call against the ``.kilo/skills/<skill>/SKILL.md``
    path inside the worker workspace.
    """
    skill_md_rel = os.path.join(".kilo", "skills", skill_name, "SKILL.md")
    loads = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") == "tool_use":
            part = obj.get("part", {})
            if part.get("tool") == "read":
                file_path = part.get("state", {}).get("input", {}).get("filePath", "")
                if skill_md_rel in file_path or (
                    skill_name in file_path and "SKILL.md" in file_path
                ):
                    loads.append({
                        "path": file_path,
                        "timestamp": obj.get("timestamp"),
                    })
    return loads


def guidance_bundle_hash(guidance_dir):
    """Deterministic hash of the EXACT guidance artifact mounted read-only into the
    target worker: SKILL.md plus references/** (sorted by relative path, each file
    hashed by content). This is the frozen bundle the evaluator intends to inject,
    recorded so the validator can prove the target worker received exactly this
    guidance (the mount is read-only; the worker cannot alter the source bundle).
    """
    if not os.path.isdir(guidance_dir):
        return None
    h = hashlib.sha256()
    rels = []
    for root, _, names in os.walk(guidance_dir):
        for n in names:
            full = os.path.join(root, n)
            if os.path.islink(full):
                continue
            rels.append(os.path.relpath(full, guidance_dir))
    for rel in sorted(rels):
        full = os.path.join(guidance_dir, rel)
        fh = hashlib.sha256(open(full, "rb").read()).hexdigest()
        h.update((rel + ":" + fh + "\n").encode())
    return HASH_PREFIX + h.hexdigest()


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


def run_container(image, model, prompt, fixture_dir, guidance_dir):
    """Run one worker container; return structured execution metadata.

    {
      "returncode": int|None, "stdout": str, "stderr": str,
      "container_id": str|None, "session_id": str|None,
      "output": str, "guidance_probe": "present"|"absent"|None,
      "status": "success"|"failed", "reason": str|None
    }

    The worker-visible prompt is the natural task ONLY — no skill name, no
    condition label, no evaluation mention. Guidance (if any) is mounted at the
    neutral ``GUIDANCE_MOUNT`` path, which is identical for the target and
    placebo conditions.

    A run is successful ONLY if: docker/Kilo returned 0, a container id exists,
    the output was parsed, a session id exists, and model text was produced.
    """
    # Place the cid/prompt files inside a mkdtemp directory (secure; avoids the
    # CodeQL py/insecure-temp-file finding on tempfile.mktemp). docker --cidfile
    # requires the file to NOT pre-exist, so we create the directory and use
    # fixed names within it rather than pre-creating the files.
    tmpd = _mkdtemp(prefix="kilo-run-")
    try:
        cidfile = os.path.join(tmpd, "cid")
        promptfile = os.path.join(tmpd, "prompt.txt")
        with open(promptfile, "w") as _pf:
            _pf.write(prompt)
        cmd = ["docker", "run", "--rm", "--cidfile", cidfile,
               "-v", f"{fixture_dir}:{WORKSPACE_MOUNT}",
               "-v", f"{promptfile}:/work/prompt.txt:ro"]
        if guidance_dir:
            cmd += ["-v", f"{guidance_dir}:{GUIDANCE_MOUNT}:ro"]
        # ENTRYPOINT is `kilo`; override to bash so we can run kilo then a boundary
        # probe that records whether the guidance path is actually present/absent.
        script = (
            "set +e\n"
            f"kilo run --model {model} --variant high --format json --pure --auto "
            f"--dir {WORKSPACE_MOUNT} \"$(cat /work/prompt.txt)\" < /dev/null "
            "> /tmp/kilo.out 2> /tmp/kilo.err\n"
            "KILO_RC=$?\n"
            "cat /tmp/kilo.out\n"
            "cat /tmp/kilo.err >&2\n"
            f"if [ -e \"{GUIDANCE_MOUNT}/SKILL.md\" ]; then "
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
            return meta

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        cid = open(cidfile).read().strip() if os.path.exists(cidfile) else None

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
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)


CONDITIONS = ("target", "baseline", "placebo")


def _conditions_arg(value):
    """Parse --conditions; require at least target+baseline; unique order kept."""
    parts = [p.strip() for p in value.split(",") if p.strip()]
    bad = [p for p in parts if p not in CONDITIONS]
    if bad:
        raise argparse.ArgumentTypeError(
            f"unknown condition(s) {bad}; choose from {', '.join(CONDITIONS)}")
    if not parts:
        raise argparse.ArgumentTypeError("at least one condition required")
    # Keep the first occurrence order; dedupe.
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    if "target" not in out or "baseline" not in out:
        raise argparse.ArgumentTypeError(
            "--conditions must include at least 'target' and 'baseline' "
            "(placebo is optional)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True)
    ap.add_argument("--case-id", type=int, required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--image", default=IMAGE)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--allow-paid-model", action="store_true",
                    help="allow a non-free model (cost-safety opt-in)")
    ap.add_argument("--conditions", type=_conditions_arg,
                    default=["target", "baseline"],
                    help="comma-separated conditions to run: target,baseline[,placebo]")
    ap.add_argument("--placebo-skill", help="skill whose guidance is the "
                    "irrelevant placebo (required when 'placebo' is in --conditions)")
    ap.add_argument("--out")
    args = ap.parse_args()
    require_free_model(args.model, args.allow_paid_model)

    if "placebo" in args.conditions and not args.placebo_skill:
        print("--placebo-skill <skill> is required when 'placebo' is in "
              "--conditions (an irrelevant, similarly-sized guidance source)",
              file=sys.stderr)
        sys.exit(2)
    if args.placebo_skill and args.placebo_skill == args.skill:
        print("--placebo-skill must differ from the target skill "
              "(placebo is irrelevant guidance)", file=sys.stderr)
        sys.exit(2)

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

    # The natural task is the ONLY worker-visible prompt text, byte-identical
    # across all conditions. Nothing here names the skill, the condition, the
    # case, or the evaluation.
    natural_task = case["prompt"]
    guidance_src = materialize_guidance(skill_dir, args.skill)
    skill_hash = source_hash_of(os.path.join(skill_dir, "SKILL.md"))
    guidance_bundle = guidance_bundle_hash(guidance_src)

    placebo_dir = None
    placebo_hash = None
    if "placebo" in args.conditions:
        pdir = os.path.join(ROOT, "skills", args.placebo_skill)
        if not os.path.exists(os.path.join(pdir, "SKILL.md")):
            print(f"placebo skill dir missing: {pdir}", file=sys.stderr)
            sys.exit(2)
        placebo_dir = materialize_guidance(pdir, args.placebo_skill)
        placebo_hash = guidance_bundle_hash(placebo_dir)

    # The frozen fixture hash the worker is SUPPOSED to receive. For a generator
    # fixture this is the worker-visible output_hash (setup.sh already stripped);
    # for a committed fixture it is content_hash. The validator must reject if the
    # runtime canonical seed does not equal this exact frozen value.
    if ftype == "generator":
        expected_fixture_hash = fx.get("output_hash")
    else:
        expected_fixture_hash = fx.get("content_hash")

    evidence = {
        "evidence_type": "execution",
        "skill": args.skill, "case_id": args.case_id, "model": args.model,
        "image": args.image, "kilo_version": runtime.get("kilo_version"),
        "image_id": runtime.get("image_id"),
        "image_digest": runtime.get("image_digest"),
        "node_version": runtime.get("node_version"),
        "model_listed": runtime.get("model_listed"),
        "skill_hash": skill_hash,
        "guidance_bundle_hash": guidance_bundle,
        "guidance_mount_path": GUIDANCE_MOUNT,
        "target_skill_kilo_path": os.path.join(".kilo", "skills", args.skill),
        "placebo_skill_kilo_path": (
            os.path.join(".kilo", "skills", args.placebo_skill)
            if "placebo" in args.conditions else None
        ),
        "expected_fixture_hash": expected_fixture_hash,
        "canonical_seed_hash": None,  # filled in after the first seed is materialized
        "conditions": list(args.conditions),
        "placebo_skill": args.placebo_skill if "placebo" in args.conditions else None,
        "placebo_bundle_hash": placebo_hash,
        "repetitions": [],
    }

    def run_condition(name, prompt, workspace, guidance):
        before = HASH_PREFIX + hash_workspace(workspace)
        snap_before = _snapshot(workspace)
        meta = run_container(args.image, args.model, prompt, workspace, guidance)
        after = HASH_PREFIX + hash_workspace(workspace)
        snap_after = _snapshot(workspace)
        return {
            "container_id": meta["container_id"],
            "session_id": meta["session_id"],
            "run_status": meta["status"],
            "returncode": meta["returncode"],
            "guidance_mounted": guidance is not None,
            "guidance_verified": (meta["guidance_probe"] == "present"),
            "guidance_verified_absent": (meta["guidance_probe"] == "absent"),
            "guidance_probe": meta["guidance_probe"],
            "starting_fixture_hash": before,
            "ending_fixture_hash": after,
            "output": meta["output"],
            "stderr": meta["stderr"],
            "stdout": meta.get("stdout", ""),
            "filesystem_snapshot_before": snap_before,
            "filesystem_snapshot_after": snap_after,
            "reason": meta["reason"],
        }

    try:
        for i in range(args.reps):
            # One pristine seed; one independent worker copy per condition.
            seed, seed_hash = materialize_fixture_seed(
                fx_src, ftype, source, invocation)
            evidence["canonical_seed_hash"] = HASH_PREFIX + seed_hash
            cond_fx = {name: _copy_seed(seed) for name in args.conditions}

            # Layer B activation: place the target/placebo skills in
            # ``.kilo/skills/<name>/`` inside each worker's workspace so Kilo
            # discovers them through its normal startup scan.  The baseline
            # receives no skill directory and therefore cannot discover the
            # target.  This is the mechanism that proves activation: not merely
            # that a file exists, but that the runtime's own discovery surface
            # was provided with the skill.
            for name in args.conditions:
                if name == "target":
                    materialize_skill_for_kilo(skill_dir, args.skill, cond_fx[name])
                elif name == "placebo" and placebo_dir:
                    materialize_skill_for_kilo(placebo_dir, args.placebo_skill,
                                               cond_fx[name])

            cond_meta = {}
            for name in args.conditions:
                guid = None
                if name == "target":
                    guid = guidance_src
                elif name == "placebo":
                    guid = placebo_dir
                cond_meta[name] = run_condition(name, natural_task,
                                                cond_fx[name], guid)
                # Detect whether the agent actually loaded the skill by reading
                # its SKILL.md from the .kilo/skills/ discovery path.
                if name == "target":
                    loads = extract_skill_loads(
                        cond_meta[name]["stdout"], args.skill, WORKSPACE_MOUNT)
                    cond_meta[name]["skill_kilo_path"] = os.path.join(
                        ".kilo", "skills", args.skill)
                    cond_meta[name]["skill_loaded"] = bool(loads)
                    cond_meta[name]["skill_loads"] = loads
                elif name == "placebo" and placebo_dir:
                    loads = extract_skill_loads(
                        cond_meta[name]["stdout"], args.placebo_skill,
                        WORKSPACE_MOUNT)
                    cond_meta[name]["skill_kilo_path"] = os.path.join(
                        ".kilo", "skills", args.placebo_skill)
                    cond_meta[name]["skill_loaded"] = bool(loads)
                    cond_meta[name]["skill_loads"] = loads
                else:
                    cond_meta[name]["skill_kilo_path"] = None
                    cond_meta[name]["skill_loaded"] = False
                    cond_meta[name]["skill_loads"] = []

            rep = {
                "rep": i + 1,
                "workspace_path": WORKSPACE_MOUNT,
                "guidance_mount_path": GUIDANCE_MOUNT,
                "canonical_seed_hash": HASH_PREFIX + seed_hash,
                "natural_task_hash": hashlib.sha256(
                    natural_task.encode()).hexdigest(),
                "natural_task_identical_across_conditions": True,
                "condition_workspace_ids": {
                    name: os.path.basename(cond_fx[name])
                    for name in args.conditions},
                "conditions": {},
                "distinct_containers": True,
                "distinct_sessions": True,
                "starting_fixture_hashes_match": True,
                "workspace_paths_differ": True,
            }
            for name in args.conditions:
                rep["conditions"][name] = cond_meta[name]
            # Cross-condition isolation facts (computed from actual captures).
            cids = [cond_meta[n]["container_id"] for n in args.conditions]
            sids = [cond_meta[n]["session_id"] for n in args.conditions]
            starts = [cond_meta[n]["starting_fixture_hash"] for n in args.conditions]
            wids = [os.path.basename(cond_fx[n]) for n in args.conditions]
            rep["distinct_containers"] = (
                all(cids) and len(set(cids)) == len(cids))
            rep["distinct_sessions"] = (
                all(sids) and len(set(sids)) == len(sids))
            rep["starting_fixture_hashes_match"] = (
                len(set(starts)) == 1 and starts[0] == HASH_PREFIX + seed_hash)
            rep["workspace_paths_differ"] = (len(set(wids)) == len(wids))
            evidence["repetitions"].append(rep)

            for name in args.conditions:
                shutil.rmtree(cond_fx[name], ignore_errors=True)
            shutil.rmtree(seed, ignore_errors=True)
    finally:
        shutil.rmtree(guidance_src, ignore_errors=True)
        if placebo_dir:
            shutil.rmtree(placebo_dir, ignore_errors=True)
        shutil.rmtree(SHARED_TMP, ignore_errors=True)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        json.dump(evidence, open(args.out, "w"), indent=2)
        print(f"wrote evidence: {args.out}")

    for r in evidence["repetitions"]:
        parts = []
        for name in args.conditions:
            cm = r["conditions"][name]
            parts.append(f"{name}[{cm['run_status']}] "
                         f"{str(cm['container_id'])[:12]} "
                         f"start={cm['starting_fixture_hash'][:10]}")
        print(f"rep{r['rep']}: {' '.join(parts)}")
        print(f"  distinct_containers={r['distinct_containers']} "
              f"distinct_sessions={r['distinct_sessions']} "
              f"start_match={r['starting_fixture_hashes_match']} "
              f"task_hash={r['natural_task_hash'][:10]}")
        for name in args.conditions:
            cm = r["conditions"][name]
            print(f"  {name}: output {len(cm['output'])} chars, "
                  f"after-hash {cm['ending_fixture_hash'][:10]}")


if __name__ == "__main__":
    main()
