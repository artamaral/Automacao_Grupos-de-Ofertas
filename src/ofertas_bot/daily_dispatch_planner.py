from __future__ import annotations

import tomllib
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path


class DispatchPlanningError(ValueError):
    """Raised when a daily dispatch plan cannot satisfy its contract."""


@dataclass(frozen=True)
class DispatchCandidate:
    profile: str
    marketplace: str
    stable_key: str
    item_id: int
    primary_subniche: str
    commercial_score: Decimal
    sales_count: int
    rating: Decimal | None


@dataclass(frozen=True)
class DailyPlanningPolicy:
    profile: str
    marketplace: str
    items_per_window: int
    schedule_hours: tuple[int, ...]
    daily_total_items: int
    rotation_items_per_day: int
    max_items_per_subniche_per_window: int
    fixed_daily_quotas: dict[str, int]
    weekly_rotation_quotas: dict[str, int]
    publication_groups: dict[str, tuple[str, ...]] = field(default_factory=dict)
    excluded_subniches: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlannedDispatch:
    candidate: DispatchCandidate
    selection_bucket: str
    selection_reason: str
    planned_date: date
    planned_hour: int
    slot_sequence: int
    daily_sequence: int


def load_daily_planning_policy(
    path: Path,
    *,
    profile: str = "feminino",
    marketplace: str = "shopee",
) -> DailyPlanningPolicy:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    for item in raw.get("policies", []):
        if item.get("slug") != profile or item.get("planning_mode") != "daily_persisted":
            continue
        fixed = _quota_map(item.get("fixed_daily_quotas"), "fixed_daily_quotas")
        rotation = _quota_map(
            item.get("weekly_rotation_quotas"), "weekly_rotation_quotas"
        )
        publication_groups = _publication_group_map(item.get("publication_groups"))
        excluded_subniches = _string_tuple(
            item.get("excluded_subniches"),
            "excluded_subniches",
        )
        policy = DailyPlanningPolicy(
            profile=profile,
            marketplace=marketplace,
            items_per_window=int(item["total_items"]),
            schedule_hours=tuple(int(hour) for hour in item["schedule_hours"]),
            daily_total_items=int(item["daily_total_items"]),
            rotation_items_per_day=int(item["rotation_items_per_day"]),
            max_items_per_subniche_per_window=int(
                item["max_items_per_subniche_per_window"]
            ),
            fixed_daily_quotas=fixed,
            weekly_rotation_quotas=rotation,
            publication_groups=publication_groups,
            excluded_subniches=excluded_subniches,
        )
        validate_daily_planning_policy(policy)
        return policy
    raise DispatchPlanningError(f"daily persisted policy not found: {profile}")


def validate_daily_planning_policy(policy: DailyPlanningPolicy) -> None:
    if len(set(policy.schedule_hours)) != len(policy.schedule_hours):
        raise DispatchPlanningError("schedule_hours must be unique")
    if any(hour < 0 or hour > 23 for hour in policy.schedule_hours):
        raise DispatchPlanningError("schedule_hours must be between 0 and 23")
    if policy.items_per_window * len(policy.schedule_hours) != policy.daily_total_items:
        raise DispatchPlanningError("daily total must match windows times items per window")
    fixed_total = sum(policy.fixed_daily_quotas.values())
    if fixed_total + policy.rotation_items_per_day != policy.daily_total_items:
        raise DispatchPlanningError("fixed and rotation daily quotas must match daily total")
    if sum(policy.weekly_rotation_quotas.values()) != policy.rotation_items_per_day * 7:
        raise DispatchPlanningError("weekly rotation quota must fill seven daily rotations")
    if set(policy.fixed_daily_quotas) & set(policy.weekly_rotation_quotas):
        raise DispatchPlanningError("fixed and rotation subniches must be disjoint")
    if policy.max_items_per_subniche_per_window <= 0:
        raise DispatchPlanningError("window subniche cap must be positive")
    for key, subniches in policy.publication_groups.items():
        if not key or not subniches:
            raise DispatchPlanningError(f"invalid publication group: {key}")
        if set(subniches) & set(policy.excluded_subniches):
            raise DispatchPlanningError(f"publication group includes excluded subniche: {key}")


