from __future__ import annotations

import tomllib
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ofertas_bot.daily_dispatch_planner import (
    DailyPlanningPolicy,
    WindowFamilyQuota,
    load_daily_planning_policy,
    weekly_rotation_daily_quotas,
)
from ofertas_bot.selection import load_selection_policies

DEFAULT_DISTRIBUTION_PROFILES_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "selection_profiles.toml"
)


@dataclass(frozen=True)
class ProfileDistributionStrategy:
    profile: str
    marketplace: str
    planning_mode: str
    required_daily_quotas: dict[str, int]
    refresh_weights: dict[str, int]
    discovery_weights: dict[str, int]
    publication_groups: dict[str, tuple[str, ...]]
    excluded_subniches: tuple[str, ...]
    window_family_quotas: tuple[WindowFamilyQuota, ...]


def resolve_profile_distribution_strategy(
    profile: str,
    *,
    operational_date: date,
    marketplace: str = "shopee",
    path: Path = DEFAULT_DISTRIBUTION_PROFILES_PATH,
) -> ProfileDistributionStrategy:
    normalized_profile = profile.strip().lower()
    normalized_marketplace = marketplace.strip().lower()

    if _declares_daily_persisted_policy(path, profile=normalized_profile):
        policy = load_daily_planning_policy(
            path,
            profile=normalized_profile,
            marketplace=normalized_marketplace,
        )
        required_daily_quotas = _daily_required_subniche_quotas(
            policy,
            operational_date=operational_date,
        )
        return ProfileDistributionStrategy(
            profile=normalized_profile,
            marketplace=normalized_marketplace,
            planning_mode="daily_persisted",
            required_daily_quotas=required_daily_quotas,
            refresh_weights=dict(required_daily_quotas),
            discovery_weights=dict(required_daily_quotas),
            publication_groups=dict(policy.publication_groups),
            excluded_subniches=policy.excluded_subniches,
            window_family_quotas=policy.window_family_quotas,
        )

    selection_policies = load_selection_policies(path)
    selection_policy = selection_policies.get(normalized_profile)
    if selection_policy is None:
        selection_policy = next(
            (
                policy
                for policy in selection_policies.values()
                if policy.slug == normalized_profile
            ),
            None,
        )
    if selection_policy is None:
        raise ValueError(f"distribution strategy not found: {normalized_profile}")
    return ProfileDistributionStrategy(
        profile=normalized_profile,
        marketplace=normalized_marketplace,
        planning_mode="bands",
        required_daily_quotas=dict(selection_policy.subniche_quotas),
        refresh_weights=dict(selection_policy.subniche_quotas),
        discovery_weights=dict(selection_policy.subniche_quotas),
        publication_groups={},
        excluded_subniches=(),
        window_family_quotas=(),
    )


def _declares_daily_persisted_policy(path: Path, *, profile: str) -> bool:
    if path.suffix.lower() == ".csv":
        return False
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    for item in raw.get("policies", []):
        if item.get("slug") == profile:
            return item.get("planning_mode") == "daily_persisted"
    return False


def _daily_required_subniche_quotas(
    policy: DailyPlanningPolicy,
    *,
    operational_date: date,
) -> dict[str, int]:
    required: Counter[str] = Counter()
    excluded = set(policy.excluded_subniches)
    for quotas in (
        policy.fixed_daily_quotas,
        weekly_rotation_daily_quotas(policy, planned_date=operational_date),
    ):
        required.update(
            _expand_quota_keys(
                quotas,
                publication_groups=policy.publication_groups,
                excluded_subniches=excluded,
            )
        )
    return {subniche: count for subniche, count in required.items() if count > 0}


def _expand_quota_keys(
    quotas: Mapping[str, int],
    *,
    publication_groups: Mapping[str, tuple[str, ...]],
    excluded_subniches: set[str],
) -> dict[str, int]:
    expanded: Counter[str] = Counter()
    for quota_key, count in quotas.items():
        members = tuple(
            subniche
            for subniche in publication_groups.get(quota_key, (quota_key,))
            if subniche not in excluded_subniches
        )
        if not members or count <= 0:
            continue
        base, remainder = divmod(count, len(members))
        for index, subniche in enumerate(members):
            expanded[subniche] += base + int(index < remainder)
    return dict(expanded)
