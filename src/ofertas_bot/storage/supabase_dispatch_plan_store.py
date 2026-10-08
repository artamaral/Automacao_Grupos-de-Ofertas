from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from ofertas_bot.daily_dispatch_planner import DispatchCandidate, PlannedDispatch


class SupabaseDispatchPlanStore:
    def __init__(self, connection: psycopg.Connection[dict[str, object]]) -> None:
        self._connection = connection

    @classmethod
    def connect_from_env(cls) -> SupabaseDispatchPlanStore:
        load_dotenv()
        database_url = os.getenv("SUPABASE_DB_URL", "").strip()
        if not database_url:
            raise ValueError("SUPABASE_DB_URL is required")
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

    def load_candidates(
        self,
        *,
        profile: str,
        marketplace: str,
        planned_date: date,
        productcatid_only: bool = False,
    ) -> list[DispatchCandidate]:
        ranking_view = (
            "offers.v_offer_ranking_productcatid_current"
            if productcatid_only
            else "offers.v_offer_ranking_current"
        )
        eligibility_column = (
            "ranking.is_productcatid_eligible"
            if productcatid_only
            else "ranking.is_eligible"
        )
        refresh_cutoff = (
            "and (ranking.refresh_required_after is null "
            "or ranking.last_checked_at >= ranking.refresh_required_after)"
            if productcatid_only
            else ""
        )
        rows = self._connection.execute(
            f"""
            select
              ranking.profile, ranking.marketplace, ranking.stable_key, ranking.item_id,
              ranking.product_cat_id, ranking.primary_subniche, ranking.commercial_score,
              ranking.sales_count, ranking.rating, catalog.selection_mode,
              ranking.product_name, ranking.offer_link, ranking.image_url, ranking.price,
              ranking.reference_price, ranking.score_reasons, ranking.rank_profile,
              ranking.rank_subniche, ranking.refresh_status, ranking.last_checked_at,
              ranking.latest_snapshot_id
            from {ranking_view} ranking
            join offers.catalog_items catalog on catalog.id = ranking.catalog_item_id
            where ranking.profile = %s
              and ranking.marketplace = %s
              and {eligibility_column}
              and ranking.refresh_status = 'FRESH'
              and ranking.last_checked_at is not null
              {refresh_cutoff}
              and (ranking.last_checked_at at time zone 'America/Sao_Paulo')::date = %s
            order by ranking.commercial_score desc, ranking.sales_count desc,
              ranking.rating desc nulls last, ranking.item_id
            """,
            (profile, marketplace, planned_date),
        ).fetchall()
        return [
            DispatchCandidate(
                profile=str(row["profile"]),
                marketplace=str(row["marketplace"]),
                stable_key=str(row["stable_key"]),
                item_id=int(row["item_id"]),
                product_cat_id=(
                    int(row["product_cat_id"])
                    if row["product_cat_id"] is not None
                    else None
                ),
                primary_subniche=str(row["primary_subniche"]),
                commercial_score=Decimal(row["commercial_score"]),
                sales_count=int(row["sales_count"] or 0),
                rating=Decimal(row["rating"]) if row["rating"] is not None else None,
                selection_mode=(
                    str(row["selection_mode"])
                    if row["selection_mode"] is not None
                    else None
                ),
                product_name=str(row["product_name"]),
                offer_link=str(row["offer_link"]),
                image_url=(
                    str(row["image_url"]) if row["image_url"] is not None else None
                ),
                price=Decimal(row["price"]),
                reference_price=(
                    Decimal(row["reference_price"])
                    if row["reference_price"] is not None
                    else None
                ),
                score_reasons=tuple(str(reason) for reason in row["score_reasons"] or ()),
                rank_profile=(
                    int(row["rank_profile"])
                    if row["rank_profile"] is not None
                    else None
                ),
                rank_subniche=(
                    int(row["rank_subniche"])
                    if row["rank_subniche"] is not None
                    else None
                ),
                refresh_status=str(row["refresh_status"]),
                last_checked_at=(
                    row["last_checked_at"]
                    if isinstance(row["last_checked_at"], datetime)
                    else datetime.fromisoformat(str(row["last_checked_at"]))
                ),
                latest_snapshot_id=int(row["latest_snapshot_id"]),
            )
            for row in rows
        ]

    def replace_day(
        self,
        *,
        profile: str,
        marketplace: str,
        planned_date: date,
        items: list[PlannedDispatch],
    ) -> None:
        for item in items:
            self._validate_dispatch_payload(item.candidate, planned_date=planned_date)
        with self._connection.transaction():
            self._connection.execute(
                "select pg_advisory_xact_lock(hashtext(%s))",
                (f"daily-dispatch:{profile}:{marketplace}:{planned_date.isoformat()}",),
            )
            existing = self._connection.execute(
                """
                select count(*) filter (where dispatch_status <> 'planned') as consumed
                from offers.daily_dispatch_plan
                where profile = %s and marketplace = %s and planned_date = %s
                """,
                (profile, marketplace, planned_date),
            ).fetchone()
            if existing and int(existing["consumed"] or 0) > 0:
                raise ValueError("cannot replace a dispatch plan after consumption started")
            self._connection.execute(
                """
                delete from offers.daily_dispatch_plan
                where profile = %s and marketplace = %s and planned_date = %s
                """,
                (profile, marketplace, planned_date),
            )
            with self._connection.cursor() as cursor:
                cursor.executemany(
                    """
                    insert into offers.daily_dispatch_plan (
                      profile, marketplace, stable_key, item_id, product_cat_id, primary_subniche,
                      commercial_score, product_name, source_offer_link, image_url, price,
                      reference_price, sales_count, rating, score_reasons, rank_profile,
                      rank_subniche, refresh_status, last_checked_at, latest_snapshot_id,
                      selection_bucket, selection_reason,
                      planned_date, planned_hour, slot_sequence, daily_sequence
                    )
                    values (
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s, %s
                    )
                    """,
                    [
                        (
                            item.candidate.profile,
                            item.candidate.marketplace,
                            item.candidate.stable_key,
                            item.candidate.item_id,
                            item.candidate.product_cat_id,
                            item.candidate.primary_subniche,
                            item.candidate.commercial_score,
                            item.candidate.product_name,
                            item.candidate.offer_link,
                            item.candidate.image_url,
                            item.candidate.price,
                            item.candidate.reference_price,
                            item.candidate.sales_count,
                            item.candidate.rating,
                            list(item.candidate.score_reasons),
                            item.candidate.rank_profile,
                            item.candidate.rank_subniche,
                            item.candidate.refresh_status,
                            item.candidate.last_checked_at,
                            item.candidate.latest_snapshot_id,
                            item.selection_bucket,
                            item.selection_reason,
                            item.planned_date,
                            item.planned_hour,
                            item.slot_sequence,
                            item.daily_sequence,
                        )
                        for item in items
                    ],
                )

    @staticmethod
    def _validate_dispatch_payload(
        candidate: DispatchCandidate,
        *,
        planned_date: date,
    ) -> None:
        if not candidate.product_name or not candidate.product_name.strip():
            raise ValueError("dispatch candidate product_name is required")
        if not candidate.offer_link or not candidate.offer_link.strip():
            raise ValueError("dispatch candidate offer_link is required")
        if candidate.price is None or candidate.price <= 0:
            raise ValueError("dispatch candidate price must be positive")
        if candidate.refresh_status != "FRESH":
            raise ValueError("dispatch candidate must be FRESH")
        if candidate.last_checked_at is None:
            raise ValueError("dispatch candidate last_checked_at is required")
        checked_date = candidate.last_checked_at.astimezone(
            ZoneInfo("America/Sao_Paulo")
        ).date()
        if checked_date != planned_date:
            raise ValueError("dispatch candidate snapshot must match planned_date")
        if candidate.latest_snapshot_id is None:
            raise ValueError("dispatch candidate latest_snapshot_id is required")
