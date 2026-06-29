from ofertas_bot.shopee_catalog_profiles import ShopeeCatalogProfile
from ofertas_bot.tools.shopee_catalog_builder import _build_clean_items


def test_build_clean_items_filters_sales_less_or_equal_one() -> None:
    profile = ShopeeCatalogProfile(
        slug="feminino",
        name="Feminino",
        negative_terms=(),
        subniches=(),
    )
    deduplicated_items = [
        {
            "itemId": 1,
            "sales": 0,
            "productName": "A",
            "shopName": "Loja",
            "productLink": "",
            "offerLink": "",
            "source_hits": [],
        },
        {
            "itemId": 2,
            "sales": 1,
            "productName": "B",
            "shopName": "Loja",
            "productLink": "",
            "offerLink": "",
            "source_hits": [],
        },
        {
            "itemId": 3,
            "sales": 2,
            "productName": "C",
            "shopName": "Loja",
            "productLink": "",
            "offerLink": "",
            "source_hits": [],
        },
    ]

    clean_items = _build_clean_items(
        profile=profile,
        deduplicated_items=deduplicated_items,
    )

    assert [item["itemId"] for item in clean_items] == [3]
