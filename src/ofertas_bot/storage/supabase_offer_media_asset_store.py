from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from ofertas_bot.tools.scrape_shopee_media import ScrapeResult


class OfferMediaAssetStoreError(ValueError):
    """Raised when offer media asset persistence cannot be completed."""


@dataclass(frozen=True)
class OfferMediaAssetUpsert:
    profile: str
    marketplace: str
    item_id: int
    shop_id: int | None
    product_link: str
    image_urls: tuple[str, ...]
    video_url: str | None
    status: str
    resolved_at: datetime
    last_checked_at: datetime
    error_detail: str | None = None
    source: str = "shopee_product_html"


@dataclass(frozen=True)
class InstagramMediaDispatchCandidate:
    dispatch_plan_id: str
    profile: str
    marketplace: str
    stable_key: str
    item_id: int
    shop_id: int | None
    product_link: str
    planned_date: date
    planned_hour: int
    slot_sequence: int
    daily_sequence: int
    primary_subniche: str


class SupabaseOfferMediaAssetStore:
    def __init__(self, connection: psycopg.Connection[dict[str, object]]) -> None:
        self._connection = connection

    @classmethod
    def connect_from_env(cls) -> SupabaseOfferMediaAssetStore:
        load_dotenv()
        database_url = os.getenv("SUPABASE_DB_URL", "").strip()
        if not database_url:
            raise OfferMediaAssetStoreError("SUPABASE_DB_URL is required")
        return cls(
            psycopg.connect(
                database_url,
                connect_timeout=15,
                autocommit=True,
                row_factory=dict_row,
            )
        )

    def close(self) -> None:
        self._connection.close()

    def load_dispatch_candidates(
        self,
        *,
        profile: str,
        marketplace: str,
        planned_date: date,
        limit: int,
        only_missing: bool = False,
        subniche: str | None = None,
    ) -> list[InstagramMediaDispatchCandidate]:
        params: list[Any] = [profile, marketplace, planned_date, limit]
        filters = [
            "ready.profile = %s",
            "ready.marketplace = %s",
            "ready.planned_date = %s",
            "ready.is_ready_for_dispatch",
            "ranking.product_link is not null",
            "btrim(ranking.product_link) <> ''",
        ]
        if subniche:
            filters.append("ready.primary_subniche = %s")
            params.insert(3, subniche)
        if only_missing:
            filters.append(
                """
                not exists (
                  select 1
                  from offers.offer_media_assets media
                  where media.profile = ready.profile
                    and media.marketplace = ready.marketplace
                    and media.item_id = ready.item_id
                    and media.status = 'valid'
                )
                """
            )

        rows = self._connection.execute(
            f"""
            select
              ready.dispatch_plan_id,
              ready.profile,
              ready.marketplace,
              ready.stable_key,
              ready.item_id,
              null::bigint as shop_id,
              ranking.product_link,
              ready.planned_date,
              ready.planned_hour,
              ready.slot_sequence,
              ready.daily_sequence,
              ready.primary_subniche
            from offers.v_daily_dispatch_ready ready
            join offers.v_offer_ranking_current ranking
              on ranking.profile = ready.profile
             and ranking.marketplace = ready.marketplace
             and ranking.stable_key = ready.stable_key
            where {" and ".join(filters)}
            order by
              ready.planned_date,
              ready.planned_hour,
              ready.slot_sequence,
              ready.daily_sequence
            limit %s
            """,
            tuple(params),
        ).fetchall()
        return [
            InstagramMediaDispatchCandidate(
                dispatch_plan_id=str(row["dispatch_plan_id"]),
                profile=str(row["profile"]),
                marketplace=str(row["marketplace"]),
                stable_key=str(row["stable_key"]),
                item_id=int(row["item_id"]),
                shop_id=int(row["shop_id"]) if row["shop_id"] is not None else None,
                product_link=str(row["product_link"]),
                planned_date=row["planned_date"],
                planned_hour=int(row["planned_hour"]),
                slot_sequence=int(row["slot_sequence"]),
                daily_sequence=int(row["daily_sequence"]),
                primary_subniche=str(row["primary_subniche"]),
            )
            for row in rows
        ]

    def upsert_media_asset(self, asset: OfferMediaAssetUpsert) -> str:
        row = self._connection.execute(
            """
            insert into offers.offer_media_assets (
              profile,
              marketplace,
              item_id,
              shop_id,
              product_link,
              image_urls,
              video_url,
              source,
              status,
              resolved_at,
              last_checked_at,
              error_detail
            )
            values (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s)
            on conflict (profile, marketplace, item_id)
            do update
            set shop_id = excluded.shop_id,
                product_link = excluded.product_link,
                image_urls = excluded.image_urls,
                video_url = excluded.video_url,
                source = excluded.source,
                status = excluded.status,
                resolved_at = excluded.resolved_at,
                last_checked_at = excluded.last_checked_at,
                error_detail = excluded.error_detail,
                updated_at = now()
            returning media_asset_id
            """,
            (
                asset.profile,
                asset.marketplace,
                asset.item_id,
                asset.shop_id,
                asset.product_link,
                Jsonb(list(asset.image_urls)),
                asset.video_url,
                asset.source,
                asset.status,
                asset.resolved_at,
                asset.last_checked_at,
                asset.error_detail,
            ),
        ).fetchone()
        if row is None:
            raise OfferMediaAssetStoreError("offer media asset upsert did not return id")
        return str(row["media_asset_id"] if isinstance(row, dict) else row[0])


def build_offer_media_asset_upsert(
    *,
    profile: str,
    marketplace: str,
    product_link: str,
    scrape_result: ScrapeResult | None,
    error_detail: str | None = None,
    item_id: int | None = None,
    shop_id: int | None = None,
) -> OfferMediaAssetUpsert:
    now = datetime.now(UTC)
    resolved_at = scrape_result.scraped_at if scrape_result is not None else now
    resolved_item_id = item_id or _optional_int(scrape_result.item_id if scrape_result else None)
    if resolved_item_id is None:
        raise OfferMediaAssetStoreError("item_id is required")
    resolved_shop_id = shop_id or _optional_int(scrape_result.shop_id if scrape_result else None)

    valid_assets = [
        asset
        for asset in (scrape_result.assets if scrape_result is not None else [])
        if asset.status == "valid"
    ]
    image_urls = tuple(
        asset.media_url for asset in valid_assets if asset.media_type == "image"
    )
    video_url = next(
        (asset.media_url for asset in valid_assets if asset.media_type == "video"),
        None,
    )
    failed_assets = [
        asset
        for asset in (scrape_result.assets if scrape_result is not None else [])
        if asset.status not in ("valid", "not_validated")
    ]

    if image_urls or video_url:
        status = "valid"
        consolidated_error = error_detail
    elif error_detail:
        status = "failed"
        consolidated_error = error_detail
    elif failed_assets:
        status = "failed"
        consolidated_error = "; ".join(
            filter(None, (asset.error_detail or asset.status for asset in failed_assets))
        )
    else:
        status = "no_media"
        consolidated_error = None

    return OfferMediaAssetUpsert(
        profile=profile,
        marketplace=marketplace,
        item_id=resolved_item_id,
        shop_id=resolved_shop_id,
        product_link=product_link,
        image_urls=image_urls,
        video_url=video_url,
        status=status,
        resolved_at=resolved_at,
        last_checked_at=now,
        error_detail=consolidated_error,
    )


def _optional_int(value: str | int | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
