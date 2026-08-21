"""Harness-neutral execution identity helpers."""

from __future__ import annotations


def _preferred_value(mapping: dict, canonical: str, *aliases: str) -> object:
    """Use a present canonical field even when it is null or empty."""

    if canonical in mapping:
        return mapping[canonical]
    for alias in aliases:
        if alias in mapping:
            return mapping[alias]
    return None


def expected_guidance_identity(evidence: dict, condition: str) -> tuple[object, object]:
    """Return the evaluator's expected identity, independent of activation path."""

    if condition == "target":
        return (
            _preferred_value(evidence, "target_guidance_identity",
                             "target_guidance_id", "skill"),
            _preferred_value(evidence, "target_guidance_hash",
                             "target_skill_content_hash"),
        )
    if condition == "placebo":
        return (
            _preferred_value(evidence, "placebo_guidance_identity",
                             "placebo_guidance_id", "placebo_skill"),
            _preferred_value(evidence, "placebo_guidance_hash",
                             "placebo_skill_content_hash"),
        )
    if condition == "candidate":
        return (
            _preferred_value(evidence, "candidate_guidance_identity",
                             "candidate_guidance_id", "skill"),
            _preferred_value(evidence, "candidate_guidance_hash",
                             "candidate_skill_content_hash"),
        )
    if condition == "reference":
        return (
            _preferred_value(evidence, "reference_guidance_identity",
                             "reference_guidance_id", "skill"),
            _preferred_value(evidence, "reference_guidance_hash",
                             "reference_skill_content_hash"),
        )
    return None, None


def validate_guidance_observation(
    cmeta: dict,
    expected_id: object,
    expected_hash: object,
    ctag: str,
    errs: list[str],
    *,
    guided: bool,
    require_canonical: bool = False,
) -> None:
    """Validate guidance identity and probes without interpreting placement."""

    if require_canonical:
        for key in ("guidance_identity", "guidance_hash", "activation_method",
                    "activation_evidence"):
            if key not in cmeta:
                errs.append(f"{ctag}: schema v3 requires canonical {key}")
        activation_evidence = cmeta.get("activation_evidence")
        if not isinstance(activation_evidence, dict):
            errs.append(f"{ctag}: canonical activation_evidence must be an object")

    observed_id = _preferred_value(
        cmeta, "guidance_identity", "guidance_id", "skill_name")
    observed_hash = _preferred_value(
        cmeta, "guidance_hash", "guidance_content_hash")
    source = cmeta.get("activation_method") or cmeta.get("guidance_source")
    if source is None:
        source = cmeta.get("activation_mechanism")
    activation_verified = cmeta.get(
        "activation_verified", cmeta.get("guidance_probe") == "present")
    context_verified = cmeta.get(
        "context_verified", cmeta.get("guidance_context_probe") == "present")
    activation_evidence = cmeta.get("activation_evidence")
    if activation_evidence is not None:
        if not isinstance(activation_evidence, dict):
            errs.append(f"{ctag}: activation_evidence must be an object")
        else:
            for key, expected in (
                    ("guidance_loaded", activation_verified),
                    ("context_loaded", context_verified)):
                if require_canonical and not isinstance(
                        activation_evidence.get(key), bool):
                    errs.append(
                        f"{ctag}: canonical activation_evidence.{key} must be boolean"
                    )
                elif key in activation_evidence and activation_evidence[key] is not expected:
                    errs.append(
                        f"{ctag}: activation_evidence.{key} does not match "
                        "the activation response"
                    )
    if guided:
        if observed_id != expected_id:
            errs.append(f"{ctag}: guidance_id does not match the evaluator identity")
        if observed_hash != expected_hash:
            errs.append(f"{ctag}: guidance_hash does not match the evaluator identity")
        if not isinstance(source, str) or not source.strip():
            errs.append(f"{ctag}: guidance_source must be non-empty")
        if activation_verified is not True:
            errs.append(f"{ctag}: activation_verified must be true")
        if context_verified is not True:
            errs.append(f"{ctag}: context_verified must be true")
        if require_canonical and (
                not isinstance(cmeta.get("activation_method"), str) or
                not cmeta.get("activation_method").strip()):
            errs.append(f"{ctag}: canonical activation_method must be non-empty")
        return
    if observed_id is not None:
        errs.append(f"{ctag}: baseline must not have a guidance_id")
    if observed_hash is not None:
        errs.append(f"{ctag}: baseline must not have a guidance_hash")
    if source not in (None, "none", ""):
        errs.append(f"{ctag}: baseline must not have a guidance_source")
    if activation_verified not in (False, None):
        errs.append(f"{ctag}: baseline activation_verified must be false")
    if context_verified not in (False, None):
        errs.append(f"{ctag}: baseline context_verified must be false")

__all__ = [
    "expected_guidance_identity",
    "validate_guidance_observation",
]
