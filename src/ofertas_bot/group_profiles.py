from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


class GroupProfileError(ValueError):
    """Raised when a group profile is invalid."""


@dataclass(frozen=True)
class GroupProfile:
    slug: str
    name: str
    allowed_niches: tuple[str, ...]
    max_offers_per_run: int = 3
    min_minutes_between_posts: int = 120
    active: bool = True

    def __post_init__(self) -> None:
        normalized_slug = self.slug.strip().lower()
        normalized_name = self.name.strip()
        normalized_niches = tuple(
            niche.strip().lower() for niche in self.allowed_niches if niche.strip()
        )

        if not normalized_slug:
            raise GroupProfileError("group profile slug is required")
        if not normalized_name:
            raise GroupProfileError("group profile name is required")
        if not normalized_niches:
            raise GroupProfileError("group profile requires at least one niche")
        if self.max_offers_per_run <= 0:
            raise GroupProfileError("group profile max_offers_per_run must be positive")
        if self.min_minutes_between_posts < 0:
            raise GroupProfileError("group profile min_minutes_between_posts cannot be negative")

        object.__setattr__(self, "slug", normalized_slug)
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "allowed_niches", normalized_niches)

    def allows_niche(self, niche: str) -> bool:
        return niche.strip().lower() in self.allowed_niches


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


DEFAULT_GROUP_PROFILES = GroupProfileCatalog.from_iterable(
    (
        GroupProfile(
            slug="maquiagem-vip",
            name="Maquiagem VIP",
            allowed_niches=("maquiagem", "beleza", "skincare"),
            max_offers_per_run=3,
            min_minutes_between_posts=120,
        ),
        GroupProfile(
            slug="casa-achadinhos",
            name="Casa e Achadinhos",
            allowed_niches=("casa", "cozinha", "organizacao"),
            max_offers_per_run=4,
            min_minutes_between_posts=180,
        ),
        GroupProfile(
            slug="pesca-e-lazer",
            name="Pesca e Lazer",
            allowed_niches=("pesca", "camping", "lazer"),
            max_offers_per_run=2,
            min_minutes_between_posts=240,
        ),
    )
)
