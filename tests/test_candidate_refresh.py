from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from ofertas_bot.candidate_refresh import (
    CandidateRefreshError,
    DiscoveryCandidate,
    ScoringCandidate,
    select_progressive_candidates,
    select_scoring_candidates,
    snapshot_from_product_offer_response,
)

NOW = datetime(2026, 8, 11, 12, tzinfo=UTC)


def test_progressive_queue_moves_to_next_missing_items_after_success() -> None:
    candidates = [_candidate(item_id) for item_id in range(1, 5)]

    first = select_progressive_candidates(
        candidates,
        limit=2,
        subniche_weights={"maquiagem-olhos": 1},
    )
    refreshed = [
        replace(
            candidate,
            refresh_status="FRESH",
            last_checked_at=NOW,
            last_attempted_at=NOW,
            last_attempt_status="success",
        )
        if candidate.item_id in {1, 2}
        else candidate
        for candidate in candidates
    ]
    second = select_progressive_candidates(
        refreshed,
        limit=2,
        subniche_weights={"maquiagem-olhos": 1},
    )

    assert [item.item_id for item in first] == [1, 2]
    assert [item.item_id for item in second] == [3, 4]


def test_never_attempted_missing_precedes_failed_missing() -> None:
    failed = replace(
        _candidate(1),
        last_attempted_at=NOW - timedelta(hours=1),
        last_attempt_status="technical_failure",
    )

    selected = select_progressive_candidates(
        [failed, _candidate(2)],
        limit=1,
        subniche_weights={"maquiagem-olhos": 1},
    )

    assert [item.item_id for item in selected] == [2]


def test_stale_precedes_fresh_and_fresh_only_fills_remaining_slots() -> None:
    stale = replace(
        _candidate(2),
        refresh_status="STALE",
        last_checked_at=NOW - timedelta(hours=24),
    )
    fresh = replace(
        _candidate(3),
        refresh_status="FRESH",
        last_checked_at=NOW - timedelta(hours=1),
    )

    selected = select_progressive_candidates(
        [fresh, stale, _candidate(1)],
        limit=3,
        subniche_weights={"maquiagem-olhos": 1},
    )

    assert [item.item_id for item in selected] == [1, 2, 3]


def test_queue_applies_seller_diversity_in_successive_passes() -> None:
    candidates = [
        replace(_candidate(1), seller_key="shop:10"),
        replace(_candidate(2), seller_key="shop:10"),
        replace(_candidate(3), seller_key="shop:20"),
    ]

    selected = select_progressive_candidates(
        candidates,
        limit=3,
        subniche_weights={"maquiagem-olhos": 1},
    )

    assert [item.item_id for item in selected] == [1, 3, 2]


def test_product_offer_response_maps_only_real_contract_fields() -> None:
    response = _response(item_id=10, price="79.90")

    snapshot = snapshot_from_product_offer_response(
        response=response,
        requested_item_id=10,
        checked_at=NOW,
    )

    assert snapshot is not None
    assert snapshot.item_id == 10
    assert snapshot.price == Decimal("79.90")
    assert snapshot.price_max == Decimal("99.90")
    assert snapshot.seller_commission_rate == Decimal("0.12")
    assert snapshot.shop_type_codes == (1, 4)
    assert snapshot.product_cat_ids == (100630, 100662)
    assert snapshot.source_payload["request"] == {"itemId": 10, "page": 1, "limit": 1}
    assert "authorization" not in snapshot.source_payload


def test_product_offer_response_without_node_is_inconclusive() -> None:
    response = {"data": {"productOfferV2": {"nodes": [], "pageInfo": {"page": 1}}}}

    assert (
        snapshot_from_product_offer_response(
            response=response,
            requested_item_id=10,
            checked_at=NOW,
        )
        is None
    )


def test_product_offer_response_rejects_mismatched_item() -> None:
    with pytest.raises(CandidateRefreshError, match="returned itemId 11"):
        snapshot_from_product_offer_response(
            response=_response(item_id=11),
            requested_item_id=10,
            checked_at=NOW,
        )


def test_product_offer_response_reuses_graphql_error_contract() -> None:
    response = {
        "errors": [
            {
                "message": "invalid item",
                "extensions": {"code": 4001},
            }
        ]
    }

    with pytest.raises(CandidateRefreshError, match="invalid item"):
        snapshot_from_product_offer_response(
            response=response,
            requested_item_id=10,
            checked_at=NOW,
        )


def test_scoring_shaping_uses_quotas_without_commercial_sorting() -> None:
    candidates = [
        _scoring_candidate(1, "maquiagem-olhos", price="20"),
        _scoring_candidate(2, "maquiagem-labios", price="999"),
        _scoring_candidate(3, "maquiagem-olhos", price="10"),
    ]

    selected = select_scoring_candidates(
        candidates,
        limit=2,
        subniche_weights={"maquiagem-olhos": 1, "maquiagem-labios": 1},
    )

    assert [item.item_id for item in selected] == [1, 2]


def _candidate(item_id: int) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        catalog_item_id=item_id,
        profile="feminino",
        marketplace="shopee",
        stable_key=f"key-{item_id}",
        item_id=item_id,
        product_name=f"Produto {item_id}",
        product_link=f"https://shopee.com.br/product/{item_id}/{item_id}",
        image_url=None,
        subniches=("maquiagem-olhos",),
        primary_subniche="maquiagem-olhos",
        refresh_status="MISSING",
        last_checked_at=None,
        last_attempted_at=None,
        last_attempt_status=None,
        seller_key=f"shop:{item_id}",
    )


def _scoring_candidate(item_id: int, subniche: str, *, price: str) -> ScoringCandidate:
    return ScoringCandidate(
        profile="feminino",
        marketplace="shopee",
        stable_key=f"key-{item_id}",
        item_id=item_id,
        product_name=f"Produto {item_id}",
        product_link=f"https://shopee.com.br/product/{item_id}/{item_id}",
        offer_link=f"https://s.shopee.com.br/{item_id}",
        image_url=None,
        subniches=(subniche,),
        primary_subniche=subniche,
        shop_id=item_id,
        price=Decimal(price),
        reference_price=Decimal("1000"),
        commission_rate=Decimal("0.1"),
        sales_count=100,
        rating=Decimal("4.9"),
        shop_type_code=1,
        last_checked_at=NOW,
        cooldown_until=None,
    )


def _response(item_id: int, *, price: str = "79.90") -> dict[str, object]:
    return {
        "data": {
            "productOfferV2": {
                "nodes": [
                    {
                        "itemId": item_id,
                        "shopId": 99,
                        "productName": "Produto atual",
                        "productLink": f"https://shopee.com.br/product/99/{item_id}",
                        "offerLink": f"https://s.shopee.com.br/{item_id}",
                        "imageUrl": "https://img.example/item.jpg",
                        "price": price,
                        "priceMin": price,
                        "priceMax": "99.90",
                        "priceDiscountRate": 20,
                        "commissionRate": "0.12",
                        "commission": "9.59",
                        "sellerCommissionRate": "0.12",
                        "shopeeCommissionRate": "0",
                        "sales": 1000,
                        "ratingStar": "4.9",
                        "shopType": [1, 4],
                        "productCatIds": [100630, 100662],
                    }
                ],
                "pageInfo": {"page": 1, "limit": 1, "hasNextPage": False},
            }
        }
    }
