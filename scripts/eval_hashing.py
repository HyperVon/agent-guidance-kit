#!/usr/bin/env python3
"""Deterministic hashing helpers shared by the evaluator validator and the
fixture hash tool.

Two fixture kinds:

* ``committed`` — the fixture directory *is* the task fixture; hash every file
  (recursively, sorted) so the hash is independent of on-disk mtimes.
* ``generator`` — the fixture is produced by running a generator (``setup.sh``)
  inside a clean, sanitized, host-independent temporary directory. The hash is
  computed over the generator's **output**, not its source:

  - if the output is a git repository, hash the committed tree
    (``git ls-tree -r HEAD`` content hashes + the tree object id) — this is
    fully content-addressed and therefore independent of commit author/date;
  - otherwise hash the generated files recursively.

A generator fixture records both ``source_hash`` (the generator source) and
``output_hash`` (the generated tree). ``content_hash`` mirrors ``output_hash``
so the rest of the validator can treat generators uniformly.
"""
import hashlib
import os
import shutil
import subprocess
import tempfile

HASH_PREFIX = "sha256:"


def sanitize_env():
    """Return a host-independent environment for running a generator.

    Strips anything that could leak the developer's identity or configuration
    into the generated fixture: global/system git config, author/committer
    identity, editor, credential helpers, and HOME/XDG that point at the user's
    real config.
    """
    env = dict(os.environ)
    # Neutral HOME / XDG so git never reads ~/.gitconfig or ~/.config.
    sandbox = tempfile.mkdtemp(prefix="eval-fixture-sandbox-")
    env["HOME"] = sandbox
    env["XDG_CONFIG_HOME"] = sandbox
    env["XDG_CACHE_HOME"] = sandbox
    # Force git to ignore any global/system configuration.
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_SYSTEM"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CEILING_DIRECTORIES"] = sandbox
    # Remove any inherited identity / credential material.
    for key in (
        "EMAIL", "USER", "NAME", "LOGNAME",
        "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL", "GIT_ASKPASS", "SSH_ASKPASS", "SSH_AUTH_SOCK",
        "GH_TOKEN", "GITHUB_TOKEN", "GIT_SSH_COMMAND", "EDITOR", "VISUAL",
    ):
        env.pop(key, None)
    return env, sandbox


def _sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _files_recursive(path):
    files = []
    for root, _, names in os.walk(path):
        for n in names:
            full = os.path.join(root, n)
            rel = os.path.relpath(full, path)
            if rel.split(os.sep)[0] == ".git":
                continue
            files.append(rel)
    return sorted(files)


def committed_hash(path: str) -> str:
    h = hashlib.sha256()
    for rel in _files_recursive(path):
        full = os.path.join(path, rel)
        fh = _sha256_of(open(full, "rb").read())
        h.update((rel + ":" + fh).encode())
    return h.hexdigest()


def _generator_output_hash(output_dir: str) -> str:
    """Hash a generated fixture directory in a host-independent, deterministic way.

    For git repositories the hash covers the FULL working-tree + index state, not
    just the committed HEAD tree. It includes tracked files, uncommitted
    modifications, staged changes, untracked files, and the relevant git metadata
    (HEAD tree id + branch name). Everything is content-addressed (blob/file
    hashes), so the hash is independent of author/commit date, mtimes, absolute
    paths, and host identity.

    For non-git fixtures it falls back to a recursive content hash of the output.
    """
    git_dir = os.path.join(output_dir, ".git")
    if os.path.isdir(git_dir):
        try:
            def _git(*args):
                return subprocess.check_output(
                    ["git", "-C", output_dir] + list(args), text=True,
                ).strip()

            meta = []
            # Content-addressed tree of the committed state (independent of
            # author/commit date, so determinism holds even when dates vary).
            meta.append("TREE=" + _git("rev-parse", "HEAD^{tree}"))
            # Current branch (or 'HEAD' when detached) — part of the routing surface.
            meta.append("BRANCH=" + _git("rev-parse", "--abbrev-ref", "HEAD"))
            # Index: every staged/tracked entry as "<mode> <type> <sha>\t<path>".
            meta.append("INDEX:\n" + _git("ls-files", "-s"))
            # Unstaged working-tree vs index diff (captures uncommitted modifications).
            meta.append("UNSTAGED:\n" + _git("diff", "--no-color"))
            # Staged vs HEAD (captures changes added but not committed).
            meta.append("STAGED:\n" + _git("diff", "--cached", "--no-color"))
            h = hashlib.sha256()
            h.update("\n".join(meta).encode("utf-8"))
            # File contents: every on-disk file (tracked + untracked), excluding
            # .git internals. Deterministically captures untracked files, uncommitted
            # modifications, and staged-but-dirty content.
            for rel in _files_recursive(output_dir):
                full = os.path.join(output_dir, rel)
                fh = _sha256_of(open(full, "rb").read())
                h.update((rel + ":" + fh + "\n").encode("utf-8"))
            return h.hexdigest()
        except subprocess.CalledProcessError:
            pass
    # Fallback: hash the generated files directly.
    return committed_hash(output_dir)


