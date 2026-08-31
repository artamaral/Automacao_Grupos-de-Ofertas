from decimal import Decimal
from pathlib import Path

import pytest

from ofertas_bot.productcatid_catalog import (
    ProductCategoryQuota,
    ProductCatIdCandidate,
    ProductCatIdCatalogError,
    is_rating_eligible,
    load_product_category_quotas,
    plan_by_product_category,
    validate_no_cross_category_item_conflicts,
    validate_quotas_against_category_csv,
)

MATRIX = Path("config/shopee_productcatid_quotas_feminino.csv")


def test_feminino_matrix_is_complete_and_matches_official_taxonomy() -> None:
    quotas = load_product_category_quotas(MATRIX)
    assert len(quotas) == 46
    assert sum(item.daily_quantity for item in quotas) == 140
    validate_quotas_against_category_csv(quotas, Path("data/shopee_product_categories.csv"))


def test_rating_floor_accepts_4_5_and_rejects_null_or_lower() -> None:
    assert is_rating_eligible("4.5")
    assert not is_rating_eligible("4.49")
    assert not is_rating_eligible(None)


def test_cross_category_item_is_blocking() -> None:
    with pytest.raises(ProductCatIdCatalogError, match="cross-category"):
        validate_no_cross_category_item_conflicts(
            [
                {"itemId": "10", "productCatId": "100350"},
                {"itemId": "10", "productCatId": "100351"},
            ]
        )


def test_planner_fills_productcatid_shortfall_with_top_score_fallback() -> None:
    quotas = (ProductCategoryQuota(1, 2), ProductCategoryQuota(2, 1))
    candidates = [
        ProductCatIdCandidate(str(index), index, category, Decimal("10"), 20, Decimal("4.5"))
        for index, category in ((1, 1), (2, 1), (3, 3))
    ]
    assert [item.product_cat_id for item in plan_by_product_category(candidates, quotas)] == [
        1,
        1,
        3,
    ]
    with pytest.raises(ProductCatIdCatalogError, match="insufficient"):
        plan_by_product_category(candidates[:2], quotas)
