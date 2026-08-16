#!/usr/bin/env python3
"""Fill content_hash for every ready fixture using the validator's canonical hash.

Run from repo root:  python3 scripts/hash_fixtures.py
Idempotent: recomputes and overwrites content_hash for status=="ready" fixtures.
"""
import os, json, glob, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_evaluations import canonical_hash, ROOT

changed = 0
for f in sorted(glob.glob(os.path.join(ROOT, "skills", "*", "evals", "evals.json"))):
    d = json.load(open(f))
    dirty = False
    for c in d["evals"]:
        fx = c.get("fixture", {})
        if fx.get("status") != "ready":
            continue
        fpath = os.path.join(os.path.dirname(os.path.dirname(f)), fx.get("path", ""))
        if not os.path.exists(fpath):
            print("MISSING FIXTURE DIR:", fpath); continue
        h = canonical_hash(fpath, fx.get("type"))
        if not h:
            print("CANNOT HASH:", fpath); continue
        newhash = "sha256:" + h
        if fx.get("content_hash") != newhash:
            fx["content_hash"] = newhash
            dirty = True
            changed += 1
    if dirty:
        json.dump(d, open(f, "w"), indent=2)
        open(f, "a").write("\n")
print(f"Updated {changed} fixture hashes.")
