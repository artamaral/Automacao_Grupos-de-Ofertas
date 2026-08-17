from __future__ import annotations

import argparse
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

CONFIRMATION = "REBUILD_PUBLICATION_COOLDOWN_2D"
PROFILE = "feminino"
MARKETPLACE = "shopee"
TIMEZONE = ZoneInfo("America/Sao_Paulo")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect or rebuild publication cooldown state from the ledger."
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--confirm-remote-write",
        help=f"Required with --apply. Expected value: {CONFIRMATION}",
    )
    return parser.parse_args()


def is_rebuild_window(value: datetime) -> bool:
    local = value.astimezone(TIMEZONE)
    return local.hour >= 21 or local.hour < 7


def connect() -> psycopg.Connection[dict[str, object]]:
    load_dotenv()
    database_url = os.getenv("SUPABASE_DB_URL", "").strip()
    if not database_url:
        raise ValueError("SUPABASE_DB_URL is required")
    return psycopg.connect(
        database_url,
        connect_timeout=15,
        row_factory=dict_row,
    )


def inspect(connection: psycopg.Connection[dict[str, object]]) -> dict[str, object]:
    row = connection.execute(
        """
        with confirmed as (
          select stable_key
          from offers.publication_events
          where profile = %s
            and marketplace = %s
            and delivery_status = 'confirmed'
            and sent_at is not null
          group by stable_key
        )
        select
          now() as database_now,
          count(*) as confirmed_items,
          count(*) filter (where state.selection_count > 0) as projected_items,
          count(*) filter (where state.cooldown_until > now()) as active_cooldowns
        from confirmed
        left join offers.offer_selection_state state
          on state.profile = %s
         and state.marketplace = %s
         and state.stable_key = confirmed.stable_key
        """,
        (PROFILE, MARKETPLACE, PROFILE, MARKETPLACE),
    ).fetchone()
    if row is None:
        raise RuntimeError("could not inspect publication cooldown state")
    return row


def mismatch_count(connection: psycopg.Connection[dict[str, object]]) -> int:
    row = connection.execute(
        """
        with expected as (
          select
            stable_key,
            count(*)::integer as selection_count,
            max(sent_at) as last_sent_at,
            (
              ((max(sent_at) at time zone 'America/Sao_Paulo')::date + 3)::timestamp
              at time zone 'America/Sao_Paulo'
            ) as cooldown_until
          from offers.publication_events
          where profile = %s
            and marketplace = %s
            and delivery_status = 'confirmed'
            and sent_at is not null
          group by stable_key
        )
        select count(*) as mismatches
        from expected
        left join offers.offer_selection_state state
          on state.profile = %s
         and state.marketplace = %s
         and state.stable_key = expected.stable_key
        where state.stable_key is null
           or state.selection_count is distinct from expected.selection_count
           or state.last_sent_at is distinct from expected.last_sent_at
           or state.cooldown_until is distinct from expected.cooldown_until
        """,
        (PROFILE, MARKETPLACE, PROFILE, MARKETPLACE),
    ).fetchone()
    return int(row["mismatches"] if row else -1)


def main() -> int:
    args = parse_args()
    if args.apply and args.confirm_remote_write != CONFIRMATION:
        raise ValueError(f"--confirm-remote-write must be exactly {CONFIRMATION}")

    with connect() as connection:
        before = inspect(connection)
        database_now = before["database_now"]
        print(f"database_now={database_now}")
        print(f"confirmed_items={before['confirmed_items']}")
        print(f"projected_items={before['projected_items']}")
        print(f"active_cooldowns={before['active_cooldowns']}")

        if not args.apply:
            print("apply=false")
            return 0
        if not isinstance(database_now, datetime) or not is_rebuild_window(database_now):
            raise ValueError("rebuild is only allowed from 21:00 through 06:59 BRT")

        connection.execute(
            "select pg_advisory_xact_lock(hashtext('publication_cooldown_rebuild'))"
        )
        reconciled = connection.execute(
            "select offers.rebuild_offer_publication_state(%s, %s) as total",
            (PROFILE, MARKETPLACE),
        ).fetchone()
        mismatches = mismatch_count(connection)
        if mismatches:
            raise RuntimeError(f"publication cooldown rebuild mismatches: {mismatches}")

        after = inspect(connection)
        print(f"reconciled_items={reconciled['total'] if reconciled else 0}")
        print(f"projected_items_after={after['projected_items']}")
        print(f"active_cooldowns_after={after['active_cooldowns']}")
        print("apply=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
