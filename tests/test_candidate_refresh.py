from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from ofertas_bot.candidate_refresh import (
    CandidateRefreshError,
    DiscoveryCandidate,
    ScoringCandidate,
    select_productcatid_refresh_candidates,
    select_progressive_candidates,
    select_ranked_refresh_candidates,
    select_scoring_candidates,
    snapshot_from_product_offer_response,
)
from ofertas_bot.productcatid_catalog import ProductCategoryQuota

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


def test_ranked_refresh_allocates_400_ranking_and_100_exploration() -> None:
    weights = {f"high-{index}": 2 for index in range(5)} | {
        f"low-{index}": 1 for index in range(10)
    }
    candidates: list[DiscoveryCandidate] = []
    item_id = 1
    for subniche, weight in weights.items():
        count = 50 if weight == 2 else 25
        for rank in range(1, count + 1):
            candidates.append(
                replace(
                    _candidate(item_id),
                    primary_subniche=subniche,
                    subniches=(subniche,),
                    rank_profile=item_id,
                    rank_subniche=rank,
                    commercial_score=Decimal(1000 - item_id),
                )
            )
            item_id += 1

    selected = select_ranked_refresh_candidates(
        candidates,
        limit=500,
        subniche_weights=weights,
    )

    assert len(selected) == 500
    assert sum(item.selection_bucket == "ranking" for item in selected) == 400
    assert sum(item.selection_bucket == "exploration" for item in selected) == 100
    for subniche, weight in weights.items():
        ranking_count = sum(
            item.primary_subniche == subniche and item.selection_bucket == "ranking"
            for item in selected
        )
        exploration_count = sum(
            item.primary_subniche == subniche
            and item.selection_bucket == "exploration"
            for item in selected
        )
        assert ranking_count == (40 if weight == 2 else 20)
        assert exploration_count == (10 if weight == 2 else 5)


def test_ranked_refresh_prefers_rank_over_refresh_status() -> None:
    stale = replace(
        _candidate(1),
        refresh_status="STALE",
        last_checked_at=NOW - timedelta(hours=25),
        rank_profile=1,
        rank_subniche=1,
        commercial_score=Decimal("90"),
    )
    missing = replace(
        _candidate(2),
        rank_profile=2,
        rank_subniche=2,
        commercial_score=Decimal("80"),
    )

    selected = select_ranked_refresh_candidates(
        [missing, stale],
        limit=1,
        subniche_weights={"maquiagem-olhos": 1},
        exploration_percent=0,
    )

    assert [item.item_id for item in selected] == [1]


def test_ranked_refresh_cache_hit_does_not_consume_api_slot() -> None:
    fresh = replace(
        _candidate(1),
        refresh_status="FRESH",
        last_checked_at=NOW,
        rank_profile=1,
        rank_subniche=1,
        commercial_score=Decimal("90"),
    )
    missing = replace(
        _candidate(2),
        rank_profile=2,
        rank_subniche=2,
        commercial_score=Decimal("80"),
    )

    selected = select_ranked_refresh_candidates(
        [fresh, missing],
        limit=1,
        subniche_weights={"maquiagem-olhos": 1},
        exploration_percent=0,
    )

    assert [(item.item_id, item.selection_bucket) for item in selected] == [
        (1, "cache_hit"),
        (2, "ranking"),
    ]


def test_ranked_refresh_returns_unused_exploration_to_quota() -> None:
    candidates = [
        replace(
            _candidate(item_id),
            refresh_status="STALE",
            last_checked_at=NOW - timedelta(hours=25),
            rank_profile=item_id,
            rank_subniche=item_id,
            commercial_score=Decimal(100 - item_id),
        )
        for item_id in range(1, 6)
    ]

    selected = select_ranked_refresh_candidates(
        candidates,
        limit=5,
        subniche_weights={"maquiagem-olhos": 1},
    )

    assert sum(item.selection_bucket == "ranking" for item in selected) == 4
    assert sum(item.selection_bucket == "quota_fallback" for item in selected) == 1


def test_product_offer_response_maps_only_real_contract_fields() -> None:
    response = _response(item_id=10, price="79.90")

    snapshot = snapshot_from_product_offer_response(
        response=response,
        requested_item_id=10,
        requested_product_cat_id=100350,
        checked_at=NOW,
    )

    assert snapshot is not None
    assert snapshot.item_id == 10
    assert snapshot.price == Decimal("79.90")
    assert snapshot.price_max == Decimal("99.90")
    assert snapshot.seller_commission_rate == Decimal("0.12")
    assert snapshot.shop_type_codes == (1, 4)
    assert snapshot.product_cat_ids == (100630, 100662)
    assert snapshot.product_cat_id == 100350
    assert snapshot.source_payload["request"] == {"itemId": 10, "page": 1, "limit": 1}
    assert "authorization" not in snapshot.source_payload


def test_productcatid_refresh_uses_top_score_fallback_for_category_shortfall() -> None:
    candidates = [
        replace(
            _candidate(item_id),
            product_cat_id=product_cat_id,
            rank_subniche=item_id,
            commercial_score=Decimal(100 - item_id),
        )
        for item_id, product_cat_id in enumerate(
            [100350, 100350, 100351, 100999],
            start=1,
        )
    ]
    quotas = (ProductCategoryQuota(100350, 2), ProductCategoryQuota(100351, 1))

    selected = select_productcatid_refresh_candidates(candidates, quotas=quotas)

    assert [item.product_cat_id for item in selected] == [100350, 100350, 100351]
    assert all(item.selection_bucket == "productcatid_exact" for item in selected)
    selected_with_reserve = select_productcatid_refresh_candidates(
        candidates,
        quotas=quotas,
        limit=4,
    )
    assert [item.product_cat_id for item in selected_with_reserve] == [
        100350,
        100350,
        100351,
        100999,
    ]
    assert selected_with_reserve[-1].selection_bucket == "productcatid_reserve"
    with pytest.raises(CandidateRefreshError, match="cannot be below quota total"):
        select_productcatid_refresh_candidates(candidates, quotas=quotas, limit=2)

    selected_with_fallback = select_productcatid_refresh_candidates(
        [
            replace(candidates[0], commercial_score=Decimal("10")),
            replace(candidates[3], commercial_score=Decimal("99")),
        ],
        quotas=quotas,
    )
    assert [item.product_cat_id for item in selected_with_fallback] == [100350, 100999]
    assert [item.selection_bucket for item in selected_with_fallback] == [
        "productcatid_exact",
        "top_score_fallback",
    ]

    selected_short = select_productcatid_refresh_candidates(candidates[:2], quotas=quotas)
    assert len(selected_short) == 2
    assert all(item.selection_bucket == "productcatid_exact" for item in selected_short)


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
