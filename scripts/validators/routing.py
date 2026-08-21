"""Routing-specific validation helpers.

Routing adapters may expose selected-skill decisions, but this module keeps
that harness-facing parsing separate from execution and regression evidence.
"""

from __future__ import annotations


def validate_selected_skill_decision(decision: object, valid_actions: set[str]) -> list[str]:
    """Validate the small provider-neutral routing decision shape."""

    errors: list[str] = []
    if not isinstance(decision, dict):
        return ["routing decision must be an object"]
    if "selected_skill" not in decision:
        errors.append("routing decision missing selected_skill")
    if decision.get("action") not in valid_actions:
        errors.append(f"routing decision has invalid action {decision.get('action')!r}")
    return errors
