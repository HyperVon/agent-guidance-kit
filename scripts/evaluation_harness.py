#!/usr/bin/env python3
"""Harness-neutral execution primitives.

The evaluation protocol owns condition isolation, task hashing, and evidence
shape.  A harness adapter owns the model/session invocation and reports the
small set of boundary facts that only it can observe.  The adapter is an
external command that receives one JSON request on stdin and returns one JSON
object on stdout, so the core evaluator does not depend on a particular agent
CLI, provider, or container runtime.

The existing Docker/Kilo runner remains available as an optional legacy
adapter.  New protocol code should use this module's neutral fields instead of
assuming that adapter.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import tempfile
import uuid

from eval_hashing import HASH_PREFIX, hash_task_workspace, hash_workspace


ADAPTER_PROTOCOL = "agent-guidance-kit.harness-adapter/v1"
EXECUTION_ATTESTATION_PROTOCOL = (
    "agent-guidance-kit.execution-attestation/v1")
ATTESTED_OBSERVATION_FIELDS = (
    "run_status", "worker_id", "session_id", "returncode", "output",
    "guidance_probe", "guidance_context_probe", "activation_mechanism",
    "workspace_receipt_path", "workspace_receipt")
WORKSPACE_RECEIPT_PATH = ".evaluation-runtime/workspace-receipt"
RUNTIME_TREATMENT_PATHS = (".evaluation-runtime/guidance",
                           WORKSPACE_RECEIPT_PATH)
DEFAULT_TIMEOUT_SECONDS = 1200


def make_temp_dir(prefix: str) -> str:
    """Create a disposable directory under the repository's ignored temp root."""

    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".evaluation-tmp",
    )
    os.makedirs(root, exist_ok=True)
    path = tempfile.mkdtemp(prefix=prefix, dir=root)
    os.chmod(path, 0o755)
    return path


def _reject_symlinks(root: str, label: str) -> None:
    """Reject symlinks before a worker-visible tree is copied or hashed."""

    if os.path.islink(root):
        raise ValueError(f"{label} must not be a symlink: {root}")
    for current, directories, files in os.walk(root, followlinks=False):
        for name in [*directories, *files]:
            path = os.path.join(current, name)
            if os.path.islink(path):
                relative = os.path.relpath(path, root)
                raise ValueError(
                    f"{label} must not contain symlinks: {relative}")


