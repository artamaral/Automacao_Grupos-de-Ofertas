from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.productcatid_catalog import ProductCategoryQuota
from ofertas_bot.providers.shopee_graphql import (
    ShopeeGraphqlPayloadError,
    extract_shopee_offer_connection,
)

REFRESH_SOURCE = "shopee_productOfferV2"
MANUAL_CONFIRMATION_SOURCE = "manual_confirmed_unavailable"
AUTO_CONFIRMATION_SOURCE = "auto_confirmed_unavailable"
REFRESH_STATUSES = ("MISSING", "STALE", "FRESH", "UNAVAILABLE_CONFIRMED")
ATTEMPT_STATUSES = (
    "success",
    "technical_failure",
    "no_node",
    "invalid_payload",
    "confirmed_unavailable",
)

_PRODUCT_PATH_SHOP_RE = re.compile(r"/product/(\d+)/")
_ITEM_PATH_SHOP_RE = re.compile(r"(?:^|/)i\.(\d+)\.\d+(?:$|[/?])")


class CandidateRefreshError(RuntimeError):
    """Raised when a candidate refresh cannot continue safely."""


@dataclass(frozen=True)
class DiscoveryCandidate:
    catalog_item_id: int
    profile: str
    marketplace: str
    stable_key: str
    item_id: int
    product_name: str
    product_link: str
    image_url: str | None
    subniches: tuple[str, ...]
    primary_subniche: str
    refresh_status: str
    last_checked_at: datetime | None
    last_attempted_at: datetime | None
    last_attempt_status: str | None
    seller_key: str
    rank_profile: int | None = None
    rank_subniche: int | None = None
    commercial_score: Decimal | None = None
    is_eligible: bool = True
    commercial_data_source: str = "catalog"
    selection_bucket: str = ""
    product_cat_id: int | None = None


@dataclass(frozen=True)
class SnapshotInput:
    marketplace: str
    item_id: int
    checked_at: datetime
    shop_id: int | None
    product_name: str | None
    product_link: str | None
    offer_link: str | None
    image_url: str | None
    price: Decimal | None
    price_min: Decimal | None
    price_max: Decimal | None
    price_discount_rate: Decimal | None
    commission_rate: Decimal | None
    commission_amount: Decimal | None
    seller_commission_rate: Decimal | None
    shopee_commission_rate: Decimal | None
    app_exist_rate: Decimal | None
    app_new_rate: Decimal | None
    web_exist_rate: Decimal | None
    web_new_rate: Decimal | None
    sales_count: int | None
    rating: Decimal | None
    shop_type_codes: tuple[int, ...]
    product_cat_ids: tuple[int, ...]
    period_start_time: int | None
    period_end_time: int | None
    source_payload: dict[str, Any]
    product_cat_id: int | None = None


@dataclass(frozen=True)
class ScoringCandidate:
    profile: str
    marketplace: str
    stable_key: str
    item_id: int
    product_name: str
    product_link: str
    offer_link: str
    image_url: str | None
    subniches: tuple[str, ...]
    primary_subniche: str
    shop_id: int | None
    price: Decimal
    reference_price: Decimal | None
    commission_rate: Decimal
    sales_count: int
    rating: Decimal | None
    shop_type_code: int | None
    last_checked_at: datetime | None
    cooldown_until: datetime | None

    @property
    def seller_key(self) -> str:
        if self.shop_id is not None:
            return f"shop:{self.shop_id}"
        return seller_key_from_link(self.product_link, self.item_id)

    def to_offer(self) -> Offer:
        return Offer(
            marketplace=Marketplace(self.marketplace),
            title=self.product_name,
            url=self.offer_link,
            image_url=self.image_url,
            price=float(self.price),
            old_price=float(self.reference_price) if self.reference_price is not None else None,
            commission_rate=float(self.commission_rate),
            sales_count=self.sales_count,
            rating=float(self.rating) if self.rating is not None else None,
            niche=self.profile,
            item_id=self.item_id,
            is_prime_or_free_shipping=None,
            shop_type_code=self.shop_type_code,
            cooldown_until=(
                self.cooldown_until.isoformat() if self.cooldown_until is not None else None
            ),
        )


