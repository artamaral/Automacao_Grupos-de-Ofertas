import csv

from ofertas_bot.tools import project_operational_catalog


def test_project_operational_catalog_rewrites_csv_with_minimal_schema(tmp_path) -> None:
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    input_path.write_text(
        "\n".join(
            [
                "itemId,productName,productLink,offerLink,imageUrl,price,priceMax,sales,ratingStar,shopType,sellerCommissionRate,shopeeCommissionRate,subniches,shopId,shopName",
                '1,Produto,https://example.com/product,https://example.com/offer,https://example.com/image.jpg,100,120,10,4.9,"[2]",0.12,0.03,"[""teste""]",999,Loja',
            ]
        ),
        encoding="utf-8",
    )

    exit_code = project_operational_catalog.run(
        [
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ]
    )

    with output_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert exit_code == 0
    assert rows[0]["itemId"] == "1"
    assert "shopId" not in rows[0]
    assert "shopName" not in rows[0]