def copy_seed(source: str) -> str:
    """Copy a pristine fixture to an independent writable condition workspace."""

    _reject_symlinks(source, "fixture seed")
    destination = make_temp_dir("harness-workspace-")
    shutil.copytree(source, destination, dirs_exist_ok=True)
    for root, directories, files in os.walk(destination, followlinks=False):
        for name in [*directories, *files]:
            path = os.path.join(root, name)
            if os.path.islink(path):
                continue
            try:
                mode = os.stat(path, follow_symlinks=False).st_mode
                os.chmod(path, mode | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
            except OSError:
                pass
    os.chmod(destination, os.stat(destination).st_mode |
             stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    return destination


def skill_tree_hash(skill_dir: str) -> str | None:
    """Hash only the worker-visible guidance tree: SKILL.md and references."""

    if not os.path.isdir(skill_dir):
        return None
    _reject_symlinks(skill_dir, "skill guidance source")
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return None
    relative_paths = ["SKILL.md"]
    references = os.path.join(skill_dir, "references")
    if os.path.isdir(references):
        for root, _, names in os.walk(references):
            for name in names:
                path = os.path.join(root, name)
                relative_paths.append(os.path.relpath(path, skill_dir))
    digest = hashlib.sha256()
    for relative in sorted(relative_paths):
        path = os.path.join(skill_dir, relative)
        with open(path, "rb") as handle:
            content_hash = hashlib.sha256(handle.read()).hexdigest()
        digest.update(f"{relative}:{content_hash}\n".encode())
    return HASH_PREFIX + digest.hexdigest()


def materialize_guidance(source_skill_dir: str, workspace: str) -> str:
    """Place guidance at a neutral evaluator-owned runtime path.

    The adapter may mount or copy this directory into its own native discovery
    mechanism.  The path intentionally has no harness-specific meaning.
    """

    _reject_symlinks(source_skill_dir, "skill guidance source")
    destination = os.path.join(workspace, RUNTIME_TREATMENT_PATHS[0])
    os.makedirs(destination, exist_ok=True)
    skill_md = os.path.join(source_skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        raise ValueError(f"skill source missing SKILL.md: {source_skill_dir}")
    shutil.copy(skill_md, os.path.join(destination, "SKILL.md"))
    references = os.path.join(source_skill_dir, "references")
    if os.path.isdir(references):
        shutil.copytree(references, os.path.join(destination, "references"),
                        dirs_exist_ok=True)
    return destination


def _write_workspace_receipt(workspace: str) -> dict[str, str]:
    """Create a random receipt that only the requested workspace can provide."""

    path = os.path.join(workspace, WORKSPACE_RECEIPT_PATH)
    if os.path.lexists(path):
        raise ValueError(f"workspace receipt path already exists: {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    token = uuid.uuid4().hex
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(token)
    return {
        "path": WORKSPACE_RECEIPT_PATH,
        "hash": HASH_PREFIX + hashlib.sha256(token.encode()).hexdigest(),
    }


def snapshot_workspace(workspace: str) -> dict:
    """Capture a deterministic pre/post task-state snapshot."""

    git = os.path.join(workspace, ".git")
    if os.path.isdir(git):
        def git_output(*arguments: str) -> str:
            return subprocess.run(
                ["git", "-C", workspace, *arguments],
                capture_output=True,
                text=True,
                check=False,
            ).stdout

        try:
            head = subprocess.check_output(
                ["git", "-C", workspace, "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except Exception:
            head = None
        return {
            "vcs": "git",
            "head": head,
            "status": git_output("status", "--porcelain=v1"),
            "diff": git_output("diff", "--no-color"),
        }
    files = {}
    for root, _, names in os.walk(workspace):
        for name in names:
            path = os.path.join(root, name)
            relative = os.path.relpath(path, workspace)
            if relative.split(os.sep)[0] == ".git":
                continue
            try:
                files[relative] = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]
            except OSError:
                pass
    return {"vcs": "files", "listing": files}


def _as_text(value) -> str:
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
    payload["output"] = _as_text(payload["output"])
    payload["workspace_receipt"] = _as_text(payload["workspace_receipt"])
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False)
    return HASH_PREFIX + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _failure(returncode: int | None, reason: str, *, stdout: str = "",
             stderr: str = "") -> dict:
    return {
        "returncode": returncode,
        "stdout": _as_text(stdout),
        "stderr": _as_text(stderr),
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

    Request input is one JSON object.  The adapter must return one JSON object
    with at least ``run_status``, ``session_id``, ``worker_id`` (or
    ``container_id``), ``returncode``, ``output``, ``guidance_probe``,
    ``guidance_context_probe``, ``workspace_receipt_path``, and
    ``workspace_receipt``. Successful runs must also return a verified
    ``execution_attestation`` bound to the request nonce, worker/session IDs,
    output, probes, activation mechanism, and workspace receipt. Extra
    harness-specific metadata is preserved under ``adapter_metadata`` and never
    interpreted by the protocol validator.
    """

    def __init__(self, command: str | list[str], *, name: str = "external",
                 timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
                 cwd: str | None = None):
        self.command = (shlex.split(command) if isinstance(command, str)
                        else list(command))
        if not self.command:
            raise ValueError("harness adapter command must not be empty")
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.cwd = cwd

    def run(self, request: dict) -> dict:
        """Run one isolated condition through the configured adapter."""

        request = dict(request)
        request.setdefault("adapter_protocol", ADAPTER_PROTOCOL)
        try:
            process = subprocess.run(
                self.command,
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=self.cwd,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return _failure(None, "harness adapter timed out",
                            stdout=exc.stdout or exc.output or "",
                            stderr=exc.stderr or "")
        except OSError as exc:
            return _failure(None, f"harness adapter invocation failed: {exc}")

        stdout = _as_text(process.stdout)
        stderr = _as_text(process.stderr)
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
        normalized["stdout"] = _as_text(normalized.get("stdout", stdout))
        normalized["stderr"] = _as_text(normalized.get("stderr", stderr))
        normalized["returncode"] = normalized.get("returncode", process.returncode)
        normalized["run_status"] = normalized.get(
            "run_status", normalized.get("status"))
        normalized["status"] = normalized["run_status"]
        normalized["output"] = _as_text(
            normalized.get("output", normalized.get("text", "")))
        normalized["worker_id"] = normalized.get(
            "worker_id", normalized.get("container_id"))
        normalized["guidance_probe"] = normalized.get(
            "guidance_probe", normalized.get("skill_probe"))
        normalized["guidance_context_probe"] = normalized.get(
            "guidance_context_probe", normalized.get("skill_context_probe"))
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
    """Run one protocol comparison using only the neutral adapter contract."""

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
        name: _write_workspace_receipt(workspaces[name]) for name in conditions
    }
    guidance = {}
    for name in conditions:
        spec = activation_specs.get(name)
        if not spec:
            continue
        tree = materialize_guidance(spec["source_dir"], workspaces[name])
        content_hash = skill_tree_hash(spec["source_dir"])
        if content_hash is None:
            raise ValueError(f"skill source has no hashable guidance tree: {spec}")
        guidance[name] = {
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
        observation.update({
            "run_status": meta.get("run_status", meta.get("status")),
            "worker_id": meta.get("worker_id") or meta.get("container_id"),
            "output": _as_text(meta.get("output", meta.get("text", ""))),
            "guidance_probe": meta.get(
                "guidance_probe", meta.get("skill_probe")),
            "guidance_context_probe": meta.get(
                "guidance_context_probe", meta.get("skill_context_probe")),
            "activation_mechanism": meta.get(
                "activation_mechanism", "adapter" if spec else "none"),
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
            "guidance_probe": meta.get("guidance_probe"),
            "guidance_context_probe": meta.get("guidance_context_probe"),
            "activation_mechanism": meta.get(
                "activation_mechanism", "adapter" if spec else "none"),
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