def select_progressive_candidates(
    candidates: Sequence[DiscoveryCandidate],
    *,
    limit: int,
    subniche_weights: Mapping[str, int],
) -> list[DiscoveryCandidate]:
    if limit <= 0:
        raise CandidateRefreshError("candidate limit must be positive")

    unique_candidates = _deduplicate_candidates(candidates)
    quotas = scale_subniche_quotas(limit=limit, weights=subniche_weights)
    selected: list[DiscoveryCandidate] = []
    selected_ids: set[tuple[str, int]] = set()

    for priority in range(4):
        bucket = sorted(
            (item for item in unique_candidates if _priority(item) == priority),
            key=_priority_sort_key,
        )
        if not bucket:
            continue

        for subniche in subniche_weights:
            remaining = quotas.get(subniche, 0) - sum(
                item.primary_subniche == subniche for item in selected
            )
            if remaining <= 0:
                continue
            matching = [
                item
                for item in bucket
                if item.primary_subniche == subniche
                and (item.marketplace, item.item_id) not in selected_ids
            ]
            _extend_diverse(
                selected,
                selected_ids,
                matching,
                count=min(remaining, limit - len(selected)),
            )
            if len(selected) >= limit:
                return selected

        remaining_bucket = [
            item
            for item in bucket
            if (item.marketplace, item.item_id) not in selected_ids
        ]
        _extend_diverse(
            selected,
            selected_ids,
            remaining_bucket,
            count=limit - len(selected),
        )
        if len(selected) >= limit:
            break

    return selected


def select_ranked_refresh_candidates(
    candidates: Sequence[DiscoveryCandidate],
    *,
    limit: int,
    subniche_weights: Mapping[str, int],
    exploration_percent: int = 20,
) -> list[DiscoveryCandidate]:
    if limit <= 0:
        raise CandidateRefreshError("candidate limit must be positive")
    if not 0 <= exploration_percent <= 100:
        raise CandidateRefreshError("exploration percent must be between 0 and 100")

    eligible = [
        item
        for item in _deduplicate_candidates(candidates)
        if (
            item.is_eligible
            and item.rank_subniche is not None
            and item.refresh_status != "UNAVAILABLE_CONFIRMED"
        )
    ]
    ranking_limit = limit * (100 - exploration_percent) // 100
    exploration_limit = limit - ranking_limit
    selected: list[DiscoveryCandidate] = []
    selected_ids: set[tuple[str, int]] = set()
    cache_hits: list[DiscoveryCandidate] = []
    cache_ids: set[tuple[str, int]] = set()

    _select_ranked_by_quota(
        eligible,
        limit=ranking_limit,
        subniche_weights=subniche_weights,
        selected=selected,
        selected_ids=selected_ids,
        cache_hits=cache_hits,
        cache_ids=cache_ids,
        bucket="ranking",
    )

    exploration_pool = [
        item
        for item in eligible
        if item.refresh_status == "MISSING"
        and item.last_attempted_at is None
        and (item.marketplace, item.item_id) not in selected_ids
    ]
    _select_ranked_by_quota(
        exploration_pool,
        limit=exploration_limit,
        subniche_weights=subniche_weights,
        selected=selected,
        selected_ids=selected_ids,
        cache_hits=cache_hits,
        cache_ids=cache_ids,
        bucket="exploration",
    )

    fallback_limit = limit - len(selected)
    if fallback_limit > 0:
        fallback_pool = [
            item
            for item in eligible
            if item.refresh_status in {"MISSING", "STALE"}
            and (item.marketplace, item.item_id) not in selected_ids
        ]
        _select_ranked_by_quota(
            fallback_pool,
            limit=fallback_limit,
            subniche_weights=subniche_weights,
            selected=selected,
            selected_ids=selected_ids,
            cache_hits=cache_hits,
            cache_ids=cache_ids,
            bucket="quota_fallback",
        )

    return cache_hits + selected


