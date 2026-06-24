from __future__ import annotations

from dataclasses import dataclass

from ofertas_bot.discovery_profiles import DiscoveryProfile
from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.amazon import AmazonProvider
from ofertas_bot.providers.mock import MockOfferProvider
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.settings import Settings, get_settings


@dataclass(frozen=True)
class CollectedOfferBatch:
    offers: list[Offer]
    raw_response: dict[str, object] | None = None


class CollectorAgent:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._mock_provider = MockOfferProvider()
        self._amazon_provider = AmazonProvider(settings=self.settings)
        self._shopee_provider = ShopeeProvider(settings=self.settings)

    def collect(self, marketplace: Marketplace, niche: str, limit: int) -> list[Offer]:
        return self.collect_with_inspection(
            marketplace=marketplace,
            niche=niche,
            limit=limit,
        ).offers

    def collect_with_inspection(
        self,
        *,
        marketplace: Marketplace,
        niche: str,
        limit: int,
        query: str | None = None,
    ) -> CollectedOfferBatch:
        search_term = query or niche

        if marketplace is Marketplace.MOCK:
            raw_response = self._mock_provider.fetch_raw_response(search_term, limit)
            offers = self._mock_provider.fetch(
                marketplace=marketplace,
                niche=search_term,
                limit=limit,
            )
            return CollectedOfferBatch(offers=offers, raw_response=raw_response)

        if marketplace is Marketplace.AMAZON:
            offers = self._amazon_provider.fetch(niche=search_term, limit=limit)
            return CollectedOfferBatch(offers=offers, raw_response=None)

        if marketplace is Marketplace.SHOPEE:
            raw_response = self._shopee_provider.fetch_raw_response(search_term, limit)
            offers = self._shopee_provider.normalize_response(
                response_data=raw_response,
                niche=niche,
                limit=limit,
            )
            return CollectedOfferBatch(offers=offers, raw_response=raw_response)

        msg = f"Unsupported marketplace: {marketplace}"
        raise ValueError(msg)

    def collect_from_profile(self, profile: DiscoveryProfile, limit: int) -> list[Offer]:
        return self.collect_from_profile_with_inspection(profile=profile, limit=limit).offers

    def collect_from_profile_with_inspection(
        self,
        profile: DiscoveryProfile,
        limit: int,
    ) -> CollectedOfferBatch:
        batch = self.collect_with_inspection(
            marketplace=profile.marketplace,
            niche=profile.niche,
            limit=limit,
            query=profile.search_term(),
        )
        filtered = profile.apply_offer_filters(batch.offers)
        return CollectedOfferBatch(offers=filtered, raw_response=batch.raw_response)
