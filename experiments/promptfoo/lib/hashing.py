"""Hashing helpers for spike provenance.

Thin wrappers over the canonical ``scripts/eval_hashing.py`` implementation so
Promptfoo-recorded hashes are directly comparable with v1 evidence.
"""
import hashlib
import json

from experiments.promptfoo.lib.paths import (
    RUNTIME_TREATMENT_PATHS,
    from_repo_root,
)

from scripts import eval_hashing


def canonical_json_hash(obj):
    """sha256 of the canonical sorted-key JSON encoding (v1 case_set_hash form)."""
    encoded = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def text_hash(text):
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def file_hash(path):
    with open(path, "rb") as f:
        return "sha256:" + hashlib.sha256(f.read()).hexdigest()


def skill_file_hash(skill_dir):
    return file_hash(from_repo_root(skill_dir, "SKILL.md"))


def hash_task_workspace(workspace):
    """Task-state hash: excludes runtime treatment paths (.kilo/skills)."""
    return eval_hashing.hash_task_workspace(
        workspace, exclude_runtime_paths=RUNTIME_TREATMENT_PATHS)


def hash_full_workspace(workspace):
    return eval_hashing.hash_workspace(workspace)
