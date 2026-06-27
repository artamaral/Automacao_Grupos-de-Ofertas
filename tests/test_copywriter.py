from dataclasses import replace

from ofertas_bot.agents.copywriter import CopywriterAgent
from ofertas_bot.group_plan import GroupPlan
from ofertas_bot.group_profiles import GroupProfile
from ofertas_bot.message_template_renderer import render_shopee_message_template
from ofertas_bot.models import Marketplace, Offer, ScoredOffer


def make_offer(
    *,
    marketplace: Marketplace = Marketplace.AMAZON,
    price: float = 10,
    old_price: float | None = 20,
    sales_count: int = 100,
    rating: float | None = 4.7,
    is_prime_or_free_shipping: bool = False,
    title: str = "Produto teste",
) -> Offer:
    return Offer(
        marketplace=marketplace,
        title=title,
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


def make_scored_offer(
    title: str = "Produto teste",
    *,
    marketplace: Marketplace = Marketplace.AMAZON,
) -> ScoredOffer:
    return ScoredOffer(
        offer=make_offer(title=title, marketplace=marketplace),
        score=10,
        reasons=["desconto", "bem avaliado", "frete"],
    )


def test_copywriter_includes_affiliate_disclosure() -> None:
    offer = make_offer()
    scored = ScoredOffer(offer=offer, score=10, reasons=["desconto"])

    draft = CopywriterAgent().create_message(scored)

    assert "afiliado" in draft.text.lower()
    assert "comiss" in draft.text.lower()
    assert offer.url in draft.text


def test_copywriter_renders_shopee_static_template_with_coupon() -> None:
    offer = make_offer(
        marketplace=Marketplace.SHOPEE,
        price=33.22,
        old_price=60.66,
        rating=5.0,
        title="Coletor Manual Silicone de Aleitamento Materno Bomba De Leite Com Tampa",
    )
    scored = ScoredOffer(offer=offer, score=10, reasons=["desconto"])

    draft = CopywriterAgent().create_message(scored)

    assert "Coletor Manual Silicone de Aleitamento Materno Bomba De Leite Com Tampa" in draft.text
    assert "🏪 Loja: Shopee" in draft.text
    assert "💵 R$ 33,22" in draft.text
    assert "🏷️ 45% OFF" in draft.text
    assert "⭐ Avaliação: 5,0/5" in draft.text
    assert "🎟️ Resgate o cupom desta página:" in draft.text
    assert "https://s.shopee.com.br/4AxtmHq4If" in draft.text
    assert "✅ Link do produto:" in draft.text
    assert "(anúncio)" in draft.text


def test_shopee_template_is_shared_by_all_niches(tmp_path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "shopee.txt").write_text(
        "PADRAO {{facts.title}} {{coupon_url}}",
        encoding="utf-8",
    )
    (template_dir / "mae-e-bebe.txt").write_text("OVERRIDE", encoding="utf-8")
    coupon_path = tmp_path / "coupons.toml"
    coupon_path.write_text(
        'global_coupon_url = "https://example.com/cupom"',
        encoding="utf-8",
    )
    offer = replace(
        make_offer(marketplace=Marketplace.SHOPEE, title="Produto mae e bebe"),
        niche="mae e bebe",
    )
    scored = ScoredOffer(offer=offer, score=10, reasons=["teste"])

    message = render_shopee_message_template(
        scored,
        template_dir=template_dir,
        coupon_urls_path=coupon_path,
    )

    assert message == "PADRAO Produto mae e bebe https://example.com/cupom"


def test_copywriter_includes_trust_line() -> None:
    offer = make_offer(sales_count=250, rating=4.8)
    scored = ScoredOffer(offer=offer, score=10, reasons=["bem avaliado"])

    draft = CopywriterAgent().create_message(scored)

    assert "Sinal de confiança:" in draft.text
    assert "250 vendas" in draft.text


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
    offer = make_offer(marketplace=Marketplace.AMAZON)
    scored = ScoredOffer(offer=offer, score=10, reasons=["desconto"])
    group_profile = make_group_profile(max_offers_per_run=3)

    draft = CopywriterAgent().create_message_for_group(scored, group_profile)

    assert "Grupo: Maquiagem VIP" in draft.text
    assert "Loja: Amazon" in draft.text
    assert "Sinal de confiança:" in draft.text
    assert "Entrega:" in draft.text


def test_copywriter_creates_shopee_template_for_group() -> None:
    scored = make_scored_offer(marketplace=Marketplace.SHOPEE)
    group_profile = make_group_profile(max_offers_per_run=3)

    draft = CopywriterAgent().create_message_for_group(scored, group_profile)

    assert "🏪 Loja: Shopee" in draft.text
    assert "Grupo: Maquiagem VIP" not in draft.text


def test_copywriter_creates_compact_message_for_single_offer_group() -> None:
    scored = make_scored_offer()
    group_profile = make_group_profile(max_offers_per_run=1)

    draft = CopywriterAgent().create_message_for_group(scored, group_profile)

    assert "Grupo: Maquiagem VIP" in draft.text
    assert "Destaques: desconto, bem avaliado." in draft.text
    assert "Loja:" not in draft.text
    assert "Sinal de confiança:" not in draft.text
    assert "Entrega:" not in draft.text


def test_copywriter_creates_message_batch_limited_by_group() -> None:
    scored_offers = [
        make_scored_offer("Produto 1"),
        make_scored_offer("Produto 2"),
        make_scored_offer("Produto 3"),
    ]
    group_profile = make_group_profile(max_offers_per_run=2)

    drafts = CopywriterAgent().create_messages_for_group(
        scored_offers,
        group_profile,
    )

    assert len(drafts) == 2
    assert "Produto 1" in drafts[0].text
    assert "Produto 2" in drafts[1].text


def test_copywriter_batch_uses_compact_messages_for_single_offer_group() -> None:
    group_profile = make_group_profile(max_offers_per_run=1)

    drafts = CopywriterAgent().create_messages_for_group(
        [make_scored_offer()],
        group_profile,
    )

    assert len(drafts) == 1
    assert "Grupo: Maquiagem VIP" in drafts[0].text
    assert "Loja:" not in drafts[0].text


def test_copywriter_creates_messages_from_allowed_plan() -> None:
    group_profile = make_group_profile(max_offers_per_run=2)
    plan = GroupPlan(
        group_slug="maquiagem-vip",
        allowed=True,
        selected_offers=(
            make_offer(title="Produto 1"),
            make_offer(title="Produto 2"),
        ),
        reasons=(),
    )

    drafts = CopywriterAgent().create_messages_for_plan(plan, group_profile)

    assert len(drafts) == 2
    assert "Produto 1" in drafts[0].text
    assert "Produto 2" in drafts[1].text
    assert "selecionada para este grupo" in drafts[0].text


def test_copywriter_does_not_create_messages_from_blocked_plan() -> None:
    group_profile = make_group_profile(max_offers_per_run=2)
    plan = GroupPlan(
        group_slug="maquiagem-vip",
        allowed=False,
        selected_offers=(make_offer(title="Produto 1"),),
        reasons=("bloqueado",),
    )

    drafts = CopywriterAgent().create_messages_for_plan(plan, group_profile)

    assert drafts == ()
