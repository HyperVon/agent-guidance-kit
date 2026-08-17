#!/usr/bin/env python3
"""Docker isolation preflight (boundary probe) for the execution layer.

Starts a *baseline-style* worker container (fixture mounted read-only, NO skill
guidance, NO mounted Kilo auth store) and asserts the worker cannot see any
host secret or out-of-scope path. This is the automated gate that must pass
before any guided/baseline execution run is trusted.

Checks (see isolation-protocol.md):
  * isolated HOME (/home/eval) with the deterministic eval git identity, NOT the
    host author;
  * no ~/.ssh, no host ~/.gitconfig (only the in-image dummy is allowed);
  * no GH_TOKEN / GITHUB_TOKEN in the environment;
  * no host path leak (e.g. /Users/<user>);
  * no mounted Kilo auth store (no ~/.config/kilo/auth.json);
  * target skill guidance absent in the baseline mount;
  * no sibling workspace / guided output leakage.

Usage:
    python3 scripts/docker_isolation_preflight.py --image kilo-eval:local
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Docker Desktop on macOS only bind-mounts paths under its shared roots (the
# project under /Users). Use a repo-relative temp dir so the fixture mount
# actually reaches the container.
SHARED_TMP = os.path.join(ROOT, ".docker-tmp")


def probe_script(target_skill, sibling_marker):
    """Shell commands run INSIDE the container; emit a JSON report on stdout."""
    return r"""
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

# Target skill guidance must be absent in the baseline mount.
if [ -e "/work/skills/__TARGET_SKILL__/SKILL.md" ]; then
  check "target_skill_absent" false
else
  check "target_skill_absent" true
fi

# No sibling workspace / guided output leakage.
if [ -e "/work/sibling" ] || [ -e "/work/guided_output" ]; then
  check "no_sibling_leak" false
else
  check "no_sibling_leak" true
fi

# Positive check: the fixture we mounted must actually have arrived. If the mount
# is empty (e.g. Docker Desktop not sharing the host path), every other check is
# meaningless.
if [ -e "/work/input/MARKER" ]; then
  check "mount_arrived" true
else
  check "mount_arrived" false
fi

echo "["
sed -e '$!s/$/,/' "$report"
echo "]"
"""

PROBE = probe_script("{target_skill}", "{sibling_marker}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="kilo-eval:local")
    ap.add_argument("--target-skill", default="code-review")
    ap.add_argument("--fixture", help="optional fixture dir to mount read-only")
    args = ap.parse_args()

    probe = PROBE.replace("__TARGET_SKILL__", args.target_skill)
    os.makedirs(SHARED_TMP, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="kilo-preflight-", dir=SHARED_TMP)
    os.chmod(tmp, 0o755)
    fixture = args.fixture or tmp
    os.makedirs(fixture, exist_ok=True)
    os.chmod(fixture, 0o755)
    open(os.path.join(fixture, "MARKER"), "w").close()

    cmd = ["docker", "run", "--rm", "--entrypoint", "bash",
           "-v", f"{fixture}:/work/input:ro",
           args.image, "-c", probe]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = proc.stdout
    # Extract the JSON array we echoed.
    start = out.find("[")
    end = out.rfind("]")
    failures = []
    passed = 0
    if start == -1 or end == -1:
        print("PREFLOW FAILED TO PARSE OUTPUT")
        print(out)
        print(proc.stderr)
        sys.exit(1)
    report = json.loads(out[start:end + 1])
    for item in report:
        if item["ok"]:
            passed += 1
        else:
            failures.append(item["name"])
        print(f"  {'PASS' if item['ok'] else 'FAIL'}: {item['name']}")
    print(f"\nIsolation preflight: {passed}/{len(report)} checks passed")
    if failures:
        print("FAILED CHECKS:", failures)
        sys.exit(1)
    print("ISOLATION PREFLIGHT PASSED")


if __name__ == "__main__":
    main()
