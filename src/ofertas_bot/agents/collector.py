from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ofertas_bot.discovery_profiles import DiscoveryProfile
from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.amazon import AmazonProvider
from ofertas_bot.providers.mock import MockOfferProvider
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.providers.shopee_graphql import ShopeeGraphqlPayloadError
from ofertas_bot.settings import Settings, get_settings
from ofertas_bot.storage.json_offer_store import OfferStoreError, offer_from_json

SHOPEE_GENERAL_DISCOVERER_PAGE_SIZE = 50
SHOPEE_GENERAL_DISCOVERER_MAX_PAGES = 50
SHOPEE_GENERAL_DISCOVERER_OFFER_SEARCH_LIMIT = 50


class CatalogSourceError(ValueError):
    """Raised when a local catalog source cannot be parsed."""


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
        catalog_source_path: Path | None = None,
    ) -> CollectedOfferBatch:
        if catalog_source_path is not None:
            offers = self.collect_from_catalog_file(
                path=catalog_source_path,
                niche=niche,
                marketplace=marketplace,
                limit=limit,
            )
            return CollectedOfferBatch(
                offers=offers,
                raw_response={
                    "catalog_source_path": str(catalog_source_path),
                    "catalog_source_kind": catalog_source_path.suffix.lower(),
                    "catalog_offer_count": len(offers),
                },
            )

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
        catalog_source_path: Path | None = None,
    ) -> CollectedOfferBatch:
        if catalog_source_path is not None:
            return self.collect_with_inspection(
                marketplace=profile.marketplace,
                niche=profile.niche,
                limit=limit,
                query=profile.search_term(),
                catalog_source_path=catalog_source_path,
            )

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

    def collect_from_catalog_file(
        self,
        *,
        path: Path,
        niche: str,
        marketplace: Marketplace,
        limit: int,
    ) -> list[Offer]:
        suffix = path.suffix.lower()
        if suffix == ".json":
            offers = self._load_offers_from_json_catalog(
                path=path,
                niche=niche,
                marketplace=marketplace,
            )
        elif suffix == ".csv":
            offers = self._load_offers_from_csv_catalog(
                path=path,
                niche=niche,
                marketplace=marketplace,
            )
        else:
            raise CatalogSourceError(f"unsupported catalog source format: {path.suffix}")
        return _deduplicate_offers(offers)[:limit]

    def _load_offers_from_json_catalog(
        self,
        *,
        path: Path,
        niche: str,
        marketplace: Marketplace,
    ) -> list[Offer]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise CatalogSourceError(f"catalog source file not found: {path}") from error
        except json.JSONDecodeError as error:
            raise CatalogSourceError(f"catalog source JSON is invalid: {path}") from error

        if not isinstance(payload, list):
            raise CatalogSourceError("catalog source JSON must contain a list")

        offers: list[Offer] = []
        for item in payload:
            offers.append(
                _offer_from_catalog_item(
                    item=item,
                    niche=niche,
                    marketplace=marketplace,
                )
            )
        return offers

    def _load_offers_from_csv_catalog(
        self,
        *,
        path: Path,
        niche: str,
        marketplace: Marketplace,
    ) -> list[Offer]:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
        except FileNotFoundError as error:
            raise CatalogSourceError(f"catalog source file not found: {path}") from error
        except OSError as error:
            raise CatalogSourceError(f"could not read catalog source file: {path}") from error

        offers: list[Offer] = []
        for row in rows:
            offers.append(
                _offer_from_catalog_item(
                    item=row,
                    niche=niche,
                    marketplace=marketplace,
                )
            )
        return offers

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


def _offer_from_catalog_item(
    *,
    item: object,
    niche: str,
    marketplace: Marketplace,
) -> Offer:
    if not isinstance(item, dict):
        raise CatalogSourceError("catalog item must be an object")

    if _looks_like_normalized_offer(item):
        try:
            offer = offer_from_json(item)
        except OfferStoreError as error:
            raise CatalogSourceError("catalog normalized offer item is invalid") from error
        return Offer(
            marketplace=marketplace,
            title=offer.title,
            url=offer.url,
            image_url=offer.image_url,
            price=offer.price,
            old_price=offer.old_price,
            commission_rate=offer.commission_rate,
            sales_count=offer.sales_count,
            rating=offer.rating,
            niche=niche,
            is_prime_or_free_shipping=offer.is_prime_or_free_shipping,
            shop_type_code=offer.shop_type_code,
        )

    title = _required_catalog_str(item, "productName")
    url = _catalog_str(item, "offerLink") or _catalog_str(item, "productLink")
    if not url:
        raise CatalogSourceError("catalog item is missing offerLink/productLink")

    price = _catalog_float(item.get("price"), default=0.0)
    old_price = _catalog_optional_float(item.get("priceMax"))
    if old_price is not None and old_price <= price:
        old_price = None

    return Offer(
        marketplace=marketplace,
        title=title,
        url=url,
        image_url=_catalog_optional_str(item.get("imageUrl")),
        price=price,
        old_price=old_price,
        commission_rate=_catalog_commission_rate(item),
        sales_count=_catalog_int(item.get("sales"), default=0),
        rating=_catalog_optional_float(item.get("ratingStar")),
        niche=niche,
        is_prime_or_free_shipping=False,
        shop_type_code=_catalog_shop_type(item.get("shopType")),
    )


def _looks_like_normalized_offer(item: dict[str, object]) -> bool:
    required_keys = {
        "marketplace",
        "title",
        "url",
        "price",
        "commission_rate",
        "sales_count",
        "niche",
    }
    return required_keys.issubset(item.keys())


def _required_catalog_str(item: dict[str, object], key: str) -> str:
    value = _catalog_str(item, key)
    if not value:
        raise CatalogSourceError(f"catalog item is missing {key}")
    return value


def _catalog_str(item: dict[str, object], key: str) -> str:
    value = item.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _catalog_optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _catalog_optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _catalog_float(value: object, *, default: float) -> float:
    if value in (None, ""):
        return default
    return float(value)


def _catalog_int(value: object, *, default: int) -> int:
    if value in (None, ""):
        return default
    return int(float(value))


def _catalog_shop_type(value: object) -> int | None:
    if value in (None, "", "[]"):
        return None
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return None
        first_value = inner.split(",", maxsplit=1)[0].strip()
        return int(first_value)
    return int(float(text))


def _catalog_commission_rate(item: dict[str, object]) -> float:
    seller_rate = _catalog_optional_float(item.get("sellerCommissionRate"))
    shopee_rate = _catalog_optional_float(item.get("shopeeCommissionRate"))
    if seller_rate is not None or shopee_rate is not None:
        return (seller_rate or 0.0) + (shopee_rate or 0.0)
    return _catalog_float(item.get("commissionRate"), default=0.0)
