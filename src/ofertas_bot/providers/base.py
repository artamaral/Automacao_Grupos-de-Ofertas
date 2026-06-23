from __future__ import annotations

from typing import Protocol

from ofertas_bot.models import Marketplace, Offer


class OfferProvider(Protocol):
    marketplace: Marketplace

    def fetch(self, niche: str, limit: int) -> list[Offer]:
        """Fetch normalized offers for a niche."""
