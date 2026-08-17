#!/usr/bin/env python3
"""Fill fixture hashes for every ready fixture.

For `committed` fixtures, `content_hash` is the recursive file hash.
For `generator` fixtures, `content_hash` mirrors the deterministic generated
`output_hash`, and `source_hash` covers the generator source.

Run from repo root:  python3 scripts/hash_fixtures.py
Idempotent: recomputes and overwrites hashes for status=="ready" fixtures.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_hashing import HASH_PREFIX, canonical_hash, source_hash_of

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
changed = 0

for f in sorted(glob.glob(os.path.join(ROOT, "skills", "*", "evals", "evals.json"))):
    d = json.load(open(f))
    dirty = False
    for c in d["evals"]:
        fx = c.get("fixture", {})
        if fx.get("status") != "ready":
            continue
        ftype = fx.get("type")
        fpath = os.path.join(os.path.dirname(os.path.dirname(f)), fx.get("path", ""))
        if not os.path.exists(fpath):
            print("MISSING FIXTURE DIR:", fpath)
            continue
        if ftype == "generator":
            src = fx.get("source", "setup.sh")
            inv = fx.get("invocation", "bash setup.sh")
            src_path = os.path.join(fpath, src)
            sh = source_hash_of(src_path)
            oh = canonical_hash(fpath, "generator", src, inv)
            new_content = HASH_PREFIX + oh
            if fx.get("source_hash") != HASH_PREFIX + sh:
                fx["source_hash"] = HASH_PREFIX + sh
                dirty = True
            if fx.get("output_hash") != new_content or fx.get("content_hash") != new_content:
                fx["output_hash"] = new_content
                fx["content_hash"] = new_content
                dirty = True
        else:
            h = canonical_hash(fpath, "committed")
            newhash = HASH_PREFIX + h
            if fx.get("content_hash") != newhash:
                fx["content_hash"] = newhash
                dirty = True
    if dirty:
        json.dump(d, open(f, "w"), indent=2)
        open(f, "a").write("\n")
        changed += 1
        print("updated", os.path.relpath(f, ROOT))
print(f"Updated {changed} evals.json files.")
