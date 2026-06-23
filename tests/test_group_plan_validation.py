import pytest

from ofertas_bot.group_plan_validation import (
    GroupPlanValidationError,
    normalize_plan_niche,
    validate_plan_limit,
)


def test_normalize_plan_niche_strips_and_lowercases() -> None:
    assert normalize_plan_niche(" Maquiagem ") == "maquiagem"


def test_normalize_plan_niche_rejects_blank_value() -> None:
    with pytest.raises(GroupPlanValidationError, match="niche"):
        normalize_plan_niche("   ")


def test_validate_plan_limit_accepts_positive_value() -> None:
    assert validate_plan_limit(1) == 1


def test_validate_plan_limit_rejects_zero_or_negative_values() -> None:
    with pytest.raises(GroupPlanValidationError, match="positive"):
        validate_plan_limit(0)

    with pytest.raises(GroupPlanValidationError, match="positive"):
        validate_plan_limit(-1)
