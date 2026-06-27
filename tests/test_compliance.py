from ofertas_bot.agents.compliance import ComplianceAgent
from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.settings import Settings


def make_offer(*, url: str = "https://example.com/produto", price: float = 10) -> Offer:
    return Offer(
        marketplace=Marketplace.SHOPEE,
        title="Produto",
        url=url,
        image_url=None,
        price=price,
        old_price=20,
        commission_rate=0.05,
        sales_count=100,
        rating=4.7,
        niche="teste",
    )


def make_approved_draft() -> MessageDraft:
    return MessageDraft(
        offer=make_offer(),
        text="Link de afiliado com comissão: https://example.com/produto",
    )


def make_blocked_draft() -> MessageDraft:
    return MessageDraft(
        offer=make_offer(),
        text="Compre agora: https://example.com/produto",
    )


def test_compliance_blocks_missing_affiliate_disclosure() -> None:
    result = ComplianceAgent(settings=Settings()).validate(
        draft=make_blocked_draft(),
        dry_run=True,
    )

    assert not result.approved
    assert "mensagem sem aviso de afiliado" in result.reasons


def test_compliance_validates_batch() -> None:
    approved_draft = make_approved_draft()
    blocked_draft = make_blocked_draft()

    results = ComplianceAgent(settings=Settings()).validate_batch(
        drafts=(approved_draft, blocked_draft),
        dry_run=True,
    )

    assert len(results) == 2
    assert results[0].approved
    assert not results[1].approved
    assert "mensagem sem aviso de afiliado" in results[1].reasons


def test_compliance_filters_approved_drafts() -> None:
    approved_draft = make_approved_draft()
    blocked_draft = make_blocked_draft()

    drafts = ComplianceAgent(settings=Settings()).approved_drafts(
        drafts=(approved_draft, blocked_draft),
        dry_run=True,
    )

    assert drafts == (approved_draft,)


def test_compliance_summarizes_batch() -> None:
    summary = ComplianceAgent(settings=Settings()).summarize_batch(
        drafts=(make_approved_draft(), make_blocked_draft()),
        dry_run=True,
    )

    assert summary == {
        "total": 2,
        "approved": 1,
        "blocked": 1,
        "reasons": ["mensagem sem aviso de afiliado"],
    }


def test_compliance_allows_unknown_price() -> None:
    draft = MessageDraft(
        offer=make_offer(price=0),
        text="Link de afiliado com comissão: https://example.com/produto",
    )

    result = ComplianceAgent(settings=Settings()).validate(draft=draft, dry_run=True)

    assert result.approved


def test_compliance_accepts_static_ad_marker() -> None:
    draft = MessageDraft(
        offer=make_offer(),
        text="Oferta aprovada\n\n(anúncio)",
    )

    result = ComplianceAgent(settings=Settings()).validate(draft=draft, dry_run=True)

    assert result.approved
