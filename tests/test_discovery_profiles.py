from pathlib import Path

import pytest

from ofertas_bot.discovery_profiles import (
    DiscoveryProfileError,
    load_discovery_profile_catalog,
)


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
keywords = ["batom", "base"]
brands = ["maybelline"]
creators = ["creator a"]
categories = ["beleza"]
include_terms = ["batom"]
exclude_terms = ["fantasia"]
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
    assert profile.search_term() == "batom maybelline"
    assert profile.brands == ("maybelline",)
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
