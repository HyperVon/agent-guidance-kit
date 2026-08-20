#!/usr/bin/env python3
"""Execution-efficacy evaluation runner (Docker-isolated layer B).

POST-ACTIVATION MODEL
---------------------
Layer B answers: *once guidance is active, does that guidance improve task
execution?* It does NOT test whether Kilo's router decides to activate the
target/placebo skill — that belongs to routing evaluation (Layer A/C).
Therefore the evaluator ACTIVATES the guidance deterministically through
Kilo's own skill-command surface:

    kilo run --command "<skill>:skill" --dir /work/task "<natural task>"

  * ``--command <skill>:skill`` resolves against the project-level skill
    discovery location ``.kilo/skills/<skill>/SKILL.md`` in the worker's
    working directory. If the skill is not discovered there, ``kilo run``
    EXITS NON-ZERO with "Command not found" and the available commands —
    so a successful (RC=0) run is machine-verifiable proof that the skill
    was discovered and its body injected into model context at session
    start.
  * The SAME mechanism activates the target and the placebo condition.
  * The baseline runs WITHOUT ``--command`` and receives no ``.kilo/skills``
    tree at all: no guidance enters its context.

For each repetition, fresh, independent Docker containers — one per condition.
The supported conditions are:

  * ``target``: an independent writable COPY of the pristine task fixture plus
    the target ``SKILL.md`` (+ ``references/``) at
    ``.kilo/skills/<target>/`` inside the workspace, activated via
    ``--command <target>:skill``; the worker receives ONLY the natural task.
  * ``baseline`` (harness/default): a SEPARATE independent COPY of the same
    task fixture, NO evaluator-owned ``.kilo/skills`` tree, NO ``--command``;
    the SAME natural
    task.
  * ``placebo`` (optional): a SEPARATE independent COPY of the same task
    fixture plus IRRELEVANT, similarly-sized guidance (a different skill) at
    ``.kilo/skills/<placebo>/``, activated via ``--command <placebo>:skill`` —
    the EXACT SAME mechanism as the target; the SAME natural task.

TREATMENT-BOUNDARY CONTRACT (see skills/skill-evaluation/SKILL.md and
docs/evaluations/RUNBOOK.md):

  * The natural user task text is BYTE-IDENTICAL across all conditions. The
    target/baseline/placebo workers must not be told that an evaluation is
    happening, which condition they are in, the target skill's canonical name,
    the expected outcome, the scoring rubric, or that another condition exists.
  * Layer B is a POST-ACTIVATION experiment: it measures whether guidance, once
    active, improves task execution. It does NOT test whether Kilo's router
    decides to activate a skill (that is Layer A/C routing). The evaluator
    ACTIVATES the target/placebo guidance deterministically through
    ``kilo run --command "<skill>:skill"`` — Kilo's own skill-command
    invocation path, which injects the full SKILL.md body into the worker
    context as the command template. The same mechanism is used for the target
    and the placebo; the baseline runs without ``--command`` and receives no
    skill tree.
  * The worker-visible prompt is the natural task only. ``--command`` is a
    runtime/harness-level activation, identical for target and placebo, and is
    NOT part of the user-visible prompt text.
  * Guidance exists in a worker's environment ONLY through its discovery tree
    ``.kilo/skills/<name>/`` (which is what ``--command`` activates). There is
    no separate neutral guidance mount: a second, un-activated copy of the
    guidance on disk would conflate "guidance active" with "guidance present
    and readable", which is exactly the confound this runner removes.
  * The placebo condition receives an irrelevant skill's guidance through the
    SAME activation mechanism, so "presence of extra procedural guidance" is
    controlled for.

TASK STATE vs RUNTIME TREATMENT STATE (see docs/evaluations/RUNBOOK.md):

  * **Task state** — the actual thing the worker works on (source, docs,
    tests, fixture content, git state). It MUST be byte-identical across
    conditions and equal to the frozen fixture hash.
  * **Runtime treatment state** — what the evaluator adds to deliver the
    treatment (``.kilo/skills/`` discovery trees, injected guidance). It is
    INTENTIONALLY different between target and placebo and absent in baseline.

  The runner therefore records, per condition, BOTH:

    * ``starting_task_hash`` / ``ending_task_hash`` — computed by
    ``eval_hashing.hash_task_workspace`` which EXCLUDES the explicit
    runtime treatment paths (``RUNTIME_TREATMENT_PATHS``, default
    ``(".kilo/skills",)``). These prove the task state was identical before the run
      and record what each worker actually changed.
    * ``starting_full_hash`` / ``ending_full_hash`` — computed by
      ``eval_hashing.hash_workspace`` over EVERYTHING (treatment included),
      proving the raw condition copies differ exactly where treatment differs.

  The runtime treatment itself is recorded separately per condition:
  ``activation_mechanism``, ``skill_command``, ``skill_kilo_path``,
  ``skill_content_hash`` (frozen discovery-tree hash), and — when the model
  ALSO issues a native ``skill`` tool call — the parsed ``activation_events``
  (see ``extract_activation_events``).

Crucial correctness properties (see docs/evaluations/isolation-protocol.md):

  * The conditions never share a mutable fixture. Each gets its own copy made
    from one pristine seed; we verify all copies hash-identically BEFORE the
    run (TASK-state hash) and record starting and ending task hashes plus the
    full-filesystem hashes separately.
  * Generator source (e.g. ``setup.sh``) is evaluator-only. It is run under a
    sanitized environment by ``eval_hashing.materialize_fixture_seed`` and then
    STRIPPED from the seed the worker sees.
  * A failed Docker/Kilo invocation (non-zero return code, missing container,
    unparseable/empty model output, missing session) is recorded as
    ``run_status="failed"`` and can never masquerade as valid evidence. The
    validator rejects any repetition whose worker failed.
  * The activation boundary is verified INSIDE the container by a probe that
    checks the discovery path ``.kilo/skills/<name>/SKILL.md`` presence AND
    content-hash match (target/placebo) / the absence of any
    ``.kilo/skills`` tree (baseline).
  * Activation is recorded per condition: ``activation_mechanism``
    (``"kilo-command-skill"`` for target/placebo, ``"none"`` for baseline),
    the resolved skill-command name, the skill discovery path, and the frozen
    skill content hash. If the model ALSO issues a native ``skill`` tool call,
    the parsed activation events are recorded as ``skill_tool_invoked`` /
    ``activation_events`` (see ``extract_activation_events``).

All workers use the same pinned, anonymous free model (cost-safety gate), so
the only systematic difference between conditions is the activated guidance.

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
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_hashing import (hash_workspace, hash_task_workspace,
                           materialize_fixture_seed, HASH_PREFIX)

IMAGE = "kilo-eval:local"
# The evaluation runs on a pinned, anonymous FREE model by default. This is a
# COST-SAFETY gate (accidental spend protection), NOT a scientific requirement:
# The target, baseline, and placebo conditions simply must use the identical
# resolved model/runtime. Pass
# --allow-paid-model to use a non-free model deliberately.
DEFAULT_MODEL = "kilo/tencent/hy3:free"

WORKSPACE_MOUNT = "/work/task"

# Evaluator-controlled runtime treatment paths inside the worker workspace.
# These are excluded from the TASK-state hash (they are intentionally different
# between target/placebo and absent in baseline) but recorded separately as
# runtime-treatment evidence. The evaluator owns only this explicit discovery
# tree; other project-level ``.kilo`` config remains task state.
RUNTIME_TREATMENT_PATHS = (".kilo/skills",)

# Docker Desktop on macOS only bind-mounts paths under its shared roots (the
# project, which lives under /Users). system temp dirs like /var/folders are NOT
# shared and silently appear empty inside the container. Materialize anything that
# gets mounted (fixtures, prompt files) under this repo-relative dir.
SHARED_TMP = os.path.join(ROOT, ".docker-tmp")

ACTIVATION_MECHANISM = "kilo-command-skill"

# Kilo expands these placeholders when a command template is invoked. A skill
# containing one cannot be evaluated as unchanged guidance through ``:skill``:
# the command surface would substitute evaluator/runtime arguments into the
# body before the model sees it. Fail closed before any worker is launched.
KILO_COMMAND_PLACEHOLDER_RE = re.compile(r"\$(?:ARGUMENTS|[0-9]+)\b")

# Kilo's exported session stores message roles under ``messages[].info.role``
# (with a top-level ``role`` fallback for compatible exports). Only user-role
# text is evidence that the command template entered user context; assistant
# echoes or tool output must not prove activation.
CONTEXT_PROBE_NODE_SCRIPT = (
    'const fs=require("fs"); '
    'let data; try { data=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); } '
    'catch (_) { process.stdout.write("absent"); process.exit(0); } '
    'const skill=fs.readFileSync(process.argv[2],"utf8"); '
    'const body=skill.replace(/^---\\r?\\n[\\s\\S]*?\\r?\\n---\\r?\\n?/,"").trim(); '
    'const texts=(data.messages||[]).filter(m=>{const role=(m.info&&m.info.role)||m.role; '
    'return role==="user";}).flatMap(m=>(m.parts||[]).filter(p=>p.type==="text").map(p=>p.text||"")); '
    'process.stdout.write(texts.some(t=>t.includes(body))?"present":"absent");'
)


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


def materialize_kilo_skill(source_skill_dir, skill_name, workspace):
    """Place a skill at Kilo's project-level discovery location.

    Creates ``<workspace>/.kilo/skills/<skill-name>/SKILL.md`` (+ ``references/``
    when present) so Kilo scans it at session start and exposes it to the model
    via the ``skill`` tool / ``<skill-name>:skill`` skill-command surface. This
    discovery tree IS the runtime treatment: ``kilo run --command
    "<skill-name>:skill"`` activates exactly this file's content.

    ``source_skill_dir`` must be the canonical repository skill directory —
    the directory that directly contains the ``SKILL.md`` to copy
    (``skills/<name>/``). It must NOT be a staged neutral bundle shaped as
    ``<dir>/task/SKILL.md``: that shape belongs to the old neutral mount which
    this runner no longer uses (an un-activated guidance copy on disk would
    conflate "guidance active" with "guidance present").

    Returns the created ``.kilo/skills/<name>`` directory.
    """
    kilo_skills = os.path.join(workspace, ".kilo", "skills", skill_name)
    os.makedirs(kilo_skills, exist_ok=True)
    skill_md = os.path.join(source_skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        raise ValueError(f"skill source missing SKILL.md: {source_skill_dir}")
    shutil.copy(skill_md, os.path.join(kilo_skills, "SKILL.md"))
    refs = os.path.join(source_skill_dir, "references")
    if os.path.isdir(refs):
        shutil.copytree(refs, os.path.join(kilo_skills, "references"),
                        dirs_exist_ok=True)
    return kilo_skills


def kilo_command_placeholders(skill_dir):
    """Return Kilo command-template placeholders found in ``SKILL.md``."""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        raise ValueError(f"skill source missing SKILL.md: {skill_dir}")
    with open(skill_md, encoding="utf-8") as fh:
        return sorted(set(KILO_COMMAND_PLACEHOLDER_RE.findall(fh.read())))


def validate_activation_sources(target_dir, target_skill, conditions,
                                placebo_dir=None, placebo_skill=None):
    """Reject command-template skills before Docker/Kilo worker launch.

    Kilo command placeholders are intentionally treated as unsafe for this
    post-activation protocol. The canonical repository files are only read;
    this check never rewrites or stages a sanitized copy.
    """
    sources = [("target", target_dir, target_skill)]
    if "placebo" in conditions:
        sources.append(("placebo", placebo_dir, placebo_skill))
    violations = []
    for label, skill_dir, skill_name in sources:
        if not skill_dir or not skill_name:
            continue
        tokens = kilo_command_placeholders(skill_dir)
        if tokens:
            violations.append(
                f"{label} skill {skill_name!r} contains Kilo command "
                f"placeholder(s) {', '.join(tokens)} in SKILL.md")
    if violations:
        raise ValueError(
            "refusing :skill activation because command placeholders would "
            "change the guidance body before model context: "
            + "; ".join(violations))


def validate_materialized_seed_hash(seed_task_hash, expected_fixture_hash):
    """Fail closed before worker launch when the seed is not the frozen task."""
    if not expected_fixture_hash:
        raise ValueError("refusing to launch workers: fixture has no frozen "
                         "worker-visible hash")
    if seed_task_hash != expected_fixture_hash:
        raise ValueError(
            "refusing to launch workers: materialized seed task hash "
            f"{seed_task_hash!r} does not match frozen fixture hash "
            f"{expected_fixture_hash!r}")


def skill_tree_hash(skill_dir):
    """Deterministic hash of a skill's DISCOVERY TREE: exactly ``SKILL.md`` +
    ``references/**``, sorted by relative path, each file hashed by content.

    This is precisely the set of files ``materialize_kilo_skill`` copies into a
    worker's ``.kilo/skills/<name>/`` tree — NOT the whole repository skill
    directory (which also contains ``evals/`` fixtures that must never reach a
    worker). Hashing the canonical ``skills/<name>/`` dir with this function
    yields the same value as hashing the materialized workspace tree, so the
    frozen runtime-guidance artifact is byte-comparable.
    """
    if not os.path.isdir(skill_dir):
        return None
    if not os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
        return None
    h = hashlib.sha256()
    rels = []
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if os.path.exists(skill_md):
        rels.append("SKILL.md")
    refs = os.path.join(skill_dir, "references")
    if os.path.isdir(refs):
        for root, _, names in os.walk(refs):
            for n in names:
                full = os.path.join(root, n)
                if os.path.islink(full):
                    continue
                rels.append(os.path.relpath(full, skill_dir))
    for rel in sorted(rels):
        full = os.path.join(skill_dir, rel)
        fh = hashlib.sha256(open(full, "rb").read()).hexdigest()
        h.update((rel + ":" + fh + "\n").encode())
    return HASH_PREFIX + h.hexdigest()


def extract_activation_events(stdout, skill_name):
    """Parse REAL Kilo JSONL activation evidence for a skill.

    Kilo's native activation event is a ``tool_use`` record whose ``part`` is a
    tool call of the dedicated ``skill`` tool. This is the actual structure
    emitted by ``kilo run --format json`` (verified against the installed CLI):

    .. code-block:: json

        {"type": "tool_use", "timestamp": 1787124430157,
         "sessionID": "ses_...",
         "part": {"type": "tool", "tool": "skill", "callID": "chatcmpl-...",
                  "state": {"status": "completed",
                            "input": {"name": "probe-skill"},
                            "output": "<skill_content name=\"probe-skill\">...",
                            "title": "Loaded skill: probe-skill",
                            "metadata": {"name": "probe-skill",
                                         "dir": "/work/task/.kilo/skills/probe-skill",
                                         "truncated": false,
                                         "approval": {...}},
                            "time": {"start": ..., "end": ...}}}}

    A normal filesystem ``read`` of ``.kilo/skills/<name>/SKILL.md`` is NOT
    activation: the guidance only enters context through the ``skill`` tool or
    an explicit skill-command invocation. We therefore parse the dedicated
    tool event and ignore arbitrary file reads.

    Layer B's PRIMARY activation is the evaluator-forced ``--command
    <skill>:skill`` invocation (see the module docstring); those runs do not
    emit a ``tool_use`` event. The events parsed here are the model's OWN
    native ``skill`` invocations — supplementary evidence recorded when they
    occur.

    Only completed calls with a non-empty ``<skill_content>`` result count: a
    running/error call or a malformed event does not prove that guidance entered
    context. Returns a list of event dicts (one per detected activation):
    ``{"tool": "skill", "skill_name": ..., "timestamp": ...,
      "session_id": ..., "title": ..., "dir": ...}``. Events whose recorded
    skill name differs from ``skill_name`` are NOT counted (another skill's
    activation must not count as this skill's).
    """
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") != "tool_use":
            continue
        part = obj.get("part") or {}
        if part.get("tool") != "skill":
            continue
        state = part.get("state") or {}
        if state.get("status") != "completed":
            continue
        inp = state.get("input") or {}
        name = inp.get("name")
        if not name or name != skill_name:
            continue
        output = state.get("output")
        opening = f'<skill_content name="{skill_name}">'
        closing = "</skill_content>"
        if not isinstance(output, str) or opening not in output:
            continue
        body_start = output.find(opening) + len(opening)
        body_end = output.find(closing, body_start)
        if body_end < 0 or not output[body_start:body_end].strip():
            continue
        session_id = obj.get("sessionID")
        if not isinstance(session_id, str) or not session_id:
            continue
        metadata = state.get("metadata") or {}
        if metadata.get("name") not in (None, skill_name):
            continue
        events.append({
            "tool": "skill",
            "skill_name": name,
            "timestamp": obj.get("timestamp"),
            "session_id": session_id,
            "title": state.get("title"),
            "dir": metadata.get("dir"),
        })
    return events


def skill_command_name(skill_name):
    """The namespaced skill-command form Kilo resolves for ``--command``.

    Skills are surfaced as commands with ``source: "skill"`` and resolve via
    the ``<name>:skill`` namespaced form (see Kilo's command registry:
    ``/name:skill`` always resolves to the skill). An unresolvable command
    makes ``kilo run`` exit non-zero with "Command not found", so RC=0 is
    machine-verifiable proof the skill command resolved.
    """
    return f"{skill_name}:skill"


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


def run_container(image, model, prompt, fixture_dir, skill_command=None,
                  skill_md_hex=None, skill_probe_path=None):
    """Run one worker container; return structured execution metadata.

    {
      "returncode": int|None, "stdout": str, "stderr": str,
      "container_id": str|None, "session_id": str|None,
      "output": str, "skill_probe": "present"|"absent"|"hash_mismatch"|None,
      "status": "success"|"failed", "reason": str|None
    }

        The worker-visible prompt is the natural task ONLY — no skill name, no
    condition label, no evaluation mention. Guidance (if any) is ACTIVATED
    through ``--command <skill>:skill``, which resolves against the
    ``.kilo/skills/`` discovery tree in the worker's own workspace
    (``fixture_dir`` mounted at /work/task); there is no separate guidance
    mount.

    A run is successful ONLY if: docker/Kilo returned 0, a container id exists,
    the output was parsed, a session id exists, and model text was produced.
    An unresolvable skill command makes kilo exit non-zero ("Command not
    found"), so a successful run implies the skill command resolved and the
    guidance body entered context at session start.
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
        # ENTRYPOINT is `kilo`; override to bash so we can run kilo then a boundary
        # probe that records whether the activation discovery path is present and
        # hash-matched (target/placebo) or absent (baseline).
        command_arg = f"--command {skill_command}" if skill_command else ""
        if skill_command:
            probe = skill_probe_path or f"{WORKSPACE_MOUNT}/.kilo/skills"
            # Probe the exact SKILL.md: presence + content hash match.
            probe_cmd = (
                f"if [ -e \"{probe}\" ]; then "
                f"A=$(sha256sum \"{probe}\" | cut -d' ' -f1); "
                f"if [ \"$A\" = \"{skill_md_hex}\" ]; then "
                "echo SKILL_PROBE:present; "
                f"else echo SKILL_PROBE:hash_mismatch; fi; "
                "else echo SKILL_PROBE:absent; fi"
            )
        else:
            # Baseline: any .kilo/skills tree at all is a treatment leak.
            probe_cmd = (f"if [ -e \"{WORKSPACE_MOUNT}/.kilo/skills\" ]; then "
                         "echo SKILL_PROBE:present; "
                         "else echo SKILL_PROBE:absent; fi")
        if skill_command:
            # ``--command <name>:skill`` is a controlled Kilo command, not a
            # native model-issued ``skill`` tool call. Export the completed
            # session and verify that Kilo serialized the complete skill body
            # into the user-context message. This is stronger evidence than
            # command resolution or filesystem presence alone and avoids
            # storing the guidance body in the evidence file.
            context_probe_cmd = (
                "SKILL_CONTEXT_PROBE=unavailable\n"
                "if [ \"$KILO_RC\" -eq 0 ]; then\n"
                "  SESSION=$(node -e 'const fs=require(\"fs\"); "
                "for (const line of fs.readFileSync(process.argv[1],\"utf8\")"
                ".split(/\\r?\\n/)) { try { const obj=JSON.parse(line); "
                "if (typeof obj.sessionID===\"string\" && obj.sessionID) "
                "{ process.stdout.write(obj.sessionID); break; } } catch (_) {} }' "
                "/tmp/kilo.out)\n"
                "  if [ -n \"$SESSION\" ]; then\n"
                "    kilo export \"$SESSION\" > /tmp/kilo.export "
                "2>/tmp/kilo-export.err\n"
                "    if [ $? -eq 0 ]; then\n"
                f"      node -e '{CONTEXT_PROBE_NODE_SCRIPT}' "
                f"/tmp/kilo.export \"{probe}\" > /tmp/kilo-context-status\n"
                "      SKILL_CONTEXT_PROBE=$(cat /tmp/kilo-context-status)\n"
                "    fi\n"
                "  fi\n"
                "fi\n"
                "echo SKILL_CONTEXT_PROBE:$SKILL_CONTEXT_PROBE\n"
            )
        else:
            context_probe_cmd = "echo SKILL_CONTEXT_PROBE:none\n"
        script = (
            "set +e\n"
            f"kilo run --model {model} --variant high --format json --pure --auto "
            f"{command_arg} "
            f"--dir {WORKSPACE_MOUNT} \"$(cat /work/prompt.txt)\" < /dev/null "
            "> /tmp/kilo.out 2> /tmp/kilo.err\n"
            "KILO_RC=$?\n"
            "cat /tmp/kilo.out\n"
            "cat /tmp/kilo.err >&2\n"
            f"{context_probe_cmd}"
            f"{probe_cmd}\n"
            "exit $KILO_RC\n"
        )
        cmd += ["--entrypoint", "bash", image, "-c", script]

        meta = {"returncode": None, "stdout": "", "stderr": "",
                "container_id": None, "session_id": None, "output": "",
                "skill_probe": None, "skill_context_probe": None,
                "status": "failed", "reason": None}
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
        context_probe = None
        for line in stdout.splitlines():
            if line.strip().startswith("SKILL_PROBE:"):
                probe = line.strip().split(":", 1)[1]
            if line.strip().startswith("SKILL_CONTEXT_PROBE:"):
                context_probe = line.strip().split(":", 1)[1]

        meta.update({"returncode": proc.returncode, "stdout": stdout,
                     "stderr": stderr, "container_id": cid, "session_id": session,
                     "output": text, "skill_probe": probe,
                     "skill_context_probe": context_probe})

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


def finalize_condition(name, meta, task_before, task_after,
                       full_before, full_after, snapshot_before,
                       snapshot_after, activation):
    """Assemble one condition's evidence dict.

    ``activation`` is None for the baseline (no treatment) or a dict with:
    ``skill_name``, ``skill_command``, ``skill_kilo_path``,
    ``skill_content_hash``. ``meta`` is the ``run_container``-shaped dict
    (the mockable subprocess boundary).
    """
    cond = {
        "container_id": meta["container_id"],
        "session_id": meta["session_id"],
        "run_status": meta["status"],
        "returncode": meta["returncode"],
        "starting_task_hash": task_before,
        "ending_task_hash": task_after,
        "starting_full_hash": full_before,
        "ending_full_hash": full_after,
        "skill_probe": meta["skill_probe"],
        "skill_context_probe": meta.get("skill_context_probe"),
        "output": meta["output"],
        "stderr": meta["stderr"],
        "stdout": meta.get("stdout", ""),
        "filesystem_snapshot_before": snapshot_before,
        "filesystem_snapshot_after": snapshot_after,
        "reason": meta["reason"],
    }
    if activation:
        events = extract_activation_events(
            meta.get("stdout", ""), activation["skill_name"])
        cond.update({
            "activation_mechanism": ACTIVATION_MECHANISM,
            "skill_command": activation["skill_command"],
            "skill_kilo_path": activation["skill_kilo_path"],
            "skill_content_hash": activation["skill_content_hash"],
            "skill_tool_invoked": bool(events),
            "activation_events": events,
        })
    else:
        cond.update({
            "activation_mechanism": "none",
            "skill_command": None,
            "skill_kilo_path": None,
            "skill_content_hash": None,
            "skill_tool_invoked": False,
            "activation_events": [],
        })
    return cond


def run_repetition(rep_index, conditions, natural_task, seed_dir,
                   target_skill, target_dir,
                   placebo_skill, placebo_dir,
                   model, image, run_fn):
    """Run one full repetition: seed copies -> treatment placement -> workers ->
    evidence. ``run_fn`` is the container boundary (mockable); it must have the
    ``run_container`` signature.

    Returns ``(rep, canonical_task_seed_hash, workspace_paths)`` where
    ``workspace_paths`` maps condition name to the FULL workspace path (used
    for cleanup; the evidence itself records only sanitized basenames).
    Workspace lifecycle (creation and cleanup) is owned by the caller.
    """
    validate_activation_sources(target_dir, target_skill, conditions,
                                placebo_dir, placebo_skill)
    canonical = HASH_PREFIX + hash_task_workspace(seed_dir,
                                                  RUNTIME_TREATMENT_PATHS)
    # The pristine seed must not already contain the evaluator-owned discovery
    # tree. Other project-level .kilo config is legitimate task state and remains
    # included in the task hash.
    collisions = [p for p in RUNTIME_TREATMENT_PATHS
                  if os.path.exists(os.path.join(seed_dir, p))]
    if collisions:
        raise ValueError(
            f"pristine seed contains evaluator runtime treatment paths "
            f"({collisions}); a user fixture must not ship those paths")

    cond_fx = {name: _copy_seed(seed_dir) for name in conditions}

    # Layer B controlled post-activation: place the target/placebo skills at
    # Kilo's project-level discovery location ``.kilo/skills/<name>/`` inside
    # each worker's workspace, and record the frozen discovery-tree hash. The
    # baseline receives no evaluator-owned ``.kilo/skills`` tree and therefore
    # cannot discover (or activate) any skill. Activation itself happens
    # deterministically via
    # ``kilo run --command <name>:skill`` (see run_container), never via the
    # model's routing choice.
    activation = {}
    for name in conditions:
        if name == "target":
            tree = materialize_kilo_skill(target_dir, target_skill, cond_fx[name])
            content_hash = skill_tree_hash(tree)
            if content_hash is None:
                raise ValueError("target skill tree missing after materialization")
            activation[name] = {
                "skill_name": target_skill,
                "skill_command": skill_command_name(target_skill),
                "skill_kilo_path": os.path.join(".kilo", "skills", target_skill),
                "skill_content_hash": content_hash,
            }
        elif name == "placebo" and placebo_dir:
            tree = materialize_kilo_skill(placebo_dir, placebo_skill,
                                          cond_fx[name])
            content_hash = skill_tree_hash(tree)
            if content_hash is None:
                raise ValueError("placebo skill tree missing after materialization")
            activation[name] = {
                "skill_name": placebo_skill,
                "skill_command": skill_command_name(placebo_skill),
                "skill_kilo_path": os.path.join(".kilo", "skills", placebo_skill),
                "skill_content_hash": content_hash,
            }

    cond_meta = {}
    for name in conditions:
        act = activation.get(name)
        workspace = cond_fx[name]
        if act:
            skill_md_hex = _skill_md_hex(workspace, act["skill_name"])
            run_args = {
                "image": image,
                "model": model,
                "prompt": natural_task,
                "fixture_dir": workspace,
                "skill_command": act["skill_command"],
                "skill_md_hex": skill_md_hex,
                "skill_probe_path": os.path.join(
                    WORKSPACE_MOUNT, ".kilo", "skills",
                    act["skill_name"], "SKILL.md"),
            }
        else:
            run_args = {
                "image": image,
                "model": model,
                "prompt": natural_task,
                "fixture_dir": workspace,
                "skill_command": None,
                "skill_md_hex": None,
                "skill_probe_path": None,
            }
        task_before = HASH_PREFIX + hash_task_workspace(
            workspace, RUNTIME_TREATMENT_PATHS)
        full_before = HASH_PREFIX + hash_workspace(workspace)
        snapshot_before = _snapshot(workspace)
        meta = run_fn(**run_args)
        task_after = HASH_PREFIX + hash_task_workspace(
            workspace, RUNTIME_TREATMENT_PATHS)
        full_after = HASH_PREFIX + hash_workspace(workspace)
        snapshot_after = _snapshot(workspace)
        cond = finalize_condition(name, meta, task_before, task_after,
                                  full_before, full_after, snapshot_before,
                                  snapshot_after, act)
        cond_meta[name] = cond

    rep = {
        "rep": rep_index + 1,
        "workspace_path": WORKSPACE_MOUNT,
        "canonical_task_seed_hash": canonical,
        "natural_task_hash": hashlib.sha256(
            natural_task.encode()).hexdigest(),
        "natural_task_identical_across_conditions": True,
        "condition_workspace_ids": {
            name: os.path.basename(cond_fx[name]) for name in conditions},
        "conditions": {},
        "distinct_containers": True,
        "distinct_sessions": True,
        "starting_task_hashes_match": True,
        "task_hashes_match_canonical_seed": True,
        "workspace_paths_differ": True,
    }
    for name in conditions:
        rep["conditions"][name] = cond_meta[name]

    # Cross-condition isolation facts (computed from actual captures).
    cids = [cond_meta[n]["container_id"] for n in conditions]
    sids = [cond_meta[n]["session_id"] for n in conditions]
    starts = [cond_meta[n]["starting_task_hash"] for n in conditions]
    wids = [os.path.basename(cond_fx[n]) for n in conditions]
    rep["distinct_containers"] = (all(cids) and len(set(cids)) == len(cids))
    rep["distinct_sessions"] = (all(sids) and len(set(sids)) == len(sids))
    rep["starting_task_hashes_match"] = (
        len(set(starts)) == 1 and starts[0] == canonical)
    rep["task_hashes_match_canonical_seed"] = all(s == canonical for s in starts)
    rep["workspace_paths_differ"] = (len(set(wids)) == len(wids))
    return rep, canonical, cond_fx


def _skill_md_hex(workspace, skill_name):
    """sha256 hex of the SKILL.md the worker will actually have at discovery."""
    p = os.path.join(workspace, ".kilo", "skills", skill_name, "SKILL.md")
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


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

    if not os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
        print(f"target skill dir missing SKILL.md: {skill_dir}", file=sys.stderr)
        sys.exit(2)

    placebo_dir = None
    placebo_tree_hash = None
    if "placebo" in args.conditions:
        pdir = os.path.join(ROOT, "skills", args.placebo_skill)
        if not os.path.exists(os.path.join(pdir, "SKILL.md")):
            print(f"placebo skill dir missing: {pdir}", file=sys.stderr)
            sys.exit(2)
        placebo_dir = pdir
        placebo_tree_hash = skill_tree_hash(pdir)

    try:
        validate_activation_sources(skill_dir, args.skill, args.conditions,
                                   placebo_dir, args.placebo_skill)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    runtime = _verify_runtime(args.image, args.model)

    # The natural task is the ONLY worker-visible prompt text, byte-identical
    # across all conditions. Nothing here names the skill, the condition, the
    # case, or the evaluation.
    natural_task = case["prompt"]
    target_tree_hash = skill_tree_hash(skill_dir)
    if target_tree_hash is None:
        print(f"target skill dir missing SKILL.md: {skill_dir}", file=sys.stderr)
        sys.exit(2)

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
        "activation_mechanism": ACTIVATION_MECHANISM,
        "runtime_treatment_paths": list(RUNTIME_TREATMENT_PATHS),
        "target_skill_kilo_path": os.path.join(".kilo", "skills", args.skill),
        "target_skill_content_hash": target_tree_hash,
        "placebo_skill_kilo_path": (
            os.path.join(".kilo", "skills", args.placebo_skill)
            if "placebo" in args.conditions else None
        ),
        "placebo_skill_content_hash": placebo_tree_hash,
        "expected_fixture_hash": expected_fixture_hash,
        "fixture_source_path": os.path.relpath(evals_path, ROOT),
        "fixture_path": os.path.normpath(os.path.relpath(fx_src, ROOT)),
        "fixture_source_hash": HASH_PREFIX + hashlib.sha256(
            open(evals_path, "rb").read()).hexdigest(),
        "target_skill_source_path": os.path.join("skills", args.skill),
        "canonical_task_seed_hash": None,  # filled in after the first seed is materialized
        "conditions": list(args.conditions),
        "placebo_skill": args.placebo_skill if "placebo" in args.conditions else None,
        "repetitions": [],
    }

    try:
        for i in range(args.reps):
            # One pristine seed; one independent worker copy per condition.
            seed, _ = materialize_fixture_seed(
                fx_src, ftype, source, invocation)
            seed_task_hash = HASH_PREFIX + hash_task_workspace(
                seed, RUNTIME_TREATMENT_PATHS)
            try:
                validate_materialized_seed_hash(seed_task_hash,
                                                expected_fixture_hash)
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                sys.exit(2)
            rep, canonical, workspace_paths = run_repetition(
                i, args.conditions, natural_task, seed,
                args.skill, skill_dir,
                args.placebo_skill if "placebo" in args.conditions else None,
                placebo_dir,
                args.model, args.image, run_container)
            evidence["canonical_task_seed_hash"] = canonical
            evidence["repetitions"].append(rep)

            for name in args.conditions:
                shutil.rmtree(workspace_paths.get(name, ""), ignore_errors=True)
            shutil.rmtree(seed, ignore_errors=True)
    finally:
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
                         f"task={cm['starting_task_hash'][:10]}")
        print(f"rep{r['rep']}: {' '.join(parts)}")
        print(f"  distinct_containers={r['distinct_containers']} "
              f"distinct_sessions={r['distinct_sessions']} "
              f"start_match={r['starting_task_hashes_match']} "
              f"task_hash={r['natural_task_hash'][:10]}")
        for name in args.conditions:
            cm = r["conditions"][name]
            print(f"  {name}: output {len(cm['output'])} chars, "
                  f"activation={cm['activation_mechanism']} "
                  f"probe={cm['skill_probe']} "
                  f"after-task-hash {cm['ending_task_hash'][:10]}")


if __name__ == "__main__":
    main()
