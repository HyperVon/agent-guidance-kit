#!/usr/bin/env python3
"""Docker isolation preflight (boundary probe) for the execution layer.

Starts worker containers and asserts, from INSIDE the container, that:

  BASELINE condition (no guidance mounted):
    * isolated HOME (/home/eval) with the deterministic eval git identity;
    * no ~/.ssh, no host ~/.gitconfig, no GH_TOKEN/GITHUB_TOKEN;
    * no host path leak (e.g. /Users/<user>);
    * no mounted Kilo auth store;
    * target skill guidance ABSENT at the REAL mount path
      /work/guidance/<skill>/SKILL.md;
    * the mounted fixture actually arrived (/work/task/MARKER);
    * no sibling workspace / guided output leakage.

  GUIDED condition (guidance mounted at /work/guidance/<skill>):
    * guidance PRESENT and readable at /work/guidance/<skill>/SKILL.md;
    * its sha256 matches the evaluator-computed SKILL.md hash;
    * references/ is available when the skill ships one;
    * the mounted fixture arrived (/work/task/MARKER).

This is the automated gate that must pass before any guided/baseline execution
run is trusted.

Usage:
    python3 scripts/docker_isolation_preflight.py --image kilo-eval:local --target-skill code-review
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_hashing import source_hash_of

SHARED_TMP = os.path.join(ROOT, ".docker-tmp")

GUIDANCE_MOUNT = "/work/guidance/__TARGET_SKILL__/SKILL.md"
FIXTURE_MOUNT = "/work/task"


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

# No sibling workspace / guided output leakage.
if [ -e "/work/sibling" ] || [ -e "/work/guided_output" ]; then
  check "no_sibling_leak" false
else
  check "no_sibling_leak" true
fi
""".replace("__FIXTURE_MOUNT__", FIXTURE_MOUNT) + (
        # Guided-only checks
        r"""
GUIDANCE_PATH="__GUIDANCE_MOUNT__"
if [ -e "$GUIDANCE_PATH" ]; then
  check "guidance_present" true
  if [ -r "$GUIDANCE_PATH" ]; then
    check "guidance_readable" true
  else
    check "guidance_readable" false
  fi
  ACTUAL=$(sha256sum "$GUIDANCE_PATH" | cut -d' ' -f1)
  if [ "$ACTUAL" = "__EXPECTED_HASH__" ]; then
    check "guidance_hash_match" true
  else
    check "guidance_hash_match" false
  fi
   if [ -d "__GUIDANCE_DIR__/references" ]; then
     check "references_present_if_required" true
   elif [ "__REFS_REQUIRED__" = "true" ]; then
     check "references_present_if_required" false
   else
     check "references_present_if_required" true
   fi
 else
   check "guidance_present" false
   check "guidance_readable" false
   check "guidance_hash_match" false
 fi
""".replace("__GUIDANCE_MOUNT__", GUIDANCE_MOUNT)
   .replace("__GUIDANCE_DIR__", "/work/guidance/__TARGET_SKILL__")
   .replace("__EXPECTED_HASH__", expected_hash)
    .replace("__REFS_REQUIRED__", "true" if refs_expected else "false")
        if guidance_present else
        # Baseline-only check
        r"""
if [ -e "__GUIDANCE_MOUNT__" ]; then
  check "target_skill_absent" false
else
  check "target_skill_absent" true
fi
""".replace("__GUIDANCE_MOUNT__", GUIDANCE_MOUNT)
    ) + r"""
echo "["
sed -e '$!s/$/,/' "$report"
echo "]"
"""
    return script.replace("__TARGET_SKILL__", target_skill)


def run_probe(image, target_skill, guidance_dir, fixture_dir, expected_hash,
              guidance_present, refs_expected):
    script = probe_script(target_skill, expected_hash, guidance_present,
                          refs_expected)
    cmd = ["docker", "run", "--rm", "--entrypoint", "bash",
           "-v", f"{fixture_dir}:{FIXTURE_MOUNT}:ro"]
    if guidance_dir:
        cmd += ["-v", f"{guidance_dir}:/work/guidance/{target_skill}:ro"]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="kilo-eval:local")
    ap.add_argument("--target-skill", default="code-review")
    ap.add_argument("--fixture", help="optional fixture dir to mount read-only")
    args = ap.parse_args()

    os.makedirs(SHARED_TMP, exist_ok=True)
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

    # Baseline probe: fixture only, no guidance.
    print("=== BASELINE probe (no guidance) ===")
    base_report = run_probe(args.image, args.target_skill, None, fixture,
                            expected_hash, guidance_present=False,
                            refs_expected=has_refs)
    # Guided probe: fixture + guidance mounted.
    print("=== GUIDED probe (guidance mounted) ===")
    guidance_dir = None
    if os.path.exists(skill_md):
        guidance_dir = tempfile.mkdtemp(prefix="kilo-guidance-", dir=SHARED_TMP)
        import shutil
        shutil.copy(skill_md, os.path.join(guidance_dir, "SKILL.md"))
        refs = os.path.join(skill_dir, "references")
        if has_refs:
            shutil.copytree(refs, os.path.join(guidance_dir, "references"))
    guided_report = run_probe(args.image, args.target_skill, guidance_dir,
                              fixture, expected_hash, guidance_present=True,
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
    report("guided", guided_report)

    print(f"\nIsolation preflight: {passed}/{total} checks passed")
    if failures:
        print("FAILED CHECKS:", failures)
        sys.exit(1)
    print("ISOLATION PREFLIGHT PASSED")


if __name__ == "__main__":
    main()
