from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ofertas_bot.group_cadence import GroupCadencePolicy
from ofertas_bot.group_eligibility import GroupEligibilityPolicy
from ofertas_bot.group_profiles import GroupProfile
from ofertas_bot.models import Offer


@dataclass(frozen=True)
class GroupPlan:
    group_slug: str
    allowed: bool
    selected_offers: tuple[Offer, ...]
    reasons: tuple[str, ...]
    next_available_at: datetime | None = None


class GroupPlanBuilder:
    def __init__(
        self,
        *,
        cadence_policy: GroupCadencePolicy | None = None,
        eligibility_policy: GroupEligibilityPolicy | None = None,
    ) -> None:
        self.cadence_policy = cadence_policy or GroupCadencePolicy()
        self.eligibility_policy = eligibility_policy or GroupEligibilityPolicy()

    def build_plan(
        self,
        *,
        group_profile: GroupProfile,
        offers: list[Offer],
        now: datetime,
        last_run_at: datetime | None,
    ) -> GroupPlan:
        cadence = self.cadence_policy.can_run_now(
            group_profile,
            now=now,
            last_run_at=last_run_at,
        )
        if not cadence.allowed:
            return GroupPlan(
                group_slug=group_profile.slug,
                allowed=False,
                selected_offers=(),
                reasons=cadence.reasons,
                next_available_at=cadence.next_available_at,
            )

        selected_offers = self.eligibility_policy.select_eligible_offers(
            offers=offers,
            group_profile=group_profile,
        )
        if not selected_offers:
            return GroupPlan(
                group_slug=group_profile.slug,
                allowed=False,
                selected_offers=(),
                reasons=("nenhuma oferta elegível para o grupo",),
            )

        return GroupPlan(
            group_slug=group_profile.slug,
            allowed=True,
            selected_offers=tuple(selected_offers),
            reasons=(),
        )

    def build_plans(
        self,
        *,
        group_profiles: tuple[GroupProfile, ...],
        offers: list[Offer],
        now: datetime,
        last_runs_by_group: dict[str, datetime | None] | None = None,
    ) -> tuple[GroupPlan, ...]:
        last_runs = last_runs_by_group or {}
        return tuple(
            self.build_plan(
                group_profile=group_profile,
                offers=offers,
                now=now,
                last_run_at=last_runs.get(group_profile.slug),
            )
            for group_profile in group_profiles
        )


def summarize_group_plans(plans: tuple[GroupPlan, ...]) -> dict[str, Any]:
    allowed_count = sum(1 for plan in plans if plan.allowed)
    selected_count = sum(len(plan.selected_offers) for plan in plans)
    return {
        "total_groups": len(plans),
        "allowed_groups": allowed_count,
        "blocked_groups": len(plans) - allowed_count,
        "total_selected_offers": selected_count,
        "groups": [_summarize_group_plan(plan) for plan in plans],
    }


def format_group_plan_summary(summary: dict[str, Any]) -> str:
    lines = [
        "Resumo do plano por grupo",
        f"total_groups={summary.get('total_groups', 0)}",
        f"allowed_groups={summary.get('allowed_groups', 0)}",
        f"blocked_groups={summary.get('blocked_groups', 0)}",
        f"total_selected_offers={summary.get('total_selected_offers', 0)}",
    ]

    metadata = summary.get("metadata")
    if isinstance(metadata, dict):
        lines.extend(
            [
                f"metadata.niche={metadata.get('niche')}",
                f"metadata.generated_at={metadata.get('generated_at')}",
                f"metadata.offer_limit={metadata.get('offer_limit')}",
                f"metadata.collected_offer_count={metadata.get('collected_offer_count')}",
                f"metadata.source_marketplace={metadata.get('source_marketplace')}",
            ]
        )

    groups = summary.get("groups")
    if isinstance(groups, list):
        for group in groups:
            if isinstance(group, dict):
                lines.extend(_format_group_summary(group))

    return "\n".join(lines)


def _summarize_group_plan(plan: GroupPlan) -> dict[str, Any]:
    return {
        "group_slug": plan.group_slug,
        "allowed": plan.allowed,
        "selected_offer_count": len(plan.selected_offers),
        "reasons": list(plan.reasons),
        "next_available_at": plan.next_available_at.isoformat()
        if plan.next_available_at
        else None,
    }


def _format_group_summary(group: dict[str, Any]) -> list[str]:
    lines = [
        "-" * 80,
        f"group={group.get('group_slug')}",
        f"allowed={group.get('allowed')}",
        f"selected_offer_count={group.get('selected_offer_count', 0)}",
    ]
    reasons = group.get("reasons")
    if isinstance(reasons, list) and reasons:
        lines.append(f"reasons={'; '.join(str(reason) for reason in reasons)}")
    next_available_at = group.get("next_available_at")
    if next_available_at:
        lines.append(f"next_available_at={next_available_at}")
    return lines
