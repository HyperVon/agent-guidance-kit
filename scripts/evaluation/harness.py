"""Execution lifecycle and adapter coordination for neutral evaluations."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid

from eval_hashing import HASH_PREFIX, hash_task_workspace, hash_workspace
from evaluation_protocols import EVIDENCE_PROTOCOL_VERSION

from .attestation import (
    EXECUTION_ATTESTATION_PROTOCOL,
    as_text,
    attestation_observation_hash,
    attestation_request_hash,
    build_attestation_layers,
)
from .guidance import materialize_guidance, skill_tree_hash, snapshot_workspace
from .receipts import (
    RUNTIME_TREATMENT_PATHS,
    WORKSPACE_RECEIPT_PATH,
    write_workspace_receipt,
)
from .workspace import (
    _reject_symlinks,
    cleanup_workspace,
    copy_seed,
    make_temp_dir,
)


ADAPTER_PROTOCOL = "agent-guidance-kit.harness-adapter/v1"
DEFAULT_TIMEOUT_SECONDS = 1200


def validate_command_argv(command: object) -> list[str]:
    """Validate an executable argv without interpreting shell syntax."""

    if isinstance(command, str):
        raise ValueError(
            "harness adapter command must be an argv list; use "
            "--harness-command-json"
        )
    if not isinstance(command, (list, tuple)):
        raise ValueError("harness adapter command must be a JSON argv list")
    if not command:
        raise ValueError("harness adapter command must not be empty")
    argv = list(command)
    if not isinstance(argv[0], str) or not argv[0].strip():
        raise ValueError("harness adapter executable must be a non-empty string")
    if any(not isinstance(argument, str) or "\x00" in argument
           for argument in argv):
        raise ValueError(
            "harness adapter argv entries must be strings without NUL bytes")
    return argv


def parse_command_argv_json(value: str) -> list[str]:
    """Parse the CLI's JSON-encoded argv without shell interpretation."""

    try:
        command = json.loads(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"harness command JSON is invalid: {exc}") from exc
    return validate_command_argv(command)


def _failure(returncode: int | None, reason: str, *, stdout: str = "",
             stderr: str = "") -> dict:
    return {
        "returncode": returncode,
        "stdout": as_text(stdout),
        "stderr": as_text(stderr),
        "output": "",
        "worker_id": None,
        "container_id": None,
        "session_id": None,
        "run_status": "failed",
        "status": "failed",
        "reason": reason,
    }


