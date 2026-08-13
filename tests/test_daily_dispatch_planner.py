from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from ofertas_bot.daily_dispatch_planner import (
    DispatchCandidate,
    load_daily_planning_policy,
    plan_daily_dispatches,
    weekly_rotation_daily_quotas,
)

POLICY_PATH = Path("config/selection_profiles.toml")


def test_feminino_policy_closes_daily_and_weekly_totals() -> None:
    policy = load_daily_planning_policy(POLICY_PATH)

    assert policy.items_per_window == 8
    assert policy.schedule_hours == tuple(range(8, 22))
    assert policy.daily_total_items == 112
    assert sum(policy.fixed_daily_quotas.values()) == 96
    assert sum(policy.weekly_rotation_quotas.values()) == 112
    assert len(policy.fixed_daily_quotas | policy.weekly_rotation_quotas) == 31


def test_weekly_rotation_closes_every_day_and_preserves_weekly_quota() -> None:
    policy = load_daily_planning_policy(POLICY_PATH)
    monday = date(2026, 8, 10)
    weekly = Counter()

    for offset in range(7):
        daily = weekly_rotation_daily_quotas(
            policy,
            planned_date=monday + timedelta(days=offset),
        )
        assert sum(daily.values()) == 16
        weekly.update(daily)

    assert dict(weekly) == policy.weekly_rotation_quotas
    assert all(count > 0 for count in weekly.values())


def test_daily_plan_builds_fourteen_windows_and_spreads_rotation() -> None:
    policy = load_daily_planning_policy(POLICY_PATH)
    candidates = _candidates_for_policy(policy, extra_per_subniche=2)

    plan = plan_daily_dispatches(
        candidates,
        policy=policy,
        planned_date=date(2026, 8, 13),
    )

    assert len(plan) == 112
    assert len({item.candidate.stable_key for item in plan}) == 112
    assert [item.daily_sequence for item in plan] == list(range(1, 113))
    by_hour = Counter(item.planned_hour for item in plan)
    assert by_hour == Counter({hour: 8 for hour in range(8, 22)})
    for hour in range(8, 22):
        window = [item for item in plan if item.planned_hour == hour]
        assert [item.slot_sequence for item in window] == list(range(1, 9))
        assert max(Counter(item.candidate.primary_subniche for item in window).values()) <= 2
        assert any(item.selection_bucket == "weekly_rotation" for item in window)
    assert sum(item.selection_bucket == "fixed_daily" for item in plan) == 96
    assert sum(item.selection_bucket == "weekly_rotation" for item in plan) == 16


def test_daily_plan_redistributes_shortfall_inside_fixed_class() -> None:
    policy = load_daily_planning_policy(POLICY_PATH)
    candidates = _candidates_for_policy(policy, extra_per_subniche=2)
    missing_subniche = "bolsas-e-carteiras"
    candidates = [
        item
        for item in candidates
        if not (
            item.primary_subniche == missing_subniche
            and item.item_id % 1000 >= policy.fixed_daily_quotas[missing_subniche]
        )
    ]

    plan = plan_daily_dispatches(
        candidates,
        policy=policy,
        planned_date=date(2026, 8, 13),
    )

    assert len(plan) == 112
    assert any(item.selection_reason == "fixed_daily:redistributed" for item in plan)


def _candidates_for_policy(policy, *, extra_per_subniche: int) -> list[DispatchCandidate]:
    candidates: list[DispatchCandidate] = []
    for subniche_index, (subniche, quota) in enumerate(
        (policy.fixed_daily_quotas | policy.weekly_rotation_quotas).items(),
        start=1,
    ):
        for rank in range(1, quota + extra_per_subniche + 1):
            item_id = subniche_index * 1000 + rank
            candidates.append(
                DispatchCandidate(
                    profile="feminino",
                    marketplace="shopee",
                    stable_key=f"{item_id:064x}",
                    item_id=item_id,
                    primary_subniche=subniche,
                    commercial_score=Decimal(1000 - rank),
                    sales_count=1000 - rank,
                    rating=Decimal("4.9"),
                )
            )
    return candidates
