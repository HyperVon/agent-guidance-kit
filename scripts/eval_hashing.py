#!/usr/bin/env python3
"""Deterministic hashing helpers shared by the evaluator validator and the
fixture hash tool.

Two fixture kinds:

* ``committed`` — the fixture directory *is* the task fixture; hash every file
  (recursively, sorted) so the hash is independent of on-disk mtimes.
* ``generator`` — the fixture is produced by running a generator (``setup.sh``)
  inside a clean, sanitized, host-independent temporary directory. The hash is
  computed over the WORKER-VISIBLE generated state, with the evaluator-only
  generator source (``setup.sh``) STRIPPED so it is never part of the recorded
  hash:

  - if the output is a git repository, hash the committed tree
    (``git ls-tree -r HEAD`` content hashes + the tree object id) — this is
    fully content-addressed and therefore independent of commit author/date;
  - otherwise hash the generated files recursively.

  Fixture-local bare remotes are represented by sorted symbolic-HEAD/ref
  manifests, while their raw storage and the working repository's raw config
  remain excluded. Working-repository remote URLs and current-branch upstream
  keys are included in normalized form.

A generator fixture records both ``source_hash`` (the evaluator-only generator
source, e.g. ``setup.sh``) and ``output_hash`` / ``content_hash`` (the
WORKER-VISIBLE generated task state — the generator source is STRIPPED before
hashing). ``content_hash`` mirrors ``output_hash`` so the rest of the validator
can treat generators uniformly. The canonical worker-visible materialization is
``materialize_fixture_seed``; ``canonical_hash`` / ``verify_generator_deterministic``
both defer to it so frozen hashes always describe exactly what workers receive.

``run_generator`` accepts only the constrained ``<interpreter> <source>`` argv
form and invokes it with ``shell=False``. Its sanitized environment normalizes
provenance; it is not an OS security boundary. Generator source must therefore
be trusted or executed by an externally supplied OS-contained adapter.
"""
import hashlib
import os
import shlex
import shutil
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit

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


def _generator_argv(source: str, invocation: str) -> list[str]:
    """Return a shell-free argv for the constrained generator contract."""

    if not isinstance(source, str) or not source.strip():
        raise ValueError("generator source must be a non-empty path")
    if not isinstance(invocation, str) or not invocation.strip():
        raise ValueError("generator invocation must be a non-empty command")
    try:
        argv = shlex.split(invocation)
    except ValueError as exc:
        raise ValueError(f"generator invocation is not valid argv: {exc}") from exc
    if len(argv) != 2 or argv[1] != source:
        raise ValueError(
            "generator invocation must be '<interpreter> <source>' with no shell syntax"
        )
    interpreter = os.path.basename(argv[0])
    if interpreter not in {"bash", "sh", "python", "python3"}:
        raise ValueError(
            "generator invocation interpreter must be bash, sh, python, or python3"
        )
    return argv


def _is_excluded(rel, exclude):
    """Whether a workspace-relative path is under an excluded path prefix.

    Exclusions are workspace-relative and may be nested (for example,
    ``.kilo/skills``). They are never matched against a nested directory with
    the same name elsewhere in the fixture.
    """
    if not exclude:
        return False
    rel_parts = rel.replace(os.sep, "/").split("/")
    for raw_prefix in exclude:
        prefix = str(raw_prefix).replace(os.sep, "/").strip("/")
        if not prefix or prefix == ".":
            continue
        prefix_parts = prefix.split("/")
        if rel_parts[:len(prefix_parts)] == prefix_parts:
            return True
    return False


def _files_recursive(path, exclude=()):
    files = []
    for root, _, names in os.walk(path):
        for n in names:
            full = os.path.join(root, n)
            rel = os.path.relpath(full, path)
            if rel.split(os.sep)[0] == ".git":
                continue
            if _is_excluded(rel, exclude):
                continue
            files.append(rel)
    return sorted(files)


def _normalized_relpath(path, root):
    """Return a repository-relative path with portable separators."""
    return os.path.relpath(os.path.realpath(path), os.path.realpath(root)).replace(
        os.sep, "/"
    )