def weekly_rotation_daily_quotas(
    policy: DailyPlanningPolicy,
    *,
    planned_date: date,
) -> dict[str, int]:
    day_index = planned_date.weekday()
    weekly_matrix: dict[str, list[int]] = {}
    day_loads = [0] * 7
    for subniche, weekly_items in policy.weekly_rotation_quotas.items():
        base, remainder = divmod(weekly_items, 7)
        weekly_matrix[subniche] = [base] * 7
        day_loads = [load + base for load in day_loads]
        offset = _stable_offset(subniche) % 7
        used_days: set[int] = set()
        for _ in range(remainder):
            selected_day = min(
                (day for day in range(7) if day not in used_days),
                key=lambda day: (day_loads[day], (day - offset) % 7),
            )
            weekly_matrix[subniche][selected_day] += 1
            day_loads[selected_day] += 1
            used_days.add(selected_day)
    quotas = {subniche: days[day_index] for subniche, days in weekly_matrix.items()}
    if sum(quotas.values()) != policy.rotation_items_per_day:
        raise DispatchPlanningError("daily rotation allocation does not match reserved slots")
    return quotas


def plan_daily_dispatches(
    candidates: list[DispatchCandidate],
    *,
    policy: DailyPlanningPolicy,
    planned_date: date,
) -> list[PlannedDispatch]:
    validate_daily_planning_policy(policy)
    eligible = [
        item
        for item in candidates
        if item.profile == policy.profile and item.marketplace == policy.marketplace
        and item.primary_subniche not in policy.excluded_subniches
    ]
    by_subniche: dict[str, deque[DispatchCandidate]] = {}
    for subniche, items in _group_candidates(eligible).items():
        by_subniche[subniche] = deque(items)

    selected: list[tuple[DispatchCandidate, str, str]] = []
    used_keys: set[str] = set()
    unmet: Counter[str] = Counter()
    daily_rotation = weekly_rotation_daily_quotas(policy, planned_date=planned_date)

    for bucket, quotas in (
        ("fixed_daily", policy.fixed_daily_quotas),
        ("weekly_rotation", daily_rotation),
    ):
        for quota_key, quota in quotas.items():
            chosen = _take_quota_candidates(
                by_subniche,
                policy=policy,
                quota_key=quota_key,
                count=quota,
                used_keys=used_keys,
            )
            selected.extend(
                (candidate, bucket, f"{bucket}:{quota_key}") for candidate in chosen
            )
            unmet[bucket] += quota - len(chosen)

    for bucket in ("fixed_daily", "weekly_rotation"):
        if not unmet[bucket]:
            continue
        pool_subniches = _quota_subniches(
            policy,
            (
                policy.fixed_daily_quotas
                if bucket == "fixed_daily"
                else policy.weekly_rotation_quotas
            ),
        )
        fallback = _fallback_candidates(by_subniche, pool_subniches, used_keys)
        if len(fallback) < unmet[bucket]:
            general_fallback = _fallback_candidates(
                by_subniche,
                None,
                used_keys | {candidate.stable_key for candidate in fallback},
            )
            fallback.extend(general_fallback)
        if len(fallback) < unmet[bucket]:
            raise DispatchPlanningError(
                f"insufficient candidates for {bucket}: missing {unmet[bucket] - len(fallback)}"
            )
        selected_fallback = fallback[: unmet[bucket]]
        used_keys.update(candidate.stable_key for candidate in selected_fallback)
        selected.extend(
            (
                candidate,
                bucket,
                (
                    f"{bucket}:redistributed"
                    if candidate.primary_subniche in pool_subniches
                    else f"{bucket}:top_score_fallback"
                ),
            )
            for candidate in selected_fallback
        )

    if len(selected) != policy.daily_total_items:
        raise DispatchPlanningError(
            f"daily plan must contain {policy.daily_total_items} items, got {len(selected)}"
        )

    return _sequence_windows(selected, policy=policy, planned_date=planned_date)


