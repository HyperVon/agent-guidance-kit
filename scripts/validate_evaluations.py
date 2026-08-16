#!/usr/bin/env python3
"""Validation gate for the skill evaluation artifacts.

Checks structure, schema, fixture references, link integrity, personal-data
leaks, and matrix/summary sync. Exits non-zero on hard failures.

Run from the repo root:  python3 scripts/validate_evaluations.py
"""
import sys, os, json, glob, re, hashlib, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVALS_DIR = os.path.join(ROOT, "docs", "evaluations")

ALLOWED_KINDS = {"matching", "neighboring", "ambiguous", "edge"}
ALLOWED_MODES = {"routing", "execution"}
ALLOWED_FIXTURE_STATUS = {"ready", "designed_only"}
ALLOWED_FIXTURE_TYPES = {"committed", "generator"}

# Personal / secret patterns that must never appear in committed fixtures/results.
LEAK_PATTERNS = [
    r"cvonness", r"charlesv", r"hypervon", r"gmail\.com",
    r"/Users/\w+", r"github\.com/HyperVon",
    r"cvonness@",
]

errors = []
warnings = []

def err(msg): errors.append(msg)
def warn(msg): warnings.append(msg)

def canonical_hash(path, ftype):
    """Deterministic sha256 over fixture contents.

    committed: all files recursively (sorted by relative path), each as
               relpath + ':' + sha256(file contents).
    generator: the generator source file only (setup.sh).
    """
    h = hashlib.sha256()
    if ftype == "generator":
        src = os.path.join(path, "setup.sh")
        if not os.path.exists(src):
            return None
        h.update(("setup.sh:" + hashlib.sha256(open(src,'rb').read()).hexdigest()).encode())
        return h.hexdigest()
    files = []
    for root, _, names in os.walk(path):
        for n in names:
            full = os.path.join(root, n)
            rel = os.path.relpath(full, path)
            if rel.startswith(".git"): continue
            files.append(rel)
    for rel in sorted(files):
        full = os.path.join(path, rel)
        fh = hashlib.sha256(open(full,'rb').read()).hexdigest()
        h.update((rel + ":" + fh).encode())
    return h.hexdigest()

def check_eval_files():
    paths = sorted(glob.glob(os.path.join(ROOT, "skills", "*", "evals", "evals.json")))
    if not paths:
        err("no evals.json found")
    skill_names = set()
    for f in paths:
        rel = os.path.relpath(f, ROOT)
        try:
            d = json.load(open(f))
        except Exception as e:
            err(f"{rel}: JSON parse error: {e}"); continue
        if "skill_name" not in d:
            err(f"{rel}: missing skill_name")
        else:
            skill_names.add(d["skill_name"])
            expected = os.path.basename(os.path.dirname(os.path.dirname(f)))
            if d["skill_name"] != expected:
                err(f"{rel}: skill_name '{d['skill_name']}' != dir name '{expected}'")
        evals = d.get("evals")
        if not isinstance(evals, list) or not evals:
            err(f"{rel}: evals missing/empty"); continue
        seen_ids = set()
        for c in evals:
            cid = c.get("id")
            if cid in seen_ids:
                err(f"{rel}: duplicate case id {cid}")
            seen_ids.add(cid)
            for k in ("kind","prompt","expected_output","assertions","evaluation_modes","requires_catalog","fixture"):
                if k not in c:
                    err(f"{rel}: case {cid} missing '{k}'")
            if c.get("kind") not in ALLOWED_KINDS:
                err(f"{rel}: case {cid} bad kind '{c.get('kind')}'")
            modes = c.get("evaluation_modes")
            if not isinstance(modes, list) or not modes or not set(modes) <= ALLOWED_MODES:
                err(f"{rel}: case {cid} bad evaluation_modes {modes}")
            if not isinstance(c.get("requires_catalog"), bool):
                err(f"{rel}: case {cid} requires_catalog not bool")
            if not isinstance(c.get("prompt"), str) or not c["prompt"].strip():
                err(f"{rel}: case {cid} empty prompt")
            if not isinstance(c.get("expected_output"), str) or not c["expected_output"]:
                err(f"{rel}: case {cid} empty expected_output")
            a = c.get("assertions")
            if not isinstance(a, list) or not a or not all(isinstance(x,str) and x.strip() for x in a):
                err(f"{rel}: case {cid} bad assertions")
            fx = c.get("fixture")
            if not isinstance(fx, dict) or fx.get("status") not in ALLOWED_FIXTURE_STATUS:
                err(f"{rel}: case {cid} bad fixture.status")
                continue
            if fx["status"] == "designed_only":
                if "path" in fx:
                    warn(f"{rel}: case {cid} designed_only but has path")
                continue
            # ready
            if fx.get("type") not in ALLOWED_FIXTURE_TYPES:
                err(f"{rel}: case {cid} ready fixture missing type")
                continue
            p = fx.get("path")
            if not p:
                err(f"{rel}: case {cid} ready fixture missing path"); continue
            fpath = os.path.join(os.path.dirname(os.path.dirname(f)), p)
            if not os.path.exists(fpath):
                err(f"{rel}: case {cid} fixture path missing: {p}"); continue
            ch = fx.get("content_hash", "")
            if not (isinstance(ch, str) and ch.startswith("sha256:") and len(ch) > 7):
                err(f"{rel}: case {cid} fixture missing/invalid content_hash")
            else:
                computed = canonical_hash(fpath, fx.get("type"))
                if computed and ch[7:] != computed:
                    err(f"{rel}: case {cid} fixture hash mismatch (recorded {ch[7:][:8]}.. computed {computed[:8]}..)")
    return skill_names

