from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ofertas_bot.discovery_profiles import DiscoveryProfile
from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.amazon import AmazonProvider
from ofertas_bot.providers.mock import MockOfferProvider
from ofertas_bot.providers.shopee_graphql import ShopeeGraphqlPayloadError
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.settings import Settings, get_settings

SHOPEE_GENERAL_DISCOVERER_PAGE_SIZE = 50
SHOPEE_GENERAL_DISCOVERER_MAX_PAGES = 50
SHOPEE_GENERAL_DISCOVERER_OFFER_SEARCH_LIMIT = 50


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
            response_data = self._shopee_provider.fetch_offer_search_raw_response(
                offer_name,
                min(limit, SHOPEE_GENERAL_DISCOVERER_OFFER_SEARCH_LIMIT),
            )
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
            match_search = self._collect_all_product_pages_for_match_id(
                profile=profile,
                match_id=match_id,
            )
            product_searches.append(match_search["raw"])
            collected_offers.extend(match_search["offers"])
            collected_offers = _deduplicate_offers(collected_offers)

        filtered = profile.apply_offer_filters(collected_offers)
        return CollectedOfferBatch(
            offers=filtered[:limit],
            raw_response={
                "discovery_method": "descobridor-geral",
                "marketplace": Marketplace.SHOPEE.value,
                "niche": profile.niche,
                "offer_searches": offer_searches,
                "selected_match_ids": list(candidate_match_ids),
                "offer_search_limit": SHOPEE_GENERAL_DISCOVERER_OFFER_SEARCH_LIMIT,
                "page_size": SHOPEE_GENERAL_DISCOVERER_PAGE_SIZE,
                "max_pages": SHOPEE_GENERAL_DISCOVERER_MAX_PAGES,
                "product_searches": product_searches,
            },
        )

    def _collect_all_product_pages_for_match_id(
        self,
        *,
        profile: DiscoveryProfile,
        match_id: int,
    ) -> dict[str, Any]:
        offers: list[Offer] = []
        pages: list[dict[str, Any]] = []

        for page in range(1, SHOPEE_GENERAL_DISCOVERER_MAX_PAGES + 1):
            try:
                response_data = self._shopee_provider.fetch_product_match_raw_response(
                    match_id=match_id,
                    limit=SHOPEE_GENERAL_DISCOVERER_PAGE_SIZE,
                    page=page,
                )
            except ShopeeGraphqlPayloadError as error:
                if _is_page_not_found_error(error):
                    pages.append(
                        {
                            "page": page,
                            "stopped_by": "page_not_found",
                        }
                    )
                    break
                raise

            page_offers = self._shopee_provider.normalize_custom_response(
                response_data=response_data,
                niche=profile.niche,
                limit=SHOPEE_GENERAL_DISCOVERER_PAGE_SIZE,
                root_field="productOfferV2",
            )
            offers.extend(page_offers)

            page_info = _extract_page_info(response_data, root_field="productOfferV2")
            pages.append(
                {
                    "page": page,
                    "node_count": len(page_offers),
                    "hasNextPage": page_info.get("hasNextPage"),
                }
            )
            if page_info.get("hasNextPage") is not True:
                break

        return {
            "offers": offers,
            "raw": {
                "match_id": match_id,
                "pages": pages,
            },
        }


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


def _extract_page_info(response_data: dict[str, Any], *, root_field: str) -> dict[str, Any]:
    data = response_data.get("data")
    if not isinstance(data, dict):
        return {}
    connection = data.get(root_field)
    if not isinstance(connection, dict):
        return {}
    page_info = connection.get("pageInfo")
    return page_info if isinstance(page_info, dict) else {}


def _is_page_not_found_error(error: Exception) -> bool:
    message = str(error).strip().lower()
    return "page not found" in message