def select_productcatid_refresh_candidates(
    candidates: Sequence[DiscoveryCandidate],
    *,
    quotas: Sequence[ProductCategoryQuota],
) -> list[DiscoveryCandidate]:
    """Select the exact category coverage required before productCatId planning."""
    allowed = {quota.product_cat_id: quota.daily_quantity for quota in quotas}
    grouped: dict[int, list[DiscoveryCandidate]] = defaultdict(list)
    for candidate in _deduplicate_candidates(candidates):
        if (
            candidate.product_cat_id in allowed
            and candidate.is_eligible
            and candidate.refresh_status != "UNAVAILABLE_CONFIRMED"
        ):
            grouped[candidate.product_cat_id].append(candidate)

    selected: list[DiscoveryCandidate] = []
    selected_ids: set[tuple[str, int]] = set()
    for product_cat_id, quota in allowed.items():
        category_candidates = sorted(
            grouped[product_cat_id],
            key=lambda item: (
                _priority(item),
                item.rank_subniche or 2**63 - 1,
                -(item.commercial_score or Decimal("0")),
                item.item_id,
            ),
        )
        category_selected: list[DiscoveryCandidate] = []
        for candidate in category_candidates:
            key = (candidate.marketplace, candidate.item_id)
            if key in selected_ids:
                continue
            selected_ids.add(key)
            category_selected.append(
                replace(candidate, selection_bucket="productcatid_exact")
            )
            if len(category_selected) == quota:
                break
        if len(category_selected) != quota:
            raise CandidateRefreshError(
                "insufficient refresh candidates for productCatId="
                f"{product_cat_id}: expected={quota} actual={len(category_selected)}"
            )
        selected.extend(category_selected)
    return selected


def select_scoring_candidates(
    candidates: Sequence[ScoringCandidate],
    *,
    limit: int,
    subniche_weights: Mapping[str, int],
) -> list[ScoringCandidate]:
    if limit <= 0:
        raise CandidateRefreshError("scoring limit must be positive")
    discovery_rows = [
        DiscoveryCandidate(
            catalog_item_id=index,
            profile=item.profile,
            marketplace=item.marketplace,
            stable_key=item.stable_key,
            item_id=item.item_id,
            product_name=item.product_name,
            product_link=item.product_link,
            image_url=item.image_url,
            subniches=item.subniches,
            primary_subniche=item.primary_subniche,
            refresh_status="FRESH",
            last_checked_at=item.last_checked_at,
            last_attempted_at=None,
            last_attempt_status=None,
            seller_key=item.seller_key,
        )
        for index, item in enumerate(candidates)
    ]
    selected_rows = select_progressive_candidates(
        discovery_rows,
        limit=limit,
        subniche_weights=subniche_weights,
    )
    by_item = {(item.marketplace, item.item_id): item for item in candidates}
    return [by_item[(item.marketplace, item.item_id)] for item in selected_rows]


def snapshot_from_product_offer_response(
    *,
    response: Mapping[str, Any],
    requested_item_id: int,
    requested_product_cat_id: int | None = None,
    checked_at: datetime | None = None,
) -> SnapshotInput | None:
    try:
        connection = extract_shopee_offer_connection(
            dict(response),
            root_field="productOfferV2",
        )
    except ShopeeGraphqlPayloadError as error:
        raise CandidateRefreshError(str(error)) from error
    nodes = connection["nodes"]
    if not nodes:
        return None
    node = nodes[0]
    if not isinstance(node, Mapping):
        raise CandidateRefreshError("productOfferV2 node is not an object")

    item_id = _required_positive_int(node.get("itemId"), "itemId")
    if item_id != requested_item_id:
        raise CandidateRefreshError(
            f"productOfferV2 returned itemId {item_id} for requested itemId {requested_item_id}"
        )

    resolved_checked_at = checked_at or datetime.now(UTC)
    page_info = connection.get("pageInfo")
    source_payload = {
        "request": {"itemId": requested_item_id, "page": 1, "limit": 1},
        "node": dict(node),
        "pageInfo": dict(page_info) if isinstance(page_info, Mapping) else {},
    }
    return SnapshotInput(
        marketplace="shopee",
        item_id=item_id,
        checked_at=resolved_checked_at,
        shop_id=_optional_positive_int(node.get("shopId")),
        product_name=_optional_text(node.get("productName")),
        product_link=_optional_text(node.get("productLink")),
        offer_link=_optional_text(node.get("offerLink")),
        image_url=_optional_text(node.get("imageUrl")),
        price=_optional_decimal(node.get("price")),
        price_min=_optional_decimal(node.get("priceMin")),
        price_max=_optional_decimal(node.get("priceMax")),
        price_discount_rate=_optional_decimal(node.get("priceDiscountRate")),
        commission_rate=_optional_decimal(node.get("commissionRate")),
        commission_amount=_optional_decimal(node.get("commission")),
        seller_commission_rate=_optional_decimal(node.get("sellerCommissionRate")),
        shopee_commission_rate=_optional_decimal(node.get("shopeeCommissionRate")),
        app_exist_rate=_optional_decimal(node.get("appExistRate")),
        app_new_rate=_optional_decimal(node.get("appNewRate")),
        web_exist_rate=_optional_decimal(node.get("webExistRate")),
        web_new_rate=_optional_decimal(node.get("webNewRate")),
        sales_count=_optional_nonnegative_int(node.get("sales")),
        rating=_optional_decimal(node.get("ratingStar")),
        shop_type_codes=_int_tuple(node.get("shopType")),
        product_cat_ids=_int_tuple(node.get("productCatIds")),
        period_start_time=_optional_int(node.get("periodStartTime")),
        period_end_time=_optional_int(node.get("periodEndTime")),
        source_payload=source_payload,
        product_cat_id=requested_product_cat_id,
    )