def _sequence_windows(
    selected: list[tuple[DispatchCandidate, str, str]],
    *,
    policy: DailyPlanningPolicy,
    planned_date: date,
) -> list[PlannedDispatch]:
    queues: dict[str, deque[tuple[DispatchCandidate, str, str]]] = defaultdict(deque)
    for item in sorted(
        selected,
        key=lambda entry: (
            entry[0].primary_subniche,
            -entry[0].commercial_score,
            -entry[0].sales_count,
            entry[0].item_id,
        ),
    ):
        queues[item[0].primary_subniche].append(item)

    planned: list[PlannedDispatch] = []
    daily_sequence = 0
    extra_rotation_windows = _spread_indexes(
        len(policy.schedule_hours),
        policy.rotation_items_per_day - len(policy.schedule_hours),
    )
    for window_index, hour in enumerate(policy.schedule_hours):
        window_counts: Counter[str] = Counter()
        rotation_target = 1 + int(window_index in extra_rotation_windows)
        rotation_selected = 0
        for slot in range(1, policy.items_per_window + 1):
            remaining_windows = len(policy.schedule_hours) - window_index - 1
            available = _available_window_subniches(
                queues,
                window_counts=window_counts,
                remaining_windows=remaining_windows,
                policy=policy,
            )
            if not available:
                raise DispatchPlanningError(f"cannot fill hour {hour} under subniche cap")
            preferred_bucket = (
                "weekly_rotation"
                if rotation_selected < rotation_target
                else "fixed_daily"
            )
            preferred = [
                subniche
                for subniche in available
                if queues[subniche][0][1] == preferred_bucket
            ]
            preferred_set = set(preferred)
            subniche = min(
                available,
                key=lambda key: (
                    _remaining_window_capacity(
                        key,
                        window_counts=window_counts,
                        remaining_windows=remaining_windows,
                        policy=policy,
                    )
                    - len(queues[key]),
                    -len(queues[key]),
                    window_counts[key],
                    int(key not in preferred_set),
                    key,
                ),
            )
            candidate, bucket, reason = queues[subniche].popleft()
            if bucket == "weekly_rotation":
                rotation_selected += 1
            window_counts[subniche] += 1
            daily_sequence += 1
            planned.append(
                PlannedDispatch(
                    candidate=candidate,
                    selection_bucket=bucket,
                    selection_reason=reason,
                    planned_date=planned_date,
                    planned_hour=hour,
                    slot_sequence=slot,
                    daily_sequence=daily_sequence,
                )
            )
    return planned


def _available_window_subniches(
    queues: dict[str, deque[tuple[DispatchCandidate, str, str]]],
    *,
    window_counts: Counter[str],
    remaining_windows: int,
    policy: DailyPlanningPolicy,
) -> list[str]:
    available = [
        subniche
        for subniche, queue in queues.items()
        if queue and window_counts[subniche] < policy.max_items_per_subniche_per_window
    ]
    urgent = [
        subniche
        for subniche in available
        if len(queues[subniche])
        > _remaining_window_capacity(
            subniche,
            window_counts=window_counts,
            remaining_windows=remaining_windows,
            policy=policy,
        )
    ]
    return urgent or available


def _remaining_window_capacity(
    subniche: str,
    *,
    window_counts: Counter[str],
    remaining_windows: int,
    policy: DailyPlanningPolicy,
) -> int:
    current_window_capacity = (
        policy.max_items_per_subniche_per_window - window_counts[subniche]
    )
    return (
        current_window_capacity
        + remaining_windows * policy.max_items_per_subniche_per_window
    )


def _spread_indexes(window_count: int, extra_count: int) -> set[int]:
    if extra_count <= 0:
        return set()
    return {
        min(window_count - 1, ((index + 1) * window_count) // (extra_count + 1))
        for index in range(extra_count)
    }


def _group_candidates(
    candidates: list[DispatchCandidate],
) -> dict[str, list[DispatchCandidate]]:
    grouped: dict[str, list[DispatchCandidate]] = defaultdict(list)
    seen: set[str] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (
            item.primary_subniche,
            -item.commercial_score,
            -item.sales_count,
            -(item.rating or Decimal(0)),
            item.item_id,
        ),
    ):
        if candidate.stable_key in seen:
            continue
        seen.add(candidate.stable_key)
        grouped[candidate.primary_subniche].append(candidate)
    return grouped


