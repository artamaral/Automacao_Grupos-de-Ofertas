from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


def load_cli_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts/shopee/query_product_offer_v2.py"
    spec = importlib.util.spec_from_file_location("query_product_offer_v2", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load query_product_offer_v2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    ok = True
    status_code = 200
    data = {
        "data": {
            "productOfferV2": {
                "nodes": [
                    {
                        "itemId": 26981196359,
                        "shopId": 800864347,
                        "productName": "Chinelo feminino",
                        "productCatIds": [100593, 100644],
                        "shopType": [1, 2],
                        "offerLink": "https://example.com/offer",
                    }
                ],
                "pageInfo": {"page": 1, "limit": 50, "hasNextPage": False},
            }
        }
    }


def test_query_product_offer_v2_defaults_are_sent_to_query(monkeypatch, capsys) -> None:
    module = load_cli_module()
    monkeypatch.setattr(module, "_execute_real_product_offer_query", lambda **kwargs: FakeResponse)

    exit_code = module.run(["--listType=100593"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '"listType": 100593' in output
    assert '"sortType": 5' in output
    assert '"isAMSOffer": true' in output
    assert '"isKeySeller": true' in output
    assert "listType: 100593" in output
    assert "sortType: 5" in output
    assert "isAMSOffer: true" in output
    assert "isKeySeller: true" in output


def test_query_product_offer_v2_allows_overriding_bool_defaults(monkeypatch, capsys) -> None:
    module = load_cli_module()
    monkeypatch.setattr(module, "_execute_real_product_offer_query", lambda **kwargs: FakeResponse)

    exit_code = module.run(
        [
            "--listType",
            "100593",
            "--sortType=2",
            "--isAMSOffer=false",
            "--isKeySeller",
            "0",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '"sortType": 2' in output
    assert '"isAMSOffer": false' in output
    assert '"isKeySeller": false' in output
    assert "sortType: 2" in output
    assert "isAMSOffer: false" in output
    assert "isKeySeller: false" in output


def test_query_product_offer_v2_writes_csv_with_bom_and_compact_arrays(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    module = load_cli_module()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "_execute_real_product_offer_query", lambda **kwargs: FakeResponse)

    exit_code = module.run(["--listType=100593", "--csv"])

    output = capsys.readouterr().out
    csv_path = tmp_path / "product_offer_v2_100593.csv"
    raw_bytes = csv_path.read_bytes()
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))
    assert exit_code == 0
    assert "nodes_recebidos=1" in output
    assert raw_bytes.startswith(b"\xef\xbb\xbf")
    assert rows[0]["itemId"] == "26981196359"
    assert rows[0]["productCatIds"] == "[100593,100644]"
    assert rows[0]["shopType"] == "[1,2]"
