from __future__ import annotations

from ofertas_bot.models import Marketplace, Offer


class MockOfferProvider:
    def fetch(self, marketplace: Marketplace, niche: str, limit: int) -> list[Offer]:
        catalog = [
            Offer(
                marketplace=marketplace,
                title=f"Kit {niche.title()} com desconto",
                url="https://example.com/oferta-1?tag=afiliado",
                image_url="https://example.com/oferta-1.jpg",
                price=49.90,
                old_price=89.90,
                commission_rate=0.08,
                sales_count=1200,
                rating=4.8,
                niche=niche,
                is_prime_or_free_shipping=True,
            ),
            Offer(
                marketplace=marketplace,
                title=f"Achadinho de {niche} popular",
                url="https://example.com/oferta-2?tag=afiliado",
                image_url="https://example.com/oferta-2.jpg",
                price=29.90,
                old_price=39.90,
                commission_rate=0.05,
                sales_count=450,
                rating=4.5,
                niche=niche,
                is_prime_or_free_shipping=False,
            ),
        ]
        return catalog[:limit]
