from __future__ import annotations

from ofertas_bot.group_profiles import GroupProfile
from ofertas_bot.models import Marketplace, MessageDraft, Offer, ScoredOffer

MARKETPLACE_LABELS = {
    Marketplace.AMAZON: "Amazon",
    Marketplace.SHOPEE: "Shopee",
    Marketplace.MOCK: "Oferta monitorada",
}


class CopywriterAgent:
    def create_message(self, scored_offer: ScoredOffer) -> MessageDraft:
        return self._create_message(scored_offer=scored_offer, group_profile=None)

    def create_message_for_group(
        self,
        scored_offer: ScoredOffer,
        group_profile: GroupProfile,
    ) -> MessageDraft:
        return self._create_message(
            scored_offer=scored_offer,
            group_profile=group_profile,
        )

    def _create_message(
        self,
        *,
        scored_offer: ScoredOffer,
        group_profile: GroupProfile | None,
    ) -> MessageDraft:
        offer = scored_offer.offer
        if group_profile and group_profile.max_offers_per_run <= 1:
            text = self._create_compact_text(scored_offer, group_profile)
        else:
            text = self._create_detailed_text(scored_offer, group_profile)
        return MessageDraft(offer=offer, text=text)

    def _create_detailed_text(
        self,
        scored_offer: ScoredOffer,
        group_profile: GroupProfile | None,
    ) -> str:
        offer = scored_offer.offer
        price_line = self._format_price_line(
            price=offer.price,
            old_price=offer.old_price,
            discount_percent=offer.discount_percent,
        )
        reasons = ", ".join(scored_offer.reasons[:3]) or "boa oportunidade"
        marketplace_line = self._format_marketplace_line(offer.marketplace)
        trust_line = self._format_trust_line(offer)
        shipping_line = self._format_shipping_line(offer)
        group_line = self._format_group_line(group_profile)

        return (
            f"🔥 {offer.title}\n"
            f"{group_line}"
            f"{marketplace_line}\n"
            f"{price_line}\n"
            f"{trust_line}\n"
            f"{shipping_line}\n"
            f"Destaques: {reasons}.\n"
            "Confira enquanto estiver disponível.\n"
            f"Link: {offer.url}\n\n"
            "Aviso: este é um link de afiliado; podemos receber comissão pela compra. "
            "Preço e disponibilidade podem mudar."
        )

    def _create_compact_text(
        self,
        scored_offer: ScoredOffer,
        group_profile: GroupProfile,
    ) -> str:
        offer = scored_offer.offer
        price_line = self._format_price_line(
            price=offer.price,
            old_price=offer.old_price,
            discount_percent=offer.discount_percent,
        )
        reasons = ", ".join(scored_offer.reasons[:2]) or "boa oportunidade"

        return (
            f"🔥 {offer.title}\n"
            f"Grupo: {group_profile.name}\n"
            f"{price_line}\n"
            f"Destaques: {reasons}.\n"
            f"Link: {offer.url}\n\n"
            "Aviso: link de afiliado; podemos receber comissão. "
            "Preço e disponibilidade podem mudar."
        )

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

    def _format_marketplace_line(self, marketplace: Marketplace) -> str:
        label = MARKETPLACE_LABELS.get(marketplace, marketplace.value.title())
        return f"Loja: {label}"

    def _format_trust_line(self, offer: Offer) -> str:
        parts: list[str] = []
        if offer.rating is not None:
            parts.append(f"avaliação {offer.rating:.1f}/5")
        if offer.sales_count > 0:
            parts.append(f"{offer.sales_count} vendas")
        if not parts:
            return "Sinal de confiança: oferta em análise."
        return f"Sinal de confiança: {'; '.join(parts)}."

    def _format_shipping_line(self, offer: Offer) -> str:
        if offer.is_prime_or_free_shipping:
            return "Entrega: benefício de frete destacado."
        return "Entrega: confira prazo e frete antes de comprar."

    def _format_group_line(self, group_profile: GroupProfile | None) -> str:
        if group_profile is None:
            return ""
        return f"Grupo: {group_profile.name}\n"
