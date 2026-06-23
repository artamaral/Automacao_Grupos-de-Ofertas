from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

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
