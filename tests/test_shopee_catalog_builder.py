import json
from pathlib import Path

import pytest

from ofertas_bot.shopee_catalog_profiles import ShopeeCatalogProfile, ShopeeCatalogSubniche
from ofertas_bot.tools.shopee_catalog_builder import (
    CatalogRunPlan,
    _build_catalog_summary,
    _classify_subniches,
    _iter_collection_sources,
    _matches_negative_terms,
    _merge_items,
    _resolve_catalog_run_plan,
)


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


def test_matches_negative_terms_accepts_phrase_and_accented_terms() -> None:
    item = {
        "productName": "Necessaire for men para caes",
        "shopName": "Loja geral",
        "productLink": "",
        "offerLink": "",
    }

    assert _matches_negative_terms(item=item, negative_terms=("for men",)) is True
    assert _matches_negative_terms(item=item, negative_terms=("caes",)) is True


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


def test_build_catalog_summary_counts_raw_deduplicated_and_clean(tmp_path: Path) -> None:
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
    plan = CatalogRunPlan(
        profile=profile,
        run_id="run-1",
        run_dir=tmp_path / "mae-e-bebe" / "run-1",
        discovery_scope=None,
        collection_keywords=profile.keyword_terms,
        target_subniches=(),
        include_shop_ids=True,
    )
    merged_items = {
        "1:1": {
            "shopId": 1,
            "itemId": 1,
            "sales": 2,
            "productName": "Fralda premium",
            "shopName": "Loja Bebe",
            "productLink": "",
            "offerLink": "",
            "source_hits": ["keyword:fralda"],
        },
        "2:2": {
            "shopId": 2,
            "itemId": 2,
            "sales": 0,
            "productName": "Cama pet",
            "shopName": "Loja Pet",
            "productLink": "",
            "offerLink": "",
            "source_hits": ["keyword:pet"],
        },
    }
    raw_rows = [
        {
            "shopId": 1,
            "itemId": 1,
            "sales": 2,
            "productName": "Fralda premium",
            "shopName": "Loja Bebe",
            "productLink": "",
            "offerLink": "",
            "source_hits": ["keyword:fralda"],
        },
        {
            "shopId": 2,
            "itemId": 2,
            "sales": 0,
            "productName": "Cama pet",
            "shopName": "Loja Pet",
            "productLink": "",
            "offerLink": "",
            "source_hits": ["keyword:pet"],
        },
        {
            "shopId": 1,
            "itemId": 1,
            "sales": 2,
            "productName": "Fralda premium",
            "shopName": "Loja Bebe",
            "productLink": "",
            "offerLink": "",
            "source_hits": ["matchId:100632"],
        },
    ]
    summary = _build_catalog_summary(
        plan=plan,
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
    assert summary["discovery_scope"] is None


def test_iter_collection_sources_ignores_start_match_ids() -> None:
    profile = ShopeeCatalogProfile(
        slug="mae-e-bebe",
        name="Mae e Bebe",
        start_match_ids=(100632,),
        keyword_terms=("bebe", "mamadeira"),
        shop_ids=(123,),
    )

    assert _iter_collection_sources(profile) == [
        ("keyword", "bebe", {"keyword": "bebe"}),
        ("keyword", "mamadeira", {"keyword": "mamadeira"}),
        ("shopId", "123", {"shop_id": 123}),
    ]


def test_resolve_catalog_run_plan_without_scope_preserves_profile_sources(tmp_path: Path) -> None:
    profile = _profile_with_macro_scopes()

    plan = _resolve_catalog_run_plan(
        profile=profile,
        discovery_scope=None,
        output_base_dir=tmp_path,
        run_id="run-1",
    )

    assert plan.profile.slug == "feminino"
    assert plan.discovery_scope is None
    assert plan.collection_keywords == ("maquiagem", "moda")
    assert plan.include_shop_ids is True
    assert plan.run_dir == tmp_path / "feminino" / "run-1"
    assert _iter_collection_sources(
        plan.profile,
        collection_keywords=plan.collection_keywords,
        include_shop_ids=plan.include_shop_ids,
    ) == [
        ("keyword", "maquiagem", {"keyword": "maquiagem"}),
        ("keyword", "moda", {"keyword": "moda"}),
        ("shopId", "123", {"shop_id": 123}),
    ]


@pytest.mark.parametrize(
    ("scope", "expected_keywords"),
    [
        ("calcado", ("sandalia", "sapatilha")),
        ("moda", ("vestido", "blusa")),
        ("cabelo", ("chapinha", "secador cabelo")),
    ],
)
def test_resolve_catalog_run_plan_with_scope_uses_macro_keywords(
    tmp_path: Path,
    scope: str,
    expected_keywords: tuple[str, ...],
) -> None:
    profile = _profile_with_macro_scopes()
    taxonomy_base_dir = _write_taxonomy(
        tmp_path,
        allowed_subniches=(
            "calcados-sandalia",
            "calcados-sapatilha",
        ),
    )

    plan = _resolve_catalog_run_plan(
        profile=profile,
        discovery_scope=scope,
        output_base_dir=tmp_path / "out",
        run_id="run-1",
        taxonomy_base_dir=taxonomy_base_dir,
    )

    assert plan.profile.slug == "feminino"
    assert plan.discovery_scope == scope
    assert plan.collection_keywords == expected_keywords
    assert plan.include_shop_ids is False
    assert plan.run_dir == tmp_path / "out" / "feminino" / "scopes" / scope / "run-1"
    assert _iter_collection_sources(
        plan.profile,
        collection_keywords=plan.collection_keywords,
        include_shop_ids=plan.include_shop_ids,
    ) == [("keyword", keyword, {"keyword": keyword}) for keyword in expected_keywords]


def test_resolve_catalog_run_plan_summary_records_scope_metadata(tmp_path: Path) -> None:
    profile = _profile_with_macro_scopes()
    taxonomy_base_dir = _write_taxonomy(
        tmp_path,
        allowed_subniches=(
            "calcados-sandalia",
            "calcados-sapatilha",
        ),
    )
    plan = _resolve_catalog_run_plan(
        profile=profile,
        discovery_scope="calcado",
        output_base_dir=tmp_path / "out",
        run_id="run-1",
        taxonomy_base_dir=taxonomy_base_dir,
    )

    summary = _build_catalog_summary(
        plan=plan,
        raw_source_rows=[],
        merged_items={},
        source_runs=[],
        raw_csv_path=plan.run_dir / "raw.csv",
        raw_json_path=plan.run_dir / "raw.json",
        deduplicated_csv_path=plan.run_dir / "dedup.csv",
        deduplicated_json_path=plan.run_dir / "dedup.json",
        clean_csv_path=plan.run_dir / "clean.csv",
        clean_json_path=plan.run_dir / "clean.json",
    )

    assert summary["profile"]["slug"] == "feminino"
    assert summary["discovery_scope"] == "calcado"
    assert summary["collection_keywords"] == ["sandalia", "sapatilha"]
    assert summary["target_subniches"] == ["calcados-sandalia", "calcados-sapatilha"]
    assert "feminino/scopes/calcado/run-1" in summary["paths"]["clean_csv"].replace("\\", "/")


def test_resolve_catalog_run_plan_rejects_unknown_scope_before_provider(tmp_path: Path) -> None:
    profile = _profile_with_macro_scopes()

    with pytest.raises(ValueError, match="discovery scope nao encontrado"):
        _resolve_catalog_run_plan(
            profile=profile,
            discovery_scope="inexistente",
            output_base_dir=tmp_path,
            run_id="run-1",
        )


def test_resolve_catalog_run_plan_rejects_scope_without_keywords(tmp_path: Path) -> None:
    profile = ShopeeCatalogProfile(
        slug="feminino",
        name="Feminino",
        subniches=(
            ShopeeCatalogSubniche(slug="vazio", name="Vazio", keyword_terms=()),
        ),
    )

    with pytest.raises(ValueError, match="sem keyword_terms"):
        _resolve_catalog_run_plan(
            profile=profile,
            discovery_scope="vazio",
            output_base_dir=tmp_path,
            run_id="run-1",
        )


def test_resolve_catalog_run_plan_rejects_invalid_target_subniche(tmp_path: Path) -> None:
    profile = _profile_with_macro_scopes()
    taxonomy_base_dir = _write_taxonomy(tmp_path, allowed_subniches=("calcados-sandalia",))

    with pytest.raises(ValueError, match="target_subniches invalidos"):
        _resolve_catalog_run_plan(
            profile=profile,
            discovery_scope="calcado",
            output_base_dir=tmp_path,
            run_id="run-1",
            taxonomy_base_dir=taxonomy_base_dir,
        )


def _profile_with_macro_scopes() -> ShopeeCatalogProfile:
    return ShopeeCatalogProfile(
        slug="feminino",
        name="Feminino",
        keyword_terms=("maquiagem", "moda"),
        shop_ids=(123,),
        subniches=(
            ShopeeCatalogSubniche(
                slug="calcado",
                name="Calcados Femininos",
                target_subniches=("calcados-sandalia", "calcados-sapatilha"),
                keyword_terms=("sandalia", "sapatilha"),
            ),
            ShopeeCatalogSubniche(
                slug="moda",
                name="Moda Feminina",
                keyword_terms=("vestido", "blusa"),
            ),
            ShopeeCatalogSubniche(
                slug="cabelo",
                name="Cabelo",
                keyword_terms=("chapinha", "secador cabelo"),
            ),
        ),
    )


def _write_taxonomy(tmp_path: Path, *, allowed_subniches: tuple[str, ...]) -> Path:
    taxonomy_dir = tmp_path / "taxonomy" / "feminino"
    taxonomy_dir.mkdir(parents=True)
    (taxonomy_dir / "shopee_feminino_subniches_taxonomia_base.json").write_text(
        json.dumps({"allowed_subniches": list(allowed_subniches)}),
        encoding="utf-8",
    )
    return tmp_path / "taxonomy"
