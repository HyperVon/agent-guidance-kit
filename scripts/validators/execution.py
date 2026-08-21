"""Harness-neutral execution identity helpers."""

from __future__ import annotations


def expected_guidance_identity(evidence: dict, condition: str) -> tuple[object, object]:
    """Return the evaluator's expected identity, independent of activation path."""

    if condition == "target":
        return (
            evidence.get("target_guidance_id") or evidence.get("skill"),
            evidence.get("target_guidance_hash") or
            evidence.get("target_skill_content_hash"),
        )
    if condition == "placebo":
        return (
            evidence.get("placebo_guidance_id") or evidence.get("placebo_skill"),
            evidence.get("placebo_guidance_hash") or
            evidence.get("placebo_skill_content_hash"),
        )
    if condition == "candidate":
        return (
            evidence.get("candidate_guidance_id") or evidence.get("skill"),
            evidence.get("candidate_guidance_hash") or
            evidence.get("candidate_skill_content_hash"),
        )
    if condition == "reference":
        return (
            evidence.get("reference_guidance_id") or evidence.get("skill"),
            evidence.get("reference_guidance_hash") or
            evidence.get("reference_skill_content_hash"),
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
) -> None:
    """Validate guidance identity and probes without interpreting placement."""

    observed_id = cmeta.get("guidance_id") or cmeta.get("skill_name")
    observed_hash = cmeta.get("guidance_hash") or cmeta.get("guidance_content_hash")
    source = cmeta.get("guidance_source")
    if source is None:
        source = cmeta.get("activation_mechanism")
    activation_verified = cmeta.get(
        "activation_verified", cmeta.get("guidance_probe") == "present")
    context_verified = cmeta.get(
        "context_verified", cmeta.get("guidance_context_probe") == "present")
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
