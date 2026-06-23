from __future__ import annotations

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.mock import MockOfferProvider
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.settings import Settings, get_settings


class CollectorAgent:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._mock_provider = MockOfferProvider()
        self._shopee_provider = ShopeeProvider(settings=self.settings)

    def collect(self, marketplace: Marketplace, niche: str, limit: int) -> list[Offer]:
        if marketplace in {Marketplace.MOCK, Marketplace.AMAZON}:
            return self._mock_provider.fetch(
                marketplace=marketplace,
                niche=niche,
                limit=limit,
            )

        if marketplace is Marketplace.SHOPEE:
            return self._shopee_provider.fetch(niche=niche, limit=limit)

        msg = f"Unsupported marketplace: {marketplace}"
        raise ValueError(msg)
