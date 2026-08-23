#!/usr/bin/env python3
"""Docker isolation preflight (boundary probe) for the execution layer.

Starts worker containers and asserts, from INSIDE the container, that:

    baseline condition (no guidance):
    * isolated HOME (/home/eval) with the deterministic eval git identity;
    * no ~/.ssh, no host ~/.gitconfig, no GH_TOKEN/GITHUB_TOKEN;
    * no host path leak (e.g. /Users/<user>);
    * no mounted Kilo auth store;
    * no ``.kilo/skills`` discovery tree in the workspace (no treatment);
    * the mounted fixture actually arrived (/work/task/MARKER);
    * no sibling workspace leakage.

  GUIDED condition (skill placed at Kilo's project-level discovery location):
    * ``.kilo/skills/<skill>/SKILL.md`` PRESENT and readable in the workspace;
    * its sha256 matches the evaluator-computed SKILL.md hash;
    * ``references/`` is available when the skill ships one;
    * the mounted fixture arrived (/work/task/MARKER).

  WORKSPACE condition (runner `_copy_seed` workspace, read-write mount):
    * the workspace ROOT is ENUMERABLE by the container's non-host uid
      (``ls -A /work/task``) — the Linux/Docker uid-mapping regression guard;
    * expected task files are readable;
    * subdirectories are traversable and their files readable;
    * new files can be created and existing files modified.

    This probe exercises container/workspace mechanics directly and does not
    depend on model behavior.

Layer B activates guidance through ``kilo run --command <skill>:skill``, which
resolves against this discovery tree; mere file presence is NOT activation, but
the tree must exist and be byte-identical to the frozen skill for the command
to resolve. The baseline workspace must contain no evaluator-owned
``.kilo/skills`` tree.

This is the automated gate that must pass before any target/baseline execution
run is trusted.

Usage:
    python3 scripts/docker_isolation_preflight.py --image kilo-eval:local --target-skill code-review
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_hashing import source_hash_of
from run_execution_eval import _copy_seed

SHARED_TMP = os.path.join(ROOT, ".docker-tmp")

FIXTURE_MOUNT = "/work/task"
KILO_DISCOVERY_DIR = "/work/task/.kilo/skills"

# Files the workspace probe expects to find/traverse/create. These names are
# probe mechanics, not task content; the probe never depends on model behavior.
PROBE_SUBDIR = "expected-subdir"
PROBE_INNER_FILE = "inner-file.txt"
PROBE_NEW_FILE = ".preflight-write-probe"


def probe_script(target_skill, expected_hash, guidance_present, refs_expected):
    """Shell commands run INSIDE the container; emit a JSON report to stdout."""
    script = r"""
set -e
report=$(mktemp)
check() { # name expected_ok
  echo "{\"name\": \"$1\", \"ok\": $2}" >> "$report"
}
HOME_OK=$([ "$HOME" = "/home/eval" ] && echo true || echo false)
check "isolated_home" "$HOME_OK"

GIT_EMAIL=$(git config --file "$HOME/.gitconfig" user.email 2>/dev/null || echo "")
if [ "$GIT_EMAIL" = "eval-worker@example.invalid" ]; then
  check "deterministic_git_identity" true
else
  check "deterministic_git_identity" false
fi

if [ -d "$HOME/.ssh" ] || [ -d "/root/.ssh" ]; then
  check "no_ssh_dir" false
else
  check "no_ssh_dir" true
fi

if [ -n "$GH_TOKEN" ] || [ -n "$GITHUB_TOKEN" ]; then
  check "no_token_env" false
else
  check "no_token_env" true
fi

if find / -path "$HOME/.gitconfig" -prune -o -name "*.gitconfig" -print 2>/dev/null \
     | grep -q "/Users/"; then
  check "no_host_gitconfig" false
else
  check "no_host_gitconfig" true
fi

if find / 2>/dev/null | grep -q "/Users/"; then
  check "no_host_path_leak" false
else
  check "no_host_path_leak" true
fi

if [ -e "$HOME/.config/kilo/auth.json" ] || [ -e "/root/.config/kilo/auth.json" ]; then
  check "no_kilo_auth_mounted" false
else
  check "no_kilo_auth_mounted" true
fi

