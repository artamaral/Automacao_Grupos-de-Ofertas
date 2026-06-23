from __future__ import annotations


class GroupPlanValidationError(ValueError):
    """Raised when group plan parameters are invalid."""


def normalize_plan_niche(niche: str) -> str:
    normalized = niche.strip().lower()
    if not normalized:
        raise GroupPlanValidationError("plan niche is required")
    return normalized


def validate_plan_limit(limit: int) -> int:
    if limit <= 0:
        raise GroupPlanValidationError("plan limit must be positive")
    return limit
