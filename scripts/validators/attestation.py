"""Execution-attestation validation and confidence classification."""

from __future__ import annotations

import hashlib
import re

from evaluation_harness import (
    ATTESTATION_CONFIDENCE_LEVELS,
    EXECUTION_ATTESTATION_PROTOCOL,
    STRONG_ATTESTATION_CONFIDENCE_LEVELS,
    attestation_observation_hash,
)
from evaluation.receipts import verify_workspace_receipt


def is_strong_confidence(value: object) -> bool:
    """Return whether confidence can support an execution-verified claim."""

    return value in STRONG_ATTESTATION_CONFIDENCE_LEVELS


def validate_execution_attestation(
    cmeta: dict,
    expected_receipt_hash: str | None,
    ctag: str,
    errs: list[str],
    *,
    observation_hash_fn=attestation_observation_hash,
) -> str | None:
    """Validate bindings and return the declared confidence level.

    ``adapter_declared`` is intentionally accepted: the evaluator can verify
    the hashes and request/response bindings without pretending it independently
    verified the adapter's worker boundary. ``runtime_verified`` additionally
    requires a compact runtime evidence block, while
    ``independently_verified`` retains the stronger worker-boundary contract.
    """

    attestation = cmeta.get("execution_attestation")
    if not isinstance(attestation, dict):
        errs.append(f"{ctag}: missing execution_attestation")
        return None
    if attestation.get("protocol") != EXECUTION_ATTESTATION_PROTOCOL:
        errs.append(f"{ctag}: execution_attestation protocol is unsupported")
    if attestation.get("status") != "verified":
        errs.append(f"{ctag}: execution_attestation is not verified")

    confidence = attestation.get("confidence")
    if confidence not in ATTESTATION_CONFIDENCE_LEVELS:
        errs.append(
            f"{ctag}: execution_attestation confidence must be one of "
            f"{sorted(ATTESTATION_CONFIDENCE_LEVELS)!r}"
        )
    source = attestation.get("source")
    if not isinstance(source, str) or not source.strip():
        errs.append(f"{ctag}: execution_attestation source must be non-empty")
    if confidence == "independently_verified":
        if attestation.get("verification_mode") != "independent":
            errs.append(
                f"{ctag}: independently_verified attestation must use independent verification"
            )
    elif confidence == "runtime_verified":
        runtime_evidence = attestation.get("runtime_evidence")
        if not isinstance(runtime_evidence, dict):
            errs.append(f"{ctag}: runtime_verified attestation missing runtime_evidence")
        else:
            for key in ("worker_id", "session_id", "observation_hash"):
                if not runtime_evidence.get(key):
                    errs.append(
                        f"{ctag}: runtime_evidence missing {key}")
            if runtime_evidence.get("worker_id") != cmeta.get("worker_id"):
                errs.append(f"{ctag}: runtime_evidence worker_id is not bound")
            if runtime_evidence.get("session_id") != cmeta.get("session_id"):
                errs.append(f"{ctag}: runtime_evidence session_id is not bound")

    for key in ("worker_id", "session_id", "nonce", "request_hash",
                "workspace_receipt_hash", "output_hash", "returncode"):
        if key not in attestation:
            errs.append(f"{ctag}: execution_attestation missing {key}")
    for key in ("worker_id", "session_id", "nonce"):
        value = attestation.get(key)
        if not isinstance(value, str) or not value.strip():
            errs.append(f"{ctag}: execution_attestation {key} must be non-empty")
    for key in ("request_hash", "workspace_receipt_hash", "output_hash",
                "observation_hash"):
        value = attestation.get(key)
        if not isinstance(value, str) or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", value):
            errs.append(
                f"{ctag}: execution_attestation {key} must be a SHA-256 digest")
    if attestation.get("worker_id") != cmeta.get("worker_id"):
        errs.append(f"{ctag}: execution_attestation worker_id is not bound")
    if attestation.get("session_id") != cmeta.get("session_id"):
        errs.append(f"{ctag}: execution_attestation session_id is not bound")
    if attestation.get("nonce") != cmeta.get("attestation_nonce"):
        errs.append(f"{ctag}: execution_attestation nonce is not bound")
    if attestation.get("request_hash") != cmeta.get("execution_request_hash"):
        errs.append(f"{ctag}: execution_attestation request is not bound")

    expected_observation_hash = observation_hash_fn(cmeta)
    if cmeta.get("execution_observation_hash") != expected_observation_hash:
        errs.append(f"{ctag}: execution observation is not evaluator-bound")
    if attestation.get("observation_hash") != expected_observation_hash:
        errs.append(f"{ctag}: execution_attestation observation is not bound")
    if confidence == "runtime_verified":
        runtime_evidence = attestation.get("runtime_evidence") or {}
        if runtime_evidence.get("observation_hash") != expected_observation_hash:
            errs.append(f"{ctag}: runtime_evidence observation is not bound")
    if attestation.get("workspace_receipt_hash") != expected_receipt_hash:
        errs.append(f"{ctag}: execution_attestation receipt is not bound")
    if (not isinstance(attestation.get("returncode"), int) or
            isinstance(attestation.get("returncode"), bool)):
        errs.append(f"{ctag}: execution_attestation returncode must be an integer")
    elif attestation.get("returncode") != cmeta.get("returncode"):
        errs.append(f"{ctag}: execution_attestation returncode is not bound")
    output = cmeta.get("output")
    if not isinstance(output, str):
        errs.append(f"{ctag}: execution_attestation cannot bind non-text output")
    else:
        output_hash = "sha256:" + hashlib.sha256(output.encode()).hexdigest()
        if attestation.get("output_hash") != output_hash:
            errs.append(f"{ctag}: execution_attestation output is not bound")
    return confidence if confidence in ATTESTATION_CONFIDENCE_LEVELS else None