# Positive check: the fixture we mounted must actually have arrived.
if [ -e "__FIXTURE_MOUNT__/MARKER" ]; then
  check "mount_arrived" true
else
  check "mount_arrived" false
fi

# No sibling workspace leakage.
if [ -e "/work/sibling" ]; then
  check "no_sibling_leak" false
else
  check "no_sibling_leak" true
fi
    """.replace("__FIXTURE_MOUNT__", FIXTURE_MOUNT) + (
        # Guided-only checks (skill placed at the Kilo discovery location).
        # Presence alone is NOT activation (activation happens via
        # `kilo run --command <skill>:skill`), but the discovery tree must be
        # present and byte-identical to the frozen skill for that command to
        # resolve and inject the guidance.
        r"""
SKILL_MD="__KILO_DISCOVERY_DIR__/__TARGET_SKILL__/SKILL.md"
if [ -e "$SKILL_MD" ]; then
  check "skill_discovery_present" true
  if [ -r "$SKILL_MD" ]; then
    check "skill_discovery_readable" true
  else
    check "skill_discovery_readable" false
  fi
  ACTUAL=$(sha256sum "$SKILL_MD" | cut -d' ' -f1)
  if [ "$ACTUAL" = "__EXPECTED_HASH__" ]; then
    check "skill_discovery_hash_match" true
  else
    check "skill_discovery_hash_match" false
  fi
  if [ -d "__KILO_DISCOVERY_DIR__/__TARGET_SKILL__/references" ]; then
    check "references_present_if_required" true
  elif [ "__REFS_REQUIRED__" = "true" ]; then
    check "references_present_if_required" false
  else
    check "references_present_if_required" true
  fi
else
  check "skill_discovery_present" false
  check "skill_discovery_readable" false
  check "skill_discovery_hash_match" false
fi
""".replace("__KILO_DISCOVERY_DIR__", KILO_DISCOVERY_DIR)
   .replace("__EXPECTED_HASH__", expected_hash)
    .replace("__REFS_REQUIRED__", "true" if refs_expected else "false")
        if guidance_present else
        # Baseline-only check: no discovery tree may exist at all.
        r"""
if [ -e "__KILO_DISCOVERY_DIR__" ]; then
  check "target_skill_absent" false
else
  check "target_skill_absent" true
fi
""".replace("__KILO_DISCOVERY_DIR__", KILO_DISCOVERY_DIR)
    ) + r"""
echo "["
sed -e '$!s/$/,/' "$report"
echo "]"
"""
    return script.replace("__TARGET_SKILL__", target_skill)


def run_probe(image, target_skill, fixture_dir, expected_hash,
              guidance_present, refs_expected):
    script = probe_script(target_skill, expected_hash, guidance_present,
                          refs_expected)
    cmd = ["docker", "run", "--rm", "--entrypoint", "bash",
           "-v", f"{fixture_dir}:{FIXTURE_MOUNT}:ro"]
    cmd += [image, "-c", script]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = proc.stdout
    start = out.find("[")
    end = out.rfind("]")
    if start == -1 or end == -1:
        print("PREFLIGHT FAILED TO PARSE OUTPUT")
        print(out)
        print(proc.stderr)
        return None
    return json.loads(out[start:end + 1])


def workspace_probe_script():
    """In-container workspace mechanics probe (no model involvement).

    Verifies that the disposable worker workspace the runner prepared through
    ``_copy_seed`` is fully usable by the container's non-host uid: the root
    can be ENUMERATED (the Linux/Docker regression this guards against — a
    write/traverse-only root cannot be listed), expected task files are
    readable, subdirectories are traversable, and new files can be created.
    """
    return r"""
set -e
report=$(mktemp)
check() { # name ok detail
  printf '{"name": "%s", "ok": %s, "detail": "%s"}\n' "$1" "$2" "$3" >> "$report"
}
WORKER_UID=$(id -u)

# 0. Deterministic non-owner proof: this probe is only meaningful when the
# container process uid DIFFERS from the host workspace owner's uid. If they
# match, FAIL rather than silently counting as coverage.
if [ "$WORKER_UID" != "__OWNER_UID__" ]; then
  check "non_owner_worker" true "container uid $WORKER_UID != workspace owner __OWNER_UID__"
else
  check "non_owner_worker" false "container uid $WORKER_UID equals workspace owner __OWNER_UID__; probe cannot prove non-owner access"
