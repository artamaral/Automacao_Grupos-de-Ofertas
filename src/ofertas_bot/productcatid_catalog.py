from __future__ import annotations

import csv
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


class ProductCatIdCatalogError(ValueError):
    """Raised when the singular productCatId catalog contract is invalid."""


@dataclass(frozen=True)
class ProductCategoryQuota:
    product_cat_id: int
    daily_quantity: int


@dataclass(frozen=True)
class ProductCatIdCandidate:
    stable_key: str
    item_id: int
    product_cat_id: int
    commercial_score: Decimal
    sales_count: int
    rating: Decimal | None


def load_product_category_quotas(path: Path) -> tuple[ProductCategoryQuota, ...]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or set(rows[0]) != {"productCatId", "daily_quantity"}:
        raise ProductCatIdCatalogError("quota matrix must contain productCatId,daily_quantity")
    quotas: list[ProductCategoryQuota] = []
    seen: set[int] = set()
    for line, row in enumerate(rows, start=2):
        try:
            product_cat_id = int(str(row["productCatId"]).strip())
            quantity = int(str(row["daily_quantity"]).strip())
        except (TypeError, ValueError) as error:
            raise ProductCatIdCatalogError(f"invalid quota at line {line}") from error
        if product_cat_id <= 0 or quantity <= 0:
            raise ProductCatIdCatalogError(f"quota values must be positive at line {line}")
        if product_cat_id in seen:
            raise ProductCatIdCatalogError(f"duplicate productCatId: {product_cat_id}")
        seen.add(product_cat_id)
        quotas.append(ProductCategoryQuota(product_cat_id, quantity))
    if len(quotas) != 46 or sum(item.daily_quantity for item in quotas) != 140:
        raise ProductCatIdCatalogError("feminino matrix must contain 46 categories totaling 140")
    return tuple(quotas)


def validate_quotas_against_category_csv(
    quotas: Iterable[ProductCategoryQuota], path: Path
) -> None:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        category_ids = {
            int(row["category_id"]) for row in csv.DictReader(handle) if row.get("category_id")
        }
    missing = sorted(
        item.product_cat_id for item in quotas if item.product_cat_id not in category_ids
    )
    if missing:
        raise ProductCatIdCatalogError(f"productCatId absent from official category CSV: {missing}")


def normalize_product_cat_id(value: Any) -> int:
    try:
        result = int(str(value).strip())
    except (TypeError, ValueError) as error:
        raise ProductCatIdCatalogError(
            "productCatId is required and must be a positive integer"
        ) from error
    if result <= 0:
        raise ProductCatIdCatalogError("productCatId is required and must be a positive integer")
    return result


def validate_no_cross_category_item_conflicts(rows: Iterable[dict[str, Any]]) -> None:
    categories_by_item: dict[int, set[int]] = defaultdict(set)
    for row in rows:
        try:
            item_id = int(str(row.get("itemId", "")).strip())
        except ValueError as error:
            raise ProductCatIdCatalogError("itemId must be a positive integer") from error
        if item_id <= 0:
            raise ProductCatIdCatalogError("itemId must be a positive integer")
        categories_by_item[item_id].add(normalize_product_cat_id(row.get("productCatId")))
    conflicts = {
        item_id: sorted(categories)
        for item_id, categories in categories_by_item.items()
        if len(categories) > 1
    }
    if conflicts:
        report = "; ".join(
            f"itemId={item_id} productCatId={categories}"
            for item_id, categories in sorted(conflicts.items())
        )
        raise ProductCatIdCatalogError(f"cross-category item conflict: {report}")


def is_rating_eligible(value: Any) -> bool:
    try:
        return value is not None and Decimal(str(value)) >= Decimal("4.5")
    except (InvalidOperation, ValueError):
        return False


def plan_by_product_category(
    candidates: Iterable[ProductCatIdCandidate], quotas: Iterable[ProductCategoryQuota]
) -> list[ProductCatIdCandidate]:
    quota_map = {item.product_cat_id: item.daily_quantity for item in quotas}
    grouped: dict[int, deque[ProductCatIdCandidate]] = defaultdict(deque)
    eligible_candidates = sorted(
        (item for item in candidates if is_rating_eligible(item.rating)),
        key=lambda item: (-item.commercial_score, -item.sales_count, item.item_id),
    )
    for candidate in eligible_candidates:
        if candidate.product_cat_id in quota_map:
            grouped[candidate.product_cat_id].append(candidate)
    selected: list[ProductCatIdCandidate] = []
    used: set[str] = set()
    shortfalls: list[tuple[int, int, int]] = []
    for product_cat_id, quantity in quota_map.items():
        category_selected: list[ProductCatIdCandidate] = []
        while grouped[product_cat_id] and len(category_selected) < quantity:
            candidate = grouped[product_cat_id].popleft()
            if candidate.stable_key not in used:
                used.add(candidate.stable_key)
                category_selected.append(candidate)
        if len(category_selected) != quantity:
            shortfalls.append((product_cat_id, quantity, len(category_selected)))
        selected.extend(category_selected)
    fallback_needed = sum(expected - actual for _, expected, actual in shortfalls)
    if fallback_needed:
        fallback_pool = [
            candidate for candidate in eligible_candidates if candidate.stable_key not in used
        ]
        if len(fallback_pool) < fallback_needed:
            details = "; ".join(
                f"productCatId={product_cat_id}: expected={expected} actual={actual}"
                for product_cat_id, expected, actual in shortfalls
            )
            raise ProductCatIdCatalogError(
                "insufficient productCatId fallback candidates: "
                f"missing={fallback_needed - len(fallback_pool)}; {details}"
            )
        selected.extend(fallback_pool[:fallback_needed])
    if len(selected) != sum(quota_map.values()):
        raise ProductCatIdCatalogError("productCatId planner did not satisfy daily total")
    return selected
