from __future__ import annotations

from ofertas_bot.models import Offer, ScoredOffer


class ScorerAgent:
    def score(self, offers: list[Offer]) -> list[ScoredOffer]:
        scored = [self._score_one(offer) for offer in offers]
        return sorted(scored, key=lambda item: item.score, reverse=True)

    def _score_one(self, offer: Offer) -> ScoredOffer:
        score = 0.0
        reasons: list[str] = []

        if offer.discount_percent >= 20:
            score += min(offer.discount_percent, 60) * 1.2
            reasons.append(f"desconto de {offer.discount_percent:.0f}%")

        if offer.commission_rate > 0:
            score += offer.commission_rate * 100
            reasons.append(f"comissão de {offer.commission_rate:.0%}")

        if offer.sales_count >= 100:
            score += min(offer.sales_count / 100, 20)
            reasons.append(f"{offer.sales_count} vendas")

        if offer.rating and offer.rating >= 4.5:
            score += 10
            reasons.append(f"avaliação {offer.rating:.1f}")

        if offer.is_prime_or_free_shipping:
            score += 8
            reasons.append("frete rápido/grátis")

        return ScoredOffer(offer=offer, score=round(score, 2), reasons=reasons)
