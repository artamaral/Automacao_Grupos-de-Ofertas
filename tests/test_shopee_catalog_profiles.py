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
  { slug = "fraldas", name = "Fraldas", keyword_terms = ["fralda"], negative_terms = [] }
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


def test_load_shopee_catalog_profile_catalog_rejects_missing_profiles(tmp_path: Path) -> None:
    config_path = tmp_path / "catalog.toml"
    config_path.write_text("", encoding="utf-8")

    try:
        load_shopee_catalog_profile_catalog(config_path)
    except ShopeeCatalogProfileError as error:
        assert "[[profiles]]" in str(error)
    else:
        raise AssertionError("expected ShopeeCatalogProfileError")
