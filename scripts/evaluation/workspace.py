"""Temporary evaluator workspaces and safe cleanup."""

from __future__ import annotations

import os
import shutil
import stat
import tempfile


def _repository_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))


def evaluation_temp_root() -> str:
    """Return the ignored root used for evaluator-owned temporary trees."""

    return os.path.join(_repository_root(), ".evaluation-tmp")


def make_temp_dir(prefix: str) -> str:
    """Create a disposable directory under the evaluator's ignored temp root."""

    root = evaluation_temp_root()
    os.makedirs(root, exist_ok=True)
    path = tempfile.mkdtemp(prefix=prefix, dir=root)
    os.chmod(path, 0o755)
    return path


def _reject_symlinks(root: str, label: str) -> None:
    """Reject symlinks before a worker-visible tree is copied or hashed."""

    if os.path.islink(root):
        raise ValueError(f"{label} must not be a symlink: {root}")
    for current, directories, files in os.walk(root, followlinks=False):
        for name in [*directories, *files]:
            path = os.path.join(current, name)
            if os.path.islink(path):
                relative = os.path.relpath(path, root)
                raise ValueError(
                    f"{label} must not contain symlinks: {relative}")


def copy_seed(source: str) -> str:
    """Copy a pristine fixture to an independent writable condition workspace."""

    _reject_symlinks(source, "fixture seed")
    destination = make_temp_dir("harness-workspace-")
    shutil.copytree(source, destination, dirs_exist_ok=True)
    for root, directories, files in os.walk(destination, followlinks=False):
        for name in [*directories, *files]:
            path = os.path.join(root, name)
            if os.path.islink(path):
                continue
            try:
                mode = os.stat(path, follow_symlinks=False).st_mode
                os.chmod(path, mode | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
            except OSError:
                pass
    os.chmod(destination, os.stat(destination).st_mode |
             stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    return destination


def cleanup_workspace(path: str) -> None:
    """Remove one evaluator-owned temporary workspace, failing closed on scope."""

    if not isinstance(path, str) or not path:
        return
    root = os.path.realpath(evaluation_temp_root())
    candidate = os.path.realpath(path)
    try:
        in_scope = os.path.commonpath((root, candidate)) == root
    except ValueError:
        in_scope = False
    if not in_scope or candidate == root:
        raise ValueError(f"refusing to clean non-evaluator workspace: {path}")
    shutil.rmtree(candidate, ignore_errors=True)


__all__ = [
    "_reject_symlinks",
    "cleanup_workspace",
    "copy_seed",
    "evaluation_temp_root",
    "make_temp_dir",
]