def validate_execution_verified_claim(
    evidence: dict,
    confidences: list[str | None],
    errs: list[str],
) -> None:
    """Reject an execution-verified claim backed only by adapter declarations."""

    protocol = evidence.get("protocol")
    protocol_claim = protocol.get("execution_verified") if isinstance(protocol, dict) else None
    claim = (evidence["execution_verified"]
             if "execution_verified" in evidence else protocol_claim)
    if claim is None:
        return
    if not isinstance(claim, bool):
        errs.append("execution_verified must be boolean when present")
        return
    if claim is True and (
            not confidences or
            not all(is_strong_confidence(value) for value in confidences)):
        errs.append(
            "execution_verified=true requires runtime_verified or "
            "independently_verified attestation for every condition"
        )


def validate_attestation_layers(
    cmeta: dict,
    expected_receipt_hash: str | None,
    expected_guidance_id: object,
    expected_guidance_hash: object,
    ctag: str,
    errs: list[str],
    *,
    guided: bool,
) -> None:
    """Validate explicit trust layers without upgrading adapter assertions.

    The field is optional for legacy evidence. When present, adapter claims
    must match the normalized adapter response, evaluator verification values
    must match facts recomputed by this validator, and independent-attestation
    metadata must agree with the declared confidence. None of these checks
    turns an adapter report into independent proof.
    """

    layers = cmeta.get("attestation_layers")
    if layers is None:
        return
    if not isinstance(layers, dict):
        errs.append(f"{ctag}: attestation_layers must be an object")
        return
    for name in ("adapter_claims", "evaluator_verification",
                 "independent_attestation"):
        if not isinstance(layers.get(name), dict):
            errs.append(f"{ctag}: attestation_layers.{name} must be an object")

    adapter_claims = layers.get("adapter_claims")
    if not isinstance(adapter_claims, dict):
        adapter_claims = {}
    expected_adapter_claims = {
        "guidance_loaded": cmeta.get(
            "guidance_loaded",
            cmeta.get("guidance_probe") == "present"),
        "context_loaded": cmeta.get(
            "context_loaded",
            cmeta.get("guidance_context_probe") == "present"),
        "execution_completed": cmeta.get(
            "execution_completed",
            cmeta.get("run_status") == "success" and
            cmeta.get("returncode") == 0),
    }
    for key, expected in expected_adapter_claims.items():
        if not isinstance(expected, bool):
            expected = bool(expected)
        if not isinstance(adapter_claims.get(key), bool):
            errs.append(f"{ctag}: adapter_claims.{key} must be boolean")
        elif adapter_claims.get(key) != expected:
            errs.append(f"{ctag}: adapter_claims.{key} does not match adapter response")

    observed_id = cmeta.get("guidance_id") or cmeta.get("skill_name")
    observed_hash = cmeta.get("guidance_hash") or cmeta.get(
        "guidance_content_hash")
    guidance_hash_matches = (
        (observed_id == expected_guidance_id and
         observed_hash == expected_guidance_hash)
        if guided else observed_id is None and observed_hash is None
    )
    required_shape = (
        "run_status", "worker_id", "session_id", "returncode", "output",
        "guidance_probe", "guidance_context_probe",
        "workspace_receipt_path", "workspace_receipt",
        "execution_attestation",
    )
    expected_evaluator_values = {
        "receipt_hash_matches": verify_workspace_receipt(
            cmeta.get("workspace_receipt"), expected_receipt_hash),
        "guidance_hash_matches": guidance_hash_matches,
        "result_schema_valid": (
            all(key in cmeta for key in required_shape)
            and isinstance(cmeta.get("execution_attestation"), dict)
            and isinstance(cmeta.get("output"), str)
        ),
    }
    evaluator_verification = layers.get("evaluator_verification")
    if not isinstance(evaluator_verification, dict):
        evaluator_verification = {}
    for key, expected in expected_evaluator_values.items():
        if not isinstance(evaluator_verification.get(key), bool):
            errs.append(f"{ctag}: evaluator_verification.{key} must be boolean")
        elif evaluator_verification.get(key) != expected:
            errs.append(
                f"{ctag}: evaluator_verification.{key} does not match evaluator checks"
            )

    attestation = cmeta.get("execution_attestation")
    confidence = attestation.get("confidence") if isinstance(attestation, dict) else None
    expected_independent = (
        confidence == "independently_verified" and
        isinstance(attestation, dict) and
        attestation.get("verification_mode") == "independent")
    independent = layers.get("independent_attestation")
    if not isinstance(independent, dict):
        independent = {}
    if not isinstance(independent.get("available"), bool):
        errs.append(f"{ctag}: independent_attestation.available must be boolean")
    elif independent.get("available") != expected_independent:
        errs.append(
            f"{ctag}: independent_attestation.available does not match confidence"
        )
    source = independent.get("source")
    if expected_independent:
        expected_source = attestation.get("source")
        if not isinstance(source, str) or not source.strip():
            errs.append(f"{ctag}: independent_attestation.source must be non-empty when available")
        elif source != expected_source:
            errs.append(f"{ctag}: independent_attestation.source is not bound")
    elif source is not None:
        errs.append(f"{ctag}: independent_attestation.source requires available=true")


__all__ = [
    "ATTESTATION_CONFIDENCE_LEVELS",
    "EXECUTION_ATTESTATION_PROTOCOL",
    "STRONG_ATTESTATION_CONFIDENCE_LEVELS",
    "is_strong_confidence",
    "validate_attestation_layers",
    "validate_execution_attestation",
    "validate_execution_verified_claim",
]
