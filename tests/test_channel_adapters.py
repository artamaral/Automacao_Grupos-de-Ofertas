from ofertas_bot.channel_adapters import build_channel_adapter
from ofertas_bot.models import Marketplace, MessageDraft, Offer


def make_draft() -> MessageDraft:
    offer = Offer(
        marketplace=Marketplace.MOCK,
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
    return MessageDraft(
        offer=offer,
        text="Oferta com comissão ✨",
    )


def test_build_channel_adapter_supports_whatsapp_and_telegram() -> None:
    whatsapp = build_channel_adapter("whatsapp")
    telegram = build_channel_adapter("telegram")

    whatsapp_result = whatsapp.publish(make_draft(), "grupo-beleza")
    telegram_result = telegram.publish(make_draft(), "grupo-beleza")

    assert whatsapp_result.adapter_kind == "whatsapp"
    assert whatsapp_result.delivery_label == "whatsapp:grupo-beleza"
    assert telegram_result.adapter_kind == "telegram"
    assert telegram_result.delivery_label == "telegram:grupo-beleza"
