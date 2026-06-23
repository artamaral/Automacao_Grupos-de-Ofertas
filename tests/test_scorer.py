from ofertas_bot.agents.scorer import ScorerAgent
from ofertas_bot.models import Marketplace, Offer


def test_scorer_prioritizes_high_discount_and_sales() -> None:
    offers = [
        Offer(
            marketplace=Marketplace.SHOPEE,
            title="Oferta fraca",
            url="https://example.com/fraca",
            image_url=None,
            price=90,
            old_price=100,
            commission_rate=0.02,
            sales_count=10,
            rating=4.0,
            niche="casa",
        ),
        Offer(
            marketplace=Marketplace.SHOPEE,
            title="Oferta forte",
            url="https://example.com/forte",
            image_url=None,
            price=50,
            old_price=100,
            commission_rate=0.08,
            sales_count=1000,
            rating=4.8,
            niche="casa",
            is_prime_or_free_shipping=True,
        ),
    ]

    scored = ScorerAgent().score(offers)

    assert scored[0].offer.title == "Oferta forte"
    assert scored[0].score > scored[1].score
