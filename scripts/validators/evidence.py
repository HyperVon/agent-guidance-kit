"""Shared evidence-boundary validation for neutral adapters."""

from __future__ import annotations

import hashlib


def validate_workspace_receipt(
    cmeta: dict,
    expected_hash: str | None,
    ctag: str,
    errs: list[str],
    *,
    expected_path: str | None,
) -> None:
    """Require the adapter to return the receipt from the requested workspace."""

    if cmeta.get("workspace_receipt_path") != expected_path:
        errs.append(f"{ctag}: workspace receipt path is not the neutral receipt path")
    receipt = cmeta.get("workspace_receipt")
    if not isinstance(receipt, str) or not receipt:
        errs.append(f"{ctag}: adapter did not return a workspace receipt")
        return
    if cmeta.get("workspace_receipt_hash") != expected_hash:
        errs.append(f"{ctag}: workspace receipt hash is not bound to its condition")
    actual_hash = "sha256:" + hashlib.sha256(receipt.encode()).hexdigest()
    if actual_hash != expected_hash:
        errs.append(f"{ctag}: workspace receipt does not match the evaluator receipt")
