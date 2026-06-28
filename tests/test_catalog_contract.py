from ofertas_bot.catalog_contract import (
    OPERATIONAL_CATALOG_FIELDNAMES,
    project_operational_catalog_row,
)
from ofertas_bot.tools.shopee_catalog_builder import _write_catalog_csv


def test_project_operational_catalog_row_keeps_only_contract_fields() -> None:
    row = {
        "itemId": 10,
        "productName": "Produto",
        "productLink": "https://example.com/product",
        "offerLink": "https://example.com/offer",
        "imageUrl": "https://example.com/image.jpg",
        "price": 100,
        "priceMax": 120,
        "sales": 50,
        "ratingStar": 4.9,
        "shopType": [2],
        "sellerCommissionRate": 0.12,
        "shopeeCommissionRate": 0.03,
        "subniches": ["teste"],
        "shopId": 999,
        "shopName": "Loja",
    }

    projected = project_operational_catalog_row(row)

    assert list(projected.keys()) == OPERATIONAL_CATALOG_FIELDNAMES
    assert "shopId" not in projected
    assert "shopName" not in projected


def test_project_operational_catalog_row_unwraps_nested_json_strings() -> None:
    row = {
        "itemId": "10",
        "productName": "Produto",
        "productLink": "https://example.com/product",
        "offerLink": "https://example.com/offer",
        "imageUrl": "https://example.com/image.jpg",
        "price": "100",
        "priceMax": "120",
        "sales": "50",
        "ratingStar": "4.9",
        "shopType": '"[2]"',
        "sellerCommissionRate": "0.12",
        "shopeeCommissionRate": "0.03",
        "subniches": '"[\\"teste\\"]"',
    }

    projected = project_operational_catalog_row(row)

    assert projected["shopType"] == [2]
    assert projected["subniches"] == ["teste"]


def test_write_catalog_csv_can_emit_operational_schema(tmp_path) -> None:
    output_path = tmp_path / "catalog.csv"
    rows = [
        project_operational_catalog_row(
            {
                "itemId": 10,
                "productName": "Produto",
                "productLink": "https://example.com/product",
                "offerLink": "https://example.com/offer",
                "imageUrl": "https://example.com/image.jpg",
                "price": 100,
                "priceMax": 120,
                "sales": 50,
                "ratingStar": 4.9,
                "shopType": [2],
                "sellerCommissionRate": 0.12,
                "shopeeCommissionRate": 0.03,
                "subniches": ["teste"],
            }
        )
    ]

    _write_catalog_csv(
        output_path,
        rows,
        fieldnames=OPERATIONAL_CATALOG_FIELDNAMES,
    )

    content = output_path.read_text(encoding="utf-8-sig")
    assert content.splitlines()[0] == ",".join(OPERATIONAL_CATALOG_FIELDNAMES)
    assert "[2]" in content
    assert '"[""teste""]"' in content


def test_write_catalog_csv_preserves_pre_serialized_contract_fields(tmp_path) -> None:
    output_path = tmp_path / "catalog.csv"
    rows = [
        {
            "itemId": 10,
            "productName": "Produto",
            "productLink": "https://example.com/product",
            "offerLink": "https://example.com/offer",
            "imageUrl": "https://example.com/image.jpg",
            "price": 100,
            "priceMax": 120,
            "sales": 50,
            "ratingStar": 4.9,
            "shopType": "[2]",
            "sellerCommissionRate": 0.12,
            "shopeeCommissionRate": 0.03,
            "subniches": "[\"teste\"]",
        }
    ]

    _write_catalog_csv(
        output_path,
        rows,
        fieldnames=OPERATIONAL_CATALOG_FIELDNAMES,
    )

    content = output_path.read_text(encoding="utf-8-sig")
    assert '"""[2]"""' not in content
    assert '"""[""' not in content
