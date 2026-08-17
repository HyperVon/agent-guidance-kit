#!/usr/bin/env python3
"""Generate the routing catalog (the harness routing projection) for an eval run.

The catalog is the *routing surface* — the discoverable skill name + description
for every skill. It is intentionally NOT part of any frozen task fixture: the
same task fixture is reused across routing conditions, while only the catalog
differs.

Two conditions are supported:

* target-present (default): the catalog contains every skill, including the
  target under test.
* target-absent (``--target-absent <skill>``): the target skill is removed, so
  the harness cannot select it. This measures whether adding the target entry
  changes correct selection.

Usage:
    python3 scripts/build_routing_catalog.py
    python3 scripts/build_routing_catalog.py --target-absent code-review
    python3 scripts/build_routing_catalog.py --format markdown --out catalog.md
"""
import argparse
import glob
import os
import re
import sys

try:
    import yaml  # PyYAML, preferred for correct YAML frontmatter parsing.
    _HAVE_YAML = True
except Exception:  # pragma: no cover - fallback path only when PyYAML missing.
    yaml = None
    _HAVE_YAML = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def extract_frontmatter(text):
    """Return the raw YAML block between the leading `---` fences, else None."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return text[3:end]


def parse_frontmatter(path):
    """Parse a SKILL.md frontmatter; return (name, description).

    Uses PyYAML when available (correctly handles folded ``>-`` and literal ``|``
    block scalars, quotes, etc.). Falls back to a small frontmatter parser that
    supports those same constructs when PyYAML is not installed.
    """
    text = open(path, encoding="utf-8").read()
    block = extract_frontmatter(text)
    if block is None:
        return None, None
    data = load_frontmatter(block)
    if not isinstance(data, dict):
        return None, None
    name = data.get("name")
    desc = data.get("description") or ""
    if isinstance(desc, (list, dict)):
        desc = ""  # unexpected shape; let the caller surface a missing description.
    return name, desc


def load_frontmatter(block):
    if _HAVE_YAML:
        try:
            return yaml.safe_load(block)
        except Exception:
            pass
    return _minimal_yaml(block)


def _strip_scalar(val):
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val


def _join_block_scalar(style, body_lines):
    """Join indented block-scalar lines per YAML folded/literal semantics."""
    # Drop leading/trailing fully-blank lines from the block body.
    while body_lines and body_lines[0].strip() == "":
        body_lines.pop(0)
    while body_lines and body_lines[-1].strip() == "":
        body_lines.pop()
    if not body_lines:
        return ""
    # Dedent by the first non-empty line's indentation.
    indents = [len(ln) - len(ln.lstrip(" ")) for ln in body_lines if ln.strip() != ""]
    indent = min(indents) if indents else 0
    dedented = [ln[indent:] if len(ln) >= indent else ln for ln in body_lines]
    strip = style.endswith("-")      # strip trailing newline(s)
    keep_all = style.endswith("+")    # keep all trailing newlines
    if style[0] == ">":
        # Folded: join non-empty lines with spaces, blank lines -> newline.
        out = []
        for ln in dedented:
            if ln.strip() == "":
                out.append("\n")
            else:
                out.append(ln + " ")
        text = "".join(out).rstrip(" ")
        if strip:
            return text.rstrip("\n")
        if keep_all:
            return text
        return text.rstrip("\n") + "\n"
    else:
        # Literal: preserve line breaks.
        text = "\n".join(dedented)
        if strip:
            return text.rstrip("\n")
        if keep_all:
            return text
        return text + "\n"


def _minimal_yaml(block):
    """Minimal YAML frontmatter parser: top-level ``key: value`` with support for
    plain, folded (``>``/``>-``/``>+``), and literal (``|``/``|-``/``|+``) scalars,
    quoted strings, and ``null``/booleans."""
    data = {}
    lines = block.splitlines()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if line.strip() == "" or line.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([\w.-]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">", ">-", ">+", "|", "|-", "|+", ">-", ">+"):
            i += 1
            body = []
            while i < n and (lines[i].startswith(" ") or lines[i] == ""):
                body.append(lines[i])
                i += 1
            data[key] = _join_block_scalar(val, body)
        elif val == "":
            # Could be a nested mapping or an empty value; only support empty.
            data[key] = None
            i += 1
        elif val in ("null", "~"):
            data[key] = None
            i += 1
        elif val in ("true", "false"):
            data[key] = val == "true"
            i += 1
        else:
            data[key] = _strip_scalar(val)
            i += 1
    return data


def build(target_absent=None):
    rows = []
    for sk in sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md"))):
        name, desc = parse_frontmatter(sk)
        if not name:
            continue
        if target_absent and name == target_absent:
            continue
        rows.append((name, desc or ""))
    return rows


def render_markdown(rows):
    out = ["# Skill catalog", "",
           "Neutral routing surface generated by "
           "`scripts/build_routing_catalog.py` from each skill's frontmatter.",
           "It is the harness routing projection, not part of any task fixture.", ""]
    for name, desc in rows:
        out.append(f"- **{name}** — {desc}")
    return "\n".join(out) + "\n"


def render_tsv(rows):
    return "".join(f"{name}\t{desc}\n" for name, desc in rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-absent", help="skill to omit (baseline condition)")
    ap.add_argument("--format", choices=["markdown", "tsv"], default="markdown")
    ap.add_argument("--out", help="write to this path instead of stdout")
    args = ap.parse_args()

    rows = build(target_absent=args.target_absent)
    text = render_markdown(rows) if args.format == "markdown" else render_tsv(rows)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text)
        print(f"wrote {args.out} ({len(rows)} skills"
              + (f", target '{args.target_absent}' absent" if args.target_absent else "") + ")",
              file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
