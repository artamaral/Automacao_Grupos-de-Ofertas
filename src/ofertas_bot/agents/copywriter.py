from __future__ import annotations

from ofertas_bot.models import MessageDraft, ScoredOffer


class CopywriterAgent:
    def create_message(self, scored_offer: ScoredOffer) -> MessageDraft:
        offer = scored_offer.offer
        price_line = self._format_price_line(price=offer.price, old_price=offer.old_price, discount_percent=offer.discount_percent)
        reasons = ", ".join(scored_offer.reasons[:3]) or "boa oportunidade"

        text = (
            f"🔥 {offer.title}\n"
            f"{price_line}\n"
            f"Destaques: {reasons}.\n"
            f"Link: {offer.url}\n\n"
            "Aviso: este é um link de afiliado; podemos receber comissão pela compra. "
            "Preço e disponibilidade podem mudar."
        )
        return MessageDraft(offer=offer, text=text)

    def _format_price_line(
        self,
        price: float,
        old_price: float | None,
        discount_percent: float,
    ) -> str:
        discount = f" ({discount_percent:.0f}% OFF)" if discount_percent else ""

        if old_price and old_price > price:
            return f"Preço: de R$ {old_price:.2f} por R$ {price:.2f}{discount}"

        return f"Preço: R$ {price:.2f}{discount}"
