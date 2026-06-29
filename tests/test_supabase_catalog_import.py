import csv
from pathlib import Path

import pytest

from scripts.supabase.import_catalog import (
    CatalogImportError,
    stable_offer_key,
    validate_catalog,
)

FIELDNAMES = [
    "itemId",
    "productName",
    "productLink",
    "offerLink",
    "imageUrl",
    "price",
    "priceMax",
    "sales",
    "ratingStar",
    "shopType",
    "sellerCommissionRate",
    "shopeeCommissionRate",
    "subniches",
]


def write_catalog(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def make_row(*, item_id: str = "123", rating: str = "4.8") -> dict[str, str]:
    return {
        "itemId": item_id,
        "productName": "Produto teste",
        "productLink": f"https://shopee.com.br/product/1/{item_id}",
        "offerLink": f"https://s.shopee.com.br/{item_id}?tracking=abc",
        "imageUrl": "https://example.com/image.jpg",
        "price": "70",
        "priceMax": "100",
        "sales": "250",
        "ratingStar": rating,
        "shopType": "[2]",
        "sellerCommissionRate": "0.05",
        "shopeeCommissionRate": "0.02",
        "subniches": '["teste"]',
    }


def test_validate_catalog_accepts_operational_contract(tmp_path: Path) -> None:
    path = tmp_path / "catalog.csv"
    write_catalog(path, [make_row()])

    validation = validate_catalog(path, profile="feminino", marketplace="shopee")

    assert validation.row_count == 1
    assert str(validation.min_rating) == "4.8"
    assert validation.subniche_count == 1
    assert validation.summary()["contract"] == "clean_catalog_rating_4_8_plus_v1"


def test_validate_catalog_rejects_rating_below_operational_cut(tmp_path: Path) -> None:
    path = tmp_path / "catalog.csv"
    write_catalog(path, [make_row(rating="4.7")])

    with pytest.raises(CatalogImportError, match="rating below 4.8"):
        validate_catalog(path, profile="feminino", marketplace="shopee")


def test_validate_catalog_rejects_duplicate_item_id(tmp_path: Path) -> None:
    path = tmp_path / "catalog.csv"
    write_catalog(path, [make_row(), make_row()])

    with pytest.raises(CatalogImportError, match="duplicate itemId"):
        validate_catalog(path, profile="feminino", marketplace="shopee")


def test_stable_offer_key_ignores_query_parameters() -> None:
    first = stable_offer_key("shopee", "https://s.shopee.com.br/abc?one=1")
    second = stable_offer_key("shopee", "https://s.shopee.com.br/abc?two=2")

    assert first == second
