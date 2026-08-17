from __future__ import annotations

from datetime import UTC, datetime

from ofertas_bot.storage.supabase_offer_media_asset_store import (
    OfferMediaAssetStoreError,
    OfferMediaAssetUpsert,
    SupabaseOfferMediaAssetStore,
    build_offer_media_asset_upsert,
)
from ofertas_bot.tools.scrape_shopee_media import MediaAsset, ScrapeResult


def test_build_offer_media_asset_upsert_consolidates_valid_assets() -> None:
    scraped_at = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
    result = ScrapeResult(
        source_url="https://shopee.com.br/product/10/20",
        item_id="20",
        shop_id="10",
        scraped_at=scraped_at,
        assets=[
            MediaAsset("image", 1, "https://cf.shopee.com.br/file/a", status="valid"),
            MediaAsset("image", 2, "https://cf.shopee.com.br/file/b", status="failed"),
            MediaAsset("video", 3, "https://mms.vod.susercontent.com/v.mp4", status="valid"),
        ],
    )

    upsert = build_offer_media_asset_upsert(
        profile="feminino",
        marketplace="shopee",
        product_link=result.source_url,
        scrape_result=result,
    )

    assert upsert.status == "valid"
    assert upsert.item_id == 20
    assert upsert.shop_id == 10
    assert upsert.image_urls == ("https://cf.shopee.com.br/file/a",)
    assert upsert.video_url == "https://mms.vod.susercontent.com/v.mp4"
    assert upsert.resolved_at == scraped_at


def test_build_offer_media_asset_upsert_marks_no_media() -> None:
    result = ScrapeResult(
        source_url="https://shopee.com.br/product/10/20",
        item_id="20",
        shop_id="10",
        scraped_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
        assets=[],
    )

    upsert = build_offer_media_asset_upsert(
        profile="feminino",
        marketplace="shopee",
        product_link=result.source_url,
        scrape_result=result,
    )

    assert upsert.status == "no_media"
    assert upsert.image_urls == ()
    assert upsert.video_url is None


def test_build_offer_media_asset_upsert_marks_failed_without_scrape_result() -> None:
    upsert = build_offer_media_asset_upsert(
        profile="feminino",
        marketplace="shopee",
        product_link="https://shopee.com.br/product/10/20",
        scrape_result=None,
        error_detail="HTTP 403",
        item_id=20,
        shop_id=10,
    )

    assert upsert.status == "failed"
    assert upsert.error_detail == "HTTP 403"


def test_build_offer_media_asset_upsert_requires_item_id() -> None:
    try:
        build_offer_media_asset_upsert(
            profile="feminino",
            marketplace="shopee",
            product_link="https://example.com",
            scrape_result=None,
        )
    except OfferMediaAssetStoreError as error:
        assert "item_id is required" in str(error)
    else:
        raise AssertionError("expected OfferMediaAssetStoreError")


def test_supabase_offer_media_asset_store_upserts_idempotently() -> None:
    execute_calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeResult:
        def fetchone(self) -> dict[str, str]:
            return {"media_asset_id": "media-1"}

    class FakeConnection:
        def execute(self, sql: str, params: tuple[object, ...]) -> FakeResult:
            execute_calls.append((sql, params))
            return FakeResult()

    store = SupabaseOfferMediaAssetStore(FakeConnection())
    media_id = store.upsert_media_asset(
        OfferMediaAssetUpsert(
            profile="feminino",
            marketplace="shopee",
            item_id=20,
            shop_id=10,
            product_link="https://shopee.com.br/product/10/20",
            image_urls=("https://cf.shopee.com.br/file/a",),
            video_url="https://mms.vod.susercontent.com/v.mp4",
            status="valid",
            resolved_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
            last_checked_at=datetime(2026, 8, 15, 12, 1, tzinfo=UTC),
        )
    )

    assert media_id == "media-1"
    assert len(execute_calls) == 1
    assert "insert into offers.offer_media_assets" in execute_calls[0][0]
    assert "on conflict (profile, marketplace, item_id)" in execute_calls[0][0]
    assert execute_calls[0][1][0] == "feminino"
    assert execute_calls[0][1][2] == 20
