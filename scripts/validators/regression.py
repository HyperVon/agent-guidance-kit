"""Harness-neutral regression claim helpers."""

from __future__ import annotations

from .protocol import (
    FORBIDDEN_REGRESSION_CLAIMS,
)


def regression_status_for_verdict(
    candidate_pass: bool, reference_pass: bool) -> tuple[str, str]:
    """Return the neutral outcome category and revision-comparison status."""

    if candidate_pass and not reference_pass:
        return "candidate_only_pass", "improved_revision_behavior"
    if reference_pass and not candidate_pass:
        return "reference_only_pass", "regression_detected"
    if candidate_pass and reference_pass:
        return "both_pass", "preserved_behavior"
    return "both_fail", "inconclusive"


def validate_regression_claim(base: str, result: dict, errs: list[str]) -> None:
    """Reject qualification/effectiveness language in a regression result."""

    claim_keys = {"claim", "decision", "regression_status"}

    def walk(value: object, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                if key in claim_keys and isinstance(child, str):
                    if child in FORBIDDEN_REGRESSION_CLAIMS:
                        errs.append(
                            f"{base}: regression protocol cannot claim "
                            f"{child!r} at {child_path}; use "
                            "revision-behavior terminology"
                        )
                elif isinstance(child, (dict, list)):
                    walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                if isinstance(child, (dict, list)):
                    walk(child, f"{path}[{index}]")

    walk(result)

__all__ = [
    "FORBIDDEN_REGRESSION_CLAIMS",
    "regression_status_for_verdict",
    "validate_regression_claim",
]