fi

# 1. The workspace ROOT must be listable (ls -la /work/task equivalence).
if LISTING=$(ls -A __FIXTURE_MOUNT__ 2>&1); then
  COUNT=$(printf '%s\n' "$LISTING" | grep -c . || true)
  check "task_root_enumerable" true "$COUNT entries as uid $WORKER_UID"
else
  check "task_root_enumerable" false "ls failed as uid $WORKER_UID: $LISTING"
fi

# 2. Expected task files must be readable.
if CONTENT=$(cat __FIXTURE_MOUNT__/MARKER 2>&1); then
  check "task_file_readable" true "MARKER read as uid $WORKER_UID"
else
  check "task_file_readable" false "read failed: $CONTENT"
fi

# 3. Subdirectories must be traversable and their contents listable/readable.
if SUB_LISTING=$(ls -A __FIXTURE_MOUNT__/__PROBE_SUBDIR__ 2>&1) \
   && SUB_CONTENT=$(cat __FIXTURE_MOUNT__/__PROBE_SUBDIR__/__PROBE_INNER__ 2>&1); then
  check "subdir_traversable" true "listed and read inner file"
else
  check "subdir_traversable" false "subdir probe failed: $SUB_LISTING $SUB_CONTENT"
fi

# 4. New files must be creatable in the workspace root.
if echo probe > __FIXTURE_MOUNT__/__PROBE_NEW__ 2>/dev/null \
   && [ -f __FIXTURE_MOUNT__/__PROBE_NEW__ ]; then
  check "file_creatable" true "created __PROBE_NEW__ as uid $WORKER_UID"
else
  check "file_creatable" false "could not create __PROBE_NEW__ as uid $WORKER_UID"
fi

# 5. Existing task files must be modifiable (runner normalizes a+rwX).
if printf 'x' >> __FIXTURE_MOUNT__/MARKER 2>/dev/null; then
  check "file_writable" true "appended to MARKER as uid $WORKER_UID"
else
  check "file_writable" false "could not modify MARKER as uid $WORKER_UID"
fi

