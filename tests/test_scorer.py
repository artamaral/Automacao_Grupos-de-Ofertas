from ofertas_bot.agents.scorer import ScorerAgent
from ofertas_bot.models import Marketplace, Offer


def make_offer(
    *,
    title: str = "Oferta",
    price: float = 100,
    old_price: float | None = None,
    commission_rate: float = 0,
    sales_count: int = 0,
    rating: float | None = None,
    is_prime_or_free_shipping: bool = False,
    shop_type_code: int | None = None,
) -> Offer:
    return Offer(
        marketplace=Marketplace.SHOPEE,
        title=title,
        url=f"https://example.com/{title.lower().replace(' ', '-')}",
        image_url=None,
        price=price,
        old_price=old_price,
        commission_rate=commission_rate,
        sales_count=sales_count,
        rating=rating,
        niche="casa",
        is_prime_or_free_shipping=is_prime_or_free_shipping,
        shop_type_code=shop_type_code,
    )


def test_scorer_prioritizes_high_discount_and_sales() -> None:
    offers = [
        make_offer(
            title="Oferta fraca",
            price=90,
            old_price=100,
            commission_rate=0.02,
            sales_count=10,
            rating=4.0,
        ),
        make_offer(
            title="Oferta forte",
            price=50,
            old_price=100,
            commission_rate=0.08,
            sales_count=1000,
            rating=4.8,
            is_prime_or_free_shipping=True,
        ),
    ]

    scored = ScorerAgent().score(offers)

    assert scored[0].offer.title == "Oferta forte"
    assert scored[0].score > scored[1].score


def test_scorer_explains_each_active_component() -> None:
    offer = make_offer(
        price=70,
        old_price=100,
        commission_rate=0.07,
        sales_count=250,
        rating=4.7,
        is_prime_or_free_shipping=True,
    )

    scored = ScorerAgent().score([offer])[0]

    assert scored.score == 42.5
    assert scored.reasons == [
        "desconto de 30%",
        "comissao de 7%",
        "250 vendas",
        "avaliacao 4.7",
        "frete rapido/gratis",
    ]


def test_scorer_ignores_weak_signals() -> None:
    offer = make_offer(
        price=85,
        old_price=100,
        commission_rate=0,
        sales_count=99,
        rating=4.4,
    )

    scored = ScorerAgent().score([offer])[0]

    assert scored.score == 0
    assert scored.reasons == []


def test_scorer_caps_discount_and_sales_points() -> None:
    offer = make_offer(
        price=10,
        old_price=100,
        sales_count=10_000,
    )

    scored = ScorerAgent().score([offer])[0]

    assert scored.score == 40
    assert scored.reasons == ["desconto de 90%", "10000 vendas"]


def test_scorer_adds_shop_type_confidence_bonus() -> None:
    official_offer = make_offer(shop_type_code=1)
    star_plus_offer = make_offer(shop_type_code=4)
    star_offer = make_offer(shop_type_code=2)
    common_offer = make_offer()

    scored = ScorerAgent().score([common_offer, star_offer, star_plus_offer, official_offer])

    assert [item.score for item in scored] == [10, 7, 5, 0]
    assert [item.reasons for item in scored] == [
        ["loja oficial"],
        ["loja star+"],
        ["loja star"],
        [],
    ]
