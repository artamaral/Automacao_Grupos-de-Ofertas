from __future__ import annotations

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.mock import MockOfferProvider


class CollectorAgent:
    def __init__(self) -> None:
        self._mock_provider = MockOfferProvider()

    def collect(self, marketplace: Marketplace, niche: str, limit: int) -> list[Offer]:
        # MVP: sempre usa provider mockado para permitir desenvolvimento sem segredos.
        return self._mock_provider.fetch(marketplace=marketplace, niche=niche, limit=limit)
