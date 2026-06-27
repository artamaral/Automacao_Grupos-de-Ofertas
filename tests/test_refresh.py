from pathlib import Path

from ofertas_bot.agents.scorer import ScorerAgent
from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.refresh import stabilize_selected_shopee_offers


def _make_offer(
    *,
    title: str,
    url: str,
    item_id: int,
    price: float,
    old_price: float | None,
    commission_rate: float,
) -> Offer:
    return Offer(
        marketplace=Marketplace.SHOPEE,
        title=title,
        url=url,
        image_url=None,
        price=price,
        old_price=old_price,
        commission_rate=commission_rate,
        sales_count=0,
        rating=5.0,
        niche="mae e bebe",
        item_id=item_id,
    )


def test_stabilize_selected_shopee_offers_rescores_full_list_after_refresh(
    tmp_path: Path,
) -> None:
    catalog_path = tmp_path / "catalog.csv"
    catalog_path.write_text(
        "\n".join(
            [
                "productName,offerLink,productLink,subniches",
                'Item A,https://example.com/a,,["mamadeiras"]',
                'Item B,https://example.com/b,,["mamadeiras"]',
            ]
        ),
        encoding="utf-8",
    )

    offers = [
        _make_offer(
            title="Item A",
            url="https://example.com/a",
            item_id=1,
            price=100.0,
            old_price=200.0,
            commission_rate=0.20,
        ),
        _make_offer(
            title="Item B",
            url="https://example.com/b",
            item_id=2,
            price=100.0,
            old_price=150.0,
            commission_rate=0.10,
        ),
    ]

    class FakeShopeeProvider:
        def fetch_product_offer_raw_response(
            self,
            *,
            limit: int,
            page: int = 1,
            item_id: int | None = None,
            **_: object,
        ) -> dict[str, object]:
            assert limit == 1
            assert page == 1
            if item_id == 1:
                return {
                    "data": {
                        "productOfferV2": {
                            "nodes": [{"itemId": 1, "price": "150", "commissionRate": "0.01"}]
                        }
                    }
                }
            return {
                "data": {
                    "productOfferV2": {
                        "nodes": [{"itemId": 2, "price": "100", "commissionRate": "0.10"}]
                    }
                }
            }

    from ofertas_bot import selection

    original_quotas = selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE
    selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = {"mae e bebe": {"mamadeiras": 1}}
    try:
        result = stabilize_selected_shopee_offers(
            offers=offers,
            scorer=ScorerAgent(),
            niche="mae e bebe",
            catalog_source_path=catalog_path,
            shopee_provider=FakeShopeeProvider(),  # type: ignore[arg-type]
            max_iterations=5,
        )
    finally:
        selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = original_quotas

    assert result.stability_reached is True
    assert result.iterations == 2
    assert result.stale_items_count == 0
    assert [item.offer.title for item in result.selection_result.scored_offers] == ["Item B"]
    assert result.offers[0].price == 150.0
    assert result.offers[0].commission_rate == 0.01


def test_stabilize_selected_shopee_offers_blocks_when_list_does_not_stabilize(
    tmp_path: Path,
) -> None:
    catalog_path = tmp_path / "catalog.csv"
    catalog_path.write_text(
        "\n".join(
            [
                "productName,offerLink,productLink,subniches",
                'Item A,https://example.com/a,,["mamadeiras"]',
            ]
        ),
        encoding="utf-8",
    )

    offers = [
        _make_offer(
            title="Item A",
            url="https://example.com/a",
            item_id=1,
            price=100.0,
            old_price=200.0,
            commission_rate=0.20,
        )
    ]

    class FakeShopeeProvider:
        call_count = 0

        def fetch_product_offer_raw_response(
            self,
            *,
            limit: int,
            page: int = 1,
            item_id: int | None = None,
            **_: object,
        ) -> dict[str, object]:
            self.call_count += 1
            return {
                "data": {
                    "productOfferV2": {
                        "nodes": [
                            {
                                "itemId": item_id,
                                "price": str(100 + self.call_count),
                                "commissionRate": "0.20",
                            }
                        ]
                    }
                }
            }

    from ofertas_bot import selection

    original_quotas = selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE
    selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = {"mae e bebe": {"mamadeiras": 1}}
    try:
        result = stabilize_selected_shopee_offers(
            offers=offers,
            scorer=ScorerAgent(),
            niche="mae e bebe",
            catalog_source_path=catalog_path,
            shopee_provider=FakeShopeeProvider(),  # type: ignore[arg-type]
            max_iterations=1,
        )
    finally:
        selection.DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = original_quotas

    assert result.stability_reached is False
    assert result.iterations == 1
    assert result.stale_items_count == 1
