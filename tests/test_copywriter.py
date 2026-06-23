from ofertas_bot.agents.copywriter import CopywriterAgent
from ofertas_bot.models import Marketplace, Offer, ScoredOffer


def make_offer(
    *,
    marketplace: Marketplace = Marketplace.AMAZON,
    price: float = 10,
    old_price: float | None = 20,
    sales_count: int = 100,
    rating: float | None = 4.7,
    is_prime_or_free_shipping: bool = False,
) -> Offer:
    return Offer(
        marketplace=marketplace,
        title="Produto teste",
        url="https://example.com/produto",
        image_url=None,
        price=price,
        old_price=old_price,
        commission_rate=0.05,
        sales_count=sales_count,
        rating=rating,
        niche="teste",
        is_prime_or_free_shipping=is_prime_or_free_shipping,
    )


def test_copywriter_includes_affiliate_disclosure() -> None:
    offer = make_offer()
    scored = ScoredOffer(offer=offer, score=10, reasons=["desconto"])

    draft = CopywriterAgent().create_message(scored)

    assert "afiliado" in draft.text.lower()
    assert "comissão" in draft.text.lower()
    assert offer.url in draft.text


def test_copywriter_formats_price_as_from_to_when_old_price_exists() -> None:
    offer = make_offer(
        marketplace=Marketplace.SHOPEE,
        price=49.90,
        old_price=89.90,
    )
    scored = ScoredOffer(offer=offer, score=10, reasons=["desconto"])

    draft = CopywriterAgent().create_message(scored)

    assert "Preço: de R$ 89.90 por R$ 49.90 (44% OFF)" in draft.text


def test_copywriter_includes_marketplace_label() -> None:
    offer = make_offer(marketplace=Marketplace.SHOPEE)
    scored = ScoredOffer(offer=offer, score=10, reasons=["desconto"])

    draft = CopywriterAgent().create_message(scored)

    assert "Loja: Shopee" in draft.text


def test_copywriter_includes_trust_line() -> None:
    offer = make_offer(sales_count=250, rating=4.8)
    scored = ScoredOffer(offer=offer, score=10, reasons=["bem avaliado"])

    draft = CopywriterAgent().create_message(scored)

    assert "Sinal de confiança: avaliação 4.8/5; 250 vendas." in draft.text


def test_copywriter_includes_shipping_benefit() -> None:
    offer = make_offer(is_prime_or_free_shipping=True)
    scored = ScoredOffer(offer=offer, score=10, reasons=["frete"])

    draft = CopywriterAgent().create_message(scored)

    assert "Entrega: benefício de frete destacado." in draft.text


def test_copywriter_includes_safe_call_to_action() -> None:
    offer = make_offer()
    scored = ScoredOffer(offer=offer, score=10, reasons=["desconto"])

    draft = CopywriterAgent().create_message(scored)

    assert "Confira enquanto estiver disponível." in draft.text
