#!/usr/bin/env python3
"""Run a cheap, harness-neutral candidate-vs-reference comparison.

The evaluator owns the frozen task, independent workspaces, hashes, and
evidence.  A caller-supplied harness adapter owns model/session execution and
skill activation.  Both conditions receive a version of the same skill;
neither condition is a no-skill baseline.

For regression, the reference revision supplies the shared frozen task. The
candidate and reference case declarations are both anchored into the evidence,
but only the reference fixture is materialized; candidate fixture generators
are never executed by this evaluator. This keeps candidate-controlled code out
of the evaluator process while preserving revision-local provenance.

Example::

    python3 scripts/run_skill_regression_eval.py \
      --skill code-review --reference <git-sha> --candidate HEAD \
      --case-id 5 --reps 1 \
      --harness-command 'python3 path/to/adapter.py'

The command never escalates to placebo or repeated confirmation.  Increase
``--reps`` or run the separate confirmation protocol only when the observed
revision difference warrants it.

The adapter receives one JSON request on stdin and must return one JSON object
on stdout.  See ``scripts/evaluation_harness.py`` for the neutral contract.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import evaluation_harness
from evaluation.regression import (
    REGRESSION_RUNNER_VERSION,
    case_set_hash,
)
from eval_hashing import HASH_PREFIX, materialize_fixture_seed
from evaluation_protocols import resolve_path_within, validate_declaration


def resolve_revision(revision: str) -> str:
    """Resolve a user-supplied Git revision to a commit SHA."""

    try:
        return subprocess.check_output(
            ["git", "-C", ROOT, "rev-parse", f"{revision}^{{commit}}"],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"cannot resolve Git revision {revision!r}: {exc.output.strip()}") from exc


def _safe_extract_archive(data: bytes, destination: str, expected_prefix: str) -> None:
    """Extract only regular files/directories below the requested skill path."""

    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for member in archive.getmembers():
            name = member.name.replace("\\", "/")
            if not name.startswith(expected_prefix + "/"):
                if (member.isdir() and
                        (name == expected_prefix or
                         expected_prefix.startswith(name + "/"))):
                    os.makedirs(os.path.join(destination, name), exist_ok=True)
                    continue
                raise ValueError(f"Git archive contained unexpected path {name!r}")
            relative = name[len(expected_prefix) + 1:]
            if relative.startswith("/") or ".." in relative.split("/"):
                raise ValueError(f"Git archive contained unsafe path {name!r}")
            if not relative:
                if not member.isdir():
                    raise ValueError(f"Git archive contained unsafe root entry {name!r}")
                os.makedirs(os.path.join(destination, expected_prefix), exist_ok=True)
                continue
            # Preserve the archived source prefix so the extracted tree has
            # the same ``skills/<name>/`` shape as the repository checkout.
            target = os.path.join(destination, expected_prefix, relative)
            if member.isdir():
                os.makedirs(target, exist_ok=True)
            elif member.isreg():
                os.makedirs(os.path.dirname(target), exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError(f"Git archive member could not be read: {name!r}")
                with open(target, "wb") as output:
                    shutil.copyfileobj(source, output)
            else:
                raise ValueError(f"Git archive contains unsupported entry {name!r}")


def materialize_skill_revision(revision: str, skill: str) -> tuple[str, str]:
    """Materialize ``skills/<skill>`` from a commit into an ignored temp root."""

    if (not skill or skill in {".", ".."} or os.path.basename(skill) != skill
            or "/" in skill or "\\" in skill):
        raise ValueError(f"invalid skill name {skill!r}")
    resolved = resolve_revision(revision)
    prefix = f"skills/{skill}"
    try:
        archive = subprocess.check_output(
            ["git", "-C", ROOT, "archive", "--format=tar", resolved, prefix],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"cannot archive skill {skill!r} from {resolved}: {exc.output.decode(errors='replace').strip()}"
        ) from exc
    root = evaluation_harness.make_temp_dir("regression-skill-")
    try:
        _safe_extract_archive(archive, root, prefix)
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise
    skill_dir = os.path.join(root, "skills", skill)
    if not os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
        shutil.rmtree(root, ignore_errors=True)
        raise ValueError(f"Git revision {resolved} does not contain skills/{skill}/SKILL.md")
    return root, resolved


def _load_case(skill_dir: str, case_id: int) -> tuple[dict, str, str, str, str]:
    evals_path = os.path.join(skill_dir, "evals", "evals.json")
    try:
        data = json.load(open(evals_path, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read candidate evals: {exc}") from exc
    case = next((item for item in data.get("evals", []) if item.get("id") == case_id), None)
    if case is None or "execution" not in case.get("evaluation_modes", []):
        raise ValueError(f"case {case_id} is not an execution case in the candidate revision")
    fixture = case.get("fixture") or {}
    if fixture.get("status") != "ready":
        raise ValueError("regression requires a frozen ready fixture in the candidate revision")
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


def _revision_tree_hash(skill_dir: str) -> str:
    value = evaluation_harness.skill_tree_hash(skill_dir)
    if value is None:
        raise ValueError(f"skill directory has no hashable SKILL.md tree: {skill_dir}")
    return value


def _case_anchor(skill: str, case: dict, evals_path: str) -> dict:
    """Capture revision-local case/fixture provenance without running it."""

    fixture = case.get("fixture") or {}
    fixture_type = fixture.get("type")
    expected_fixture_hash = (
        fixture.get("output_hash") if fixture_type == "generator"
        else fixture.get("content_hash")
    )
    if not expected_fixture_hash:
        raise ValueError("fixture is missing its frozen content/output hash")
    fixture_rel = os.path.normpath(os.path.join(
        f"skills/{skill}", fixture.get("path", "")))
    generator_source_hash = None
    if fixture_type == "generator":
        source_path = resolve_path_within(
            os.path.join(os.path.dirname(evals_path), ".."),
            os.path.join(fixture.get("path", ""),
                         fixture.get("source", "setup.sh")),
        )
        if source_path is None or not os.path.isfile(source_path):
            raise ValueError("generator source path must remain under the skill directory")
        generator_source_hash = HASH_PREFIX + hashlib.sha256(
            open(source_path, "rb").read()).hexdigest()
    return {
        "source_path": f"skills/{skill}/evals/evals.json",
        "source_hash": HASH_PREFIX + hashlib.sha256(
            open(evals_path, "rb").read()).hexdigest(),
        "prompt_hash": hashlib.sha256(
            case.get("prompt", "").encode()).hexdigest(),
        "fixture_type": fixture_type,
        "fixture_path": fixture_rel,
        "fixture_hash": expected_fixture_hash,
        "generator_source_hash": generator_source_hash,
    }


def build_evidence(args, candidate_dir: str, reference_dir: str,
                   candidate_revision: str, reference_revision: str,
                   adapter: evaluation_harness.CommandHarnessAdapter) -> dict:
    candidate_skill_dir = os.path.join(candidate_dir, "skills", args.skill)
    reference_skill_dir = os.path.join(reference_dir, "skills", args.skill)
    candidate_case, candidate_evals_path, _, _, _ = _load_case(
        candidate_skill_dir, args.case_id)
    reference_case, reference_evals_path, fixture_dir, source, invocation = _load_case(
        reference_skill_dir, args.case_id)
    candidate_anchor = _case_anchor(
        args.skill, candidate_case, candidate_evals_path)
    reference_anchor = _case_anchor(
        args.skill, reference_case, reference_evals_path)
    candidate_anchor["revision"] = candidate_revision
    reference_anchor["revision"] = reference_revision
    if candidate_anchor["prompt_hash"] != reference_anchor["prompt_hash"]:
        raise ValueError(
            "candidate and reference regression prompts must be identical")
    case = reference_case
    fixture = case["fixture"]
    ftype = fixture["type"]
    expected_fixture_hash = reference_anchor["fixture_hash"]
    if not expected_fixture_hash:
        raise ValueError("reference fixture is missing its frozen content/output hash")
    protocol_errors = validate_declaration("regression", ["candidate", "reference"], args.reps)
    if protocol_errors:
        raise ValueError("; ".join(protocol_errors))

    natural_task = case["prompt"]
    candidate_hash = _revision_tree_hash(candidate_skill_dir)
    reference_hash = _revision_tree_hash(reference_skill_dir)
    evidence = {
        "result_schema_version": 3,
        "evidence_type": "regression",
        "protocol": "regression",
        "skill": args.skill,
        "case_id": args.case_id,
        "model": args.model,
        "harness": {
            "name": adapter.name,
            "adapter_protocol": evaluation_harness.ADAPTER_PROTOCOL,
        },
        "runtime_treatment_paths": list(evaluation_harness.RUNTIME_TREATMENT_PATHS),
        "candidate_revision": candidate_revision,
        "reference_revision": reference_revision,
        "fixture_revision": reference_revision,
        "reproduction_status": "reproducible",
        "runner_version": REGRESSION_RUNNER_VERSION,
        "case_set_hash": case_set_hash(candidate_anchor, reference_anchor),
        "fixture_hash": expected_fixture_hash,
        "case_anchors": {
            "candidate": candidate_anchor,
            "reference": reference_anchor,
        },
        "candidate_skill_source_path": f"skills/{args.skill}",
        "reference_skill_source_path": f"skills/{args.skill}",
        "candidate_skill_content_hash": candidate_hash,
        "reference_skill_content_hash": reference_hash,
        "candidate_skill_hash": candidate_hash,
        "reference_skill_hash": reference_hash,
        "candidate_guidance_id": args.skill,
        "reference_guidance_id": args.skill,
        "candidate_guidance_hash": candidate_hash,
        "reference_guidance_hash": reference_hash,
        "candidate_guidance_path": evaluation_harness.RUNTIME_TREATMENT_PATHS[0],
        "reference_guidance_path": evaluation_harness.RUNTIME_TREATMENT_PATHS[0],
        "fixture_source_path": reference_anchor["source_path"],
        "fixture_path": reference_anchor["fixture_path"],
        "fixture_source_hash": reference_anchor["source_hash"],
        "expected_fixture_hash": expected_fixture_hash,
        "canonical_task_seed_hash": None,
        "conditions": ["candidate", "reference"],
        "repetitions": [],
    }

    activation_specs = {
        "candidate": {"skill_name": args.skill, "source_dir": candidate_skill_dir},
        "reference": {"skill_name": args.skill, "source_dir": reference_skill_dir},
    }
    for index in range(args.reps):
        seed, _ = materialize_fixture_seed(fixture_dir, ftype, source, invocation)
        try:
            seed_hash = HASH_PREFIX + evaluation_harness.hash_task_workspace(
                seed, evaluation_harness.RUNTIME_TREATMENT_PATHS)
            if seed_hash != expected_fixture_hash:
                raise ValueError(
                    "materialized seed task hash does not match frozen fixture: "
                    f"{seed_hash!r} != {expected_fixture_hash!r}")
            repetition, canonical, workspaces = evaluation_harness.run_condition_repetition(
                index, ["candidate", "reference"], natural_task, seed,
                activation_specs, args.model, adapter,
                protocol="regression", case_id=args.case_id,
            )
            evidence["canonical_task_seed_hash"] = canonical
            evidence["repetitions"].append(repetition)
            for workspace in workspaces.values():
                evaluation_harness.cleanup_workspace(workspace)
        finally:
            shutil.rmtree(seed, ignore_errors=True)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--reference", required=True,
                        help="previous known-good Git revision")
    parser.add_argument("--candidate", default="HEAD",
                        help="candidate Git revision (default: HEAD)")
    parser.add_argument("--case-id", type=int, required=True)
    parser.add_argument("--model", default=None,
                        help="opaque model/runtime identifier passed to the adapter")
    parser.add_argument("--harness-command", required=True,
                        help="command implementing the JSON harness-adapter contract")
    parser.add_argument("--harness-name", default="external",
                        help="name recorded in evidence (default: external)")
    parser.add_argument("--harness-timeout", type=int, default=1200,
                        help="adapter timeout in seconds (default: 1200)")
    parser.add_argument("--harness-cwd", default=None,
                        help="optional working directory for the adapter command")
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--out", default=None,
                        help="evidence output path (normally under .eval-evidence)")
    args = parser.parse_args()

    candidate_root = reference_root = None
    try:
        adapter = evaluation_harness.CommandHarnessAdapter(
            args.harness_command,
            name=args.harness_name,
            timeout_seconds=args.harness_timeout,
            cwd=args.harness_cwd,
        )
        candidate_root, candidate_revision = materialize_skill_revision(args.candidate, args.skill)
        reference_root, reference_revision = materialize_skill_revision(args.reference, args.skill)
        evidence = build_evidence(args, candidate_root, reference_root,
                                  candidate_revision, reference_revision,
                                  adapter)
        out = args.out or os.path.join(
            ROOT, ".eval-evidence",
            f"regression-{args.skill}-case{args.case_id}.json",
        )
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(evidence, fh, indent=2)
        print(f"wrote evidence: {out}")
        for repetition in evidence["repetitions"]:
            states = " ".join(
                f"{name}[{repetition['conditions'][name]['run_status']}]"
                for name in ("candidate", "reference")
            )
            print(f"rep{repetition['rep']}: {states} "
                  f"distinct={repetition['distinct_workers']} "
                  f"task_hash={repetition['natural_task_hash'][:10]}")
    finally:
        if candidate_root:
            evaluation_harness.cleanup_workspace(candidate_root)
        if reference_root:
            evaluation_harness.cleanup_workspace(reference_root)


if __name__ == "__main__":
    main()
