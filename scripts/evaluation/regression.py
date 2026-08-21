"""Immutable regression metadata and observation-only comparison semantics."""

from __future__ import annotations

import hashlib
import json


REGRESSION_RUNNER_VERSION = "agent-guidance-kit.regression-runner/v2"
INVALID_REPRODUCTION_ENVIRONMENT = "INVALID_REPRODUCTION_ENVIRONMENT"
REPRODUCTION_STATUSES = frozenset({
    "reproducible",
    "invalid_reproduction_environment",
})
OBSERVED_REGRESSION_STATUSES = frozenset({
    "observed_candidate_only_pass",
    "observed_reference_only_pass",
    "observed_both_pass",
    "observed_both_fail",
    "inconclusive",
    "not_run",
})
LEGACY_REGRESSION_STATUS_ALIASES = {
    "improved_revision_behavior": "observed_candidate_only_pass",
    "regression_detected": "observed_reference_only_pass",
    "preserved_behavior": "observed_both_pass",
}
LEGACY_REGRESSION_STATUSES = frozenset(LEGACY_REGRESSION_STATUS_ALIASES)


def canonical_hash(value: object) -> str:
    """Hash canonical JSON for immutable metadata, independent of formatting."""

    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False)
    return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def case_set_hash(candidate_anchor: dict, reference_anchor: dict) -> str:
    """Hash both revision-local case anchors and their ordering."""

    return canonical_hash({
        "candidate": candidate_anchor,
        "reference": reference_anchor,
    })


def normalize_regression_status(value: object) -> object:
    """Map pre-v2 labels to observation-only labels for old consumers."""

    return LEGACY_REGRESSION_STATUS_ALIASES.get(value, value)


def regression_status_for_verdict(
    candidate_pass: bool, reference_pass: bool) -> tuple[str, str]:
    """Return neutral category and observation-only comparison status."""

    if candidate_pass and not reference_pass:
        return "candidate_only_pass", "observed_candidate_only_pass"
    if reference_pass and not candidate_pass:
        return "reference_only_pass", "observed_reference_only_pass"
    if candidate_pass and reference_pass:
        return "both_pass", "observed_both_pass"
    return "both_fail", "observed_both_fail"


__all__ = [
    "LEGACY_REGRESSION_STATUS_ALIASES",
    "LEGACY_REGRESSION_STATUSES",
    "INVALID_REPRODUCTION_ENVIRONMENT",
    "OBSERVED_REGRESSION_STATUSES",
    "REGRESSION_RUNNER_VERSION",
    "REPRODUCTION_STATUSES",
    "canonical_hash",
    "case_set_hash",
    "normalize_regression_status",
    "regression_status_for_verdict",
]
