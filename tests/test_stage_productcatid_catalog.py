from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.supabase.import_catalog import CatalogImportError
from scripts.supabase.stage_productcatid_catalog import validate_productcatid_stage


def write_catalog(path: Path, product_cat_id: str) -> None:
    fields = [
        "itemId", "productCatId", "productName", "productLink", "offerLink", "imageUrl",
        "price", "priceMax", "sales", "ratingStar", "shopType", "sellerCommissionRate",
        "shopeeCommissionRate", "subniches",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "itemId": "1", "productCatId": product_cat_id, "productName": "Produto",
                "productLink": "https://shopee.com.br/product/1/1",
                "offerLink": "https://s.shopee.com.br/abc", "imageUrl": "https://example.com/a.jpg",
                "price": "10", "priceMax": "20", "sales": "2", "ratingStar": "4.5",
                "shopType": "[]", "sellerCommissionRate": "0.1", "shopeeCommissionRate": "0.1",
                "subniches": "[]",
            }
        )


def test_stage_validation_requires_all_matrix_categories_to_have_candidates(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.csv"
    write_catalog(catalog, "100350")

    with pytest.raises(CatalogImportError, match="matrix categories without staged candidates"):
        validate_productcatid_stage(
            catalog,
            catalog_generation="productcatid-20260830",
            matrix_path=Path("config/shopee_productcatid_quotas_feminino.csv"),
            categories_path=Path("data/shopee_product_categories.csv"),
        )


def test_stage_validation_rejects_category_outside_matrix(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.csv"
    write_catalog(catalog, "999999")

    with pytest.raises(CatalogImportError, match="outside the active feminino matrix"):
        validate_productcatid_stage(
            catalog,
            catalog_generation="productcatid-20260830",
            matrix_path=Path("config/shopee_productcatid_quotas_feminino.csv"),
            categories_path=Path("data/shopee_product_categories.csv"),
        )
