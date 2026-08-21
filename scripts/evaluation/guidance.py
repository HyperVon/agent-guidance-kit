"""Guidance materialization, hashing, and worker-state snapshots."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess

from eval_hashing import HASH_PREFIX

from .workspace import _reject_symlinks


def snapshot_workspace(workspace: str) -> dict:
    """Capture a deterministic pre/post task-state snapshot."""

    git = os.path.join(workspace, ".git")
    if os.path.isdir(git):
        def git_output(*arguments: str) -> str:
            return subprocess.run(
                ["git", "-C", workspace, *arguments],
                capture_output=True,
                text=True,
                check=False,
            ).stdout

        try:
            head = subprocess.check_output(
                ["git", "-C", workspace, "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except Exception:
            head = None
        return {
            "vcs": "git",
            "head": head,
            "status": git_output("status", "--porcelain=v1"),
            "diff": git_output("diff", "--no-color"),
        }
    files = {}
    for root, _, names in os.walk(workspace):
        for name in names:
            path = os.path.join(root, name)
            relative = os.path.relpath(path, workspace)
            if relative.split(os.sep)[0] == ".git":
                continue
            try:
                with open(path, "rb") as handle:
                    files[relative] = hashlib.sha256(handle.read()).hexdigest()[:16]
            except OSError:
                pass
    return {"vcs": "files", "listing": files}


def skill_tree_hash(skill_dir: str) -> str | None:
    """Hash only the worker-visible guidance tree: SKILL.md and references."""

    if not os.path.isdir(skill_dir):
        return None
    _reject_symlinks(skill_dir, "skill guidance source")
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return None
    relative_paths = ["SKILL.md"]
    references = os.path.join(skill_dir, "references")
    if os.path.isdir(references):
        for root, _, names in os.walk(references):
            for name in names:
                path = os.path.join(root, name)
                relative_paths.append(os.path.relpath(path, skill_dir))
    digest = hashlib.sha256()
    for relative in sorted(relative_paths):
        path = os.path.join(skill_dir, relative)
        with open(path, "rb") as handle:
            content_hash = hashlib.sha256(handle.read()).hexdigest()
        digest.update(f"{relative}:{content_hash}\n".encode())
    return HASH_PREFIX + digest.hexdigest()


def materialize_guidance(
    source_skill_dir: str,
    workspace: str,
    destination_relative: str = ".evaluation-runtime/guidance",
) -> str:
    """Place guidance at an evaluator-neutral runtime path.

    The adapter may copy or mount this bundle into its native discovery
    mechanism.  The evaluator does not interpret that mechanism.
    """

    _reject_symlinks(source_skill_dir, "skill guidance source")
    destination = os.path.join(workspace, destination_relative)
    os.makedirs(destination, exist_ok=True)
    skill_md = os.path.join(source_skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        raise ValueError(f"skill source missing SKILL.md: {source_skill_dir}")
    shutil.copy(skill_md, os.path.join(destination, "SKILL.md"))
    references = os.path.join(source_skill_dir, "references")
    if os.path.isdir(references):
        shutil.copytree(references, os.path.join(destination, "references"),
                        dirs_exist_ok=True)
    return destination


__all__ = ["materialize_guidance", "skill_tree_hash", "snapshot_workspace"]