def _git_output(args, *, cwd=None, git_dir=None):
    cmd = ["git"]
    if cwd is not None:
        cmd += ["-C", cwd]
    if git_dir is not None:
        cmd += ["--git-dir", git_dir]
    cmd += list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _normalize_fixture_remote_url(url, workspace):
    """Keep external URLs intact while making local fixture paths portable."""
    raw = url.strip()
    if not raw:
        return raw

    local_path = _fixture_local_remote_path(raw, workspace)
    if local_path is None:
        return raw
    relative = os.path.relpath(
        local_path, os.path.realpath(workspace),
    ).replace(os.sep, "/")
    return "fixture://" + relative


def _fixture_local_remote_path(raw, workspace):
    """Resolve a local remote URL only when it stays inside the fixture."""
    is_windows_path = len(raw) > 1 and raw[1] == ":" and raw[0].isalpha()
    parsed = urlsplit("") if is_windows_path else urlsplit(raw)
    if parsed.scheme and parsed.scheme != "file":
        return None
    if parsed.scheme == "file":
        if parsed.netloc not in ("", "localhost"):
            return None
        candidate = unquote(parsed.path)
    else:
        # Preserve scp-style external URLs such as git@github.com:org/repo.git.
        if "@" in raw and ":" in raw and not os.path.isabs(raw):
            return None
        candidate = raw

    if os.path.isabs(candidate):
        absolute = os.path.realpath(candidate)
    else:
        absolute = os.path.realpath(os.path.join(workspace, candidate))
    workspace_abs = os.path.realpath(workspace)
    try:
        if os.path.commonpath((absolute, workspace_abs)) != workspace_abs:
            return None
    except ValueError:
        return None
    return absolute


def _bare_repo_semantic_manifest(path, workspace):
    """Return a deterministic semantic manifest for a bare Git repository."""
    if _git_output(["rev-parse", "--is-bare-repository"], git_dir=path) != "true":
        return None
    relative = _normalized_relpath(path, workspace)
    head = _git_output(["symbolic-ref", "--quiet", "HEAD"], git_dir=path)
    head_lines = ["HEAD=" + head] if head else ["HEAD=(detached)"]
    if head is None:
        head_object = _git_output(["rev-parse", "--verify", "HEAD"],
                                  git_dir=path)
        head_lines.append("HEAD_OBJECT=" + (head_object or "(unborn)"))
    refs = _git_output(
        ["for-each-ref", "--format=%(refname) %(objectname)"], git_dir=path,
    )
    ref_lines = sorted(line.strip() for line in (refs or "").splitlines()
                       if line.strip())
    return "\n".join([
        "BARE_REMOTE:" + relative,
        *head_lines,
        "REFS:",
        *ref_lines,
    ])


def _discover_bare_repositories(workspace):
    """Find fixture-local bare repositories without traversing their internals."""
    workspace = os.path.realpath(workspace)
    working_git = os.path.realpath(os.path.join(workspace, ".git"))
    configured = set()
    remotes = _git_output(
        ["config", "--local", "--get-regexp", r"^remote\..+\.url$"],
        cwd=workspace,
    )
    for line in (remotes or "").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            local_path = _fixture_local_remote_path(parts[1], workspace)
            if local_path is not None:
                configured.add(os.path.realpath(local_path))
    found = []
    for root, dirs, _ in os.walk(workspace, topdown=True):
        kept = []
        for name in dirs:
            candidate = os.path.join(root, name)
            candidate_real = os.path.realpath(candidate)
            if candidate_real == working_git:
                continue
            is_bare_candidate = (
                candidate_real in configured
                or name == ".origin.git"
                or name.endswith(".git")
            )
            if not is_bare_candidate:
                kept.append(name)
                continue
            if _bare_repo_semantic_manifest(candidate, workspace) is None:
                kept.append(name)
                continue
            found.append(candidate)
        dirs[:] = kept
    return sorted(found, key=lambda p: _normalized_relpath(p, workspace))


