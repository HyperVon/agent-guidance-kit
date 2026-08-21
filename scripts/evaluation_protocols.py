#!/usr/bin/env python3
"""Small, explicit protocol definitions for progressive skill evaluation.

The evaluation question determines the minimum experiment.  This module is
deliberately a data table plus a few helpers rather than a general-purpose
configuration language, so runners and validators share one source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
import ntpath
import os

from evaluation.regression import (
    LEGACY_REGRESSION_STATUSES,
    OBSERVED_REGRESSION_STATUSES,
)


@dataclass(frozen=True)
class Protocol:
    """Requirements for one evaluation protocol."""

    name: str
    required_conditions: tuple[str, ...]
    allowed_conditions: tuple[str, ...]
    minimum_repetitions: int
    scored_scopes: tuple[str, ...]


PROTOCOLS = {
    "smoke": Protocol(
        name="smoke",
        required_conditions=("target",),
        allowed_conditions=("target", "baseline", "placebo"),
        minimum_repetitions=1,
        scored_scopes=("shared-outcome", "universal-safety"),
    ),
    "qualification": Protocol(
        name="qualification",
        required_conditions=("target", "baseline"),
        allowed_conditions=("target", "baseline"),
        minimum_repetitions=1,
        scored_scopes=("shared-outcome", "universal-safety"),
    ),
    "regression": Protocol(
        name="regression",
        required_conditions=("candidate", "reference"),
        allowed_conditions=("candidate", "reference"),
        minimum_repetitions=1,
        scored_scopes=("shared-outcome", "skill-contract", "universal-safety"),
    ),
    "confirmation": Protocol(
        name="confirmation",
        required_conditions=("target", "baseline", "placebo"),
        allowed_conditions=("target", "baseline", "placebo"),
        minimum_repetitions=3,
        scored_scopes=("shared-outcome", "skill-contract", "universal-safety"),
    ),
}

PROTOCOL_NAMES = frozenset(PROTOCOLS)
CONDITION_NAMES = frozenset({"target", "baseline", "placebo", "candidate", "reference"})
ALLOWED_ASSERTION_SCOPES = frozenset({"shared-outcome", "skill-contract", "universal-safety"})
REGRESSION_STATUSES = OBSERVED_REGRESSION_STATUSES

# Historical consumers may still emit the pre-v2 labels. They are accepted as
# compatibility aliases by result validation; new runners emit observation-
# only names.
LEGACY_RESULT_REGRESSION_STATUSES = LEGACY_REGRESSION_STATUSES

LIFECYCLE_STAGES = (
    "activation_verified",
    "execution_attested",
    "isolation_verified",
    "protocol_valid",
)
LIFECYCLE_FIELD_STAGE = {
    "activation_verified": "activation_verified",
    "context_verified": "activation_verified",
    "execution_attestation": "execution_attested",
    "execution_verified": "execution_attested",
    "isolation_attestation": "isolation_verified",
    "worker_isolation_verified": "isolation_verified",
    "protocol.status": "protocol_valid",
}


def is_safe_skill_name(value: object) -> bool:
    """Return whether a skill identifier is one repository directory name.

    Evidence and CLI arguments must never turn a skill name into an absolute,
    parent-relative, or drive-relative filesystem path.
    """

    return (
        isinstance(value, str)
        and bool(value)
        and value not in {".", ".."}
        and "\x00" not in value
        and "/" not in value
        and "\\" not in value
        and not ntpath.splitdrive(value)[0]
    )


def resolve_path_within(root: str, relative: object) -> str | None:
    """Resolve a path only when it remains under the supplied root."""

    if not isinstance(relative, str) or not relative or "\x00" in relative:
        return None
    if (os.path.isabs(relative) or ntpath.isabs(relative)
            or ntpath.splitdrive(relative)[0]):
        return None
    root_real = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(root_real, relative))
    try:
        if os.path.commonpath((root_real, candidate)) != root_real:
            return None
    except ValueError:
        return None
    return candidate


def get_protocol(name: str | None) -> Protocol | None:
    """Return a protocol definition, or ``None`` for an omitted legacy name."""

    if not isinstance(name, str):
        return None
    return PROTOCOLS.get(name)


def protocol_name(protocol: object) -> str | None:
    """Read the explicit ``protocol.name`` field from a result/evidence block."""

    if not isinstance(protocol, dict):
        return None
    name = protocol.get("name")
    return name if isinstance(name, str) else None


def legacy_protocol_name(protocol: object, evaluation_mode: str | None = None) -> str | None:
    """Infer only the old strict artifact shape, never a new protocol claim.

    Historical execution results predate ``protocol.name``.  A valid result
    with a placebo and three repetitions is the old strict confirmation shape;
    everything else remains unnamed and is handled by legacy validation rules.
    """

    if not isinstance(protocol, dict) or evaluation_mode != "execution":
        return None
    conditions = protocol.get("conditions")
    repeats = protocol.get("repeats")
    if (
        isinstance(conditions, list)
        and all(isinstance(condition, str) for condition in conditions)
        and set(conditions) == set(PROTOCOLS["confirmation"].required_conditions)
        and isinstance(repeats, int)
        and not isinstance(repeats, bool)
        and repeats >= PROTOCOLS["confirmation"].minimum_repetitions
    ):
        return "confirmation"
    return None


def early_stop_recommendation(
    target_pass: bool | None,
    baseline_pass: bool | None,
    *,
    meaningful_difference: bool = False,
) -> dict[str, object]:
    """Return a cheap, explicit qualification stopping decision.

    This function never launches a follow-up run.  It only describes the next
    decision from already-observed n=1 evidence.
    """

    if target_pass is False:
        return {
            "stopped": True,
            "reason": "target failed the shared-outcome qualification criteria",
            "next_protocol": "none",
        }
    if target_pass is True and baseline_pass is True and not meaningful_difference:
        return {
            "stopped": True,
            "reason": "target and baseline both passed shared-outcome criteria at n=1",
            "next_protocol": "none",
        }
    if target_pass is True and baseline_pass is False:
        return {
            "stopped": False,
            "reason": "target showed an observed shared-outcome advantage; optional confirmation may be warranted",
            "next_protocol": "confirmation",
        }
    return {
        "stopped": True,
        "reason": "qualification evidence is incomplete or inconclusive",
        "next_protocol": "none",
    }


def validate_declaration(
    name: str,
    conditions: object,
    repetitions: object,
) -> list[str]:
    """Validate protocol-owned conditions and repetition requirements."""

    protocol = get_protocol(name)
    if protocol is None:
        return [f"unknown evaluation protocol {name!r}"]
    errors: list[str] = []
    if not isinstance(conditions, list) or not conditions:
        return [f"protocol {name!r} requires a non-empty conditions list"]
    if any(not isinstance(condition, str) for condition in conditions):
        errors.append(f"protocol {name!r} conditions must contain strings")
    else:
        declared = set(conditions)
        unknown = declared - set(protocol.allowed_conditions)
        if unknown:
            errors.append(
                f"protocol {name!r} has unsupported condition(s): {sorted(unknown)!r}"
            )
        missing = set(protocol.required_conditions) - declared
        if missing:
            errors.append(
                f"protocol {name!r} is missing required condition(s): {sorted(missing)!r}"
            )
        if len(declared) != len(conditions):
            errors.append(f"protocol {name!r} conditions must be unique")
    if not isinstance(repetitions, int) or isinstance(repetitions, bool):
        errors.append(f"protocol {name!r} repetitions must be a positive integer")
    elif repetitions < protocol.minimum_repetitions:
        errors.append(
            f"protocol {name!r} requires at least {protocol.minimum_repetitions} repetition(s)"
        )
    return errors
