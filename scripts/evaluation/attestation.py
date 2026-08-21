"""Harness-neutral attestation constants, hashes, and evidence layers."""

from __future__ import annotations

import hashlib
import json

from eval_hashing import HASH_PREFIX

from .receipts import verify_workspace_receipt


EXECUTION_ATTESTATION_PROTOCOL = (
    "agent-guidance-kit.execution-attestation/v1")
ATTESTATION_CONFIDENCE_LEVELS = frozenset({
    "adapter_declared",
    "runtime_verified",
    "independently_verified",
})
STRONG_ATTESTATION_CONFIDENCE_LEVELS = frozenset({
    "runtime_verified",
    "independently_verified",
})
ATTESTED_OBSERVATION_FIELDS = (
    "run_status", "worker_id", "session_id", "returncode", "output",
    "guidance_probe", "guidance_context_probe", "activation_mechanism",
    "workspace_receipt_path", "workspace_receipt")


def as_text(value: object) -> str:
    """Normalize subprocess streams, including partial timeout byte output."""

    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def attestation_request_hash(request: dict) -> str:
    """Hash the exact evaluator request bound by a worker attestation."""

    serialized = json.dumps(request, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False)
    return HASH_PREFIX + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def attestation_observation_hash(observation: dict) -> str:
    """Hash the adapter observation bound by a worker attestation."""

    payload = {field: observation.get(field)
               for field in ATTESTED_OBSERVATION_FIELDS}
    payload["output"] = as_text(payload["output"])
    payload["workspace_receipt"] = as_text(payload["workspace_receipt"])
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False)
    return HASH_PREFIX + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _bool_claim(meta: dict, key: str, fallback: bool) -> bool:
    value = meta.get(key)
    return value if isinstance(value, bool) else fallback


def _guidance_matches(meta: dict, expected_id: object,
                      expected_hash: object, guided: bool) -> bool:
    observed_id = meta.get("guidance_id") or meta.get("skill_name")
    observed_hash = meta.get("guidance_hash") or meta.get(
        "guidance_content_hash")
    if not guided:
        return observed_id is None and observed_hash is None
    return observed_id == expected_id and observed_hash == expected_hash


def _response_shape_valid(meta: dict) -> bool:
    required = (
        "run_status", "worker_id", "session_id", "returncode", "output",
        "guidance_probe", "guidance_context_probe",
        "workspace_receipt_path", "workspace_receipt",
        "execution_attestation",
    )
    return (
        all(key in meta for key in required)
        and isinstance(meta.get("execution_attestation"), dict)
        and isinstance(meta.get("output"), str)
    )


def build_attestation_layers(
    meta: dict,
    *,
    expected_receipt_hash: str | None,
    expected_guidance_id: object,
    expected_guidance_hash: object,
    guided: bool,
) -> dict[str, dict[str, object]]:
    """Build explicit adapter/evaluator/independent evidence layers.

    The adapter layer is a preserved report.  The evaluator layer is derived
    from the normalized response and expected evaluator-owned values.  The
    independent layer records whether the adapter supplied an explicitly
    independent attestation; it is availability metadata, not a claim that the
    evaluator independently performed that verification.
    """

    adapter_claims = {
        "guidance_loaded": _bool_claim(
            meta, "guidance_loaded", meta.get("guidance_probe") == "present"),
        "context_loaded": _bool_claim(
            meta, "context_loaded",
            meta.get("guidance_context_probe") == "present"),
        "execution_completed": _bool_claim(
            meta, "execution_completed",
            meta.get("run_status") == "success" and meta.get("returncode") == 0),
    }
    evaluator_verification = {
        "receipt_hash_matches": verify_workspace_receipt(
            meta.get("workspace_receipt"), expected_receipt_hash),
        "guidance_hash_matches": _guidance_matches(
            meta, expected_guidance_id, expected_guidance_hash, guided),
        "result_schema_valid": _response_shape_valid(meta),
    }
    attestation = meta.get("execution_attestation")
    if not isinstance(attestation, dict):
        attestation = {}
    independent = (
        attestation.get("confidence") == "independently_verified" and
        attestation.get("verification_mode") == "independent")
    source = attestation.get("source") if independent else None
    if not isinstance(source, str) or not source.strip():
        source = None
    return {
        "adapter_claims": adapter_claims,
        "evaluator_verification": evaluator_verification,
        "independent_attestation": {
            "available": independent,
            "source": source,
        },
    }


__all__ = [
    "ATTESTED_OBSERVATION_FIELDS",
    "ATTESTATION_CONFIDENCE_LEVELS",
    "EXECUTION_ATTESTATION_PROTOCOL",
    "STRONG_ATTESTATION_CONFIDENCE_LEVELS",
    "as_text",
    "attestation_observation_hash",
    "attestation_request_hash",
    "build_attestation_layers",
]
