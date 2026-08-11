from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from ofertas_bot.candidate_refresh import (
    ATTEMPT_STATUSES,
    REFRESH_SOURCE,
    CandidateRefreshError,
    DiscoveryCandidate,
    ScoringCandidate,
    SnapshotInput,
    seller_key_from_link,
)


class SupabaseCandidateRefreshStore:
    def __init__(self, connection: psycopg.Connection[dict[str, object]]) -> None:
        self._connection = connection

    @classmethod
    def connect_from_env(cls) -> SupabaseCandidateRefreshStore:
        load_dotenv()
        database_url = os.getenv("SUPABASE_DB_URL", "").strip()
        if not database_url:
            raise CandidateRefreshError("SUPABASE_DB_URL is required")
        connection = psycopg.connect(
            database_url,
            connect_timeout=15,
            autocommit=True,
            row_factory=dict_row,
        )
        return cls(connection)

    def close(self) -> None:
        self._connection.close()

    def load_ttl_hours(self, *, profile: str, marketplace: str) -> int:
        row = self._connection.execute(
            """
            select ttl_hours
            from offers.candidate_refresh_policies
            where profile = %s and marketplace = %s
            """,
            (profile, marketplace),
        ).fetchone()
        if row is None:
            raise CandidateRefreshError(
                f"candidate refresh policy not found: {profile}/{marketplace}"
            )
        return int(row["ttl_hours"])

    def load_discovery_candidates(
        self,
        *,
        profile: str,
        marketplace: str,
        item_ids: Sequence[int] | None = None,
    ) -> list[DiscoveryCandidate]:
        params: list[object] = [profile, marketplace]
        item_filter = ""
        if item_ids is not None:
            if not item_ids:
                return []
            item_filter = "and ranking.item_id = any(%s)"
            params.append(list(item_ids))
        rows = self._connection.execute(
            f"""
            select
              ranking.catalog_item_id,
              ranking.profile,
              ranking.marketplace,
              ranking.stable_key,
              ranking.item_id,
              ranking.product_name,
              ranking.product_link,
              ranking.image_url,
              ranking.subniches,
              ranking.primary_subniche,
              ranking.refresh_status,
              ranking.last_checked_at,
              status.last_attempted_at,
              status.last_attempt_status,
              ranking.rank_profile,
              ranking.rank_subniche,
              ranking.commercial_score,
              ranking.is_eligible,
              ranking.commercial_data_source
            from offers.v_offer_ranking_current ranking
            join offers.v_offer_refresh_status status
              on status.catalog_item_id = ranking.catalog_item_id
            where ranking.profile = %s
              and ranking.marketplace = %s
              {item_filter}
            """,
            params,
        ).fetchall()
        candidates = [_discovery_candidate(row) for row in rows]
        if item_ids is None:
            return candidates
        by_item = {candidate.item_id: candidate for candidate in candidates}
        missing = [item_id for item_id in item_ids if item_id not in by_item]
        if missing:
            raise CandidateRefreshError(
                f"itemIds not found in active {profile} catalog: {missing}"
            )
        return [by_item[item_id] for item_id in item_ids]

    def load_scoring_candidates(
        self,
        *,
        profile: str,
        marketplace: str,
        item_ids: Sequence[int],
    ) -> list[ScoringCandidate]:
        if not item_ids:
            return []
        rows = self._connection.execute(
            """
            select
              profile,
              marketplace,
              stable_key,
              item_id,
              product_name,
              product_link,
              offer_link,
              image_url,
              subniches,
              primary_subniche,
              shop_id,
              price,
              reference_price,
              commission_rate,
              sales_count,
              rating,
              shop_type_code,
              last_checked_at,
              cooldown_until
            from offers.v_offer_scoring_current
            where profile = %s
              and marketplace = %s
              and item_id = any(%s)
              and is_scoring_ready
            """,
            (profile, marketplace, list(item_ids)),
        ).fetchall()
        by_item = {int(row["item_id"]): _scoring_candidate(row) for row in rows}
        return [by_item[item_id] for item_id in item_ids if item_id in by_item]

    def record_success(self, *, profile: str, snapshot: SnapshotInput) -> int:
        with self._connection.transaction():
            row = self._connection.execute(
                """
                insert into offers.offer_snapshots (
                  marketplace,
                  item_id,
                  checked_at,
                  shop_id,
                  product_name,
                  product_link,
                  offer_link,
                  image_url,
                  price,
                  price_min,
                  price_max,
                  price_discount_rate,
                  commission_rate,
                  commission_amount,
                  seller_commission_rate,
                  shopee_commission_rate,
                  app_exist_rate,
                  app_new_rate,
                  web_exist_rate,
                  web_new_rate,
                  sales_count,
                  rating,
                  shop_type_codes,
                  product_cat_ids,
                  period_start_time,
                  period_end_time,
                  source,
                  source_payload
                )
                values (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                returning id
                """,
                (
                    snapshot.marketplace,
                    snapshot.item_id,
                    snapshot.checked_at,
                    snapshot.shop_id,
                    snapshot.product_name,
                    snapshot.product_link,
                    snapshot.offer_link,
                    snapshot.image_url,
                    snapshot.price,
                    snapshot.price_min,
                    snapshot.price_max,
                    snapshot.price_discount_rate,
                    snapshot.commission_rate,
                    snapshot.commission_amount,
                    snapshot.seller_commission_rate,
                    snapshot.shopee_commission_rate,
                    snapshot.app_exist_rate,
                    snapshot.app_new_rate,
                    snapshot.web_exist_rate,
                    snapshot.web_new_rate,
                    snapshot.sales_count,
                    snapshot.rating,
                    list(snapshot.shop_type_codes),
                    list(snapshot.product_cat_ids),
                    snapshot.period_start_time,
                    snapshot.period_end_time,
                    REFRESH_SOURCE,
                    Jsonb(snapshot.source_payload),
                ),
            ).fetchone()
            snapshot_id = int(row["id"])
            self._connection.execute(
                """
                insert into offers.offer_refresh_attempts (
                  profile,
                  marketplace,
                  item_id,
                  attempted_at,
                  status,
                  snapshot_id,
                  source
                )
                values (%s, %s, %s, %s, 'success', %s, %s)
                """,
                (
                    profile,
                    snapshot.marketplace,
                    snapshot.item_id,
                    snapshot.checked_at,
                    snapshot_id,
                    REFRESH_SOURCE,
                ),
            )
        return snapshot_id

    def record_failure(
        self,
        *,
        profile: str,
        marketplace: str,
        item_id: int,
        attempted_at: datetime,
        status: str,
        error_type: str,
        error_detail: str,
    ) -> None:
        if status not in ATTEMPT_STATUSES or status == "success":
            raise CandidateRefreshError(f"invalid failure attempt status: {status}")
        self._connection.execute(
            """
            insert into offers.offer_refresh_attempts (
              profile,
              marketplace,
              item_id,
              attempted_at,
              status,
              error_type,
              error_detail,
              source
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                profile,
                marketplace,
                item_id,
                attempted_at,
                status,
                error_type[:200],
                error_detail[:2000],
                REFRESH_SOURCE,
            ),
        )


def _discovery_candidate(row: dict[str, object]) -> DiscoveryCandidate:
    item_id = int(row["item_id"])
    product_link = str(row["product_link"])
    subniches = tuple(str(item) for item in (row["subniches"] or []))
    return DiscoveryCandidate(
        catalog_item_id=int(row["catalog_item_id"]),
        profile=str(row["profile"]),
        marketplace=str(row["marketplace"]),
        stable_key=str(row["stable_key"]),
        item_id=item_id,
        product_name=str(row["product_name"]),
        product_link=product_link,
        image_url=str(row["image_url"]) if row["image_url"] else None,
        subniches=subniches,
        primary_subniche=str(row["primary_subniche"]),
        refresh_status=str(row["refresh_status"]),
        last_checked_at=_optional_datetime(row["last_checked_at"]),
        last_attempted_at=_optional_datetime(row["last_attempted_at"]),
        last_attempt_status=(
            str(row["last_attempt_status"]) if row["last_attempt_status"] else None
        ),
        seller_key=seller_key_from_link(product_link, item_id),
        rank_profile=int(row["rank_profile"]) if row["rank_profile"] is not None else None,
        rank_subniche=(
            int(row["rank_subniche"]) if row["rank_subniche"] is not None else None
        ),
        commercial_score=(
            Decimal(row["commercial_score"])
            if row["commercial_score"] is not None
            else None
        ),
        is_eligible=bool(row["is_eligible"]),
        commercial_data_source=str(row["commercial_data_source"]),
    )


def _scoring_candidate(row: dict[str, object]) -> ScoringCandidate:
    return ScoringCandidate(
        profile=str(row["profile"]),
        marketplace=str(row["marketplace"]),
        stable_key=str(row["stable_key"]),
        item_id=int(row["item_id"]),
        product_name=str(row["product_name"]),
        product_link=str(row["product_link"]),
        offer_link=str(row["offer_link"]),
        image_url=str(row["image_url"]) if row["image_url"] else None,
        subniches=tuple(str(item) for item in (row["subniches"] or [])),
        primary_subniche=str(row["primary_subniche"]),
        shop_id=int(row["shop_id"]) if row["shop_id"] is not None else None,
        price=Decimal(row["price"]),
        reference_price=(
            Decimal(row["reference_price"]) if row["reference_price"] is not None else None
        ),
        commission_rate=Decimal(row["commission_rate"]),
        sales_count=int(row["sales_count"] or 0),
        rating=Decimal(row["rating"]) if row["rating"] is not None else None,
        shop_type_code=(
            int(row["shop_type_code"]) if row["shop_type_code"] is not None else None
        ),
        last_checked_at=_optional_datetime(row["last_checked_at"]),
        cooldown_until=_optional_datetime(row["cooldown_until"]),
    )


def _optional_datetime(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None
