from ofertas_bot.copy_brief import build_copy_brief
from ofertas_bot.models import Marketplace, Offer, ScoredOffer


def make_offer() -> Offer:
    return Offer(
        marketplace=Marketplace.SHOPEE,
        title="Produto teste",
        url="https://example.com/produto",
        image_url="https://example.com/produto.jpg",
        price=75,
        old_price=100,
        commission_rate=0.12,
        sales_count=250,
        rating=4.9,
        niche="auto e moto",
        is_prime_or_free_shipping=True,
        shop_type_code=2,
    )


def test_build_copy_brief_preserves_scorer_decision_and_offer_facts() -> None:
    scored = ScoredOffer(
        offer=make_offer(),
        score=37,
        reasons=["desconto de 25%", "comissao de 12%", "loja star"],
    )

    brief = build_copy_brief(scored)

    assert brief.content_type == "product_offer"
    assert brief.offer.title == "Produto teste"
    assert brief.score == 37
    assert brief.score_reasons == (
        "desconto de 25%",
        "comissao de 12%",
        "loja star",
    )
    assert any("afiliado" in item for item in brief.required_disclosures)
    assert any("Nao alterar preco" in item for item in brief.copy_constraints)
    assert "preco garantido" in brief.forbidden_claims
