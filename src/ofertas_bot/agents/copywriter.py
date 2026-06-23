from __future__ import annotations

from ofertas_bot.models import MessageDraft, ScoredOffer


class CopywriterAgent:
    def create_message(self, scored_offer: ScoredOffer) -> MessageDraft:
        offer = scored_offer.offer
        old_price = f" de R$ {offer.old_price:.2f}" if offer.old_price else ""
        discount = f" ({offer.discount_percent:.0f}% OFF)" if offer.discount_percent else ""
        reasons = ", ".join(scored_offer.reasons[:3]) or "boa oportunidade"

        text = (
            f"🔥 {offer.title}\n"
            f"Preço: R$ {offer.price:.2f}{old_price}{discount}\n"
            f"Destaques: {reasons}.\n"
            f"Link: {offer.url}\n\n"
            "Aviso: este é um link de afiliado; podemos receber comissão pela compra. "
            "Preço e disponibilidade podem mudar."
        )
        return MessageDraft(offer=offer, text=text)
