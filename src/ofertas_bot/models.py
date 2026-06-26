from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit, urlunsplit


class Marketplace(StrEnum):
    SHOPEE = "shopee"
    AMAZON = "amazon"
    MOCK = "mock"


@dataclass(frozen=True)
class Offer:
    marketplace: Marketplace
    title: str
    url: str
    image_url: str | None
    price: float
    old_price: float | None
    commission_rate: float
    sales_count: int
    rating: float | None
    niche: str
    is_prime_or_free_shipping: bool = False

    @property
    def discount_percent(self) -> float:
        if not self.old_price or self.old_price <= self.price:
            return 0.0
        return round(((self.old_price - self.price) / self.old_price) * 100, 2)

    @property
    def stable_key(self) -> str:
        normalized_url = _normalize_offer_url(self.url)
        raw_key = f"{self.marketplace.value}|{normalized_url}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ScoredOffer:
    offer: Offer
    score: float
    reasons: list[str]


@dataclass(frozen=True)
class MessageDraft:
    offer: Offer
    text: str


@dataclass(frozen=True)
class ComplianceResult:
    approved: bool
    reasons: list[str]


@dataclass(frozen=True)
class PublishResult:
    sent: bool
    dry_run: bool
    target: str
    message: str


def _normalize_offer_url(value: str) -> str:
    parts = urlsplit(value.strip())
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))
