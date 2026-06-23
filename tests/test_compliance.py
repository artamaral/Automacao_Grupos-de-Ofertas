from ofertas_bot.agents.compliance import ComplianceAgent
from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.settings import Settings


def make_offer(*, url: str = "https://example.com/produto") -> Offer:
    return Offer(
        marketplace=Marketplace.SHOPEE,
        title="Produto",
        url=url,
        image_url=None,
        price=10,
        old_price=20,
        commission_rate=0.05,
        sales_count=100,
        rating=4.7,
        niche="teste",
    )


def test_compliance_blocks_missing_affiliate_disclosure() -> None:
    offer = make_offer()
    draft = MessageDraft(offer=offer, text="Compre agora: https://example.com/produto")

    result = ComplianceAgent(settings=Settings()).validate(draft=draft, dry_run=True)

    assert not result.approved
    assert "mensagem sem aviso de afiliado" in result.reasons


def test_compliance_validates_batch() -> None:
    approved_draft = MessageDraft(
        offer=make_offer(),
        text="Link de afiliado com comissão: https://example.com/produto",
    )
    blocked_draft = MessageDraft(
        offer=make_offer(),
        text="Compre agora: https://example.com/produto",
    )

    results = ComplianceAgent(settings=Settings()).validate_batch(
        drafts=(approved_draft, blocked_draft),
        dry_run=True,
    )

    assert len(results) == 2
    assert results[0].approved
    assert not results[1].approved
    assert "mensagem sem aviso de afiliado" in results[1].reasons
