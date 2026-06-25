from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
        if (
            profile.marketplace is Marketplace.SHOPEE
            and profile.uses_discovery_method("descobridor-geral")
        ):
            return self._collect_from_shopee_general_discoverer(profile=profile, limit=limit)

        batch = self.collect_with_inspection(
            marketplace=profile.marketplace,
            niche=profile.niche,
            limit=limit,
            query=profile.search_term(),
        )
        filtered = profile.apply_offer_filters(batch.offers)
        return CollectedOfferBatch(offers=filtered, raw_response=batch.raw_response)

    def _collect_from_shopee_general_discoverer(
        self,
        *,
        profile: DiscoveryProfile,
        limit: int,
    ) -> CollectedOfferBatch:
        offer_names = profile.shopee_offer_search_terms() or (profile.search_term(),)
        offer_searches: list[dict[str, Any]] = []
        discovered_match_ids: list[int] = []

        for offer_name in offer_names:
            response_data = self._shopee_provider.fetch_offer_search_raw_response(offer_name, limit)
            offer_searches.append(
                {
                    "offer_name": offer_name,
                    "response": response_data,
                }
            )
            discovered_match_ids.extend(_extract_category_match_ids(response_data))

        candidate_match_ids = tuple(
            dict.fromkeys(discovered_match_ids + list(profile.shopee_product_match_ids))
        )

        collected_offers: list[Offer] = []
        product_searches: list[dict[str, Any]] = []
        for match_id in candidate_match_ids:
            response_data = self._shopee_provider.fetch_product_match_raw_response(
                match_id=match_id,
                limit=limit,
            )
            product_searches.append(
                {
                    "match_id": match_id,
                    "response": response_data,
                }
            )
            offers = self._shopee_provider.normalize_custom_response(
                response_data=response_data,
                niche=profile.niche,
                limit=limit,
                root_field="productOfferV2",
            )
            collected_offers.extend(offers)
            collected_offers = _deduplicate_offers(collected_offers)[:limit]
            if len(collected_offers) >= limit:
                break

        filtered = profile.apply_offer_filters(collected_offers[:limit])
        return CollectedOfferBatch(
            offers=filtered,
            raw_response={
                "discovery_method": "descobridor-geral",
                "marketplace": Marketplace.SHOPEE.value,
                "niche": profile.niche,
                "offer_searches": offer_searches,
                "selected_match_ids": list(candidate_match_ids),
                "product_searches": product_searches,
            },
        )


def _extract_category_match_ids(response_data: dict[str, Any]) -> list[int]:
    data = response_data.get("data")
    if not isinstance(data, dict):
        return []
    connection = data.get("shopeeOfferV2")
    if not isinstance(connection, dict):
        return []
    nodes = connection.get("nodes")
    if not isinstance(nodes, list):
        return []

    match_ids: list[int] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        category_id = node.get("categoryId")
        if isinstance(category_id, int):
            match_ids.append(category_id)
    return match_ids


def _deduplicate_offers(offers: list[Offer]) -> list[Offer]:
    deduplicated: list[Offer] = []
    seen_urls: set[str] = set()
    for offer in offers:
        if offer.url in seen_urls:
            continue
        seen_urls.add(offer.url)
        deduplicated.append(offer)
    return deduplicated