def _working_repo_semantic_manifest(workspace):
    """Return the task-relevant, normalized subset of working-repo Git config."""
    if not os.path.isdir(os.path.join(workspace, ".git")):
        return None
    branch = _git_output(["symbolic-ref", "--quiet", "--short", "HEAD"],
                         cwd=workspace)
    branch = branch or "(detached)"
    lines = ["WORKING_REPO", "BRANCH=" + branch]

    remotes = _git_output(
        ["config", "--local", "--get-regexp", r"^remote\..+\.url$"],
        cwd=workspace,
    )
    for line in sorted((remotes or "").splitlines()):
        parts = line.split(None, 1)
        if len(parts) == 2:
            key, value = parts
            lines.append(
                "REMOTE_URL=" + key + "="
                + _normalize_fixture_remote_url(value, workspace)
            )

    if branch != "(detached)":
        for suffix in ("remote", "merge"):
            key = "branch." + branch + "." + suffix
            value = _git_output(["config", "--local", "--get", key],
                                cwd=workspace)
            lines.append("UPSTREAM=" + key + "=" + (value or "(unset)"))
    return "\n".join(lines)


def _semantic_git_state(workspace, bare_repositories):
    entries = []
    working = _working_repo_semantic_manifest(workspace)
    if working is not None:
        entries.append(working)
    for path in bare_repositories:
        manifest = _bare_repo_semantic_manifest(path, workspace)
        if manifest is not None:
            entries.append(manifest)
    return entries


def committed_hash(path: str, exclude=()) -> str:
    h = hashlib.sha256()
    for rel in _files_recursive(path, exclude=exclude):
        full = os.path.join(path, rel)
        fh = _sha256_of(open(full, "rb").read())
        rel_posix = rel.replace(os.sep, "/")
        h.update((rel_posix + ":" + fh).encode())
    return h.hexdigest()


def _generator_output_hash(output_dir: str, exclude=()) -> str:
    """Hash a generated fixture directory in a host-independent, deterministic way.

    For git repositories the hash covers the FULL working-tree + index state, not
    just the committed HEAD tree. It includes tracked files, uncommitted
    modifications, staged changes, untracked files, and the relevant git metadata
    (HEAD tree id + branch name). Everything is content-addressed (blob/file
    hashes), so the hash is independent of author/commit date, mtimes, absolute
    paths, and host identity.

    For non-git fixtures it falls back to a recursive content hash of the output.

    ``exclude`` is a tuple of workspace-relative runtime paths (e.g.
    ``(".kilo/skills",)``) that are omitted from the file-content portion — used by
    :func:`hash_task_workspace` so evaluator treatment trees never enter the
    task-state hash. Git metadata (TREE/BRANCH/INDEX/diffs) is still captured
    as-is; treatment files are untracked, so they never appear there either.
    """
    git_dir = os.path.join(output_dir, ".git")
    if os.path.isdir(git_dir):
        try:
            bare_repositories = _discover_bare_repositories(output_dir)
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
            # Include semantic Git state while excluding raw repository internals.
            meta.extend(_semantic_git_state(output_dir, bare_repositories))
            h = hashlib.sha256()
            h.update("\n".join(meta).encode("utf-8"))
            # File contents: every on-disk file (tracked + untracked), excluding
            # .git internals. Deterministically captures untracked files, uncommitted
            # modifications, and staged-but-dirty content.
            for rel in _files_recursive(output_dir, exclude=exclude):
                # .origin.git is a bare upstream created by git init --bare;
                # its config contains platform-specific keys (e.g. macOS
                # precomposeunicode) that vary across git versions/filesystems
                # and must not affect the worker-visible task hash.
                rel_posix = rel.replace(os.sep, "/")
                if any(rel_posix == _normalized_relpath(bare, output_dir)
                       or rel_posix.startswith(
                           _normalized_relpath(bare, output_dir) + "/")
                       for bare in bare_repositories):
                    continue
                full = os.path.join(output_dir, rel)
                fh = _sha256_of(open(full, "rb").read())
                h.update((rel_posix + ":" + fh + "\n").encode("utf-8"))
            return h.hexdigest()
        except subprocess.CalledProcessError:
            pass
    # Fallback: hash the generated files directly.
    return committed_hash(output_dir, exclude=exclude)


