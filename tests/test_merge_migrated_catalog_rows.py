import csv

from ofertas_bot.tools import merge_migrated_catalog_rows


def test_merge_catalog_rows_appends_only_maternity_and_baby_candidates(tmp_path) -> None:
    source_path = tmp_path / "feminino.csv"
    target_path = tmp_path / "mae-e-bebe.csv"
    output_path = tmp_path / "merged.csv"

    source_path.write_text(
        "\n".join(
                [
                "itemId,shopId,productName,productLink,offerLink,imageUrl,price,priceMax,sales,ratingStar,shopType,sellerCommissionRate,shopeeCommissionRate,subniches,shopName,source_hits",
                '1,10,Vestido Gestante Premium,https://example.com/p1,https://example.com/o1,https://example.com/i1.jpg,100,120,10,4.9,"[2]",0.12,0.03,"[""moda-gestante""]",Loja Gestante,"[""keyword:vestido""]"',
                '2,20,Conjunto Infantil Menina,https://example.com/p2,https://example.com/o2,https://example.com/i2.jpg,90,120,10,4.9,"[2]",0.12,0.03,"[""moda-geral""]",Kids,"[""keyword:conjunto""]"',
                '3,30,Saida Maternidade Menino,https://example.com/p3,https://example.com/o3,https://example.com/i3.jpg,130,150,10,4.9,"[2]",0.12,0.03,"[""moda-geral""]",Baby,"[""keyword:macacao""]"',
                ]
            ),
            encoding="utf-8-sig",
    )
    target_path.write_text(
        "\n".join(
                [
                "itemId,shopId,productName,productLink,offerLink,imageUrl,price,priceMax,sales,ratingStar,shopType,sellerCommissionRate,shopeeCommissionRate,subniches,shopName,source_hits",
                '9,90,Bolsa maternidade,https://example.com/p9,https://example.com/o9,https://example.com/i9.jpg,80,100,8,4.9,"[2]",0.12,0.03,"[""maternidade-bolsas-mochilas""]",Mae,"[""keyword:bolsa maternidade""]"',
                ]
            ),
            encoding="utf-8-sig",
        )

    summary = merge_migrated_catalog_rows.merge_catalog_rows(
        source_path=source_path,
        target_path=target_path,
        output_path=output_path,
    )

    with output_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert summary == {
        "target_rows": 1,
        "migrated_candidates": 2,
        "migrated_added": 2,
        "output_rows": 3,
    }
    assert [row["itemId"] for row in rows] == ["9", "1", "3"]
    assert 'keyword:vestido gestante' in rows[1]["source_hits"]
    assert 'keyword:saida maternidade' in rows[2]["source_hits"]


def test_merge_catalog_rows_deduplicates_existing_target_identity(tmp_path) -> None:
    source_path = tmp_path / "feminino.csv"
    target_path = tmp_path / "mae-e-bebe.csv"
    output_path = tmp_path / "merged.csv"

    csv_payload = "\n".join(
        [
            "itemId,shopId,productName,productLink,offerLink,imageUrl,price,priceMax,sales,ratingStar,shopType,sellerCommissionRate,shopeeCommissionRate,subniches,shopName,source_hits",
            '1,10,Vestido Gestante Premium,https://example.com/p1,https://example.com/o1,https://example.com/i1.jpg,100,120,10,4.9,"[2]",0.12,0.03,"[""moda-gestante""]",Loja Gestante,"[""keyword:roupa gestante""]"',
        ]
    )
    source_path.write_text(csv_payload, encoding="utf-8-sig")
    target_path.write_text(csv_payload, encoding="utf-8-sig")

    summary = merge_migrated_catalog_rows.merge_catalog_rows(
        source_path=source_path,
        target_path=target_path,
        output_path=output_path,
    )

    assert summary["migrated_added"] == 0
