from __future__ import annotations

import tomllib
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ofertas_bot.models import Marketplace, Offer


class DiscoveryProfileError(ValueError):
    """Raised when a discovery profile is invalid."""


@dataclass(frozen=True)
class DiscoverySubgroup:
    slug: str
    label: str
    query: str
    categories: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        normalized_slug = self.slug.strip().lower()
        normalized_label = self.label.strip()
        normalized_query = self.query.strip().lower()

        if not normalized_slug:
            raise DiscoveryProfileError("discovery subgroup slug is required")
        if not normalized_label:
            raise DiscoveryProfileError("discovery subgroup label is required")
        if not normalized_query:
            raise DiscoveryProfileError("discovery subgroup query is required")

        object.__setattr__(self, "slug", normalized_slug)
        object.__setattr__(self, "label", normalized_label)
        object.__setattr__(self, "query", normalized_query)
        object.__setattr__(self, "categories", _normalize_string_list(self.categories))


@dataclass(frozen=True)
class DiscoveryProfile:
    slug: str
    name: str
    niche: str
    marketplace: Marketplace
    discovery_method: str | None = None
    query: str | None = None
    target: str | None = None
    limit: int | None = None
    catalog_file: str | None = None
    keywords: tuple[str, ...] = ()
    brands: tuple[str, ...] = ()
    creators: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    include_terms: tuple[str, ...] = ()
    exclude_terms: tuple[str, ...] = ()
    shopee_offer_keyword: str | None = None
    shopee_offer_names: tuple[str, ...] = ()
    shopee_category_urls: tuple[str, ...] = ()
    shopee_product_match_ids: tuple[int, ...] = ()
    shopee_product_category_ids: tuple[int, ...] = ()
    subgroups: tuple[DiscoverySubgroup, ...] = ()

    def __post_init__(self) -> None:
        normalized_slug = self.slug.strip().lower()
        normalized_name = self.name.strip()
        normalized_niche = self.niche.strip().lower()
        normalized_target = self.target.strip() if self.target else None

        if not normalized_slug:
            raise DiscoveryProfileError("discovery profile slug is required")
        if not normalized_name:
            raise DiscoveryProfileError("discovery profile name is required")
        if not normalized_niche:
            raise DiscoveryProfileError("discovery profile niche is required")
        if self.limit is not None and self.limit <= 0:
            raise DiscoveryProfileError("discovery profile limit must be positive")

        object.__setattr__(self, "slug", normalized_slug)
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "niche", normalized_niche)
        object.__setattr__(
            self,
            "discovery_method",
            _normalize_optional_identifier(self.discovery_method),
        )
        object.__setattr__(self, "query", _normalize_optional_text(self.query))
        object.__setattr__(self, "target", normalized_target)
        object.__setattr__(self, "catalog_file", _normalize_optional_text(self.catalog_file))
        object.__setattr__(self, "keywords", _normalize_string_list(self.keywords))
        object.__setattr__(self, "brands", _normalize_string_list(self.brands))
        object.__setattr__(self, "creators", _normalize_string_list(self.creators))
        object.__setattr__(self, "categories", _normalize_string_list(self.categories))
        object.__setattr__(self, "include_terms", _normalize_string_list(self.include_terms))
        object.__setattr__(self, "exclude_terms", _normalize_string_list(self.exclude_terms))
        normalized_shopee_offer_keyword = _normalize_optional_text(self.shopee_offer_keyword)
        normalized_shopee_offer_names = _normalize_preserved_string_list(self.shopee_offer_names)
        if normalized_shopee_offer_keyword is None and normalized_shopee_offer_names:
            normalized_shopee_offer_keyword = normalized_shopee_offer_names[0]
        object.__setattr__(self, "shopee_offer_keyword", normalized_shopee_offer_keyword)
        object.__setattr__(self, "shopee_offer_names", normalized_shopee_offer_names)
        object.__setattr__(
            self,
            "shopee_category_urls",
            _normalize_preserved_string_list(self.shopee_category_urls),
        )
        object.__setattr__(
            self,
            "shopee_product_match_ids",
            _deduplicate_ints(self.shopee_product_match_ids),
        )
        object.__setattr__(
            self,
            "shopee_product_category_ids",
            _deduplicate_ints(self.shopee_product_category_ids),
        )
        subgroup_slugs = [subgroup.slug for subgroup in self.subgroups]
        if len(subgroup_slugs) != len(set(subgroup_slugs)):
            raise DiscoveryProfileError("discovery subgroup slugs must be unique within profile")

    def search_term(self) -> str:
        if self.query:
            return self.query

        tokens = (
            self.keywords
            + self.brands
            + self.creators
            + self.categories
        )
        deduplicated = tuple(dict.fromkeys(token for token in tokens if token))
        if deduplicated:
            return " ".join(deduplicated)
        return self.niche

    def get_subgroup(self, slug: str) -> DiscoverySubgroup | None:
        normalized_slug = slug.strip().lower()
        for subgroup in self.subgroups:
            if subgroup.slug == normalized_slug:
                return subgroup
        return None

    def scoped_to_subgroup(self, slug: str) -> DiscoveryProfile:
        subgroup = self.get_subgroup(slug)
        if subgroup is None:
            raise DiscoveryProfileError(f"discovery subgroup not found: {slug}")

        merged_categories = self.categories + tuple(
            category for category in subgroup.categories if category not in self.categories
        )
        return DiscoveryProfile(
            slug=f"{self.slug}:{subgroup.slug}",
            name=f"{self.name} / {subgroup.label}",
            niche=self.niche,
            marketplace=self.marketplace,
            query=subgroup.query,
            target=self.target,
            limit=self.limit,
            catalog_file=self.catalog_file,
            keywords=self.keywords,
            brands=self.brands,
            creators=self.creators,
            categories=merged_categories,
            include_terms=self.include_terms,
            exclude_terms=self.exclude_terms,
            subgroups=self.subgroups,
        )

    def apply_offer_filters(self, offers: Iterable[Offer]) -> list[Offer]:
        filtered: list[Offer] = []
        include_terms = tuple(_normalize_match_text(term) for term in self.include_terms)
        exclude_terms = tuple(_normalize_match_text(term) for term in self.exclude_terms)

        for offer in offers:
            haystack = _normalize_match_text(f"{offer.title} {offer.niche}")
            if include_terms and not any(term in haystack for term in include_terms):
                continue
            if exclude_terms and any(term in haystack for term in exclude_terms):
                continue
            filtered.append(_replace_offer_niche(offer=offer, niche=self.niche))

        return filtered

    def uses_discovery_method(self, method: str) -> bool:
        normalized = method.strip().lower()
        return self.discovery_method == normalized if normalized else False

    def shopee_offer_search_terms(self) -> tuple[str, ...]:
        if self.shopee_offer_keyword:
            return (self.shopee_offer_keyword,)
        if self.shopee_offer_names:
            return self.shopee_offer_names
        return ()


