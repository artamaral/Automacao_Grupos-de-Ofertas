from ofertas_bot.agents.copywriter import CopywriterAgent
from ofertas_bot.group_profiles import GroupProfile
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


def make_group_profile(*, max_offers_per_run: int = 3) -> GroupProfile:
    return GroupProfile(
        slug="maquiagem-vip",
        name="Maquiagem VIP",
        allowed_niches=("teste",),
        max_offers_per_run=max_offers_per_run,
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


def test_copywriter_creates_detailed_message_for_group() -> None:
    offer = make_offer()
    scored = ScoredOffer(offer=offer, score=10, reasons=["desconto"])
    group_profile = make_group_profile(max_offers_per_run=3)

    draft = CopywriterAgent().create_message_for_group(scored, group_profile)

    assert "Grupo: Maquiagem VIP" in draft.text
    assert "Loja: Amazon" in draft.text
    assert "Sinal de confiança:" in draft.text
    assert "Entrega:" in draft.text


def test_copywriter_creates_compact_message_for_single_offer_group() -> None:
    offer = make_offer()
    scored = ScoredOffer(
        offer=offer,
        score=10,
        reasons=["desconto", "bem avaliado", "frete"],
    )
    group_profile = make_group_profile(max_offers_per_run=1)

    draft = CopywriterAgent().create_message_for_group(scored, group_profile)

    assert "Grupo: Maquiagem VIP" in draft.text
    assert "Destaques: desconto, bem avaliado." in draft.text
    assert "Loja:" not in draft.text
    assert "Sinal de confiança:" not in draft.text
    assert "Entrega:" not in draft.text
