from dataclasses import replace
from pathlib import Path

from ofertas_bot.models import Marketplace, Offer, ScoredOffer
from ofertas_bot.selection import (
    DEFAULT_SELECTION_POLICIES_BY_NICHE,
    apply_default_selection_policy,
)


def _make_scored_offer(title: str, score: float, url: str) -> ScoredOffer:
    offer = Offer(
        marketplace=Marketplace.SHOPEE,
        title=title,
        url=url,
        image_url=None,
        price=10.0,
        old_price=None,
        commission_rate=0.1,
        sales_count=1,
        rating=5.0,
        niche="mae e bebe",
    )
    return ScoredOffer(offer=offer, score=score, reasons=["teste"])


def _make_scored_offer_with_sales(
    title: str,
    score: float,
    url: str,
    *,
    sales_count: int,
) -> ScoredOffer:
    scored_offer = _make_scored_offer(title, score, url)
    return replace(
        scored_offer,
        offer=replace(scored_offer.offer, sales_count=sales_count),
    )


def test_operational_selection_policies_cover_all_curated_niches() -> None:
    assert set(DEFAULT_SELECTION_POLICIES_BY_NICHE) == {
        "mae e bebe",
        "feminino",
        "auto e moto",
    }
    for policy in DEFAULT_SELECTION_POLICIES_BY_NICHE.values():
        assert policy.total_items == 20
        assert sum(policy.subniche_quotas.values()) == 20
        assert policy.max_zero_sales_items == 4
        assert policy.minimum_daily_runs == 5


def test_default_selection_policy_keeps_top_scores_within_subniche_quota(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.csv"
    catalog_path.write_text(
        "\n".join(
            [
                "productName,offerLink,productLink,subniches",
                'Item 1,https://example.com/1,,["mamadeiras"]',
                'Item 2,https://example.com/2,,["mamadeiras"]',
                'Item 3,https://example.com/3,,["mamadeiras"]',
                'Item 4,https://example.com/4,,["mamadeiras"]',
            ]
        ),
        encoding="utf-8",
    )

    scored_offers = [
        _make_scored_offer("Item 1", 20.0, "https://example.com/1"),
        _make_scored_offer("Item 2", 19.0, "https://example.com/2"),
        _make_scored_offer("Item 3", 18.0, "https://example.com/3"),
        _make_scored_offer("Item 4", 17.0, "https://example.com/4"),
    ]

    from ofertas_bot import selection

    original = selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE
    selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = {"mae e bebe": {"mamadeiras": 2}}
    try:
        result = apply_default_selection_policy(
            scored_offers,
            niche="mae e bebe",
            catalog_source_path=catalog_path,
        )
    finally:
        selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = original

    assert result.applied_default_policy is True
    assert result.selected_count == 2
    assert [item.offer.title for item in result.scored_offers] == ["Item 1", "Item 2"]


def test_default_selection_policy_limits_zero_sales_items_without_forcing_them(
    tmp_path: Path,
) -> None:
    catalog_path = tmp_path / "catalog.csv"
    catalog_path.write_text(
        "\n".join(
            [
                "productName,offerLink,productLink,subniches",
                'Zero 1,https://example.com/1,,["mamadeiras"]',
                'Zero 2,https://example.com/2,,["mamadeiras"]',
                'Zero 3,https://example.com/3,,["mamadeiras"]',
                'Zero 4,https://example.com/4,,["mamadeiras"]',
                'Zero 5,https://example.com/5,,["mamadeiras"]',
                'Com Venda,https://example.com/6,,["mamadeiras"]',
            ]
        ),
        encoding="utf-8",
    )

    scored_offers = [
        _make_scored_offer_with_sales(
            "Zero 1",
            20.0,
            "https://example.com/1",
            sales_count=0,
        ),
        _make_scored_offer_with_sales(
            "Zero 2",
            19.0,
            "https://example.com/2",
            sales_count=0,
        ),
        _make_scored_offer_with_sales(
            "Zero 3",
            18.0,
            "https://example.com/3",
            sales_count=0,
        ),
        _make_scored_offer_with_sales(
            "Zero 4",
            17.0,
            "https://example.com/4",
            sales_count=0,
        ),
        _make_scored_offer_with_sales(
            "Zero 5",
            16.0,
            "https://example.com/5",
            sales_count=0,
        ),
        _make_scored_offer("Com Venda", 15.0, "https://example.com/6"),
    ]

    from ofertas_bot import selection

    original_quotas = selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE
    original_limits = selection.DEFAULT_MAX_ZERO_SALES_ITEMS_BY_NICHE
    selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = {"mae e bebe": {"mamadeiras": 5}}
    selection.DEFAULT_MAX_ZERO_SALES_ITEMS_BY_NICHE = {"mae e bebe": 4}
    try:
        result = apply_default_selection_policy(
            scored_offers,
            niche="mae e bebe",
            catalog_source_path=catalog_path,
        )
    finally:
        selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = original_quotas
        selection.DEFAULT_MAX_ZERO_SALES_ITEMS_BY_NICHE = original_limits

    assert result.applied_default_policy is True
    assert result.selected_count == 5
    assert [item.offer.title for item in result.scored_offers] == [
        "Zero 1",
        "Zero 2",
        "Zero 3",
        "Zero 4",
        "Com Venda",
    ]
