import json

from ofertas_bot import harness


def test_harness_saves_normalized_offers_when_requested(tmp_path) -> None:
    output_path = tmp_path / "offers.json"

    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
            "--save-json",
            str(output_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert len(payload) == 1
    assert payload[0]["marketplace"] == "mock"
    assert payload[0]["niche"] == "maquiagem"
    assert payload[0]["title"]
    assert payload[0]["url"]
    assert "price" in payload[0]


def test_harness_does_not_save_json_by_default(tmp_path) -> None:
    output_path = tmp_path / "offers.json"

    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
        ]
    )

    assert exit_code == 0
    assert not output_path.exists()


def test_harness_handles_save_json_write_error(tmp_path, capsys) -> None:
    output_path = tmp_path

    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
            "--save-json",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Não foi possível salvar o JSON de ofertas" in captured.err
    assert "AÇÃO | Verifique se o caminho é um arquivo válido" in captured.err


def test_harness_saves_copy_briefs_when_requested(tmp_path) -> None:
    output_path = tmp_path / "copy_briefs.json"

    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
            "--save-copy-briefs-json",
            str(output_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert len(payload) == 1
    assert payload[0]["content_type"] == "product_offer"
    assert payload[0]["facts"]["niche"] == "maquiagem"
    assert "score" in payload[0]["selection"]
    assert payload[0]["selection"]["reasons"]
    assert payload[0]["required_disclosures"]
    assert payload[0]["copy_constraints"]
    assert payload[0]["refresh"] == {
        "iterations": 0,
        "stability_reached": True,
        "changed_items": [],
    }


def test_harness_saves_messages_preview_html_when_requested(tmp_path) -> None:
    output_path = tmp_path / "messages_preview.html"

    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
            "--save-messages-preview-html",
            str(output_path),
        ]
    )

    html = output_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "<!DOCTYPE html>" in html
    assert "Preview HTML gerado automaticamente a partir da rodada." in html
    assert "🛍️" in html


def test_harness_applies_default_selection_policy_before_saving_copy_briefs(tmp_path) -> None:
    catalog_path = tmp_path / "catalog.csv"
    output_path = tmp_path / "copy_briefs.json"
    catalog_path.write_text(
        "\n".join(
            [
                "productName,offerLink,productLink,price,priceMax,sales,ratingStar,shopType,sellerCommissionRate,shopeeCommissionRate,subniches",
                'Item A,https://example.com/a,,100,,10,5,[2],0.20,0.00,["mamadeiras"]',
                'Item B,https://example.com/b,,100,,10,5,[2],0.10,0.00,["mamadeiras"]',
                'Item C,https://example.com/c,,100,,10,5,[2],0.05,0.00,["mamadeiras"]',
            ]
        ),
        encoding="utf-8",
    )

    from ofertas_bot import selection

    original = selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE
    selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = {"mae e bebe": {"mamadeiras": 2}}
    try:
        exit_code = harness.run(
            [
                "--marketplace",
                "shopee",
                "--niche",
                "mae e bebe",
                "--limit",
                "10",
                "--catalog-file",
                str(catalog_path),
                "--save-copy-briefs-json",
                str(output_path),
            ]
        )
    finally:
        selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = original

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert len(payload) == 2
    assert [item["facts"]["title"] for item in payload] == ["Item A", "Item B"]


def test_harness_limits_zero_sales_items_in_default_selection_policy(tmp_path) -> None:
    catalog_path = tmp_path / "catalog.csv"
    output_path = tmp_path / "copy_briefs.json"
    catalog_path.write_text(
        "\n".join(
            [
                "productName,offerLink,productLink,price,priceMax,sales,ratingStar,shopType,sellerCommissionRate,shopeeCommissionRate,subniches",
                'Zero A,https://example.com/a,,100,,0,5,[2],0.20,0.00,["mamadeiras"]',
                'Zero B,https://example.com/b,,100,,0,5,[2],0.19,0.00,["mamadeiras"]',
                'Zero C,https://example.com/c,,100,,0,5,[2],0.18,0.00,["mamadeiras"]',
                'Zero D,https://example.com/d,,100,,0,5,[2],0.17,0.00,["mamadeiras"]',
                'Zero E,https://example.com/e,,100,,0,5,[2],0.16,0.00,["mamadeiras"]',
                'Com Venda,https://example.com/f,,100,,5,5,[2],0.15,0.00,["mamadeiras"]',
            ]
        ),
        encoding="utf-8",
    )

    from ofertas_bot import selection

    original_quotas = selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE
    original_limits = selection.DEFAULT_MAX_ZERO_SALES_ITEMS_BY_NICHE
    selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = {"mae e bebe": {"mamadeiras": 5}}
    selection.DEFAULT_MAX_ZERO_SALES_ITEMS_BY_NICHE = {"mae e bebe": 4}
    try:
        exit_code = harness.run(
            [
                "--marketplace",
                "shopee",
                "--niche",
                "mae e bebe",
                "--limit",
                "10",
                "--catalog-file",
                str(catalog_path),
                "--save-copy-briefs-json",
                str(output_path),
            ]
        )
    finally:
        selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = original_quotas
        selection.DEFAULT_MAX_ZERO_SALES_ITEMS_BY_NICHE = original_limits

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert len(payload) == 5
    assert [item["facts"]["title"] for item in payload] == [
        "Zero A",
        "Zero B",
        "Zero C",
        "Zero D",
        "Com Venda",
    ]
