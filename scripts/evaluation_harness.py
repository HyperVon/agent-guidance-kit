#!/usr/bin/env python3
"""Backward-compatible facade for the harness-neutral evaluation package.

New code should import the focused modules under ``evaluation`` when it needs
one responsibility. Existing runners and adapters may continue importing this
module; the public names remain stable while the implementation is split into
workspace, guidance, receipt, attestation, and harness modules.
"""

import subprocess

from eval_hashing import hash_task_workspace, hash_workspace

from evaluation.attestation import (
    ATTESTED_OBSERVATION_FIELDS,
    ATTESTATION_CONFIDENCE_LEVELS,
    EXECUTION_ATTESTATION_PROTOCOL,
    STRONG_ATTESTATION_CONFIDENCE_LEVELS,
    as_text,
    attestation_observation_hash,
    attestation_request_hash,
    build_attestation_layers,
)
from evaluation.guidance import (
    materialize_guidance,
    skill_tree_hash,
    snapshot_workspace,
)
from evaluation.harness import (
    ADAPTER_PROTOCOL,
    DEFAULT_TIMEOUT_SECONDS,
    CommandHarnessAdapter,
    _failure,
    parse_command_argv_json,
    run_condition_repetition,
    validate_command_argv,
)
from evaluation.receipts import (
    RUNTIME_TREATMENT_PATHS,
    WORKSPACE_RECEIPT_PATH,
    receipt_hash,
    verify_workspace_receipt,
    write_workspace_receipt as _write_workspace_receipt,
)
from evaluation.workspace import (
    _reject_symlinks,
    cleanup_workspace,
    copy_seed,
    make_temp_dir,
)


__all__ = [
    "ADAPTER_PROTOCOL",
    "ATTESTED_OBSERVATION_FIELDS",
    "ATTESTATION_CONFIDENCE_LEVELS",
    "CommandHarnessAdapter",
    "DEFAULT_TIMEOUT_SECONDS",
    "EXECUTION_ATTESTATION_PROTOCOL",
    "RUNTIME_TREATMENT_PATHS",
    "STRONG_ATTESTATION_CONFIDENCE_LEVELS",
    "WORKSPACE_RECEIPT_PATH",
    "_failure",
    "_reject_symlinks",
    "_write_workspace_receipt",
    "as_text",
    "attestation_observation_hash",
    "attestation_request_hash",
    "build_attestation_layers",
    "cleanup_workspace",
    "copy_seed",
    "make_temp_dir",
    "materialize_guidance",
    "parse_command_argv_json",
    "hash_task_workspace",
    "hash_workspace",
    "receipt_hash",
    "run_condition_repetition",
    "skill_tree_hash",
    "snapshot_workspace",
    "subprocess",
    "verify_workspace_receipt",
    "validate_command_argv",
]
