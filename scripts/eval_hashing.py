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
    """Hash a generated fixture directory in a host-independent way."""
    git_dir = os.path.join(output_dir, ".git")
    if os.path.isdir(git_dir):
        # Content-addressed: committed tree only, independent of author/date.
        try:
            tree = subprocess.check_output(
                ["git", "-C", output_dir, "rev-parse", "HEAD^{tree}"],
                text=True,
            ).strip()
            ls = subprocess.check_output(
                ["git", "-C", output_dir, "ls-tree", "-r", "HEAD"],
                text=True,
            ).splitlines()
            h = hashlib.sha256()
            h.update(("tree:" + tree + "\n").encode())
            for line in sorted(ls):
                # "<mode> <type> <sha>\t<path>"
                parts = line.split("\t", 1)
                if len(parts) != 2:
                    continue
                meta, objpath = parts
                sha = meta.split()[2]
                h.update((objpath + ":" + sha + "\n").encode())
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