def run_generator(fixture_dir: str, source: str = "setup.sh",
                  invocation: str = "bash setup.sh"):
    """Run a generator in a sanitized temp dir; return (output_dir, hash)."""
    env, sandbox = sanitize_env()
    work = tempfile.mkdtemp(prefix="eval-gen-")
    try:
        # Copy the generator directory (minus any previous .git) into the work dir.
        for name in os.listdir(fixture_dir):
            if name == ".git":
                continue
            src = os.path.join(fixture_dir, name)
            dst = os.path.join(work, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        subprocess.check_call(
            invocation, shell=True, cwd=work, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        h = _generator_output_hash(work)
        return work, h
    finally:
        pass


def source_hash_of(source_path: str) -> str:
    return _sha256_of(open(source_path, "rb").read())


def hash_workspace(path: str) -> str:
    """Deterministic content hash of a (possibly git) workspace.

    Uses the git-aware hasher for git repositories and a plain recursive file
    hash otherwise. This is what the execution runner uses to prove a guided and
    a baseline worker started from byte-identical copies and to record the
    pre/post task-state mutation.
    """
    if os.path.isdir(os.path.join(path, ".git")):
        return _generator_output_hash(path)
    return committed_hash(path)


def materialize_fixture_seed(fixture_dir: str, ftype: str,
                            source: str = "setup.sh",
                            invocation: str = "bash setup.sh"):
    """Produce a pristine, worker-ready seed copy of a fixture.

    * committed  : a byte-identical copy of the fixture directory.
    * generator  : runs the generator under a sanitized environment (via
      ``run_generator``) and then STRIPS the generator source files so the worker
      can never read evaluator-only construction logic (e.g. ``setup.sh`` which
      may contain the intended defect / answer key).

    Returns ``(seed_dir, hash)`` where ``hash`` is a git-aware content hash of
    the seed. The returned ``seed_dir`` is a fresh temp dir the caller owns.
    """
    sandbox = tempfile.mkdtemp(prefix="eval-seed-")
    if ftype == "generator":
        work, _h = run_generator(fixture_dir, source, invocation)
        try:
            shutil.copytree(work, sandbox, symlinks=True, dirs_exist_ok=True)
            # Remove the generator source so it is not worker-visible.
            gen_names = [n for n in os.listdir(fixture_dir) if n != ".git"]
            for n in gen_names:
                p = os.path.join(sandbox, n)
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p, ignore_errors=True)
                elif os.path.exists(p):
                    os.remove(p)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    else:
        shutil.copytree(fixture_dir, sandbox, symlinks=True, dirs_exist_ok=True)
    return sandbox, hash_workspace(sandbox)


def canonical_hash(path: str, ftype: str, source: str = "setup.sh",
                   invocation: str = "bash setup.sh") -> str:
    """Return the canonical hash for a fixture directory.

    For ``committed`` fixtures this hashes the directory contents. For
    ``generator`` fixtures this runs the generator and hashes its output.
    """
    if ftype == "generator":
        work, h = run_generator(path, source, invocation)
        shutil.rmtree(work, ignore_errors=True)
        return h
    return committed_hash(path)


def verify_generator_deterministic(fixture_dir: str, source: str = "setup.sh",
                                   invocation: str = "bash setup.sh"):
    """Run the generator twice; return the stable output hash or raise."""
    work1, h1 = run_generator(fixture_dir, source, invocation)
    shutil.rmtree(work1, ignore_errors=True)
    work2, h2 = run_generator(fixture_dir, source, invocation)
    shutil.rmtree(work2, ignore_errors=True)
    if h1 != h2:
        raise ValueError(
            f"generator {fixture_dir} is NON-DETERMINISTIC: {h1} != {h2}"
        )
    return h1