@dataclass(frozen=True)
class DiscoveryProfileCatalog:
    profiles: tuple[DiscoveryProfile, ...]

    @classmethod
    def from_iterable(cls, profiles: Iterable[DiscoveryProfile]) -> DiscoveryProfileCatalog:
        collected = tuple(profiles)
        slugs = [profile.slug for profile in collected]
        if len(slugs) != len(set(slugs)):
            raise DiscoveryProfileError("discovery profile slugs must be unique")
        return cls(profiles=collected)

    def get(self, slug: str) -> DiscoveryProfile | None:
        normalized_slug = slug.strip().lower()
        for profile in self.profiles:
            if profile.slug == normalized_slug:
                return profile
        return None


def load_discovery_profile_catalog(path: Path) -> DiscoveryProfileCatalog:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise DiscoveryProfileError(f"discovery profile file not found: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise DiscoveryProfileError(f"invalid discovery profile file: {error}") from error

    raw_profiles = raw.get("profiles")
    if not isinstance(raw_profiles, list):
        raise DiscoveryProfileError("discovery profile file must define a [profiles] array")

    profiles = tuple(_build_profile(item) for item in raw_profiles)
    if not profiles:
        raise DiscoveryProfileError("discovery profile file must contain at least one profile")
    return DiscoveryProfileCatalog.from_iterable(profiles)


def _build_profile(item: object) -> DiscoveryProfile:
    if not isinstance(item, dict):
        raise DiscoveryProfileError("each discovery profile must be an object")

    marketplace_value = str(item.get("marketplace", Marketplace.MOCK.value))
    try:
        marketplace = Marketplace(marketplace_value)
    except ValueError as error:
        raise DiscoveryProfileError(
            f"unsupported discovery profile marketplace: {marketplace_value}"
        ) from error

    return DiscoveryProfile(
        slug=str(item.get("slug", "")),
        name=str(item.get("name", "")),
        niche=str(item.get("niche", "")),
        marketplace=marketplace,
        discovery_method=_string_or_none(item.get("discovery_method")),
        query=_string_or_none(item.get("query")),
        target=_string_or_none(item.get("target")),
        limit=_int_or_none(item.get("limit")),
        catalog_file=_string_or_none(item.get("catalog_file")),
        keywords=_string_tuple(item.get("keywords")),
        brands=_string_tuple(item.get("brands")),
        creators=_string_tuple(item.get("creators")),
        categories=_string_tuple(item.get("categories")),
        include_terms=_string_tuple(item.get("include_terms")),
        exclude_terms=_string_tuple(item.get("exclude_terms")),
        shopee_offer_keyword=_string_or_none(item.get("shopee_offer_keyword")),
        shopee_offer_names=_string_tuple(item.get("shopee_offer_names")),
        shopee_category_urls=_string_tuple(item.get("shopee_category_urls")),
        shopee_product_match_ids=_int_tuple(item.get("shopee_product_match_ids")),
        shopee_product_category_ids=_int_tuple(item.get("shopee_product_category_ids")),
        subgroups=_subgroup_tuple(item.get("subgroups")),
    )


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise DiscoveryProfileError("list fields in discovery profile must be arrays")
    return tuple(str(item) for item in value)


def _subgroup_tuple(value: object) -> tuple[DiscoverySubgroup, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise DiscoveryProfileError("subgroups in discovery profile must be arrays")

    subgroups: list[DiscoverySubgroup] = []
    for item in value:
        if not isinstance(item, dict):
            raise DiscoveryProfileError("each discovery subgroup must be an object")
        subgroups.append(
            DiscoverySubgroup(
                slug=str(item.get("slug", "")),
                label=str(item.get("label", "")),
                query=str(item.get("query", "")),
                categories=_string_tuple(item.get("categories")),
            )
        )
    return tuple(subgroups)


def _int_tuple(value: object) -> tuple[int, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise DiscoveryProfileError("integer list fields in discovery profile must be arrays")
    normalized: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise DiscoveryProfileError(
                "integer list fields in discovery profile must contain integers"
            )
        normalized.append(item)
    return tuple(normalized)


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise DiscoveryProfileError("discovery profile limit must be an integer")
    return value


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_match_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_marks.strip().lower()


def _normalize_optional_identifier(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    return normalized.lower()


def _normalize_string_list(values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(item.strip().lower() for item in values if item.strip())
    return tuple(dict.fromkeys(normalized))


def _normalize_preserved_string_list(values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(item.strip() for item in values if item.strip())
    return tuple(dict.fromkeys(normalized))


def _deduplicate_ints(values: Iterable[int]) -> tuple[int, ...]:
    return tuple(dict.fromkeys(values))


def _replace_offer_niche(*, offer: Offer, niche: str) -> Offer:
    return Offer(
        marketplace=offer.marketplace,
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
