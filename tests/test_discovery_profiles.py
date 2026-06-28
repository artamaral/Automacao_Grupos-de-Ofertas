from pathlib import Path

import pytest

from ofertas_bot.discovery_profiles import (
    DiscoveryProfileError,
    load_discovery_profile_catalog,
)
from ofertas_bot.selection import DEFAULT_SELECTION_POLICIES_BY_NICHE


def test_load_discovery_profile_catalog_reads_profile_data(tmp_path: Path) -> None:
    config_path = tmp_path / "profiles.toml"
    config_path.write_text(
        """
[[profiles]]
slug = "maquiagem-promocoes"
name = "Maquiagem Promocoes"
niche = "maquiagem"
marketplace = "shopee"
query = "batom maybelline"
target = "grupo-maquiagem"
limit = 4
catalog_file = "catalogs/clean/maquiagem/clean_catalog.csv"
discovery_method = "descobridor-geral"
keywords = ["batom", "base"]
brands = ["maybelline"]
creators = ["creator a"]
categories = ["beleza"]
include_terms = ["batom"]
exclude_terms = ["fantasia"]
shopee_offer_keyword = "Beauty Deals"
shopee_product_match_ids = [123, 123]
subgroups = [
  { slug = "labios", label = "Labios", query = "batom gloss", categories = ["Maquiagem"] },
]
""".strip(),
        encoding="utf-8",
    )

    catalog = load_discovery_profile_catalog(config_path)
    profile = catalog.get("maquiagem-promocoes")

    assert profile is not None
    assert profile.marketplace.value == "shopee"
    assert profile.niche == "maquiagem"
    assert profile.target == "grupo-maquiagem"
    assert profile.limit == 4
    assert profile.catalog_file == "catalogs/clean/maquiagem/clean_catalog.csv"
    assert profile.search_term() == "batom maybelline"
    assert profile.discovery_method == "descobridor-geral"
    assert profile.brands == ("maybelline",)
    assert profile.shopee_offer_keyword == "Beauty Deals"
    assert profile.shopee_offer_search_terms() == ("Beauty Deals",)
    assert profile.shopee_product_match_ids == (123,)
    assert profile.get_subgroup("labios") is not None
    assert profile.get_subgroup("labios").query == "batom gloss"


def test_discovery_profile_scopes_to_subgroup(tmp_path: Path) -> None:
    config_path = tmp_path / "profiles.toml"
    config_path.write_text(
        "\n".join(
            [
                "[[profiles]]",
                'slug = "auto-e-moto"',
                'name = "Auto e Moto"',
                'niche = "auto e moto"',
                'marketplace = "mock"',
                'categories = ["auto e moto"]',
                "subgroups = [",
                '  { slug = "limpeza", label = "Limpeza", '
                'query = "limpeza veicular cera", '
                'categories = ["Limpeza Veicular"] },',
                "]",
            ]
        ),
        encoding="utf-8",
    )

    profile = load_discovery_profile_catalog(config_path).get("auto-e-moto")

    assert profile is not None
    scoped = profile.scoped_to_subgroup("limpeza")
    assert scoped.slug == "auto-e-moto:limpeza"
    assert scoped.search_term() == "limpeza veicular cera"
    assert "limpeza veicular" in scoped.categories


def test_load_discovery_profile_catalog_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(DiscoveryProfileError, match="file not found"):
        load_discovery_profile_catalog(tmp_path / "missing.toml")


def test_load_discovery_profile_catalog_reads_csv_export(tmp_path: Path) -> None:
    config_path = tmp_path / "discovery_profiles.csv"
    config_path.write_text(
        "\n".join(
            [
                "slug,name,niche,marketplace,discovery_method,query,target,limit,catalog_file,keywords_csv,brands_csv,categories_csv,include_terms_csv,exclude_terms_csv,shopee_offer_names_csv,shopee_category_urls_csv,shopee_product_match_ids_csv,shopee_product_category_ids_csv,subgroups_json,notes",
                'maquiagem-promocoes,Maquiagem Promocoes,maquiagem,shopee,descobridor-geral,batom maybelline,grupo-maquiagem,4,catalogs/clean/maquiagem/clean_catalog.csv,batom|base,maybelline,beleza,batom,fantasia,Beauty Deals,,123|123,,"[{""slug"":""labios"",""label"":""Labios"",""query"":""batom gloss"",""categories"":[""Maquiagem""]}]",teste',
            ]
        ),
        encoding="utf-8",
    )

    catalog = load_discovery_profile_catalog(config_path)
    profile = catalog.get("maquiagem-promocoes")

    assert profile is not None
    assert profile.marketplace.value == "shopee"
    assert profile.discovery_method == "descobridor-geral"
    assert profile.search_term() == "batom maybelline"
    assert profile.shopee_offer_search_terms() == ("Beauty Deals",)
    assert profile.shopee_product_match_ids == (123,)
    assert profile.get_subgroup("labios") is not None


def test_operational_profiles_share_the_same_curated_flow_contract() -> None:
    catalog = load_discovery_profile_catalog(Path("config/discovery_profiles.toml"))

    for slug in ("mae-e-bebe", "feminino", "auto-e-moto"):
        profile = catalog.get(slug)

        assert profile is not None
        assert profile.marketplace.value == "shopee"
        assert profile.catalog_file is not None
        assert f"/{slug}/" in profile.catalog_file.replace("\\", "/")
        assert Path(profile.catalog_file).is_file()
        assert profile.niche in DEFAULT_SELECTION_POLICIES_BY_NICHE
