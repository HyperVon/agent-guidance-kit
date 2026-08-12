"""Main entrypoint for install_skills."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .apply import apply_plan, build_plan, print_summary
from .receipts import read_json, write_new_json
from .validation import AdoptionError, validate_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan and apply receipt-aware skill adoption from Agent Guidance Kit."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Create a read-only adoption plan")
    plan_parser.add_argument("--kit-root", required=True)
    plan_parser.add_argument("--target", required=True)
    plan_parser.add_argument("--skill", action="append", required=True)
    plan_parser.add_argument(
        "--output", help="Write plan JSON to a new file; defaults to stdout"
    )

    apply_parser = subparsers.add_parser(
        "apply", help="Apply an unchanged approved plan"
    )
    apply_parser.add_argument("--kit-root", required=True)
    apply_parser.add_argument("--target", required=True)
    apply_parser.add_argument("--plan", required=True)
    apply_parser.add_argument(
        "--approve", action="store_true", help="Required explicit apply acknowledgement"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        kit_root = validate_root(Path(args.kit_root), "kit root")
        target_root = validate_root(Path(args.target), "target root")
        if args.command == "plan":
            from .validation import normalize_skills

            skills = normalize_skills(args.skill)
            plan = build_plan(kit_root, target_root, skills)
            if args.output:
                write_new_json(Path(args.output).expanduser(), plan)
                print_summary(plan)
                print(f"Plan file: {Path(args.output).expanduser()}")
            else:
                json.dump(plan, sys.stdout, indent=2, sort_keys=True)
                sys.stdout.write("\n")
            has_conflict = (
                any(item["status"] == "CONFLICT" for item in plan["skills"])
                or plan["routing"]["status"] == "CONFLICT"
                or plan["source_resolution"]["status"] in {"CONFLICT", "ASK"}
            )
            return 1 if has_conflict else 0

        if not args.approve:
            raise AdoptionError(
                "apply requires --approve after review of the exact plan"
            )
        plan = read_json(Path(args.plan).expanduser())
        receipt = apply_plan(kit_root, target_root, plan)
        print(f"Applied plan {plan['plan_id']}")
        print(f"Receipt: {receipt.relative_to(target_root)}")
        return 0
    except AdoptionError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
