from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from ofertas_bot.daily_dispatch_planner import (
    DailyPlanningPolicy,
    DispatchCandidate,
    load_daily_planning_policy,
    plan_daily_dispatches,
    weekly_rotation_daily_quotas,
)

POLICY_PATH = Path("config/selection_profiles.toml")
MODA_FIXED_GROUPS = {
    "moda-tops",
    "moda-bottoms",
    "moda-looks",
    "moda-fitness-praia",
    "moda-especial",
}
MAQUIAGEM_FIXED = {
    "maquiagem-pele",
    "maquiagem-olhos",
    "maquiagem-labios",
    "maquiagem-pinceis-e-esponjas",
    "maquiagem-organizacao",
    "maquiagem-geral",
}
MODA_SUBNICHES = {
    "moda-partes-de-cima",
    "moda-calcas",
    "moda-saias-e-shorts",
    "moda-vestidos",
    "moda-conjuntos",
    "moda-macacoes-e-macaquinhos",
    "moda-fitness",
    "moda-praia",
    "moda-plus-size",
    "moda-social-e-trabalho",
    "moda-casual",
    "moda-inverno",
    "moda-ofertas-e-basicos",
    "moda-geral",
}
EXCLUDED_MODA = {"moda-evangelica", "moda-festa", "moda-gestante"}
CALCADOS_SUBNICHES = {
    "calcados-sandalia",
    "calcados-sapatilha",
    "calcados-chinelo",
    "calcados-rasteirinha",
    "calcados-mocassim",
}
CALCADOS_DAILY_QUOTAS = {
    "calcados-sandalia": 10,
    "calcados-sapatilha": 8,
    "calcados-chinelo": 4,
    "calcados-rasteirinha": 4,
    "calcados-mocassim": 2,
}


def test_feminino_policy_closes_daily_and_weekly_totals() -> None:
    policy = load_daily_planning_policy(POLICY_PATH)

    assert policy.items_per_window == 10
    assert policy.schedule_hours == tuple(range(8, 22))
    assert policy.daily_total_items == 140
    assert sum(policy.fixed_daily_quotas.values()) == 124
    assert sum(policy.weekly_rotation_quotas.values()) == 112
    assert policy.rotation_items_per_day == 16
    assert sum(
        policy.fixed_daily_quotas[group] for group in MODA_FIXED_GROUPS
    ) == 36
    assert {
        subniche: policy.fixed_daily_quotas[subniche]
        for subniche in CALCADOS_SUBNICHES
    } == CALCADOS_DAILY_QUOTAS
    assert policy.window_family_quotas[0].family == "calcados"
    assert set(policy.window_family_quotas[0].subniches) == CALCADOS_SUBNICHES
    assert policy.window_family_quotas[0].items_per_window == 2
    assert policy.weekly_rotation_quotas["rotacao-moda"] == 28
    assert policy.publication_groups["moda-bottoms"] == (
        "moda-calcas",
        "moda-saias-e-shorts",
    )
    assert policy.publication_groups["moda-tops"] == ("moda-partes-de-cima",)
    assert set(policy.excluded_subniches) == EXCLUDED_MODA


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


