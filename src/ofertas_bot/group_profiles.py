from __future__ import annotations

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ofertas_bot.models import Marketplace

VALID_CHANNEL_ADAPTERS = ("console", "whatsapp", "telegram")


class GroupProfileError(ValueError):
    """Raised when a group profile is invalid."""


DEFAULT_GROUP_PROFILES_PATH = Path(__file__).resolve().parents[2] / "config" / "group_profiles.toml"


@dataclass(frozen=True)
class GroupProfile:
    slug: str
    name: str
    allowed_niches: tuple[str, ...]
    allowed_marketplaces: tuple[Marketplace, ...] = (Marketplace.MOCK,)
    destination_kind: str = "group"
    destination_ref: str | None = None
    channel_adapter: str = "whatsapp"
    message_tone: str = "direto"
    allowed_content_types: tuple[str, ...] = ("product", "coupon", "context")
    max_offers_per_run: int = 3
    min_minutes_between_posts: int = 120
    active: bool = True

    def __post_init__(self) -> None:
        normalized_slug = self.slug.strip().lower()
        normalized_name = self.name.strip()
        normalized_niches = tuple(
            niche.strip().lower() for niche in self.allowed_niches if niche.strip()
        )
        normalized_destination_kind = self.destination_kind.strip().lower()
        normalized_destination_ref = _normalize_optional_text(self.destination_ref)
        normalized_channel_adapter = self.channel_adapter.strip().lower()
        normalized_message_tone = self.message_tone.strip().lower()
        normalized_content_types = _normalize_string_tuple(self.allowed_content_types)

        if not normalized_slug:
            raise GroupProfileError("group profile slug is required")
        if not normalized_name:
            raise GroupProfileError("group profile name is required")
        if not normalized_niches:
            raise GroupProfileError("group profile requires at least one niche")
        if not self.allowed_marketplaces:
            raise GroupProfileError("group profile requires at least one marketplace")
        if not normalized_destination_kind:
            raise GroupProfileError("group profile destination_kind is required")
        if normalized_channel_adapter not in VALID_CHANNEL_ADAPTERS:
            raise GroupProfileError("group profile channel_adapter is invalid")
        if not normalized_message_tone:
            raise GroupProfileError("group profile message_tone is required")
        if not normalized_content_types:
            raise GroupProfileError("group profile requires at least one content type")
        if self.max_offers_per_run <= 0:
            raise GroupProfileError("group profile max_offers_per_run must be positive")
        if self.min_minutes_between_posts < 0:
            raise GroupProfileError("group profile min_minutes_between_posts cannot be negative")

        object.__setattr__(self, "slug", normalized_slug)
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "allowed_niches", normalized_niches)
        object.__setattr__(self, "destination_kind", normalized_destination_kind)
        object.__setattr__(self, "destination_ref", normalized_destination_ref)
        object.__setattr__(self, "channel_adapter", normalized_channel_adapter)
        object.__setattr__(self, "message_tone", normalized_message_tone)
        object.__setattr__(self, "allowed_content_types", normalized_content_types)

    def allows_niche(self, niche: str) -> bool:
        return niche.strip().lower() in self.allowed_niches

    def allows_marketplace(self, marketplace: Marketplace) -> bool:
        return marketplace in self.allowed_marketplaces

    def allows_content_type(self, content_type: str) -> bool:
        return content_type.strip().lower() in self.allowed_content_types


@dataclass(frozen=True)
class GroupProfileCatalog:
    profiles: tuple[GroupProfile, ...]

    @classmethod
    def from_iterable(cls, profiles: Iterable[GroupProfile]) -> GroupProfileCatalog:
        collected = tuple(profiles)
        slugs = [profile.slug for profile in collected]
        if len(slugs) != len(set(slugs)):
            raise GroupProfileError("group profile slugs must be unique")
        return cls(profiles=collected)

    def active_profiles(self) -> tuple[GroupProfile, ...]:
        return tuple(profile for profile in self.profiles if profile.active)

    def get(self, slug: str) -> GroupProfile | None:
        normalized_slug = slug.strip().lower()
        for profile in self.profiles:
            if profile.slug == normalized_slug:
                return profile
        return None

    def profiles_for_niche(self, niche: str) -> tuple[GroupProfile, ...]:
        return tuple(
            profile
            for profile in self.active_profiles()
            if profile.allows_niche(niche)
        )


def load_group_profile_catalog(path: Path = DEFAULT_GROUP_PROFILES_PATH) -> GroupProfileCatalog:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise GroupProfileError(f"group profile file not found: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise GroupProfileError(f"invalid group profile file: {error}") from error

    raw_profiles = raw.get("profiles")
    if not isinstance(raw_profiles, list):
        raise GroupProfileError("group profile file must define a [[profiles]] array")

    profiles = tuple(_build_group_profile(item) for item in raw_profiles)
    if not profiles:
        raise GroupProfileError("group profile file must contain at least one profile")
    return GroupProfileCatalog.from_iterable(profiles)


def _build_group_profile(item: object) -> GroupProfile:
    if not isinstance(item, dict):
        raise GroupProfileError("each group profile must be an object")

    return GroupProfile(
        slug=str(item.get("slug", "")),
        name=str(item.get("name", "")),
        allowed_niches=_string_tuple(item.get("allowed_niches")),
        allowed_marketplaces=_marketplace_tuple(item.get("allowed_marketplaces")),
        destination_kind=str(item.get("destination_kind", "group")),
        destination_ref=_optional_str(item.get("destination_ref")),
        channel_adapter=str(item.get("channel_adapter", "whatsapp")),
        message_tone=str(item.get("message_tone", "direto")),
        allowed_content_types=_string_tuple(item.get("allowed_content_types"))
        or ("product", "coupon", "context"),
        max_offers_per_run=_int_or_default(item.get("max_offers_per_run"), 3),
        min_minutes_between_posts=_int_or_default(item.get("min_minutes_between_posts"), 120),
        active=bool(item.get("active", True)),
    )


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise GroupProfileError("list fields in group profile must be arrays")
    return tuple(str(item) for item in value)


def _marketplace_tuple(value: object) -> tuple[Marketplace, ...]:
    if value is None:
        return (Marketplace.MOCK,)
    if not isinstance(value, list):
        raise GroupProfileError("allowed_marketplaces in group profile must be an array")

    marketplaces: list[Marketplace] = []
    for item in value:
        try:
            marketplaces.append(Marketplace(str(item)))
        except ValueError as error:
            raise GroupProfileError(f"unsupported marketplace in group profile: {item}") from error
    return tuple(dict.fromkeys(marketplaces))


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_string_tuple(values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(item.strip().lower() for item in values if item.strip())
    return tuple(dict.fromkeys(normalized))


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_default(value: object, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise GroupProfileError("numeric fields in group profile must be integers")
    return value


DEFAULT_GROUP_PROFILES = load_group_profile_catalog()
