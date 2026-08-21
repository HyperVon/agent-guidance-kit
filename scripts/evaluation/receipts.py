"""Evaluator-owned workspace receipt creation and verification."""

from __future__ import annotations

import hashlib
import os
import uuid

from eval_hashing import HASH_PREFIX


WORKSPACE_RECEIPT_PATH = ".evaluation-runtime/workspace-receipt"
RUNTIME_TREATMENT_PATHS = (".evaluation-runtime/guidance",
                           WORKSPACE_RECEIPT_PATH)


def receipt_hash(receipt: str) -> str:
    """Return the content digest used to bind a receipt to a workspace."""

    return HASH_PREFIX + hashlib.sha256(receipt.encode()).hexdigest()


def write_workspace_receipt(workspace: str) -> dict[str, str]:
    """Create a random receipt that only the requested workspace can provide."""

    path = os.path.join(workspace, WORKSPACE_RECEIPT_PATH)
    if os.path.lexists(path):
        raise ValueError(f"workspace receipt path already exists: {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    token = uuid.uuid4().hex
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(token)
    return {"path": WORKSPACE_RECEIPT_PATH, "hash": receipt_hash(token)}


def verify_workspace_receipt(receipt: object, expected_hash: object) -> bool:
    """Check a returned receipt without treating it as isolation proof."""

    return (isinstance(receipt, str) and isinstance(expected_hash, str)
            and bool(receipt) and receipt_hash(receipt) == expected_hash)


__all__ = [
    "RUNTIME_TREATMENT_PATHS",
    "WORKSPACE_RECEIPT_PATH",
    "receipt_hash",
    "verify_workspace_receipt",
    "write_workspace_receipt",
]
