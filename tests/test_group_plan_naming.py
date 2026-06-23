from datetime import UTC, datetime, timedelta, timezone

import pytest

from ofertas_bot.group_plan_naming import build_group_plan_file_prefix
from ofertas_bot.group_plan_validation import GroupPlanValidationError


def test_build_group_plan_file_prefix_uses_utc_timestamp_and_slug() -> None:
    prefix = build_group_plan_file_prefix(
        niche=" Maquiagem ",
        generated_at=datetime(2026, 6, 23, 18, 0, tzinfo=UTC),
    )

    assert prefix == "20260623T180000Z-maquiagem"


def test_build_group_plan_file_prefix_normalizes_timezone_to_utc() -> None:
    prefix = build_group_plan_file_prefix(
        niche="casa e cozinha",
        generated_at=datetime(
            2026,
            6,
            23,
            15,
            0,
            tzinfo=timezone(timedelta(hours=-3)),
        ),
    )

    assert prefix == "20260623T180000Z-casa-e-cozinha"


def test_build_group_plan_file_prefix_rejects_blank_niche() -> None:
    with pytest.raises(GroupPlanValidationError, match="niche"):
        build_group_plan_file_prefix(
            niche="   ",
            generated_at=datetime(2026, 6, 23, 18, 0, tzinfo=UTC),
        )