def _take_candidates(
    queue: deque[DispatchCandidate] | None,
    count: int,
    used_keys: set[str],
) -> list[DispatchCandidate]:
    selected: list[DispatchCandidate] = []
    while queue and len(selected) < count:
        candidate = queue.popleft()
        if candidate.stable_key in used_keys:
            continue
        used_keys.add(candidate.stable_key)
        selected.append(candidate)
    return selected


def _take_quota_candidates(
    queues: dict[str, deque[DispatchCandidate]],
    *,
    policy: DailyPlanningPolicy,
    quota_key: str,
    count: int,
    used_keys: set[str],
) -> list[DispatchCandidate]:
    candidates = [
        item
        for subniche in _resolve_quota_subniches(policy, quota_key)
        for item in queues.get(subniche, ())
        if item.stable_key not in used_keys
    ]
    candidates.sort(
        key=lambda item: (
            -item.commercial_score,
            -item.sales_count,
            -(item.rating or Decimal(0)),
            item.item_id,
        )
    )
    selected = candidates[:count]
    used_keys.update(candidate.stable_key for candidate in selected)
    _remove_used_candidates(queues, used_keys)
    return selected


def _remove_used_candidates(
    queues: dict[str, deque[DispatchCandidate]],
    used_keys: set[str],
) -> None:
    for subniche, queue in list(queues.items()):
        queues[subniche] = deque(
            candidate for candidate in queue if candidate.stable_key not in used_keys
        )


def _fallback_candidates(
    queues: dict[str, deque[DispatchCandidate]],
    allowed_subniches: set[str] | None,
    used_keys: set[str],
) -> list[DispatchCandidate]:
    subniches = allowed_subniches if allowed_subniches is not None else queues
    candidates = [
        item
        for subniche in subniches
        for item in queues.get(subniche, ())
        if item.stable_key not in used_keys
    ]
    candidates.sort(
        key=lambda item: (-item.commercial_score, -item.sales_count, item.item_id)
    )
    return candidates


def _quota_subniches(
    policy: DailyPlanningPolicy,
    quotas: dict[str, int],
) -> set[str]:
    return {
        subniche
        for quota_key in quotas
        for subniche in _resolve_quota_subniches(policy, quota_key)
    }


def _resolve_quota_subniches(
    policy: DailyPlanningPolicy,
    quota_key: str,
) -> tuple[str, ...]:
    return policy.publication_groups.get(quota_key, (quota_key,))


def _quota_map(raw: object, field: str) -> dict[str, int]:
    if not isinstance(raw, list) or not raw:
        raise DispatchPlanningError(f"{field} must contain quotas")
    quotas: dict[str, int] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise DispatchPlanningError(f"invalid quota in {field}")
        subniche = str(item.get("subniche", "")).strip()
        count = int(item.get("items", 0))
        if not subniche or count <= 0 or subniche in quotas:
            raise DispatchPlanningError(f"invalid quota in {field}: {subniche}")
        quotas[subniche] = count
    return quotas


def _publication_group_map(raw: object) -> dict[str, tuple[str, ...]]:
    if raw is None:
        return {}
    if not isinstance(raw, list):
        raise DispatchPlanningError("publication_groups must contain groups")
    groups: dict[str, tuple[str, ...]] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise DispatchPlanningError("invalid publication group")
        group = str(item.get("group", "")).strip()
        subniches = _string_tuple(item.get("subniches"), f"publication_groups.{group}")
        if not group or not subniches or group in groups:
            raise DispatchPlanningError(f"invalid publication group: {group}")
        groups[group] = subniches
    return groups


def _string_tuple(raw: object, field: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise DispatchPlanningError(f"{field} must be a list")
    values = tuple(str(item).strip() for item in raw)
    if any(not item for item in values) or len(set(values)) != len(values):
        raise DispatchPlanningError(f"invalid values in {field}")
    return values


def _stable_offset(value: str) -> int:
    return sum((index + 1) * ord(character) for index, character in enumerate(value))