def seller_key_from_link(product_link: str, item_id: int) -> str:
    for pattern in (_PRODUCT_PATH_SHOP_RE, _ITEM_PATH_SHOP_RE):
        match = pattern.search(product_link)
        if match:
            return f"shop:{match.group(1)}"
    return f"item:{item_id}"


def _priority(candidate: DiscoveryCandidate) -> int:
    if candidate.refresh_status == "MISSING":
        return 0 if candidate.last_attempted_at is None else 1
    if candidate.refresh_status == "STALE":
        return 2
    if candidate.refresh_status == "FRESH":
        return 3
    if candidate.refresh_status == "UNAVAILABLE_CONFIRMED":
        return 4
    raise CandidateRefreshError(f"invalid refresh status: {candidate.refresh_status}")


def _priority_sort_key(candidate: DiscoveryCandidate) -> tuple[datetime, int]:
    timestamp = candidate.last_attempted_at
    if candidate.refresh_status in {"STALE", "FRESH"}:
        timestamp = candidate.last_checked_at
    return timestamp or datetime.min.replace(tzinfo=UTC), candidate.item_id


def _rank_sort_key(candidate: DiscoveryCandidate) -> tuple[int, Decimal, int]:
    return (
        candidate.rank_subniche or 2**63 - 1,
        -(candidate.commercial_score or Decimal("0")),
        candidate.item_id,
    )


def _select_ranked_by_quota(
    candidates: Sequence[DiscoveryCandidate],
    *,
    limit: int,
    subniche_weights: Mapping[str, int],
    selected: list[DiscoveryCandidate],
    selected_ids: set[tuple[str, int]],
    cache_hits: list[DiscoveryCandidate],
    cache_ids: set[tuple[str, int]],
    bucket: str,
) -> None:
    if limit <= 0:
        return
    quotas = scale_subniche_quotas(limit=limit, weights=subniche_weights)
    start_count = len(selected)

    for subniche in subniche_weights:
        matching = sorted(
            (item for item in candidates if item.primary_subniche == subniche),
            key=_rank_sort_key,
        )
        _consume_ranked_candidates(
            matching,
            count=quotas.get(subniche, 0),
            selected=selected,
            selected_ids=selected_ids,
            cache_hits=cache_hits,
            cache_ids=cache_ids,
            bucket=bucket,
        )

    remaining = limit - (len(selected) - start_count)
    if remaining <= 0:
        return
    global_remaining = sorted(
        (
            item
            for item in candidates
            if (item.marketplace, item.item_id) not in selected_ids
        ),
        key=lambda item: (
            item.rank_profile or 2**63 - 1,
            _rank_sort_key(item),
        ),
    )
    _consume_ranked_candidates(
        global_remaining,
        count=remaining,
        selected=selected,
        selected_ids=selected_ids,
        cache_hits=cache_hits,
        cache_ids=cache_ids,
        bucket=bucket,
    )


