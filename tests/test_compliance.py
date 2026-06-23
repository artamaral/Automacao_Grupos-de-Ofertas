from ofertas_bot.agents.compliance import ComplianceAgent
from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.settings import Settings


def test_compliance_blocks_missing_affiliate_disclosure() -> None:
    offer = Offer(
        marketplace=Marketplace.SHOPEE,
        title="Produto",
        url="https://example.com/produto",
        image_url=None,
        price=10,
        old_price=20,
        commission_rate=0.05,
        sales_count=100,
        rating=4.7,
        niche="teste",
    )
    draft = MessageDraft(offer=offer, text="Compre agora: https://example.com/produto")

    result = ComplianceAgent(settings=Settings()).validate(draft=draft, dry_run=True)

    assert not result.approved
    assert "mensagem sem aviso de afiliado" in result.reasons