def run_generator(fixture_dir: str, source: str = "setup.sh",
                  invocation: str = "bash setup.sh"):
    """Run a generator in a sanitized temp dir; return (output_dir, hash).

    ``invocation`` is parsed as a shell-free ``argv`` and must name the supplied
    ``source`` as its only argument. Environment sanitization does not provide
    OS-level containment for generator code.

    The returned ``output_dir`` is the GENERATED workspace and still contains the
    generator source (e.g. ``setup.sh``). It is the caller's responsibility to
    strip evaluator-only generator source before presenting the task to a worker
    (see ``materialize_fixture_seed``). The returned hash covers the generated
    workspace INCLUDING the generator source; the worker-visible hash is produced
    by ``materialize_fixture_seed`` and excludes it.
    """
    argv = _generator_argv(source, invocation)
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
            argv, shell=False, cwd=work, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        h = _generator_output_hash(work)
        return work, h
    finally:
        # The sanitized HOME/XDG sandbox is host-scoped and must never leak.
        shutil.rmtree(sandbox, ignore_errors=True)


def source_hash_of(source_path: str) -> str:
    return _sha256_of(open(source_path, "rb").read())


def hash_workspace(path: str) -> str:
    """Deterministic content hash of a (possibly git) workspace.

    Uses the git-aware hasher for git repositories and a plain recursive file
    hash otherwise. This hashes EVERYTHING under ``path`` — including any
    evaluator-added runtime/treatment artifacts (e.g. ``.kilo/skills/``).
    It is the FULL-FILESYSTEM hash, used to prove the raw condition copies are
    structurally different where treatment differs; it is NOT the task-state
    hash (see :func:`hash_task_workspace`).
    """
    if os.path.isdir(os.path.join(path, ".git")):
        return _generator_output_hash(path)
    return committed_hash(path)


def hash_task_workspace(path: str,
                        exclude_runtime_paths=(".kilo/skills",)) -> str:
    """Deterministic hash of the TASK STATE of a workspace, excluding
    evaluator/harness-controlled runtime treatment paths.

    Layer B separates two kinds of state:

    * **task state** — the actual thing the worker works on (source, docs,
      tests, fixture content, git state). This MUST be byte-identical across
      the target/baseline/placebo conditions and equal to the frozen fixture
      hash.
    * **runtime treatment state** — what the evaluator adds to deliver the
      treatment (``.kilo/skills/`` skill discovery trees, injected guidance,
      condition-control metadata). This is INTENTIONALLY different between
      target and placebo (and absent in baseline).

    Hashing those together and then requiring equality would fail by
    construction, because the treatment state differs. This hasher therefore
    excludes the explicit runtime paths the evaluator controls (default:
    ``.kilo/skills``, the Kilo project skill-discovery tree) while hashing
    everything else, so real task mutations still change the hash.

    ``exclude_runtime_paths`` entries are workspace-relative path prefixes (e.g.
    ``".kilo/skills"``); both git and non-git workspaces honor them. The
    exclusion is deliberately NOT a global ".kilo" rule: other project config
    under the root ``.kilo`` directory, and nested ``.kilo`` content elsewhere,
    are still hashed.
    """
    exclude = tuple(p for p in exclude_runtime_paths if p)
    if os.path.isdir(os.path.join(path, ".git")):
        return _generator_output_hash(path, exclude=exclude)
    return committed_hash(path, exclude=exclude)


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
    ``generator`` fixtures this materializes the worker-visible seed (generator
    run under a sanitized environment, with the evaluator-only generator source
    STRIPPED) and hashes THAT — never the generator source. This is the exact
    artifact the execution worker receives, so the frozen ``output_hash`` /
    ``content_hash`` describes the worker-visible task state.
    """
    if ftype == "generator":
        seed, h = materialize_fixture_seed(path, ftype, source, invocation)
        shutil.rmtree(seed, ignore_errors=True)
        return h
    return committed_hash(path)


def verify_generator_deterministic(fixture_dir: str, source: str = "setup.sh",
                                    invocation: str = "bash setup.sh"):
    """Run the generator twice; return the stable worker-visible hash or raise.

    Compares two independently materialized WORKER-VISIBLE seeds, so the check is
    about the artifact actually handed to workers (setup.sh excluded), not the
    generator source.
    """
    seed1, h1 = materialize_fixture_seed(fixture_dir, "generator", source, invocation)
    shutil.rmtree(seed1, ignore_errors=True)
    seed2, h2 = materialize_fixture_seed(fixture_dir, "generator", source, invocation)
    shutil.rmtree(seed2, ignore_errors=True)
    if h1 != h2:
        raise ValueError(
            f"generator {fixture_dir} is NON-DETERMINISTIC: {h1} != {h2}"
        )
    return h1
