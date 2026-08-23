"""Deterministic per-case workspace materialization for Layer B conditions.

Each (case, condition, repetition) receives an independent fresh host
directory materialized from the pristine fixture seed. Target/placebo
conditions additionally get the skill discovery tree ``.kilo/skills/<name>/``
installed; baseline gets none. Isolation level: independent disposable host
workspaces (NOT Docker attestation; the existing Docker evaluator remains the
strict-confirmation reference).
"""
import json
import os
import re
import shutil

from experiments.promptfoo.lib import hashing
from experiments.promptfoo.lib.paths import WORKSPACE_ROOT, from_repo_root


def workspace_path(run_id, case_id, condition, rep):
    name = f"{run_id}-case{case_id}-{condition}-r{rep}"
    return os.path.join(WORKSPACE_ROOT, name)


def install_skill_tree(workspace, skill_name, skill_source_dir):
    """Install .kilo/skills/<skill_name>/ from a source skill directory."""
    dest = os.path.join(workspace, ".kilo", "skills", skill_name)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copytree(skill_source_dir, dest, dirs_exist_ok=True)
    return hashing.file_hash(os.path.join(dest, "SKILL.md"))


def materialize_skill_from_revision(git_sha, skill_name):
    """Materialize a skill directory from a historical git revision.

    Returns (temp_dir, content_hash). Only SKILL.md and references/ are
    projected; that is the full discovery surface the worker sees.
    """
    import subprocess
    import tempfile

    out = subprocess.run(
        ["git", "show", f"{git_sha}:skills/{skill_name}/SKILL.md"],
        cwd=from_repo_root(), capture_output=True, text=True, check=True)
    tmp = tempfile.mkdtemp(prefix=f"skill-{skill_name}-{git_sha[:8]}-")
    skill_dir = os.path.join(tmp, skill_name)
    os.makedirs(skill_dir, exist_ok=True)
    sk = os.path.join(skill_dir, "SKILL.md")
    with open(sk, "w") as f:
        f.write(out.stdout)
    refs = subprocess.run(
        ["git", "ls-tree", "--name-only", git_sha,
         f"skills/{skill_name}/references"],
        cwd=from_repo_root(), capture_output=True, text=True)
    if refs.stdout.strip():
        raw = subprocess.run(
            ["git", "archive", git_sha, f"skills/{skill_name}/references"],
            cwd=from_repo_root(), capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", skill_dir], input=raw, check=True)
    return skill_dir, hashing.file_hash(sk)


def changed_files(workspace):
    """List task-state files that differ from a fresh copy is not possible
    post-hoc; instead report files newer than a marker or git status when the
    fixture is a git repo."""
    repo = os.path.join(workspace, ".git")
    marker = os.path.join(workspace, ".agk-pf-start")
    if os.path.isdir(repo):
        import subprocess
        proc = subprocess.run(
            ["git", "status", "--porcelain"], cwd=workspace,
            capture_output=True, text=True, timeout=60)
        return [ln for ln in proc.stdout.splitlines() if ln.strip()]
    changed = []
    start = os.path.getmtime(marker) if os.path.exists(marker) else 0
    for root, _dirs, files in os.walk(workspace):
        if os.path.relpath(root, workspace).startswith(".kilo"):
            continue
        for name in files:
            p = os.path.join(root, name)
            if p == marker:
                continue
            if os.path.getmtime(p) > start:
                changed.append(os.path.relpath(p, workspace))
    return sorted(changed)


def stamp_start(workspace):
    with open(os.path.join(workspace, ".agk-pf-start"), "w") as f:
        f.write("evaluation run start marker\n")


def summary(workspace):
    return {
        "workspace": workspace,
        "starting_task_hash": None,
        "ending_task_hash": None,
        "changed_files": [],
        "git_status": [],
        "isolation_level": "independent-host-workspace",
    }


def cleanup(run_id, keep=False):
    if keep:
        return
    root = WORKSPACE_ROOT
    for name in os.listdir(root):
        if name.startswith(f"{run_id}-"):
            shutil.rmtree(os.path.join(root, name), ignore_errors=True)


def load_state(workspace):
    state_path = os.path.join(workspace, ".agk-pf-state.json")
    if not os.path.exists(state_path):
        return {}
    with open(state_path) as f:
        return json.load(f)


def save_state(workspace, state):
    state_path = os.path.join(workspace, ".agk-pf-state.json")
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


_KILO_SESSION_RE = re.compile(r'"sessionID":"(ses_[^"]+)"')


def extract_session_id(raw_stream):
    m = _KILO_SESSION_RE.search(raw_stream or "")
    return m.group(1) if m else None
