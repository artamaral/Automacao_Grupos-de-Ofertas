from datetime import UTC, datetime

from ofertas_bot.group_plan_approval import GroupPlanApproval
from ofertas_bot.group_plan_simulation import GroupPlanSimulation
from ofertas_bot.group_profiles import GroupProfile, GroupProfileCatalog
from ofertas_bot.settings import Settings
from ofertas_bot.storage.json_group_run_history_store import JsonGroupRunHistoryStore


def make_simulation() -> GroupPlanSimulation:
    catalog = GroupProfileCatalog.from_iterable(
        (
            GroupProfile(
                slug="maquiagem-vip",
                name="Maquiagem VIP",
                allowed_niches=("maquiagem",),
            ),
        )
    )
    return GroupPlanSimulation(
        settings=Settings(max_offers_per_run=1),
        catalog=catalog,
    )


def test_update_history_after_approval_writes_allowed_plans(tmp_path) -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    history_path = tmp_path / "history.json"
    approval = GroupPlanApproval(
        approved=True,
        reviewer="arthur",
        reviewed_at=now,
    )

    result = make_simulation().build(niche="maquiagem", now=now)
    approval_result = result.update_history_after_approval(
        approval=approval,
        history_path=history_path,
        ran_at=now,
    )

    assert approval_result.approved
    assert JsonGroupRunHistoryStore(path=history_path).load() == {
        "maquiagem-vip": now
    }


def test_update_history_after_approval_does_not_write_without_approval(tmp_path) -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    history_path = tmp_path / "history.json"

    result = make_simulation().build(niche="maquiagem", now=now)
    approval_result = result.update_history_after_approval(
        approval=None,
        history_path=history_path,
        ran_at=now,
    )

    assert not approval_result.approved
    assert not history_path.exists()
