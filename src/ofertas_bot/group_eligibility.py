from __future__ import annotations

from dataclasses import dataclass

from ofertas_bot.group_profiles import GroupProfile
from ofertas_bot.models import Offer


@dataclass(frozen=True)
class GroupEligibilityResult:
    approved: bool
    reasons: tuple[str, ...]


class GroupEligibilityPolicy:
    def validate_offer(self, offer: Offer, group_profile: GroupProfile) -> GroupEligibilityResult:
        reasons: list[str] = []

        if not group_profile.active:
            reasons.append("grupo inativo")

        if not group_profile.allows_niche(offer.niche):
            reasons.append("nicho não permitido para o grupo")

        if offer.price <= 0:
            reasons.append("preço inválido")

        if not offer.url:
            reasons.append("oferta sem link")

        return GroupEligibilityResult(approved=not reasons, reasons=tuple(reasons))

    def select_eligible_offers(
        self,
        offers: list[Offer],
        group_profile: GroupProfile,
    ) -> list[Offer]:
        eligible = [
            offer
            for offer in offers
            if self.validate_offer(offer=offer, group_profile=group_profile).approved
        ]
        return eligible[: group_profile.max_offers_per_run]
