from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

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
    ) -> list[DispatchCandidate]:
        rows = self._connection.execute(
            """
            select
              profile, marketplace, stable_key, item_id, primary_subniche,
              commercial_score, sales_count, rating
            from offers.v_offer_ranking_current
            where profile = %s
              and marketplace = %s
              and is_eligible
              and refresh_status = 'FRESH'
              and last_checked_at is not null
              and (last_checked_at at time zone 'America/Sao_Paulo')::date = %s
            order by commercial_score desc, sales_count desc, rating desc nulls last, item_id
            """,
            (profile, marketplace, planned_date),
        ).fetchall()
        return [
            DispatchCandidate(
                profile=str(row["profile"]),
                marketplace=str(row["marketplace"]),
                stable_key=str(row["stable_key"]),
                item_id=int(row["item_id"]),
                primary_subniche=str(row["primary_subniche"]),
                commercial_score=Decimal(row["commercial_score"]),
                sales_count=int(row["sales_count"] or 0),
                rating=Decimal(row["rating"]) if row["rating"] is not None else None,
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
                      profile, marketplace, stable_key, item_id, primary_subniche,
                      commercial_score, selection_bucket, selection_reason,
                      planned_date, planned_hour, slot_sequence, daily_sequence
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            item.candidate.profile,
                            item.candidate.marketplace,
                            item.candidate.stable_key,
                            item.candidate.item_id,
                            item.candidate.primary_subniche,
                            item.candidate.commercial_score,
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
