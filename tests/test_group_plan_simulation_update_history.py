from datetime import UTC, datetime

from ofertas_bot.group_plan_simulation import GroupPlanSimulation
from ofertas_bot.group_profiles import GroupProfile, GroupProfileCatalog
from ofertas_bot.settings import Settings
from ofertas_bot.storage.json_group_run_history_store import JsonGroupRunHistoryStore


def test_group_plan_simulation_result_updates_history(tmp_path) -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    history_path = tmp_path / "history.json"
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
    history = result.update_history(history_path=history_path, ran_at=now)

    assert history == {"maquiagem-vip": now}
    assert JsonGroupRunHistoryStore(path=history_path).load() == history
