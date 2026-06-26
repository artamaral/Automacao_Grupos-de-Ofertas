from ofertas_bot.tools.shopee_catalog_builder import (
    _build_catalog_summary,
    _build_clean_items,
    _build_deduplicated_items,
    _classify_subniches,
    _iter_collection_sources,
    _matches_negative_terms,
    _merge_items,
)
from ofertas_bot.shopee_catalog_profiles import ShopeeCatalogProfile, ShopeeCatalogSubniche


def test_merge_items_combines_source_hits_without_duplication() -> None:
    target: dict[str, dict[str, object]] = {}
    _merge_items(
        target,
        [
            {"shopId": 1, "itemId": 2, "source_hits": ["keyword:bebe"], "productName": "Produto"},
            {"shopId": 1, "itemId": 2, "source_hits": ["matchId:100632"], "productName": "Produto"},
        ],
    )

    item = target["1:2"]
    assert item["source_hits"] == ["keyword:bebe", "matchId:100632"]


def test_matches_negative_terms_uses_text_fields() -> None:
    item = {
        "productName": "Cama para cachorro",
        "shopName": "Loja Pet",
        "productLink": "",
        "offerLink": "",
    }

    assert _matches_negative_terms(item=item, negative_terms=("cachorro",)) is True
    assert _matches_negative_terms(item=item, negative_terms=("maternidade",)) is False


def test_classify_subniches_matches_keywords_and_respects_negative_terms() -> None:
    item = {
        "productName": "Fralda descartavel premium",
        "shopName": "Loja Bebe",
        "productLink": "",
        "offerLink": "",
    }
    subniches = (
        ShopeeCatalogSubniche(
            slug="fraldas",
            name="Fraldas",
            keyword_terms=("fralda",),
            negative_terms=(),
        ),
        ShopeeCatalogSubniche(
            slug="pets",
            name="Pets",
            keyword_terms=("fralda",),
            negative_terms=("bebe",),
        ),
    )

    assert _classify_subniches(item=item, subniches=subniches) == ["fraldas"]


def test_build_catalog_summary_counts_raw_deduplicated_and_clean(tmp_path) -> None:
    profile = ShopeeCatalogProfile(
        slug="mae-e-bebe",
        name="Mae e Bebe",
        negative_terms=("pet",),
        subniches=(
            ShopeeCatalogSubniche(
                slug="fraldas",
                name="Fraldas",
                keyword_terms=("fralda",),
            ),
        ),
    )
    merged_items = {
        "1:1": {
            "shopId": 1,
            "itemId": 1,
            "productName": "Fralda premium",
            "shopName": "Loja Bebe",
            "productLink": "",
            "offerLink": "",
            "source_hits": ["keyword:fralda"],
        },
        "2:2": {
            "shopId": 2,
            "itemId": 2,
            "productName": "Cama pet",
            "shopName": "Loja Pet",
            "productLink": "",
            "offerLink": "",
            "source_hits": ["keyword:pet"],
        },
    }
    raw_rows = [
        {"shopId": 1, "itemId": 1, "productName": "Fralda premium", "shopName": "Loja Bebe", "productLink": "", "offerLink": "", "source_hits": ["keyword:fralda"]},
        {"shopId": 2, "itemId": 2, "productName": "Cama pet", "shopName": "Loja Pet", "productLink": "", "offerLink": "", "source_hits": ["keyword:pet"]},
        {"shopId": 1, "itemId": 1, "productName": "Fralda premium", "shopName": "Loja Bebe", "productLink": "", "offerLink": "", "source_hits": ["matchId:100632"]},
    ]
    summary = _build_catalog_summary(
        profile=profile,
        run_id="run-1",
        raw_source_rows=raw_rows,
        merged_items=merged_items,
        source_runs=[],
        raw_csv_path=tmp_path / "raw.csv",
        raw_json_path=tmp_path / "raw.json",
        deduplicated_csv_path=tmp_path / "dedup.csv",
        deduplicated_json_path=tmp_path / "dedup.json",
        clean_csv_path=tmp_path / "clean.csv",
        clean_json_path=tmp_path / "clean.json",
    )

    assert summary["summary"]["raw_row_count"] == 3
    assert summary["summary"]["deduplicated_item_count"] == 2
    assert summary["summary"]["clean_item_count"] == 1


def test_iter_collection_sources_ignores_start_match_ids() -> None:
    profile = ShopeeCatalogProfile(
        slug="mae-e-bebe",
        name="Mae e Bebe",
        start_match_ids=(100632,),
        keyword_terms=("bebê", "mamadeira"),
        shop_ids=(123,),
    )

    assert _iter_collection_sources(profile) == [
        ("keyword", "bebê", {"keyword": "bebê"}),
        ("keyword", "mamadeira", {"keyword": "mamadeira"}),
        ("shopId", "123", {"shop_id": 123}),
    ]
