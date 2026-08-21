#!/usr/bin/env python3
"""Run a harness-neutral smoke or qualification execution comparison.

This is the generic counterpart to the repository's optional legacy
``run_execution_eval.py`` Docker/Kilo adapter.  The evaluator prepares the
fixture and independent condition workspaces; ``--harness-command-json`` performs
the actual worker/session invocation using the JSON contract in
``docs/evaluations/harness-adapter.md``.

Examples::

    python3 scripts/run_harness_eval.py \
      --skill code-review --case-id 5 --protocol qualification --reps 1 \
      --harness-command-json '["python3","path/to/adapter.py"]'

    python3 scripts/run_harness_eval.py \
      --skill code-review --case-id 5 --protocol smoke --conditions target \
      --harness-command-json '["python3","path/to/adapter.py"]'

No follow-up placebo or confirmation run is launched implicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import evaluation_harness
from eval_hashing import HASH_PREFIX, materialize_fixture_seed
from evaluation_protocols import (EVIDENCE_PROTOCOL_VERSION,
                                  PROTOCOL_NAMES, RESULT_SCHEMA_VERSION,
                                  is_safe_skill_name, resolve_path_within,
                                  validate_declaration)


def _load_case(skill: str, case_id: int) -> tuple[dict, str, str, str, str]:
    if not is_safe_skill_name(skill):
        raise ValueError(f"invalid skill name {skill!r}")
    skill_dir = os.path.join(ROOT, "skills", skill)
    evals_path = os.path.join(skill_dir, "evals", "evals.json")
    try:
        data = json.load(open(evals_path, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read skill evals: {exc}") from exc
    case = next((item for item in data.get("evals", [])
                 if item.get("id") == case_id), None)
    if case is None or "execution" not in case.get("evaluation_modes", []):
        raise ValueError(f"case {case_id} is not an execution case")
    fixture = case.get("fixture") or {}
    if fixture.get("status") != "ready":
        raise ValueError("execution requires a frozen ready fixture")
    fixture_dir = resolve_path_within(skill_dir, fixture.get("path"))
    if fixture_dir is None:
        raise ValueError("fixture path must remain under the skill directory")
    if fixture.get("type") == "generator" and resolve_path_within(
            fixture_dir, fixture.get("source", "setup.sh")) is None:
        raise ValueError("generator source path must remain under the fixture")
    return (
        case,
        evals_path,
        fixture_dir,
        fixture.get("source", "setup.sh"),
        fixture.get("invocation", "bash setup.sh"),
    )


def _expected_fixture_hash(fixture: dict) -> str | None:
    return (fixture.get("output_hash") if fixture.get("type") == "generator"
            else fixture.get("content_hash"))


def build_evidence(args, adapter: evaluation_harness.CommandHarnessAdapter) -> dict:
    skill_dir = os.path.join(ROOT, "skills", args.skill)
    case, evals_path, fixture_dir, source, invocation = _load_case(
        args.skill, args.case_id)
    fixture = case["fixture"]
    conditions = args.conditions
    protocol_errors = validate_declaration(args.protocol, conditions, args.reps)
    if protocol_errors:
        raise ValueError("; ".join(protocol_errors))
    if "placebo" in conditions:
        if not args.placebo_skill:
            raise ValueError("--placebo-skill is required for a placebo condition")
        if args.placebo_skill == args.skill:
            raise ValueError("--placebo-skill must differ from --skill")
        if not is_safe_skill_name(args.placebo_skill):
            raise ValueError(f"invalid placebo skill name {args.placebo_skill!r}")
        placebo_dir = os.path.join(ROOT, "skills", args.placebo_skill)
        if not os.path.isfile(os.path.join(placebo_dir, "SKILL.md")):
            raise ValueError(f"placebo skill does not exist: {args.placebo_skill}")
    else:
        placebo_dir = None
    expected_fixture_hash = _expected_fixture_hash(fixture)
    if not expected_fixture_hash:
        raise ValueError("fixture is missing its frozen content/output hash")
    target_hash = evaluation_harness.skill_tree_hash(skill_dir)
    if target_hash is None:
        raise ValueError(f"skill has no hashable guidance tree: {skill_dir}")

    evidence = {
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "evidence_protocol_version": EVIDENCE_PROTOCOL_VERSION,
        "adapter_protocol_version": evaluation_harness.ADAPTER_PROTOCOL,
        "evidence_type": "execution",
        "protocol": args.protocol,
        "harness": {
            "name": adapter.name,
            "adapter_protocol": evaluation_harness.ADAPTER_PROTOCOL,
        },
        "skill": args.skill,
        "case_id": args.case_id,
        "model": args.model,
        "conditions": list(conditions),
        "target_skill_source_path": f"skills/{args.skill}",
        "target_skill_content_hash": target_hash,
        "target_guidance_identity": args.skill,
        "target_guidance_id": args.skill,
        "target_guidance_hash": target_hash,
        "target_guidance_present": "adapter guidance probe required",
        "target_absent_in_baseline": (
            "baseline adapter reported no target guidance"
            if "baseline" in conditions else None),
        "baseline_guidance_absent": (
            "baseline adapter reported no guidance"
            if "baseline" in conditions else None),
        "placebo_skill": args.placebo_skill if "placebo" in conditions else None,
        "placebo_skill_content_hash": (
            evaluation_harness.skill_tree_hash(placebo_dir)
            if placebo_dir else None),
        "placebo_guidance_identity": args.placebo_skill if placebo_dir else None,
        "placebo_guidance_id": args.placebo_skill if placebo_dir else None,
        "placebo_guidance_hash": (
            evaluation_harness.skill_tree_hash(placebo_dir)
            if placebo_dir else None),
        "expected_fixture_hash": expected_fixture_hash,
        "fixture_source_path": os.path.relpath(evals_path, ROOT),
        "fixture_path": os.path.normpath(os.path.relpath(fixture_dir, ROOT)),
        "fixture_source_hash": HASH_PREFIX + hashlib.sha256(
            open(evals_path, "rb").read()).hexdigest(),
        "canonical_task_seed_hash": None,
        "repetitions": [],
        "preserved_artifacts": [],
    }
    activation_specs = {
        "target": {"skill_name": args.skill, "source_dir": skill_dir},
        "baseline": None,
    }
    if placebo_dir:
        activation_specs["placebo"] = {
            "skill_name": args.placebo_skill, "source_dir": placebo_dir,
        }
    preserve_requested = bool(getattr(args, "preserve_failed_artifacts", False))
    for index in range(args.reps):
        seed, _ = materialize_fixture_seed(
            fixture_dir, fixture.get("type"), source, invocation)
        workspaces = {}
        preserve = preserve_requested
        try:
            seed_hash = HASH_PREFIX + evaluation_harness.hash_task_workspace(
                seed, evaluation_harness.RUNTIME_TREATMENT_PATHS)
            if seed_hash != expected_fixture_hash:
                raise ValueError(
                    "materialized seed task hash does not match frozen fixture: "
                    f"{seed_hash!r} != {expected_fixture_hash!r}")
            repetition, canonical, workspaces = evaluation_harness.run_condition_repetition(
                index, conditions, case["prompt"], seed, activation_specs,
                args.model, adapter, protocol=args.protocol, case_id=args.case_id)
            evidence["canonical_task_seed_hash"] = canonical
            evidence["repetitions"].append(repetition)
            preserve = preserve or any(
                condition.get("run_status") != "success" or
                condition.get("returncode") != 0
                for condition in repetition["conditions"].values()
            )
        except Exception:
            preserve = True
            raise
        finally:
            if preserve:
                evidence["preserved_artifacts"].extend(
                    [*workspaces.values(), seed])
            else:
                for workspace in workspaces.values():
                    evaluation_harness.cleanup_workspace(workspace)
                shutil.rmtree(seed, ignore_errors=True)
    return evidence


def _conditions(value: str) -> list[str]:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        raise argparse.ArgumentTypeError("at least one condition is required")
    if len(set(parts)) != len(parts):
        raise argparse.ArgumentTypeError("conditions must be unique")
    return parts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--case-id", type=int, required=True)
    parser.add_argument("--protocol", choices=sorted(PROTOCOL_NAMES - {"regression"}),
                        default="qualification")
    parser.add_argument("--conditions", type=_conditions,
                        default=["target", "baseline"])
    parser.add_argument("--placebo-skill")
    parser.add_argument("--model", default=None)
    parser.add_argument("--harness-command-json", required=True,
                        type=evaluation_harness.parse_command_argv_json,
                        help="JSON-encoded executable argv; shell syntax is not interpreted")
    parser.add_argument("--harness-name", default="external")
    parser.add_argument("--harness-timeout", type=int, default=1200)
    parser.add_argument("--harness-cwd")
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--preserve-failed-artifacts", action="store_true",
                        help="preserve evaluator workspaces and seeds for debugging")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    try:
        adapter = evaluation_harness.CommandHarnessAdapter(
            args.harness_command_json, name=args.harness_name,
            timeout_seconds=args.harness_timeout, cwd=args.harness_cwd)
        evidence = build_evidence(args, adapter)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    out = args.out or os.path.join(
        ROOT, ".eval-evidence",
        f"exec-neutral-{args.skill}-case{args.case_id}.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(evidence, handle, indent=2)
    print(f"wrote evidence: {out}")
    for repetition in evidence["repetitions"]:
        states = " ".join(
            f"{name}[{repetition['conditions'][name]['run_status']}]"
            for name in args.conditions)
        print(f"rep{repetition['rep']}: {states} "
              f"distinct={repetition['distinct_workers']} "
              f"task_hash={repetition['natural_task_hash'][:10]}")


if __name__ == "__main__":
    main()
