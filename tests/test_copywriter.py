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