class CommandHarnessAdapter:
    """Invoke any harness implementing the JSON adapter contract.

    Request input is one JSON object. The adapter returns one JSON object with
    generic worker/session, output, guidance-probe, receipt, and attestation
    fields. Harness-specific metadata is preserved under ``adapter_metadata``
    and is never interpreted by the protocol validator.

    The attestation confidence distinguishes an adapter-declared binding from
    runtime or independently verified evidence. Adapter-declared evidence is
    useful for limited comparisons, but it cannot support an
    ``execution_verified`` claim.
    """

    def __init__(self, command: list[str] | tuple[str, ...], *,
                 name: str = "external",
                 timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
                 cwd: str | None = None):
        self.command = validate_command_argv(command)
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.cwd = cwd

    def run(self, request: dict) -> dict:
        """Run one isolated condition through the configured adapter."""

        request = dict(request)
        request.setdefault("adapter_protocol", ADAPTER_PROTOCOL)
        request.setdefault("evidence_protocol_version", EVIDENCE_PROTOCOL_VERSION)
        try:
            process = subprocess.run(
                self.command,
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=self.cwd,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            return _failure(None, "harness adapter timed out",
                            stdout=exc.stdout or exc.output or "",
                            stderr=exc.stderr or "")
        except OSError as exc:
            return _failure(None, f"harness adapter invocation failed: {exc}")

        stdout = as_text(process.stdout)
        stderr = as_text(process.stderr)
        if process.returncode != 0:
            return _failure(process.returncode, "harness adapter exited non-zero",
                            stdout=stdout, stderr=stderr)
        try:
            response = json.loads(stdout)
        except (TypeError, ValueError) as exc:
            return _failure(process.returncode,
                            f"harness adapter returned invalid JSON: {exc}",
                            stdout=stdout, stderr=stderr)
        if not isinstance(response, dict):
            return _failure(process.returncode,
                            "harness adapter response must be a JSON object",
                            stdout=stdout, stderr=stderr)

        normalized = dict(response)
        normalized["stdout"] = as_text(normalized.get("stdout", stdout))
        normalized["stderr"] = as_text(normalized.get("stderr", stderr))
        normalized["returncode"] = normalized.get("returncode", process.returncode)
        normalized["run_status"] = normalized.get(
            "run_status", normalized.get("status"))
        normalized["status"] = normalized["run_status"]
        normalized["output"] = as_text(
            normalized.get("output", normalized.get("text", "")))
        normalized["worker_id"] = normalized.get(
            "worker_id", normalized.get("container_id"))
        normalized["guidance_probe"] = normalized.get(
            "guidance_probe", normalized.get("skill_probe"))
        normalized["guidance_context_probe"] = normalized.get(
            "guidance_context_probe", normalized.get("skill_context_probe"))
        normalized["guidance_identity"] = normalized.get(
            "guidance_identity", normalized.get("guidance_id") or
            normalized.get("skill_name"))
        normalized["guidance_hash"] = normalized.get(
            "guidance_hash", normalized.get("guidance_content_hash"))
        normalized["activation_method"] = normalized.get(
            "activation_method", normalized.get("activation_mechanism"))
        if "activation_evidence" not in normalized:
            normalized["activation_evidence"] = {
                "guidance_loaded": normalized.get("guidance_loaded",
                                                   normalized.get(
                                                       "guidance_probe") ==
                                                   "present"),
                "context_loaded": normalized.get("context_loaded",
                                                  normalized.get(
                                                      "guidance_context_probe") ==
                                                  "present"),
            }
        activation_evidence = normalized.get("activation_evidence")
        if isinstance(activation_evidence, dict):
            if not isinstance(normalized.get("activation_verified"), bool):
                normalized["activation_verified"] = activation_evidence.get(
                    "guidance_loaded",
                    normalized.get("guidance_probe") == "present")
            if not isinstance(normalized.get("context_verified"), bool):
                normalized["context_verified"] = activation_evidence.get(
                    "context_loaded",
                    normalized.get("guidance_context_probe") == "present")
        normalized["adapter_metadata"] = normalized.get("adapter_metadata", {
            "name": self.name,
            "protocol": ADAPTER_PROTOCOL,
        })
        return normalized


def run_condition_repetition(
    rep_index: int,
    conditions: list[str],
    natural_task: str,
    seed_dir: str,
    activation_specs: dict[str, dict | None],
    model: str | None,
    adapter: CommandHarnessAdapter,
    *,
    protocol: str,
    case_id: int | None = None,
) -> tuple[dict, str, dict[str, str]]:
    """Run one protocol comparison through only the neutral adapter contract."""

    canonical = HASH_PREFIX + hash_task_workspace(
        seed_dir, RUNTIME_TREATMENT_PATHS)
    repetition_id = str(uuid.uuid4())
    collisions = [path for path in RUNTIME_TREATMENT_PATHS
                  if os.path.exists(os.path.join(seed_dir, path))]
    if collisions:
        raise ValueError(
            f"pristine seed contains evaluator runtime treatment paths: {collisions}")

    workspaces = {name: copy_seed(seed_dir) for name in conditions}
    workspace_receipts = {
        name: write_workspace_receipt(workspaces[name]) for name in conditions
    }
    guidance = {}
    for name in conditions:
        spec = activation_specs.get(name)
        if not spec:
            continue
        tree = materialize_guidance(
            spec["source_dir"], workspaces[name], RUNTIME_TREATMENT_PATHS[0])
        content_hash = skill_tree_hash(spec["source_dir"])
        if content_hash is None:
            raise ValueError(f"skill source has no hashable guidance tree: {spec}")
        guidance[name] = {
            "guidance_id": spec.get("guidance_id", spec["skill_name"]),
            "guidance_identity": spec.get("guidance_id", spec["skill_name"]),
            "guidance_hash": content_hash,
            "guidance_activation_reference": {
                "identity": spec.get("guidance_id", spec["skill_name"]),
                "content_hash": content_hash,
            },
            "guidance_source": spec.get("guidance_source", "evaluator_runtime"),
            "skill_name": spec["skill_name"],
            "guidance_path": os.path.relpath(tree, workspaces[name]),
            "guidance_content_hash": content_hash,
        }

    condition_evidence = {}
    for name in conditions:
        spec = activation_specs.get(name)
        task_before = HASH_PREFIX + hash_task_workspace(
            workspaces[name], RUNTIME_TREATMENT_PATHS)
        full_before = HASH_PREFIX + hash_workspace(workspaces[name])
        snapshot_before = snapshot_workspace(workspaces[name])
        request = {
            "adapter_protocol": ADAPTER_PROTOCOL,
            "evidence_protocol_version": EVIDENCE_PROTOCOL_VERSION,
            "protocol": protocol,
            "condition": name,
            "repetition_id": repetition_id,
            "case_id": case_id,
            "natural_task": natural_task,
            "natural_task_hash": hashlib.sha256(natural_task.encode()).hexdigest(),
            "workspace": workspaces[name],
            "workspace_receipt_path": WORKSPACE_RECEIPT_PATH,
            "attestation_nonce": uuid.uuid4().hex,
            "model": model,
            "guidance": guidance.get(name),
        }
        request_hash = attestation_request_hash(request)
        meta = adapter.run(request)
        observation = dict(meta)
        canonical_activation_fields_observed = any(
            field in meta for field in (
                "guidance_identity", "activation_method", "activation_evidence"))
        activation_evidence = meta.get("activation_evidence")
        if "activation_evidence" not in meta:
            activation_evidence = {
                "guidance_loaded": meta.get(
                    "activation_verified",
                    meta.get("guidance_probe") == "present"),
                "context_loaded": meta.get(
                    "context_verified",
                    meta.get("guidance_context_probe") == "present"),
            }
        activation_verified = meta.get("activation_verified")
        if "activation_verified" not in meta:
            activation_verified = (
                activation_evidence.get(
                    "guidance_loaded", meta.get("guidance_probe") == "present")
                if isinstance(activation_evidence, dict)
                else meta.get("guidance_probe") == "present")
        context_verified = meta.get("context_verified")
        if "context_verified" not in meta:
            context_verified = (
                activation_evidence.get(
                    "context_loaded",
                    meta.get("guidance_context_probe") == "present")
                if isinstance(activation_evidence, dict)
                else meta.get("guidance_context_probe") == "present")
        guidance_probe = meta.get("guidance_probe", meta.get("skill_probe"))
        guidance_context_probe = meta.get(
            "guidance_context_probe", meta.get("skill_context_probe"))
        if canonical_activation_fields_observed:
            observed_guidance_identity = meta.get("guidance_identity")
            observed_guidance_hash = meta.get("guidance_hash")
            observed_activation_method = meta.get("activation_method")
        else:
            observed_guidance_identity = (
                meta.get("guidance_id") or meta.get("skill_name") or
                (guidance.get(name) or {}).get("guidance_identity"))
            observed_guidance_hash = (
                meta.get("guidance_hash") or meta.get("guidance_content_hash") or
                (guidance.get(name) or {}).get("guidance_hash"))
            observed_activation_method = (
                meta.get("activation_mechanism") or
                ("adapter" if spec else "none"))
        if canonical_activation_fields_observed:
            observation["canonical_activation_fields_observed"] = True
            observation.update({
                "guidance_identity": observed_guidance_identity,
                "guidance_hash": observed_guidance_hash,
                "activation_method": observed_activation_method,
                "activation_evidence": activation_evidence,
            })
        observation.update({
            "run_status": meta.get("run_status", meta.get("status")),
            "worker_id": meta.get("worker_id") or meta.get("container_id"),
            "output": as_text(meta.get("output", meta.get("text", ""))),
            "guidance_probe": guidance_probe,
            "guidance_context_probe": guidance_context_probe,
            "activation_mechanism": (
                meta.get("activation_mechanism")
                if canonical_activation_fields_observed else
                meta.get("activation_mechanism",
                         observed_activation_method or ("adapter" if spec else "none"))),
            "workspace_receipt_path": meta.get("workspace_receipt_path"),
            "workspace_receipt": meta.get("workspace_receipt"),
        })
        observation_hash = attestation_observation_hash(observation)
        task_after = HASH_PREFIX + hash_task_workspace(
            workspaces[name], RUNTIME_TREATMENT_PATHS)
        full_after = HASH_PREFIX + hash_workspace(workspaces[name])
        snapshot_after = snapshot_workspace(workspaces[name])
        current = dict(meta)
        current.update({
            "repetition_id": repetition_id,
            "worker_id": meta.get("worker_id") or meta.get("container_id"),
            "container_id": meta.get("container_id"),
            "session_id": meta.get("session_id"),
            "run_status": meta.get("run_status", meta.get("status")),
            "returncode": meta.get("returncode"),
            "output": observation["output"],
            "starting_task_hash": task_before,
            "ending_task_hash": task_after,
            "starting_full_hash": full_before,
            "ending_full_hash": full_after,
            "guidance_probe": guidance_probe,
            "guidance_context_probe": guidance_context_probe,
            "guidance_identity": observed_guidance_identity,
            "activation_method": observed_activation_method,
            "activation_evidence": activation_evidence,
            "canonical_activation_fields_observed":
                canonical_activation_fields_observed,
            "activation_verified": activation_verified,
            "context_verified": context_verified,
            "activation_mechanism": (
                meta.get("activation_mechanism")
                if canonical_activation_fields_observed else
                meta.get("activation_mechanism",
                         observed_activation_method or ("adapter" if spec else "none"))),
            "guidance_id": meta.get("guidance_id") or observed_guidance_identity,
            "guidance_hash": observed_guidance_hash,
            "guidance_source": (meta.get("guidance_source") or
                                (guidance.get(name) or {}).get("guidance_source")),
            "guidance_path": (meta.get("guidance_path") or
                              (guidance.get(name) or {}).get("guidance_path")),
            "guidance_content_hash": (meta.get("guidance_content_hash") or
                                       (guidance.get(name) or {}).get(
                                           "guidance_content_hash")),
            "workspace_receipt": meta.get("workspace_receipt"),
            "workspace_receipt_path": meta.get("workspace_receipt_path"),
            "workspace_receipt_hash": workspace_receipts[name]["hash"],
            "attestation_nonce": request["attestation_nonce"],
            "execution_request_hash": request_hash,
            "execution_observation_hash": observation_hash,
            "execution_attestation": meta.get("execution_attestation"),
            "filesystem_snapshot_before": snapshot_before,
            "filesystem_snapshot_after": snapshot_after,
        })
        expected_guidance = guidance.get(name) or {}
        current["attestation_layers"] = build_attestation_layers(
            current,
            expected_receipt_hash=workspace_receipts[name]["hash"],
            expected_guidance_id=expected_guidance.get("guidance_id"),
            expected_guidance_hash=expected_guidance.get("guidance_hash"),
            guided=bool(spec),
        )
        condition_evidence[name] = current

    repetition = {
        "rep": rep_index + 1,
        "repetition_id": repetition_id,
        "workspace_path": "adapter-provided",
        "canonical_task_seed_hash": canonical,
        "natural_task_hash": hashlib.sha256(natural_task.encode()).hexdigest(),
        "natural_task_identical_across_conditions": True,
        "condition_workspace_ids": {
            name: os.path.basename(workspaces[name]) for name in conditions},
        "condition_workspace_receipt_hashes": {
            name: workspace_receipts[name]["hash"] for name in conditions},
        "workspace_receipt_path": WORKSPACE_RECEIPT_PATH,
        "conditions": condition_evidence,
        "distinct_workers": len({condition_evidence[name].get("worker_id")
                                  for name in conditions}) == len(conditions),
        "distinct_sessions": len({condition_evidence[name].get("session_id")
                                   for name in conditions}) == len(conditions),
        "starting_task_hashes_match": len({
            condition_evidence[name].get("starting_task_hash")
            for name in conditions}) == 1,
        "task_hashes_match_canonical_seed": all(
            condition_evidence[name].get("starting_task_hash") == canonical
            for name in conditions),
        "workspace_paths_differ": len({
            os.path.basename(workspaces[name]) for name in conditions
        }) == len(conditions),
    }
    return repetition, canonical, workspaces


__all__ = [
    "ADAPTER_PROTOCOL",
    "CommandHarnessAdapter",
    "DEFAULT_TIMEOUT_SECONDS",
    "EXECUTION_ATTESTATION_PROTOCOL",
    "RUNTIME_TREATMENT_PATHS",
    "WORKSPACE_RECEIPT_PATH",
    "_failure",
    "_reject_symlinks",
    "as_text",
    "attestation_observation_hash",
    "attestation_request_hash",
    "cleanup_workspace",
    "copy_seed",
    "make_temp_dir",
    "materialize_guidance",
    "parse_command_argv_json",
    "run_condition_repetition",
    "skill_tree_hash",
    "snapshot_workspace",
    "validate_command_argv",
]
