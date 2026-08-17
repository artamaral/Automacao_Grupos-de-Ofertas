import csv
import json
from pathlib import Path
from typing import Any

from ofertas_bot.catalog_contract import OPERATIONAL_CATALOG_FIELDNAMES
from ofertas_bot.tools.refresh_catalog_prices import refresh_catalog_prices


class FakeShopeeProvider:
    def __init__(self, responses: dict[int, dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[int] = []

    def fetch_product_offer_raw_response(
        self,
        *,
        limit: int,
        page: int = 1,
        item_id: int | None = None,
        **_: object,
    ) -> dict[str, Any]:
        assert limit == 1
        assert page == 1
        assert item_id is not None
        self.calls.append(item_id)
        return self.responses[item_id]


def test_refresh_catalog_prices_writes_updated_candidate_and_diff(tmp_path: Path) -> None:
    catalog_path = _write_catalog(
        tmp_path,
        [
            {
                "itemId": "1",
                "productName": "Produto antigo",
                "productLink": "https://example.com/p1",
                "offerLink": "https://example.com/o1",
                "imageUrl": "https://example.com/i1.jpg",
                "price": "100",
                "priceMax": "120",
                "sales": "10",
                "ratingStar": "4.9",
                "shopType": "[2]",
                "sellerCommissionRate": "0.05",
                "shopeeCommissionRate": "0.02",
                "subniches": '["maquiagem"]',
            }
        ],
    )
    provider = FakeShopeeProvider(
        {
            1: _response(
                {
                    "itemId": 1,
                    "productName": "Produto novo",
                    "productLink": "https://example.com/p1-new",
                    "offerLink": "https://example.com/o1-new",
                    "imageUrl": "https://example.com/i1-new.jpg",
                    "price": "80",
                    "priceMax": "160",
                    "sales": "15",
                    "ratingStar": "5.0",
                    "shopType": [1],
                    "sellerCommissionRate": "0.08",
                    "shopeeCommissionRate": "0.03",
                }
            )
        }
    )

    result = refresh_catalog_prices(
        profile_slug="feminino",
        catalog_file=catalog_path,
        output_base_dir=tmp_path / "out",
        run_id="run-1",
        provider=provider,
    )

    candidate_rows = _read_csv(result.paths.candidate_catalog)
    diff_rows = _read_csv(result.paths.price_diff)
    report = json.loads(result.paths.refresh_report.read_text(encoding="utf-8"))

    assert candidate_rows[0]["productName"] == "Produto novo"
    assert candidate_rows[0]["price"] == "80"
    assert candidate_rows[0]["priceMax"] == "160"
    assert candidate_rows[0]["subniches"] == '["maquiagem"]'
    assert diff_rows[0]["price_before"] == "100"
    assert diff_rows[0]["price_after"] == "80"
    assert diff_rows[0]["discount_percent_after"] == "50.00"
    assert "price" in diff_rows[0]["changed_fields"]
    assert report["summary"]["updated_rows"] == 1
    assert report["summary"]["candidate_rows"] == 1


def test_refresh_catalog_prices_excludes_item_without_return(tmp_path: Path) -> None:
    catalog_path = _write_catalog(
        tmp_path,
        [
            _catalog_row(item_id="1", product_name="Produto A"),
            _catalog_row(item_id="2", product_name="Produto B"),
        ],
    )
    provider = FakeShopeeProvider(
        {
            1: _response({"itemId": 1, "price": "90", "sales": "3"}),
            2: _response_none(),
        }
    )

    result = refresh_catalog_prices(
        profile_slug="feminino",
        catalog_file=catalog_path,
        output_base_dir=tmp_path / "out",
        run_id="run-1",
        provider=provider,
    )

    candidate_rows = _read_csv(result.paths.candidate_catalog)
    unresolved_rows = _read_csv(result.paths.unresolved_items)

    assert [row["itemId"] for row in candidate_rows] == ["1"]
    assert unresolved_rows[0]["itemId"] == "2"
    assert unresolved_rows[0]["reason"] == "no_return"


def test_refresh_catalog_prices_excludes_refreshed_rating_below_contract(
    tmp_path: Path,
) -> None:
    catalog_path = _write_catalog(tmp_path, [_catalog_row(item_id="1", product_name="Produto")])
    provider = FakeShopeeProvider(
        {
            1: _response(
                {
                    "itemId": 1,
                    "price": "90",
                    "sales": "3",
                    "ratingStar": "4.5",
                }
            )
        }
    )

    result = refresh_catalog_prices(
        profile_slug="feminino",
        catalog_file=catalog_path,
        output_base_dir=tmp_path / "out",
        run_id="run-1",
        provider=provider,
    )

    candidate_rows = _read_csv(result.paths.candidate_catalog)
    unresolved_rows = _read_csv(result.paths.unresolved_items)
    report = json.loads(result.paths.refresh_report.read_text(encoding="utf-8"))

    assert candidate_rows == []
    assert unresolved_rows[0]["reason"] == "rating_below_4_8"
    assert report["summary"]["rating_below_4_8_rows"] == 1


def test_refresh_catalog_prices_keeps_unchanged_item_and_reports_unchanged(
    tmp_path: Path,
) -> None:
    catalog_path = _write_catalog(tmp_path, [_catalog_row(item_id="1", product_name="Produto")])
    provider = FakeShopeeProvider(
        {
            1: _response(
                {
                    "itemId": 1,
                    "productName": "Produto",
                    "productLink": "https://example.com/p1",
                    "offerLink": "https://example.com/o1",
                    "imageUrl": "https://example.com/i1.jpg",
                    "price": "100",
                    "priceMax": "120",
                    "sales": "2",
                    "ratingStar": "4.9",
                    "shopType": [2],
                    "sellerCommissionRate": "0.05",
                    "shopeeCommissionRate": "0.02",
                }
            )
        }
    )

    result = refresh_catalog_prices(
        profile_slug="feminino",
        catalog_file=catalog_path,
        output_base_dir=tmp_path / "out",
        run_id="run-1",
        provider=provider,
    )

    report = json.loads(result.paths.refresh_report.read_text(encoding="utf-8"))
    diff_rows = _read_csv(result.paths.price_diff)

    assert report["summary"]["unchanged_rows"] == 1
    assert diff_rows[0]["changed_fields"] == ""


def test_refresh_catalog_prices_limit_processes_only_first_rows(tmp_path: Path) -> None:
    catalog_path = _write_catalog(
        tmp_path,
        [
            _catalog_row(item_id="1", product_name="Produto A"),
            _catalog_row(item_id="2", product_name="Produto B"),
        ],
    )
    provider = FakeShopeeProvider(
        {
            1: _response({"itemId": 1, "price": "90", "sales": "3"}),
            2: _response({"itemId": 2, "price": "80", "sales": "4"}),
        }
    )

    result = refresh_catalog_prices(
        profile_slug="feminino",
        catalog_file=catalog_path,
        output_base_dir=tmp_path / "out",
        run_id="run-1",
        limit=1,
        provider=provider,
    )

    candidate_rows = _read_csv(result.paths.candidate_catalog)
    report = json.loads(result.paths.refresh_report.read_text(encoding="utf-8"))

    assert provider.calls == [1]
    assert [row["itemId"] for row in candidate_rows] == ["1"]
    assert report["summary"]["rows_processed"] == 1


def test_refresh_catalog_prices_uses_operational_fieldnames(tmp_path: Path) -> None:
    catalog_path = _write_catalog(tmp_path, [_catalog_row(item_id="1", product_name="Produto")])
    provider = FakeShopeeProvider({1: _response({"itemId": 1, "price": "90", "sales": "3"})})

    result = refresh_catalog_prices(
        profile_slug="feminino",
        catalog_file=catalog_path,
        output_base_dir=tmp_path / "out",
        run_id="run-1",
        provider=provider,
    )

    with result.paths.candidate_catalog.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)

    assert header == OPERATIONAL_CATALOG_FIELDNAMES


def _catalog_row(*, item_id: str, product_name: str) -> dict[str, str]:
    return {
        "itemId": item_id,
        "productName": product_name,
        "productLink": f"https://example.com/p{item_id}",
        "offerLink": f"https://example.com/o{item_id}",
        "imageUrl": f"https://example.com/i{item_id}.jpg",
        "price": "100",
        "priceMax": "120",
        "sales": "2",
        "ratingStar": "4.9",
        "shopType": "[2]",
        "sellerCommissionRate": "0.05",
        "shopeeCommissionRate": "0.02",
        "subniches": '["maquiagem"]',
    }


def _write_catalog(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    catalog_path = tmp_path / "catalog.csv"
    with catalog_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=OPERATIONAL_CATALOG_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return catalog_path


def _response(node: dict[str, Any]) -> dict[str, Any]:
    return {"data": {"productOfferV2": {"nodes": [node]}}}


def _response_none() -> dict[str, Any]:
    return {"data": {"productOfferV2": {"nodes": []}}}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))