def test_daily_plan_builds_ideal_editorial_distribution_without_fallback() -> None:
    policy = load_daily_planning_policy(POLICY_PATH)
    candidates = _candidates_for_policy(policy, extra_per_subniche=6)

    plan = plan_daily_dispatches(
        candidates,
        policy=policy,
        planned_date=date(2026, 8, 13),
    )

    assert len(plan) == 140
    assert len({item.candidate.stable_key for item in plan}) == 140
    assert [item.daily_sequence for item in plan] == list(range(1, 141))
    by_hour = Counter(item.planned_hour for item in plan)
    assert by_hour == Counter({hour: 10 for hour in range(8, 22)})
    for hour in range(8, 22):
        window = [item for item in plan if item.planned_hour == hour]
        assert [item.slot_sequence for item in window] == list(range(1, 11))
        assert max(Counter(item.candidate.primary_subniche for item in window).values()) <= 2
        assert (
            sum(item.candidate.primary_subniche in CALCADOS_SUBNICHES for item in window)
            == 2
        )
    assert sum(item.selection_bucket == "fixed_daily" for item in plan) == 124
    assert sum(item.selection_bucket == "weekly_rotation" for item in plan) == 16
    assert Counter(
        item.candidate.primary_subniche
        for item in plan
        if item.candidate.primary_subniche in CALCADOS_SUBNICHES
    ) == CALCADOS_DAILY_QUOTAS
    assert sum(
        item.selection_bucket == "fixed_daily"
        and item.selection_reason.removeprefix("fixed_daily:") in MODA_FIXED_GROUPS
        for item in plan
    ) == 36
    assert sum(item.selection_reason == "weekly_rotation:rotacao-moda" for item in plan) == 4
    assert sum(item.candidate.primary_subniche in MODA_SUBNICHES for item in plan) == 40
    assert sum(
        item.selection_bucket == "fixed_daily"
        and item.selection_reason.removeprefix("fixed_daily:") in MAQUIAGEM_FIXED
        for item in plan
    ) == 19
    assert sum(
        item.selection_bucket == "fixed_daily"
        and item.selection_reason
        in {"fixed_daily:cabelo-tratamento", "fixed_daily:cabelo-ferramentas"}
        for item in plan
    ) == 13
    assert sum(item.selection_reason == "fixed_daily:skincare-facial" for item in plan) == 9
    assert sum(item.selection_reason == "fixed_daily:unhas-manicure" for item in plan) == 5
    assert sum(item.selection_reason == "fixed_daily:cuidados-depilacao" for item in plan) == 1
    assert not any(item.candidate.primary_subniche in EXCLUDED_MODA for item in plan)
    assert not any(
        item.selection_reason.endswith(":redistributed")
        or item.selection_reason.endswith(":top_score_fallback")
        for item in plan
    )
    score_by_key = {candidate.stable_key: candidate.commercial_score for candidate in candidates}
    assert all(
        item.candidate.commercial_score == score_by_key[item.candidate.stable_key]
        for item in plan
    )


def test_moda_publication_group_selects_by_score_without_subniche_bonus() -> None:
    policy = load_daily_planning_policy(POLICY_PATH)
    candidates = _candidates_for_policy(policy, extra_per_subniche=6)
    candidates = [
        item
        for item in candidates
        if item.primary_subniche not in {"moda-calcas", "moda-saias-e-shorts"}
    ]
    scores = [
        ("moda-calcas", 61),
        ("moda-saias-e-shorts", 73),
        ("moda-calcas", 68),
        ("moda-saias-e-shorts", 40),
        ("moda-calcas", 39),
        ("moda-saias-e-shorts", 38),
        ("moda-calcas", 37),
        ("moda-saias-e-shorts", 36),
        ("moda-calcas", 35),
        ("moda-saias-e-shorts", 34),
    ]
    for index, (subniche, score) in enumerate(scores, start=1):
        candidates.append(
            _candidate(
                subniche=subniche,
                item_id=900_000 + index,
                score=Decimal(score),
            )
        )

    plan = plan_daily_dispatches(
        candidates,
        policy=policy,
        planned_date=date(2026, 8, 13),
    )

    selected_scores = sorted(
        (
            item.candidate.commercial_score
            for item in plan
            if item.selection_reason == "fixed_daily:moda-bottoms"
        ),
        reverse=True,
    )
    assert selected_scores[:3] == [Decimal(73), Decimal(68), Decimal(61)]


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

    assert len(plan) == 140
    assert any(item.selection_reason == "fixed_daily:redistributed" for item in plan)
    assert not any(
        item.selection_reason == f"fixed_daily:{missing_subniche}"
        and item.candidate.primary_subniche != missing_subniche
        for item in plan
    )


