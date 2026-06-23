from datetime import UTC, datetime, timedelta

import pytest

from ofertas_bot.group_plan_simulation import GroupPlanSimulation
from ofertas_bot.group_plan_validation import GroupPlanValidationError
from ofertas_bot.group_profiles import GroupProfile, GroupProfileCatalog
from ofertas_bot.settings import Settings


def make_catalog() -> GroupProfileCatalog:
    return GroupProfileCatalog.from_iterable(
        (
            GroupProfile(
                slug="maquiagem-vip",
                name="Maquiagem VIP",
                allowed_niches=("maquiagem",),
                max_offers_per_run=1,
                min_minutes_between_posts=120,
            ),
            GroupProfile(
                slug="casa-vip",
                name="Casa VIP",
                allowed_niches=("casa",),
                max_offers_per_run=1,
                min_minutes_between_posts=120,
            ),
        )
    )


def test_group_plan_simulation_builds_summary_with_mock_offers() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    simulation = GroupPlanSimulation(
        settings=Settings(max_offers_per_run=2),
        catalog=make_catalog(),
    )

    result = simulation.build(niche="maquiagem", now=now)

    assert len(result.plans) == 2
    assert result.summary["total_groups"] == 2
    assert result.summary["allowed_groups"] == 1
    assert result.summary["blocked_groups"] == 1
    assert result.summary["total_selected_offers"] == 1
    assert result.summary["groups"][0]["group_slug"] == "maquiagem-vip"
    assert result.summary["metadata"] == {
        "niche": "maquiagem",
        "generated_at": "2026-06-23T18:00:00+00:00",
        "file_prefix": "20260623T180000Z-maquiagem",
        "offer_limit": 2,
        "collected_offer_count": 2,
        "source_marketplace": "mock",
    }


def test_group_plan_simulation_normalizes_metadata_niche() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    simulation = GroupPlanSimulation(
        settings=Settings(max_offers_per_run=2),
        catalog=make_catalog(),
    )

    result = simulation.build(niche=" Maquiagem ", now=now, limit=1)

    assert result.summary["metadata"]["niche"] == "maquiagem"
    assert result.summary["metadata"]["file_prefix"] == "20260623T180000Z-maquiagem"
    assert result.summary["metadata"]["offer_limit"] == 1


def test_group_plan_simulation_rejects_blank_niche() -> None:
    simulation = GroupPlanSimulation(
        settings=Settings(max_offers_per_run=2),
        catalog=make_catalog(),
    )

    with pytest.raises(GroupPlanValidationError, match="niche"):
        simulation.build(
            niche="   ",
            now=datetime(2026, 6, 23, 18, 0, tzinfo=UTC),
        )


def test_group_plan_simulation_rejects_invalid_limit() -> None:
    simulation = GroupPlanSimulation(
        settings=Settings(max_offers_per_run=2),
        catalog=make_catalog(),
    )

    with pytest.raises(GroupPlanValidationError, match="positive"):
        simulation.build(
            niche="maquiagem",
            now=datetime(2026, 6, 23, 18, 0, tzinfo=UTC),
            limit=0,
        )


def test_group_plan_simulation_respects_group_last_run() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    simulation = GroupPlanSimulation(
        settings=Settings(max_offers_per_run=2),
        catalog=make_catalog(),
    )

    result = simulation.build(
        niche="maquiagem",
        now=now,
        last_runs_by_group={"maquiagem-vip": now - timedelta(minutes=30)},
    )

    assert result.summary["allowed_groups"] == 0
    assert result.summary["blocked_groups"] == 2
    assert result.summary["total_selected_offers"] == 0
    assert result.summary["groups"][0]["next_available_at"] == "2026-06-23T19:30:00+00:00"


def test_group_plan_simulation_saves_summary(tmp_path) -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    simulation = GroupPlanSimulation(
        settings=Settings(max_offers_per_run=2),
        catalog=make_catalog(),
    )
    result = simulation.build(niche="maquiagem", now=now)
    path = tmp_path / "summary.json"

    simulation.save_summary(summary=result.summary, path=path)

    assert path.exists()
    assert "maquiagem-vip" in path.read_text(encoding="utf-8")
