from ofertas_bot.agents.copywriter import CopywriterAgent
from ofertas_bot.models import Marketplace, Offer, ScoredOffer


def test_copywriter_includes_affiliate_disclosure() -> None:
    offer = Offer(
        marketplace=Marketplace.AMAZON,
        title="Produto teste",
        url="https://example.com/produto",
        image_url=None,
        price=10,
        old_price=20,
        commission_rate=0.05,
        sales_count=100,
        rating=4.7,
        niche="teste",
    )
    scored = ScoredOffer(offer=offer, score=10, reasons=["desconto"])

    draft = CopywriterAgent().create_message(scored)

    assert "afiliado" in draft.text.lower()
    assert "comissão" in draft.text.lower()
    assert offer.url in draft.text


def test_copywriter_formats_price_as_from_to_when_old_price_exists() -> None:
    offer = Offer(
        marketplace=Marketplace.SHOPEE,
        title="Produto com desconto",
        url="https://example.com/produto",
        image_url=None,
        price=49.90,
        old_price=89.90,
        commission_rate=0.08,
        sales_count=100,
        rating=4.7,
        niche="maquiagem",
    )
    scored = ScoredOffer(offer=offer, score=10, reasons=["desconto"])

    draft = CopywriterAgent().create_message(scored)

    assert "Preço: de R$ 89.90 por R$ 49.90 (44% OFF)" in draft.text