def test_daily_plan_fills_rotation_shortfall_from_top_general_score() -> None:
    policy = load_daily_planning_policy(POLICY_PATH)
    candidates = []
    for quota_index, (quota_key, quota) in enumerate(
        policy.fixed_daily_quotas.items(),
        start=1,
    ):
        subniche = policy.publication_groups.get(quota_key, (quota_key,))[0]
        for rank in range(1, quota + 1):
            candidates.append(
                _candidate(
                    subniche=subniche,
                    item_id=quota_index * 1000 + rank,
                )
            )
    for index in range(1, 17):
        candidates.append(
            _candidate(
                subniche="feminino-geral",
                item_id=800_000 + index,
                score=Decimal(10_000 - index),
            )
        )

    plan = plan_daily_dispatches(
        candidates,
        policy=policy,
        planned_date=date(2026, 8, 16),
    )

    assert len(plan) == 140
    assert sum(item.selection_bucket == "weekly_rotation" for item in plan) == 16
    assert sum(
        item.selection_reason == "weekly_rotation:top_score_fallback" for item in plan
    ) == 16
    assert len({item.candidate.stable_key for item in plan}) == 140


def test_excluded_moda_subniches_never_enter_plan_even_with_high_scores() -> None:
    policy = load_daily_planning_policy(POLICY_PATH)
    candidates = _candidates_for_policy(policy, extra_per_subniche=6)
    for index, subniche in enumerate(EXCLUDED_MODA, start=1):
        candidates.append(
            _candidate(
                subniche=subniche,
                item_id=950_000 + index,
                score=Decimal(10_000 + index),
            )
        )

    plan = plan_daily_dispatches(
        candidates,
        policy=policy,
        planned_date=date(2026, 8, 13),
    )

    assert not any(item.candidate.primary_subniche in EXCLUDED_MODA for item in plan)


def test_policy_without_publication_groups_preserves_subniche_behavior() -> None:
    policy = DailyPlanningPolicy(
        profile="teste",
        marketplace="shopee",
        items_per_window=2,
        schedule_hours=(8,),
        daily_total_items=2,
        rotation_items_per_day=1,
        max_items_per_subniche_per_window=2,
        fixed_daily_quotas={"sub-a": 1},
        weekly_rotation_quotas={"sub-b": 7},
    )
    candidates = [
        _candidate(profile="teste", subniche="sub-a", item_id=1, score=Decimal(20)),
        _candidate(profile="teste", subniche="sub-b", item_id=2, score=Decimal(10)),
    ]

    plan = plan_daily_dispatches(
        candidates,
        policy=policy,
        planned_date=date(2026, 8, 13),
    )

    assert [item.selection_reason for item in plan] == [
        "weekly_rotation:sub-b",
        "fixed_daily:sub-a",
    ]


def _candidates_for_policy(policy, *, extra_per_subniche: int) -> list[DispatchCandidate]:
    candidates: list[DispatchCandidate] = []
    required = Counter()
    for quotas in (policy.fixed_daily_quotas, policy.weekly_rotation_quotas):
        for quota_key, quota in quotas.items():
            for subniche in policy.publication_groups.get(quota_key, (quota_key,)):
                required[subniche] += quota
    for subniche_index, (subniche, quota) in enumerate(required.items(), start=1):
        for rank in range(1, quota + extra_per_subniche + 1):
            item_id = subniche_index * 1000 + rank
            candidates.append(_candidate(subniche=subniche, item_id=item_id))
    return candidates


def _candidate(
    *,
    subniche: str,
    item_id: int,
    score: Decimal | None = None,
    profile: str = "feminino",
) -> DispatchCandidate:
    resolved_score = score or Decimal(1000 - item_id % 1000)
    return DispatchCandidate(
        profile=profile,
        marketplace="shopee",
        stable_key=f"{item_id:064x}",
        item_id=item_id,
        primary_subniche=subniche,
        commercial_score=resolved_score,
        sales_count=int(resolved_score),
        rating=Decimal("4.9"),
    )


def _quota_subniches(
    policy: DailyPlanningPolicy,
    quotas: dict[str, int],
) -> set[str]:
    return {
        subniche
        for quota_key in quotas
        for subniche in policy.publication_groups.get(quota_key, (quota_key,))
    }
