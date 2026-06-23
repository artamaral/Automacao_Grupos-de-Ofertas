from datetime import UTC, datetime

from ofertas_bot.group_plan_simulation import GroupPlanSimulation
from ofertas_bot.group_profiles import GroupProfile, GroupProfileCatalog
from ofertas_bot.settings import Settings


def test_group_plan_simulation_result_returns_text() -> None:
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

    text = simulation.build(
        niche="maquiagem",
        now=datetime(2026, 6, 23, 18, 0, tzinfo=UTC),
    ).to_text()

    assert "Resumo do plano por grupo" in text
    assert "metadata.niche=maquiagem" in text
    assert "group=maquiagem-vip" in text
