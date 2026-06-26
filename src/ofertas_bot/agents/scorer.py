from __future__ import annotations

from dataclasses import dataclass

from ofertas_bot.models import Offer, ScoredOffer

MIN_DISCOUNT_PERCENT = 20
DISCOUNT_SCORE_CAP_PERCENT = 40
DISCOUNT_SCORE_WEIGHT = 0.5

MIN_SALES_COUNT = 100
SALES_SCORE_BUCKET_SIZE = 100
SALES_SCORE_CAP = 20

MIN_RATING = 4.5
RATING_SCORE_POINTS = 10

FREE_SHIPPING_SCORE_POINTS = 8

SHOP_TYPE_SCORE_POINTS = {
    1: 10,  # Shopee Mall / loja oficial
    4: 7,   # Star+ Shop
    2: 5,   # Star Shop
}

SHOP_TYPE_REASONS = {
    1: "loja oficial",
    4: "loja star+",
    2: "loja star",
}


@dataclass(frozen=True)
class ScoreComponent:
    points: float
    reason: str


class ScorerAgent:
    def score(self, offers: list[Offer]) -> list[ScoredOffer]:
        scored = [self._score_one(offer) for offer in offers]
        return sorted(scored, key=lambda item: item.score, reverse=True)

    def _score_one(self, offer: Offer) -> ScoredOffer:
        components = self._score_components(offer)
        score = sum(component.points for component in components)
        reasons = [component.reason for component in components]
        return ScoredOffer(offer=offer, score=round(score, 2), reasons=reasons)

    def _score_components(self, offer: Offer) -> list[ScoreComponent]:
        components: list[ScoreComponent] = []
        components.extend(self._discount_component(offer))
        components.extend(self._commission_component(offer))
        components.extend(self._sales_component(offer))
        components.extend(self._rating_component(offer))
        components.extend(self._shipping_component(offer))
        components.extend(self._shop_type_component(offer))
        return components

    def _discount_component(self, offer: Offer) -> list[ScoreComponent]:
        if offer.discount_percent < MIN_DISCOUNT_PERCENT:
            return []
        points = min(offer.discount_percent, DISCOUNT_SCORE_CAP_PERCENT) * DISCOUNT_SCORE_WEIGHT
        return [ScoreComponent(points=points, reason=f"desconto de {offer.discount_percent:.0f}%")]

    def _commission_component(self, offer: Offer) -> list[ScoreComponent]:
        if offer.commission_rate <= 0:
            return []
        return [
            ScoreComponent(
                points=offer.commission_rate * 100,
                reason=f"comissao de {offer.commission_rate:.0%}",
            )
        ]

    def _sales_component(self, offer: Offer) -> list[ScoreComponent]:
        if offer.sales_count < MIN_SALES_COUNT:
            return []
        points = min(offer.sales_count / SALES_SCORE_BUCKET_SIZE, SALES_SCORE_CAP)
        return [ScoreComponent(points=points, reason=f"{offer.sales_count} vendas")]

    def _rating_component(self, offer: Offer) -> list[ScoreComponent]:
        if offer.rating is None or offer.rating < MIN_RATING:
            return []
        return [
            ScoreComponent(
                points=RATING_SCORE_POINTS,
                reason=f"avaliacao {offer.rating:.1f}",
            )
        ]

    def _shipping_component(self, offer: Offer) -> list[ScoreComponent]:
        if not offer.is_prime_or_free_shipping:
            return []
        return [
            ScoreComponent(
                points=FREE_SHIPPING_SCORE_POINTS,
                reason="frete rapido/gratis",
            )
        ]

    def _shop_type_component(self, offer: Offer) -> list[ScoreComponent]:
        if offer.shop_type_code is None:
            return []
        points = SHOP_TYPE_SCORE_POINTS.get(offer.shop_type_code)
        reason = SHOP_TYPE_REASONS.get(offer.shop_type_code)
        if points is None or reason is None:
            return []
        return [ScoreComponent(points=points, reason=reason)]