def check_leaks():
    targets = []
    for ext in ("md","json"):
        targets += glob.glob(os.path.join(ROOT, "docs", "evaluations", "**", f"*.{ext}"), recursive=True)
        targets += glob.glob(os.path.join(ROOT, "skills", "*", "evals", "**", f"*.{ext}"), recursive=True)
    targets += glob.glob(os.path.join(ROOT, "skills", "*", "evals", "files", "**", "*"), recursive=True)
    for t in set(targets):
        if os.path.isdir(t): continue
        try:
            text = open(t, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for pat in LEAK_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                err(f"LEAK {os.path.relpath(t,ROOT)}: matches /{pat}/")

def check_links():
    md_files = glob.glob(os.path.join(ROOT, "docs","evaluations","**","*.md"), recursive=True)
    md_files += glob.glob(os.path.join(ROOT,"skills","skill-evaluation","**","*.md"), recursive=True)
    for mf in md_files:
        text = open(mf, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
            link = m.group(2)
            if link.startswith(("http://","https://","mailto:")): continue
            if link.startswith("#"): continue
            anchor = ""
            if "#" in link:
                link, anchor = link.split("#",1)
            if not link: continue
            target = os.path.normpath(os.path.join(os.path.dirname(mf), link))
            if not os.path.exists(target):
                err(f"{os.path.relpath(mf,ROOT)}: broken link {link}")

def check_results_exploratory():
    res_dir = os.path.join(EVALS_DIR, "results")
    if not os.path.isdir(res_dir): return
    for rf in glob.glob(os.path.join(res_dir, "*.md")):
        text = open(rf, encoding="utf-8", errors="replace").read()
        base = os.path.basename(rf)
        # These four are the historical exploratory pilots; must not claim validity.
        if base in ("code-review.md","git-github-workflow.md","review-feedback-resolution.md","security-review.md"):
            if "protocol_status: invalid" not in text and "exploratory" not in text.lower():
                err(f"{base}: historical pilot must be marked exploratory/invalid")
            if "✓" in text:
                err(f"{base}: must not present an overloaded ✓ validation")
            if "authoritative" in text.lower():
                err(f"{base}: must not use 'authoritative' for a single pilot")

def check_matrix_sync(skill_names):
    matrix = os.path.join(EVALS_DIR, "validation-matrix.md")
    if not os.path.exists(matrix): return
    text = open(matrix, encoding="utf-8", errors="replace").read()
    # every skill dir must appear as a link target
    for sn in skill_names:
        if f"skills/{sn}/evals/evals.json" not in text:
            err(f"matrix missing row for skill '{sn}'")
    # result links must resolve
    for m in re.finditer(r"\]\((results/[^)]+)\)", text):
        tgt = os.path.join(EVALS_DIR, m.group(1))
        if not os.path.exists(tgt):
            err(f"matrix broken result link {m.group(1)}")

def main():
    print("=== Evaluating skill eval artifacts ===")
    skill_names = check_eval_files()
    check_leaks()
    check_links()
    check_results_exploratory()
    check_matrix_sync(skill_names)

    print(f"\nSkills with evals.json: {len(skill_names)}")
    print(f"Hard errors: {len(errors)}")
    print(f"Warnings:   {len(warnings)}")
    for w in warnings:
        print("  WARN:", w)
    for e in errors:
        print("  ERR :", e)
    if errors:
        print("\nVALIDATION FAILED")
        sys.exit(1)
    print("\nVALIDATION PASSED")
    sys.exit(0)

if __name__ == "__main__":
    main()
