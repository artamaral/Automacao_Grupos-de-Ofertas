from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


class ShopeeCatalogProfileError(ValueError):
    """Raised when a Shopee catalog profile is invalid."""


@dataclass(frozen=True)
class ShopeeCatalogSubniche:
    slug: str
    name: str
    keyword_terms: tuple[str, ...] = ()
    negative_terms: tuple[str, ...] = ()
    shop_ids: tuple[int, ...] = ()
    shop_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        slug = self.slug.strip().lower()
        name = self.name.strip()
        if not slug:
            raise ShopeeCatalogProfileError("catalog subniche slug is required")
        if not name:
            raise ShopeeCatalogProfileError("catalog subniche name is required")
        object.__setattr__(self, "slug", slug)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "keyword_terms", _normalize_terms(self.keyword_terms))
        object.__setattr__(self, "negative_terms", _normalize_terms(self.negative_terms))
        object.__setattr__(self, "shop_ids", _normalize_ints(self.shop_ids))
        object.__setattr__(self, "shop_names", _normalize_texts(self.shop_names))


@dataclass(frozen=True)
class ShopeeCatalogProfile:
    slug: str
    name: str
    start_match_ids: tuple[int, ...] = ()
    keyword_terms: tuple[str, ...] = ()
    negative_terms: tuple[str, ...] = ()
    shop_ids: tuple[int, ...] = ()
    shop_names: tuple[str, ...] = ()
    subniches: tuple[ShopeeCatalogSubniche, ...] = ()

    def __post_init__(self) -> None:
        slug = self.slug.strip().lower()
        name = self.name.strip()
        if not slug:
            raise ShopeeCatalogProfileError("catalog profile slug is required")
        if not name:
            raise ShopeeCatalogProfileError("catalog profile name is required")
        object.__setattr__(self, "slug", slug)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "start_match_ids", _normalize_ints(self.start_match_ids))
        object.__setattr__(self, "keyword_terms", _normalize_terms(self.keyword_terms))
        object.__setattr__(self, "negative_terms", _normalize_terms(self.negative_terms))
        object.__setattr__(self, "shop_ids", _normalize_ints(self.shop_ids))
        object.__setattr__(self, "shop_names", _normalize_texts(self.shop_names))


@dataclass(frozen=True)
class ShopeeCatalogProfileCatalog:
    profiles: tuple[ShopeeCatalogProfile, ...]

    @classmethod
    def from_iterable(
        cls,
        profiles: tuple[ShopeeCatalogProfile, ...] | list[ShopeeCatalogProfile],
    ) -> ShopeeCatalogProfileCatalog:
        items = tuple(profiles)
        slugs = [item.slug for item in items]
        if len(slugs) != len(set(slugs)):
            raise ShopeeCatalogProfileError("catalog profile slugs must be unique")
        return cls(profiles=items)

    def get(self, slug: str) -> ShopeeCatalogProfile | None:
        normalized_slug = slug.strip().lower()
        for profile in self.profiles:
            if profile.slug == normalized_slug:
                return profile
        return None


def load_shopee_catalog_profile_catalog(path: Path) -> ShopeeCatalogProfileCatalog:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ShopeeCatalogProfileError(f"catalog profile file not found: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ShopeeCatalogProfileError(f"invalid catalog profile file: {error}") from error

    raw_profiles = raw.get("profiles")
    if not isinstance(raw_profiles, list):
        raise ShopeeCatalogProfileError("catalog profile file must define a [[profiles]] array")

    profiles = tuple(_build_profile(item) for item in raw_profiles)
    if not profiles:
        raise ShopeeCatalogProfileError("catalog profile file must contain at least one profile")
    return ShopeeCatalogProfileCatalog.from_iterable(profiles)


def _build_profile(item: object) -> ShopeeCatalogProfile:
    if not isinstance(item, dict):
        raise ShopeeCatalogProfileError("each catalog profile must be an object")
    return ShopeeCatalogProfile(
        slug=str(item.get("slug", "")),
        name=str(item.get("name", "")),
        start_match_ids=_int_tuple(item.get("start_match_ids")),
        keyword_terms=_text_tuple(item.get("keyword_terms")),
        negative_terms=_text_tuple(item.get("negative_terms")),
        shop_ids=_int_tuple(item.get("shop_ids")),
        shop_names=_text_tuple(item.get("shop_names")),
        subniches=_subniche_tuple(item.get("subniches")),
    )


def _subniche_tuple(value: object) -> tuple[ShopeeCatalogSubniche, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ShopeeCatalogProfileError("subniches in catalog profile must be arrays")
    items: list[ShopeeCatalogSubniche] = []
    for item in value:
        if not isinstance(item, dict):
            raise ShopeeCatalogProfileError("each catalog subniche must be an object")
        items.append(
            ShopeeCatalogSubniche(
                slug=str(item.get("slug", "")),
                name=str(item.get("name", "")),
                keyword_terms=_text_tuple(item.get("keyword_terms")),
                negative_terms=_text_tuple(item.get("negative_terms")),
                shop_ids=_int_tuple(item.get("shop_ids")),
                shop_names=_text_tuple(item.get("shop_names")),
            )
        )
    return tuple(items)


def _text_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ShopeeCatalogProfileError("catalog text fields must be arrays")
    return tuple(str(item) for item in value)


def _int_tuple(value: object) -> tuple[int, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ShopeeCatalogProfileError("catalog integer fields must be arrays")
    values: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ShopeeCatalogProfileError("catalog integer fields must contain integers")
        values.append(item)
    return tuple(values)


def _normalize_terms(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.strip().lower() for item in values if item.strip()))


def _normalize_texts(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.strip() for item in values if item.strip()))


def _normalize_ints(values: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(dict.fromkeys(values))
