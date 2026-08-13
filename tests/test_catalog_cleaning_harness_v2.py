from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "catalog-cleaning"
    / "catalog_cleaning_harness_v2.py"
)
pytest.importorskip("pandas")
SPEC = importlib.util.spec_from_file_location("catalog_cleaning_harness_v2", MODULE_PATH)
assert SPEC is not None
catalog_cleaning_harness_v2 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(catalog_cleaning_harness_v2)


def test_catalog_cleaning_harness_removes_forbidden_terms(tmp_path: Path) -> None:
    taxonomy_path = tmp_path / "taxonomy.json"
    taxonomy_path.write_text(
        json.dumps(
            {
                "version": "test",
                "allowed_subniches": ["moda-vestidos", "feminino-geral"],
                "source_keyword_to_subniche": {"vestido": "moda-vestidos"},
                "generic_source_hits": ["feminino"],
                "generic_default_subniche": "feminino-geral",
                "forbidden_terms": ["infantil", "juvenil", "gestante", "maternidade"],
                "fallback_product_name_rules": [],
            }
        ),
        encoding="utf-8",
    )
    input_path = tmp_path / "catalog.csv"
    input_path.write_text(
        "\n".join(
            [
                "itemId,shopId,productName,productLink,offerLink,imageUrl,commission,price,sales,ratingStar,priceDiscountRate,source_hits",
                '1,10,Vestido feminino adulto,https://example.com/p1,https://example.com/o1,https://example.com/i1.jpg,5,100,3,4.8,10,"[""keyword:vestido""]"',
                '2,20,Vestido juvenil promocao,https://example.com/p2,https://example.com/o2,https://example.com/i2.jpg,5,100,3,4.8,10,"[""keyword:vestido""]"',
                '3,30,Kit maternidade gestante,https://example.com/p3,https://example.com/o3,https://example.com/i3.jpg,5,100,3,4.8,10,"[""keyword:vestido""]"',
            ]
        ),
        encoding="utf-8",
    )
    outdir = tmp_path / "out"

    summary = catalog_cleaning_harness_v2.run(input_path, outdir, taxonomy_path)

    with (outdir / "shopee_catalogo_limpo_subniches.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        clean_rows = list(csv.DictReader(handle))
    with (outdir / "shopee_catalogo_removidos.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        removed_rows = list(csv.DictReader(handle))

    assert summary["clean_rows"] == 1
    assert summary["removed_forbidden_term_rows"] == 2
    assert clean_rows[0]["itemId"] == "1"
    assert removed_rows[0]["itemId"] == "2"
    assert removed_rows[0]["removal_reason"] == "termo_proibido"
    assert json.loads(removed_rows[0]["forbidden_term_hits"]) == ["juvenil"]
    assert removed_rows[1]["itemId"] == "3"
    assert json.loads(removed_rows[1]["forbidden_term_hits"]) == ["gestante", "maternidade"]