echo "["
sed -e '$!s/$/,/' "$report"
echo "]"
""" .replace("__FIXTURE_MOUNT__", FIXTURE_MOUNT) \
    .replace("__PROBE_SUBDIR__", PROBE_SUBDIR) \
    .replace("__PROBE_INNER__", PROBE_INNER_FILE) \
    .replace("__PROBE_NEW__", PROBE_NEW_FILE)


def select_non_owner_uid(owner_uid):
    """Pick a numeric container uid GUARANTEED to differ from ``owner_uid``.

    The image's default worker account is uid 1001, but on many Linux hosts
    the workspace owner is ALSO 1000/1001, so trusting the image default does
    not prove a non-owner probe. Deterministically pick 1001 unless that is
    the owner, in which case fall back to 1000.
    """
    return 1001 if owner_uid != 1001 else 1000


def run_workspace_probe(image, workspace_dir):
    """Mount a disposable _copy_seed workspace READ-WRITE and probe it.

    Runs as a container uid deterministically chosen to differ from the
    host-side workspace owner (see :func:`select_non_owner_uid`) so the
    probe genuinely exercises non-owner access; if the uids ever match the
    probe FAILS rather than silently counting as coverage.
    """
    owner_uid = os.stat(workspace_dir).st_uid
    worker_uid = select_non_owner_uid(owner_uid)
    script = workspace_probe_script().replace("__OWNER_UID__", str(owner_uid))
    cmd = ["docker", "run", "--rm", "--entrypoint", "bash",
           "--user", f"{worker_uid}:{worker_uid}",
           "-v", f"{workspace_dir}:{FIXTURE_MOUNT}"]
    cmd += [image, "-c", script]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = proc.stdout
    start = out.find("[")
    end = out.rfind("]")
    if start == -1 or end == -1:
        print("WORKSPACE PROBE FAILED TO PARSE OUTPUT")
        print(out)
        print(proc.stderr)
        return None
    report = json.loads(out[start:end + 1])
    # Bind the uid proof into every returned record for evidence purposes.
    for item in report:
        item["workspace_owner_uid"] = owner_uid
        item["container_worker_uid"] = worker_uid
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="kilo-eval:local")
    ap.add_argument("--target-skill", default="code-review")
    ap.add_argument("--fixture", help="optional fixture dir to mount read-only")
    args = ap.parse_args()

    os.makedirs(SHARED_TMP, exist_ok=True)
    # Keep the shared staging parent private to the evaluator (same policy as
    # the runner's _mkdtemp); Docker mounts by path as root, so the restrictive
    # parent never blocks container access to mounted leaves.
    os.chmod(SHARED_TMP, 0o700)
    tmp = tempfile.mkdtemp(prefix="kilo-preflight-", dir=SHARED_TMP)
    os.chmod(tmp, 0o755)
    fixture = args.fixture or tmp
    os.makedirs(fixture, exist_ok=True)
    os.chmod(fixture, 0o755)
    open(os.path.join(fixture, "MARKER"), "w").close()

    skill_dir = os.path.join(ROOT, "skills", args.target_skill)
    skill_md = os.path.join(skill_dir, "SKILL.md")
    expected_hash = source_hash_of(skill_md) if os.path.exists(skill_md) else ""
    has_refs = os.path.isdir(os.path.join(skill_dir, "references"))

    # Baseline probe: fixture only, no .kilo/skills tree.
    print("=== baseline probe (no guidance) ===")
    base_report = run_probe(args.image, args.target_skill, fixture,
                            expected_hash, guidance_present=False,
                            refs_expected=has_refs)

    # Guided probe: stage the skill at Kilo's project-level discovery location
    # INSIDE the fixture (this is where the runner places it per condition).
    # The runner also activates it via `kilo run --command <skill>:skill`;
    # activation resolution is verified by the runner evidence, this probe
    # verifies the discovery tree boundary.
    print("=== GUIDED probe (skill at .kilo/skills/<name>/) ===")
    if os.path.exists(skill_md):
        discovery = os.path.join(fixture, ".kilo", "skills", args.target_skill)
        os.makedirs(discovery, exist_ok=True)
        shutil.copy(skill_md, os.path.join(discovery, "SKILL.md"))
        refs = os.path.join(skill_dir, "references")
        if has_refs:
            shutil.copytree(refs, os.path.join(discovery, "references"))
    target_report = run_probe(args.image, args.target_skill, fixture,
                              expected_hash, guidance_present=True,
                              refs_expected=has_refs)

    failures = []
    passed = 0
    total = 0

    def report(label, rep):
        nonlocal failures, passed, total
        if rep is None:
            failures.append(f"{label}: probe did not return a report")
            return
        for item in rep:
            total += 1
            if item["ok"]:
                passed += 1
            else:
                failures.append(f"{label}: {item['name']}")
            print(f"  [{'PASS' if item['ok'] else 'FAIL'}] {label}/{item['name']}")

    report("baseline", base_report)
    report("target", target_report)

    # Workspace mechanics probe (Linux/Docker uid-mapping regression): mount a
    # disposable workspace prepared by the runner's actual `_copy_seed`
    # READ-WRITE and verify, as the container's non-host uid, that the root is
    # ENUMERABLE, task files readable, subdirs traversable, and writes work.
    # This probes container/workspace mechanics directly; it never depends on
    # model behavior.
    print("=== WORKSPACE probe (_copy_seed workspace, non-owner container uid) ===")
    ws_source = tempfile.mkdtemp(prefix="kilo-preflight-src-", dir=SHARED_TMP)
    os.chmod(ws_source, 0o700)
    open(os.path.join(ws_source, "MARKER"), "w").close()
    os.makedirs(os.path.join(ws_source, PROBE_SUBDIR))
    with open(os.path.join(ws_source, PROBE_SUBDIR, PROBE_INNER_FILE), "w") as fh:
        fh.write("inner\n")
    ws_copy = None
    try:
        ws_copy = _copy_seed(ws_source)
        workspace_report = run_workspace_probe(args.image, ws_copy)
    finally:
        if ws_copy:
            shutil.rmtree(ws_copy, ignore_errors=True)
        shutil.rmtree(ws_source, ignore_errors=True)
    report("workspace", workspace_report)

    print(f"\nIsolation preflight: {passed}/{total} checks passed")
    if failures:
        print("FAILED CHECKS:", failures)
        sys.exit(1)
    print("ISOLATION PREFLIGHT PASSED")


if __name__ == "__main__":
    main()
