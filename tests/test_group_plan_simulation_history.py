from datetime import UTC, datetime, timedelta

from ofertas_bot.group_plan_simulation import GroupPlanSimulation
from ofertas_bot.group_profiles import GroupProfile, GroupProfileCatalog
from ofertas_bot.settings import Settings
from ofertas_bot.storage.json_group_run_history_store import JsonGroupRunHistoryStore


def test_group_plan_simulation_builds_with_history_file(tmp_path) -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    history_path = tmp_path / "history.json"
    JsonGroupRunHistoryStore(path=history_path).save(
        {"maquiagem-vip": now - timedelta(minutes=30)}
    )
    catalog = GroupProfileCatalog.from_iterable(
        (
            GroupProfile(
                slug="maquiagem-vip",
                name="Maquiagem VIP",
                allowed_niches=("maquiagem",),
                min_minutes_between_posts=120,
            ),
        )
    )
    simulation = GroupPlanSimulation(
        settings=Settings(max_offers_per_run=1),
        catalog=catalog,
    )

    result = simulation.build_with_history(
        niche="maquiagem",
        now=now,
        history_path=history_path,
    )

    assert result.summary["allowed_groups"] == 0
    assert result.summary["blocked_groups"] == 1
    assert result.summary["groups"][0]["next_available_at"] == "2026-06-23T19:30:00+00:00"
