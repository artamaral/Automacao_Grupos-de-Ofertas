from pathlib import Path

from ofertas_bot.shopee_catalog_profiles import (
    ShopeeCatalogProfileError,
    load_shopee_catalog_profile_catalog,
)


def test_load_shopee_catalog_profile_catalog_reads_profiles(tmp_path: Path) -> None:
    config_path = tmp_path / "catalog.toml"
    config_path.write_text(
        """
[[profiles]]
slug = "mae-e-bebe"
name = "Mae e Bebe"
start_match_ids = [100632]
keyword_terms = ["mae e bebe", "fralda"]
negative_terms = ["pet"]
shop_ids = [123]
shop_names = ["Loja 1"]
subniches = [
  { slug = "fraldas", name = "Fraldas", target_subniches = ["fraldas"], keyword_terms = ["fralda"] }
]
""",
        encoding="utf-8",
    )

    catalog = load_shopee_catalog_profile_catalog(config_path)

    profile = catalog.get("mae-e-bebe")
    assert profile is not None
    assert profile.start_match_ids == (100632,)
    assert profile.keyword_terms == ("mae e bebe", "fralda")
    assert profile.negative_terms == ("pet",)
    assert profile.shop_ids == (123,)
    assert profile.shop_names == ("Loja 1",)
    assert profile.subniches[0].slug == "fraldas"
    assert profile.subniches[0].target_subniches == ("fraldas",)


def test_load_shopee_catalog_profile_catalog_rejects_missing_profiles(tmp_path: Path) -> None:
    config_path = tmp_path / "catalog.toml"
    config_path.write_text("", encoding="utf-8")

    try:
        load_shopee_catalog_profile_catalog(config_path)
    except ShopeeCatalogProfileError as error:
        assert "[[profiles]]" in str(error)
    else:
        raise AssertionError("expected ShopeeCatalogProfileError")


def test_feminino_profile_blocks_infantil_and_juvenil_terms() -> None:
    catalog = load_shopee_catalog_profile_catalog(Path("config/shopee_catalog_profiles.toml"))

    profile = catalog.get("feminino")

    assert profile is not None
    assert "infantil" in profile.negative_terms
    assert "juvenil" in profile.negative_terms
    assert "gestante" in profile.negative_terms
    assert "maternidade" in profile.negative_terms
    assert "bebê" in profile.negative_terms
    assert "moda gestante" not in profile.keyword_terms


def test_mae_e_bebe_profile_absorbs_maternity_keywords() -> None:
    catalog = load_shopee_catalog_profile_catalog(Path("config/shopee_catalog_profiles.toml"))

    profile = catalog.get("mae-e-bebe")

    assert profile is not None
    assert "moda gestante" in profile.keyword_terms
    assert "roupa gestante" in profile.keyword_terms
    assert "vestido gestante" in profile.keyword_terms


def test_feminino_profile_declares_calcado_macro_without_operational_profile() -> None:
    catalog = load_shopee_catalog_profile_catalog(Path("config/shopee_catalog_profiles.toml"))

    profile = catalog.get("feminino")

    assert profile is not None
    assert catalog.get("feminino-calcados") is None
    calcado = next(item for item in profile.subniches if item.slug == "calcado")
    assert calcado.keyword_terms == (
        "sandalia",
        "sapatilha",
        "chinelo",
        "rasteirinha",
        "rasteira",
        "mocassim",
        "loafer",
        "papete",
        "tamanco",
        "slide",
        "birken",
    )
    assert calcado.target_subniches == (
        "calcados-sandalia",
        "calcados-sapatilha",
        "calcados-chinelo",
        "calcados-rasteirinha",
        "calcados-mocassim",
    )