def _consume_ranked_candidates(
    candidates: Sequence[DiscoveryCandidate],
    *,
    count: int,
    selected: list[DiscoveryCandidate],
    selected_ids: set[tuple[str, int]],
    cache_hits: list[DiscoveryCandidate],
    cache_ids: set[tuple[str, int]],
    bucket: str,
) -> None:
    if count <= 0:
        return
    ordered = _diverse_order(candidates)
    added = 0
    for candidate in ordered:
        key = (candidate.marketplace, candidate.item_id)
        if key in selected_ids:
            continue
        if candidate.refresh_status == "FRESH":
            if key not in cache_ids:
                cache_hits.append(replace(candidate, selection_bucket="cache_hit"))
                cache_ids.add(key)
            continue
        selected.append(replace(candidate, selection_bucket=bucket))
        selected_ids.add(key)
        added += 1
        if added >= count:
            return


def _deduplicate_candidates(
    candidates: Sequence[DiscoveryCandidate],
) -> list[DiscoveryCandidate]:
    by_item: dict[tuple[str, int], DiscoveryCandidate] = {}
    for candidate in candidates:
        key = (candidate.marketplace, candidate.item_id)
        current = by_item.get(key)
        if current is None or _priority_sort_key(candidate) < _priority_sort_key(current):
            by_item[key] = candidate
    return list(by_item.values())


def scale_subniche_quotas(*, limit: int, weights: Mapping[str, int]) -> dict[str, int]:
    if not weights:
        return {}
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise CandidateRefreshError("subniche weights must be positive")
    raw = {key: Decimal(limit * weight) / Decimal(total_weight) for key, weight in weights.items()}
    quotas = {key: int(value) for key, value in raw.items()}
    remaining = limit - sum(quotas.values())
    ordered_remainders = sorted(
        weights,
        key=lambda key: (raw[key] - quotas[key], weights[key]),
        reverse=True,
    )
    for key in ordered_remainders[:remaining]:
        quotas[key] += 1
    return quotas


def _extend_diverse(
    selected: list[DiscoveryCandidate],
    selected_ids: set[tuple[str, int]],
    candidates: Iterable[DiscoveryCandidate],
    *,
    count: int,
) -> None:
    if count <= 0:
        return
    seller_groups: dict[str, list[DiscoveryCandidate]] = defaultdict(list)
    seller_order: list[str] = []
    for candidate in candidates:
        if candidate.seller_key not in seller_groups:
            seller_order.append(candidate.seller_key)
        seller_groups[candidate.seller_key].append(candidate)

    round_index = 0
    added = 0
    while added < count:
        added_this_round = 0
        for seller_key in seller_order:
            group = seller_groups[seller_key]
            if round_index >= len(group):
                continue
            candidate = group[round_index]
            key = (candidate.marketplace, candidate.item_id)
            if key in selected_ids:
                continue
            selected.append(candidate)
            selected_ids.add(key)
            added += 1
            added_this_round += 1
            if added >= count:
                return
        if added_this_round == 0:
            return
        round_index += 1


def _diverse_order(candidates: Iterable[DiscoveryCandidate]) -> list[DiscoveryCandidate]:
    ordered: list[DiscoveryCandidate] = []
    selected_ids: set[tuple[str, int]] = set()
    candidate_list = list(candidates)
    _extend_diverse(
        ordered,
        selected_ids,
        candidate_list,
        count=len(candidate_list),
    )
    return ordered


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def _optional_positive_int(value: object) -> int | None:
    parsed = _optional_int(value)
    return parsed if parsed is not None and parsed > 0 else None


def _optional_nonnegative_int(value: object) -> int | None:
    parsed = _optional_int(value)
    return parsed if parsed is not None and parsed >= 0 else None


def _required_positive_int(value: object, field_name: str) -> int:
    parsed = _optional_positive_int(value)
    if parsed is None:
        raise CandidateRefreshError(f"{field_name} missing or invalid")
    return parsed


def _int_tuple(value: object) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    parsed: list[int] = []
    for item in value:
        number = _optional_int(item)
        if number is not None:
            parsed.append(number)
    return tuple(parsed)
