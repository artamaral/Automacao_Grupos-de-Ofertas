from datetime import UTC, datetime

from ofertas_bot.group_plan_approval import GroupPlanApproval
from ofertas_bot.group_plan_simulation import GroupPlanSimulation
from ofertas_bot.group_profiles import GroupProfile, GroupProfileCatalog
from ofertas_bot.settings import Settings


def test_group_plan_simulation_result_evaluates_approval() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    catalog = GroupProfileCatalog.from_iterable(
        (
            GroupProfile(
                slug="maquiagem-vip",
                name="Maquiagem VIP",
                allowed_niches=("maquiagem",),
            ),
            GroupProfile(
                slug="casa-vip",
                name="Casa VIP",
                allowed_niches=("casa",),
            ),
        )
    )
    simulation = GroupPlanSimulation(
        settings=Settings(max_offers_per_run=1),
        catalog=catalog,
    )
    approval = GroupPlanApproval(
        approved=True,
        reviewer="arthur",
        reviewed_at=now,
    )

    result = simulation.build(niche="maquiagem", now=now)
    approval_result = result.evaluate_approval(approval)

    assert approval_result.approved
    assert len(approval_result.plans) == 1
    assert approval_result.plans[0].group_slug == "maquiagem-vip"


def test_group_plan_simulation_result_blocks_missing_approval() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    catalog = GroupProfileCatalog.from_iterable(
        (
            GroupProfile(
                slug="maquiagem-vip",
                name="Maquiagem VIP",
                allowed_niches=("maquiagem",),
            ),
        )
    )
    simulation = GroupPlanSimulation(
        settings=Settings(max_offers_per_run=1),
        catalog=catalog,
    )

    result = simulation.build(niche="maquiagem", now=now)
    approval_result = result.evaluate_approval(None)

    assert not approval_result.approved
    assert approval_result.reasons == ("aprovacao humana ausente",)
