from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


def load_batch_cli_module():
    script_dir = Path(__file__).resolve().parents[1] / "scripts/shopee"
    script_path = script_dir / "query_product_offer_v2_product_categories.py"
    spec = importlib.util.spec_from_file_location(
        "query_product_offer_v2_product_categories",
        script_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load query_product_offer_v2_product_categories.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_product_cat_ids_accepts_comma_list() -> None:
    module = load_batch_cli_module()

    assert module._parse_product_cat_ids("100350, 100351,100594") == [
        100350,
        100351,
        100594,
    ]


def test_product_category_loop_writes_pages_until_empty(tmp_path, monkeypatch) -> None:
    module = load_batch_cli_module()
    calls = []

    def fake_fetch_product_offer_page(*, provider, params):
        calls.append(dict(params))
        if params["page"] == 1:
            return {
                "data": {
                    "productOfferV2": {
                        "nodes": [
                            {
                                "itemId": params["productCatId"] * 10,
                                "shopId": 123,
                                "productName": f"Produto {params['productCatId']}",
                                "productCatIds": [params["productCatId"]],
                                "shopType": [1],
                            }
                        ],
                        "pageInfo": {
                            "page": params["page"],
                            "limit": params["limit"],
                            "hasNextPage": True,
                            "scrollId": "scroll-1",
                        },
                    }
                }
            }
        return {
            "data": {
                "productOfferV2": {
                    "nodes": [],
                    "pageInfo": {
                        "page": params["page"],
                        "limit": params["limit"],
                        "hasNextPage": False,
                    },
                }
            }
        }

    monkeypatch.setattr(module, "_fetch_product_offer_page", fake_fetch_product_offer_page)
    output_path = tmp_path / "out.csv"

    summary = module._write_product_category_pages(
        provider=object(),
        output_path=output_path,
        product_cat_ids=[100350, 100351],
        start_page=1,
        max_pages=3,
        limit=50,
        sort_type=5,
        is_ams_offer=True,
        is_key_seller=True,
    )

    rows = list(csv.DictReader(output_path.open(encoding="utf-8-sig")))
    assert len(calls) == 4
    assert summary["productCatIds"] == 2
    assert summary["pages"] == 4
    assert summary["nodes"] == 2
    assert rows[0]["productCatId"] == "100350"
    assert rows[0]["requestPage"] == "1"
    assert rows[0]["productCatIds"] == "[100350]"
    assert rows[1]["productCatId"] == "100351"
