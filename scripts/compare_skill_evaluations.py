#!/usr/bin/env python3
"""Summarize observed skill-version comparisons without inventing precision.

The input may be one committed regression ``result-json``/JSON file, or two
result files whose cases contain candidate/reference (or target/baseline)
grades. The report keeps shared-outcome scoring separate from skill-contract
observations and uses qualitative language suitable for n=1 development runs.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHARED_SCOPES = {"shared-outcome", "universal-safety"}


def load_result(path: str | Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix == ".json":
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError(f"{path}: JSON root must be an object")
        return value
    blocks = re.findall(r"```result-json\s*\n(.*?)```", text, re.DOTALL)
    if not blocks:
        raise ValueError(f"{path}: no result-json block found")
    value = json.loads(blocks[0])
    if not isinstance(value, dict):
        raise ValueError(f"{path}: result-json root must be an object")
    return value


def _grade(assertion: dict, condition: str) -> bool | None:
    value = assertion.get(condition)
    return value.get("pass") if isinstance(value, dict) and isinstance(value.get("pass"), bool) else None


def _scope(assertion: dict) -> str:
    return assertion.get("scope", "shared-outcome")


def _case_map(result: dict) -> dict[int, dict]:
    return {
        case.get("case_id"): case
        for case in result.get("cases", [])
        if isinstance(case, dict) and isinstance(case.get("case_id"), int)
    }


def _observed_case(case: dict, left: str, right: str) -> tuple[str, str, str]:
    """Return shared result, contract result, and a compact evidence note."""

    assertions = [a for a in case.get("assertions", []) if isinstance(a, dict)]
    shared = [a for a in assertions if _scope(a) in SHARED_SCOPES]
    contract = [a for a in assertions if _scope(a) == "skill-contract"]
    left_values = [_grade(a, left) for a in shared]
    right_values = [_grade(a, right) for a in shared]
    if not shared or any(value is None for value in left_values + right_values):
        shared_status = "INCONCLUSIVE"
    else:
        left_pass = all(left_values)
        right_pass = all(right_values)
        if left_pass and not right_pass:
            shared_status = "IMPROVED_REVISION_BEHAVIOR"
        elif right_pass and not left_pass:
            shared_status = "REGRESSION_DETECTED"
        elif left_pass and right_pass:
            shared_status = "PRESERVED_BEHAVIOR"
        else:
            shared_status = "INCONCLUSIVE"
    if not contract:
        contract_status = "NOT_REPORTED"
    else:
        left_contract = [_grade(a, left) for a in contract]
        right_contract = [_grade(a, right) for a in contract]
        if any(value is None for value in left_contract + right_contract):
            contract_status = "INCONCLUSIVE"
        elif all(left_contract) == all(right_contract):
            contract_status = "NONE OBSERVED"
        elif all(left_contract):
            contract_status = "CANDIDATE CONTRACT ADHERENCE DIFFERED"
        else:
            contract_status = "CANDIDATE CONTRACT ADHERENCE DIFFERED"
    note = (
        f"shared {sum(value is True for value in left_values)}/"
        f"{len(shared) if shared else 0} vs "
        f"{sum(value is True for value in right_values)}/"
        f"{len(shared) if shared else 0}"
    )
    return shared_status, contract_status, note


def compare_results(candidate: dict, reference: dict | None = None) -> str:
    """Return a compact comparison report for one or two result documents."""

    if reference is None and candidate.get("evaluation_mode") == "regression":
        cases = _case_map(candidate)
        lines = []
        statuses = []
        for case_id in sorted(cases):
            case = cases[case_id]
            shared_status, contract_status, note = _observed_case(
                case, "candidate", "reference")
            declared = (case.get("outcome") or {}).get(
                "regression_status", "inconclusive")
            lines.extend([
                f"Case {case_id}:",
                f"candidate shared-outcome: {shared_status} ({note})",
                f"contract regression: {contract_status}",
                f"declared regression status: {str(declared).upper()}",
            ])
            statuses.append(shared_status)
        overall = (statuses[0] if statuses and all(
            status == statuses[0] for status in statuses) else "INCONCLUSIVE")
        lines.append(f"Overall: {overall} (observed comparison; not a statistical claim)")
        return "\n".join(lines)

    if reference is None:
        raise ValueError("provide either a regression result or both candidate and reference results")
    candidate_cases = _case_map(candidate)
    reference_cases = _case_map(reference)
    case_ids = sorted(set(candidate_cases) | set(reference_cases))
    lines = []
    observed = []
    for case_id in case_ids:
        if case_id not in candidate_cases or case_id not in reference_cases:
            lines.append(f"Case {case_id}: inconclusive (case missing from one result)")
            observed.append("inconclusive")
            continue
        candidate_case = candidate_cases[case_id]
        reference_case = reference_cases[case_id]
        if any(
            _grade(a, "candidate") is not None
            for a in candidate_case.get("assertions", [])
            if isinstance(a, dict)
        ):
            shared_status, contract_status, note = _observed_case(
                candidate_case, "candidate", "reference"
            )
        else:
            combined = {"assertions": []}
            candidate_assertions = {
                a.get("assertion"): a
                for a in candidate_case.get("assertions", [])
                if isinstance(a, dict)
            }
            reference_assertions = {
                a.get("assertion"): a
                for a in reference_case.get("assertions", [])
                if isinstance(a, dict)
            }
            for text, left in candidate_assertions.items():
                right = reference_assertions.get(text)
                if right is None:
                    continue
                combined["assertions"].append({
                    "scope": left.get("scope", right.get("scope", "shared-outcome")),
                    "candidate": left.get("target", left.get("candidate")),
                    "reference": right.get("target", right.get("reference")),
                })
            shared_status, contract_status, note = _observed_case(
                combined, "candidate", "reference"
            )
        lines.extend([
            f"Case {case_id}:",
            f"candidate shared-outcome: {shared_status} ({note})",
            f"contract regression: {contract_status}",
        ])
        observed.append(shared_status)
    overall = observed[0] if observed and all(status == observed[0] for status in observed) else "INCONCLUSIVE"
    lines.append(f"Overall: {overall}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", help="candidate result JSON/Markdown")
    parser.add_argument("reference", nargs="?", help="reference result JSON/Markdown")
    args = parser.parse_args()
    candidate = load_result(args.candidate)
    reference = load_result(args.reference) if args.reference else None
    print(compare_results(candidate, reference))


if __name__ == "__main__":
    main()
