from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from ofertas_bot.agents.scorer import ScorerAgent
from ofertas_bot.models import Offer, RefreshChangedItem, ScoredOffer
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.selection import SelectionResult, apply_default_selection_policy


@dataclass(frozen=True)
class OfferRefreshChange:
    offer: Offer
    changed_fields: tuple[str, ...]


@dataclass(frozen=True)
class SelectionRefreshResult:
    offers: list[Offer]
    scored_offers: list[ScoredOffer]
    selection_result: SelectionResult
    iterations: int
    stability_reached: bool
    stale_items_count: int
    changed_items: tuple[RefreshChangedItem, ...] = ()


def stabilize_selected_shopee_offers(
    *,
    offers: list[Offer],
    scorer: ScorerAgent,
    niche: str,
    catalog_source_path: Path | None,
    shopee_provider: ShopeeProvider,
    max_iterations: int = 5,
) -> SelectionRefreshResult:
    current_offers = list(offers)
    changed_items: list[RefreshChangedItem] = []

    for iteration in range(1, max_iterations + 1):
        scored_offers = scorer.score(current_offers)
        selection_result = apply_default_selection_policy(
            scored_offers,
            niche=niche,
            catalog_source_path=catalog_source_path,
        )
        refresh_changes = refresh_selected_shopee_offers(
            selected_scored_offers=selection_result.scored_offers,
            shopee_provider=shopee_provider,
        )
        changed_items.extend(
            RefreshChangedItem(
                item_id=change.offer.item_id,
                title=change.offer.title,
                refresh_iteration=iteration,
                changed_fields=change.changed_fields,
            )
            for change in refresh_changes
        )
        if not refresh_changes:
            return SelectionRefreshResult(
                offers=current_offers,
                scored_offers=scored_offers,
                selection_result=selection_result,
                iterations=iteration,
                stability_reached=True,
                stale_items_count=0,
                changed_items=tuple(changed_items),
            )
        current_offers = _apply_refresh_changes(current_offers, refresh_changes)

    scored_offers = scorer.score(current_offers)
    selection_result = apply_default_selection_policy(
        scored_offers,
        niche=niche,
        catalog_source_path=catalog_source_path,
    )
    refresh_changes = refresh_selected_shopee_offers(
        selected_scored_offers=selection_result.scored_offers,
        shopee_provider=shopee_provider,
    )
    return SelectionRefreshResult(
        offers=current_offers,
        scored_offers=scored_offers,
        selection_result=selection_result,
        iterations=max_iterations,
        stability_reached=False,
        stale_items_count=len(refresh_changes),
        changed_items=tuple(changed_items),
    )


def refresh_selected_shopee_offers(
    *,
    selected_scored_offers: list[ScoredOffer],
    shopee_provider: ShopeeProvider,
) -> list[OfferRefreshChange]:
    changes: list[OfferRefreshChange] = []
    seen_item_ids: set[int] = set()
    for scored_offer in selected_scored_offers:
        offer = scored_offer.offer
        if offer.item_id is None or offer.item_id in seen_item_ids:
            continue
        seen_item_ids.add(offer.item_id)
        change = refresh_shopee_offer_by_item_id(
            offer=offer,
            shopee_provider=shopee_provider,
        )
        if change is not None:
            changes.append(change)
    return changes


def refresh_shopee_offer_by_item_id(
    *,
    offer: Offer,
    shopee_provider: ShopeeProvider,
) -> OfferRefreshChange | None:
    if offer.item_id is None:
        return None

    response_data = shopee_provider.fetch_product_offer_raw_response(
        limit=1,
        page=1,
        item_id=offer.item_id,
    )
    nodes = response_data.get("data", {}).get("productOfferV2", {}).get("nodes", [])
    if not isinstance(nodes, list) or not nodes:
        return None

    node = nodes[0]
    changed_fields: list[str] = []
    refreshed_offer = offer

    refreshed_price = _optional_float(node.get("price"))
    if refreshed_price is not None and refreshed_price != offer.price:
        refreshed_offer = replace(refreshed_offer, price=refreshed_price)
        changed_fields.append("price")

    refreshed_commission_rate = _optional_float(node.get("commissionRate"))
    if refreshed_commission_rate is not None and refreshed_commission_rate != offer.commission_rate:
        refreshed_offer = replace(
            refreshed_offer,
            commission_rate=refreshed_commission_rate,
        )
        changed_fields.append("commission_rate")

    if not changed_fields:
        return None
    return OfferRefreshChange(
        offer=refreshed_offer,
        changed_fields=tuple(changed_fields),
    )


def _apply_refresh_changes(
    offers: list[Offer],
    refresh_changes: list[OfferRefreshChange],
) -> list[Offer]:
    change_by_item_id = {
        change.offer.item_id: change.offer
        for change in refresh_changes
        if change.offer.item_id is not None
    }
    refreshed_offers: list[Offer] = []
    for offer in offers:
        if offer.item_id is not None and offer.item_id in change_by_item_id:
            refreshed_offers.append(change_by_item_id[offer.item_id])
        else:
            refreshed_offers.append(offer)
    return refreshed_offers


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
