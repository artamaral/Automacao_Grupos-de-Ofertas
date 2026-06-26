import json
from pathlib import Path

from ofertas_bot import harness


def test_harness_collects_from_profile_file(tmp_path: Path, capsys) -> None:
    profiles_path = tmp_path / "profiles.toml"
    profiles_path.write_text(
        """
[[profiles]]
slug = "maquiagem-promocoes"
name = "Maquiagem Promocoes"
niche = "maquiagem"
marketplace = "mock"
query = "maquiagem"
target = "grupo-maquiagem"
limit = 1
discovery_method = "descobridor-geral"
keywords = ["batom"]
brands = ["maybelline"]
creators = []
categories = ["beleza"]
include_terms = []
exclude_terms = []
shopee_offer_keyword = "Beauty Deals"
shopee_product_match_ids = [123]
subgroups = [
  { slug = "labios", label = "Labios", query = "batom gloss", categories = ["Maquiagem"] },
]
""".strip(),
        encoding="utf-8",
    )
    output_path = tmp_path / "offers.json"

    exit_code = harness.run(
        [
            "--profile",
            "maquiagem-promocoes",
            "--profiles-file",
            str(profiles_path),
            "--save-json",
            str(output_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert payload[0]["niche"] == "maquiagem"
    assert payload[0]["marketplace"] == "mock"
    assert "INFO | Perfil de descoberta=maquiagem-promocoes" in captured.out
    assert "target=grupo-maquiagem" in captured.out
    assert "INFO | discovery_method=descobridor-geral" in captured.out
    assert "INFO | shopee_offer_keyword=Beauty Deals" in captured.out


def test_harness_collects_from_profile_subgroup(tmp_path: Path, capsys) -> None:
    profiles_path = tmp_path / "profiles.toml"
    profiles_path.write_text(
        "\n".join(
            [
                "[[profiles]]",
                'slug = "auto-e-moto"',
                'name = "Auto e Moto"',
                'niche = "auto e moto"',
                'marketplace = "mock"',
                'target = "grupo-auto-e-moto"',
                "subgroups = [",
                '  { slug = "limpeza", label = "Limpeza", '
                'query = "limpeza veicular cera", '
                'categories = ["Limpeza Veicular"] },',
                "]",
            ]
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "offers.json"

    exit_code = harness.run(
        [
            "--profile",
            "auto-e-moto",
            "--subgroup",
            "limpeza",
            "--profiles-file",
            str(profiles_path),
            "--save-json",
            str(output_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert payload[0]["niche"] == "auto e moto"
    assert "INFO | Perfil de descoberta=auto-e-moto:limpeza" in captured.out
    assert 'query="limpeza veicular cera"' in captured.out


def test_harness_requires_profile_when_subgroup_is_used(capsys) -> None:
    exit_code = harness.run(["--subgroup", "limpeza"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Perfil de descoberta inv" in captured.err


def test_harness_saves_collection_inspection_json(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.toml"
    profiles_path.write_text(
        "\n".join(
            [
                "[[profiles]]",
                'slug = "beleza"',
                'name = "Beleza"',
                'niche = "beleza"',
                'marketplace = "mock"',
                'target = "grupo-beleza"',
                'query = "beleza skincare maquiagem"',
                'discovery_method = "descobridor-geral"',
                'shopee_offer_keyword = "Beauty Deals"',
                'shopee_product_match_ids = [123]',
            ]
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "inspection.json"

    exit_code = harness.run(
        [
            "--profile",
            "beleza",
            "--profiles-file",
            str(profiles_path),
            "--save-inspection-json",
            str(output_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["metadata"]["profile_slug"] == "beleza"
    assert payload["metadata"]["search_term"] == "beleza skincare maquiagem"
    assert payload["metadata"]["collected_offer_count"] == 2
    assert payload["metadata"]["discovery_method"] == "descobridor-geral"
    assert payload["metadata"]["shopee_offer_keyword"] == "Beauty Deals"
    assert payload["metadata"]["shopee_offer_names"] == []
    assert payload["metadata"]["shopee_product_match_ids"] == [123]
    assert payload["metadata"]["shopee_product_category_ids"] == []
    assert payload["provider_snapshot"]["supports_raw_response"] is True
    assert payload["provider_snapshot"]["offer_node_count"] == 2
    assert payload["provider_snapshot"]["page_info"]["hasNextPage"] is False
    assert len(payload["offers"]) == 2


def test_harness_profile_reports_missing_slug(tmp_path: Path, capsys) -> None:
    profiles_path = tmp_path / "profiles.toml"
    profiles_path.write_text(
        '\n'.join(
            [
                "[[profiles]]",
                'slug = "x"',
                'name = "X"',
                'niche = "maquiagem"',
                'marketplace = "mock"',
            ]
        ),
        encoding="utf-8",
    )

    exit_code = harness.run(
        [
            "--profile",
            "inexistente",
            "--profiles-file",
            str(profiles_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Perfil de descoberta não encontrado" in captured.err

def test_harness_uses_catalog_file_as_collector_input(tmp_path: Path, capsys) -> None:
    catalog_path = tmp_path / "catalog.csv"
    catalog_path.write_text(
        "\n".join(
            [
                "productName,offerLink,imageUrl,price,priceMax,commissionRate,sales,ratingStar",
                "Produto catalogado,https://example.com/produto,https://example.com/produto.jpg,49.9,79.9,0.1,12,4.7",
            ]
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "offers.json"

    exit_code = harness.run(
        [
            "--niche",
            "mae e bebe",
            "--marketplace",
            "shopee",
            "--catalog-file",
            str(catalog_path),
            "--save-json",
            str(output_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert payload[0]["title"] == "Produto catalogado"
    assert payload[0]["marketplace"] == "shopee"
    assert payload[0]["niche"] == "mae e bebe"
    assert f"INFO | catalog_file={catalog_path}" in captured.out
