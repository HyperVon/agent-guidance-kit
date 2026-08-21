"""Protocol-level claim validation independent of any harness."""

from __future__ import annotations

from evaluation_protocols import REGRESSION_STATUSES

__all__ = ["FORBIDDEN_REGRESSION_CLAIMS", "REGRESSION_STATUSES"]

FORBIDDEN_REGRESSION_CLAIMS = frozenset({
    "skill_improved",
    "skill_effective",
    "better_skill",
})
