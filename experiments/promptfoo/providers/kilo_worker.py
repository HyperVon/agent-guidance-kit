"""Layer B post-activation execution provider for Promptfoo.

Per test row this provider materializes an independent fresh host workspace
from the pristine fixture seed, installs the runtime treatment
(``.kilo/skills/<skill>/``) for target/placebo conditions, activates guidance
through Kilo's own skill-command surface (``kilo run --command <skill>:skill``)
exactly like the existing evaluator, runs the natural task, and records
task-state hashes plus activation provenance.

Conditions:
    target   fixture copy + target skill tree + --command <target>:skill
    placebo  fixture copy + irrelevant skill tree + --command <placebo>:skill
    baseline fixture copy only, no skill tree, no --command

The worker-visible prompt is the natural task text, byte-identical across
conditions. Activation is FORCED (post-activation experiment); native harness
routing (Layer C) is not claimed.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from experiments.promptfoo.lib import hashing, workspace  # noqa: E402

from scripts import eval_hashing  # noqa: E402

DEFAULT_MODEL = "kilo/tencent/hy3:free"
_KILO_SESSION_RE = re.compile(r'"sessionID":"(ses_[^"]+)"')


IGNORED_VERIFICATION_ARTIFACTS = ("__pycache__", ".pytest_cache",
                                  ".agk-pf-state.json", ".agk-pf-start")


def _ignored_rel(rel):
    parts = rel.split("/")
    return any(part in IGNORED_VERIFICATION_ARTIFACTS for part in parts[:-1]) \
        or parts[-1] in IGNORED_VERIFICATION_ARTIFACTS


def _task_manifest(ws_path):
    """relpath -> sha256 for every task-state file (runtime treatment paths
    and transient verification artifacts excluded)."""
    import hashlib as _hashlib
    manifest = {}
    for root, _dirs, files in os.walk(ws_path):
        rel_root = os.path.relpath(root, ws_path).replace(os.sep, "/")
        for name in files:
            rel = name if rel_root == "." else f"{rel_root}/{name}"
            if rel.startswith(".kilo/") or _ignored_rel(rel):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, "rb") as f:
                    manifest[rel] = _hashlib.sha256(f.read()).hexdigest()
            except OSError:
                continue
    return manifest


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


def _materialize_workspace(variables, cfg):
    case_id = variables["case_id"]
    condition = variables["condition"]
    rep = variables.get("rep", 1)
    ws_path = variables.get("workspace") or workspace.workspace_path(
        os.environ.get("AGK_PF_RUN_ID", "exec"), case_id, condition, rep)
    if os.path.exists(ws_path):
        shutil.rmtree(ws_path, ignore_errors=True)
    os.makedirs(os.path.dirname(ws_path), exist_ok=True)

    fixture_rel = variables.get("fixture_path")
    seed_dir, seed_hash = eval_hashing.materialize_fixture_seed(
        os.path.join(_REPO_ROOT, fixture_rel),
        variables.get("fixture_type", "committed"),
        source=variables.get("fixture_source", "setup.sh"),
        invocation=variables.get("fixture_invocation", "bash setup.sh"),
    )
    try:
        dest = shutil.copytree(seed_dir, ws_path, symlinks=True,
                               dirs_exist_ok=True)
    finally:
        shutil.rmtree(seed_dir, ignore_errors=True)
    return dest, seed_hash


def _install_treatment(ws_path, variables, cfg=None):
    """Install the .kilo/skills tree; returns (skill_name, content_hash)."""
    skill_name = variables["skill_name"]
    revision_sha = (variables.get("skill_revision_sha")
                    or (cfg or {}).get("skill_revision_sha"))
    if revision_sha:
        skill_dir, content_hash = workspace.materialize_skill_from_revision(
            revision_sha, skill_name)
    else:
        skill_dir = os.path.join(_REPO_ROOT, "skills", skill_name)
        content_hash = hashing.file_hash(
            os.path.join(skill_dir, "SKILL.md"))
    try:
        installed_hash = workspace.install_skill_tree(
            ws_path, skill_name, skill_dir)
    finally:
        if revision_sha:
            shutil.rmtree(os.path.dirname(skill_dir), ignore_errors=True)
    return skill_name, installed_hash or content_hash


def _run_kilo(task, model, ws_path, skill_command, timeout_s):
    cmd = ["kilo", "run", "--model", model, "--variant", "high",
           "--format", "json", "--auto"]
    if skill_command:
        cmd += ["--command", skill_command]
    cmd += ["--pure", task]
    child_env = dict(os.environ, PWD=ws_path)
    proc = subprocess.run(cmd, cwd=ws_path, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          timeout=timeout_s, env=child_env)
    return proc


def call_api(prompt, options, context):
    cfg = options.get("config", {})
    model = cfg.get("model", DEFAULT_MODEL)
    timeout_s = int(cfg.get("timeout_s", 900))
    v = context.get("vars", {})

    state = {
        "case_id": v.get("case_id"),
        "condition": v.get("condition"),
        "rep": v.get("rep", 1),
        "model": model,
        "isolation_level": "independent-host-workspace",
        "activation_evidence": "forced",
        "layer_c_status": "not_run",
    }
    try:
        ws_path, seed_hash = _materialize_workspace(v, cfg)
        state["workspace"] = ws_path
        state["starting_task_hash"] = hashing.hash_task_workspace(ws_path)
        state["starting_manifest"] = _task_manifest(ws_path)
        state["seed_hash"] = seed_hash

        skill_command = None
        condition = v.get("condition", "baseline")
        if condition == "placebo":
            treat_name = v.get("placebo_skill")
            v2 = dict(v, skill_name=treat_name)
            skill_name, content_hash = _install_treatment(ws_path, v2, cfg)
            state["treatment_skill"] = skill_name
            state["skill_content_hash"] = content_hash
            state["activation_mechanism"] = "kilo-command-skill"
            state["skill_command"] = f"{skill_name}:skill"
            skill_command = state["skill_command"]
        elif condition != "baseline":
            skill_name, content_hash = _install_treatment(ws_path, v, cfg)
            state["treatment_skill"] = skill_name
            state["skill_content_hash"] = content_hash
            state["activation_mechanism"] = "kilo-command-skill"
            state["skill_command"] = f"{skill_name}:skill"
            skill_command = state["skill_command"]
        else:
            state["activation_mechanism"] = "none"

        task_text = v.get("task") or prompt
        proc = _run_kilo(task_text, model, ws_path, skill_command,
                         timeout_s)
        raw = proc.stdout or ""
        output_text = _collect_text(raw)
        session = _KILO_SESSION_RE.search(raw)
        state.update({
            "returncode": proc.returncode,
            "session_id": session.group(1) if session else None,
            "ending_task_hash": hashing.hash_task_workspace(ws_path),
            "changed_files": workspace.changed_files(ws_path),
            "output_hash": hashlib.sha256(raw.encode()).hexdigest(),
        })
        workspace.save_state(ws_path, state)
        if proc.returncode != 0:
            return {
                "output": output_text,
                "error": f"kilo exited {proc.returncode}: "
                         f"{(proc.stderr or '')[:300]}",
                "metadata": state,
            }
        return {"output": output_text, "metadata": state}
    except subprocess.TimeoutExpired:
        state["error"] = f"kilo invocation timed out after {timeout_s}s"
        return {"output": "", "error": state["error"], "metadata": state}
    except Exception as exc:
        return {"output": "", "error": f"invocation error: {exc}",
                "metadata": state}
