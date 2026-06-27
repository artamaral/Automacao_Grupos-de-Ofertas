from __future__ import annotations

from ofertas_bot.models import CopyBrief, RefreshChangedItem, ScoredOffer

PRODUCT_OFFER_CONTENT_TYPE = "product_offer"

DEFAULT_REQUIRED_DISCLOSURES = (
    "Informar que o link e de afiliado e pode gerar comissao.",
    "Informar que preco e disponibilidade podem mudar.",
)

DEFAULT_COPY_CONSTRAINTS = (
    "Usar somente os fatos estruturados deste brief.",
    "Nao alterar preco, desconto, marketplace, link ou sinais de confianca.",
    "Nao prometer estoque, prazo de entrega, garantia ou beneficio nao informado.",
    "Manter a mensagem curta, clara e adequada para grupo opt-in.",
    "Evitar urgencia falsa ou promessa de preco permanente.",
)

DEFAULT_FORBIDDEN_CLAIMS = (
    "preco garantido",
    "ultima chance",
    "estoque garantido",
    "entrega garantida",
    "menor preco da internet",
)


def build_copy_brief(
    scored_offer: ScoredOffer,
    *,
    refresh_iterations: int = 0,
    refresh_stability_reached: bool = True,
    refresh_changed_items: tuple[RefreshChangedItem, ...] = (),
) -> CopyBrief:
    return CopyBrief(
        content_type=PRODUCT_OFFER_CONTENT_TYPE,
        offer=scored_offer.offer,
        score=scored_offer.score,
        score_reasons=tuple(scored_offer.reasons),
        required_disclosures=DEFAULT_REQUIRED_DISCLOSURES,
        copy_constraints=DEFAULT_COPY_CONSTRAINTS,
        forbidden_claims=DEFAULT_FORBIDDEN_CLAIMS,
        refresh_iterations=refresh_iterations,
        refresh_stability_reached=refresh_stability_reached,
        refresh_changed_items=refresh_changed_items,
    )


def build_copy_briefs(
    scored_offers: list[ScoredOffer],
    *,
    refresh_iterations: int = 0,
    refresh_stability_reached: bool = True,
    refresh_changed_items: tuple[RefreshChangedItem, ...] = (),
) -> tuple[CopyBrief, ...]:
    return tuple(
        build_copy_brief(
            scored_offer,
            refresh_iterations=refresh_iterations,
            refresh_stability_reached=refresh_stability_reached,
            refresh_changed_items=refresh_changed_items,
        )
        for scored_offer in scored_offers
    )
