from datetime import UTC, datetime

from ofertas_bot.group_plan_simulation import GroupPlanSimulation
from ofertas_bot.group_profiles import GroupProfile, GroupProfileCatalog
from ofertas_bot.settings import Settings


def test_group_plan_simulation_result_saves_text(tmp_path) -> None:
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
    result = simulation.build(
        niche="maquiagem",
        now=datetime(2026, 6, 23, 18, 0, tzinfo=UTC),
    )
    path = tmp_path / "summary.txt"

    result.save_text(path)

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "Resumo do plano por grupo" in text
    assert "group=maquiagem-vip" in text
