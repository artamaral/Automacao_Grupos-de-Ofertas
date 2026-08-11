from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv

EXPECTED_RELATIONS = {
    ("candidate_refresh_policies", "BASE TABLE"),
    ("catalog_imports", "BASE TABLE"),
    ("catalog_items", "BASE TABLE"),
    ("offer_refresh_attempts", "BASE TABLE"),
    ("offer_selection_state", "BASE TABLE"),
    ("offer_snapshots", "BASE TABLE"),
    ("publication_events", "BASE TABLE"),
    ("schema_migrations", "BASE TABLE"),
    ("v_offer_latest_snapshot", "VIEW"),
    ("v_offer_ranking_current", "VIEW"),
    ("v_offer_refresh_status", "VIEW"),
    ("v_offer_scoring_current", "VIEW"),
}

EXPECTED_CONTROL_COLUMNS = {
    "selected_at",
    "cooldown_until",
    "last_sent_at",
    "selection_count",
    "selection_reason",
    "selection_bucket",
    "similarity_status",
    "refresh_iteration",
    "fields_changed",
    "stability_reached",
    "rescored_at",
}

EXPECTED_SCORE_COLUMNS = {
    "score_version",
    "discount_percent",
    "discount_score",
    "commission_score",
    "sales_score",
    "rating_score",
    "shipping_score",
    "shop_type_score",
    "commercial_score",
    "score_reasons",
    "is_eligible",
    "ineligibility_reasons",
    "rank_profile",
    "rank_subniche",
}

EXPECTED_PUBLICATION_EVENT_COLUMNS = {
    "publish_id",
    "profile",
    "marketplace",
    "stable_key",
    "item_id",
    "target",
    "channel_adapter",
    "delivery_status",
    "manifest_item_number",
    "artifact_generated_at",
    "manifest_created_at",
    "planned_at",
    "sent_at",
    "offer_title",
    "offer_url",
    "offer_price",
    "message_text",
    "payload",
    "created_at",
    "updated_at",
}

EXPECTED_SNAPSHOT_COLUMNS = {
    "item_id",
    "checked_at",
    "price",
    "price_max",
    "commission_rate",
    "seller_commission_rate",
    "shopee_commission_rate",
    "sales_count",
    "rating",
    "shop_type_codes",
    "source",
    "source_payload",
}

EXPECTED_REFRESH_STATUS_COLUMNS = {
    "item_id",
    "profile",
    "subniches",
    "last_checked_at",
    "last_attempted_at",
    "refresh_status",
    "age_hours",
}

EXPECTED_SCORING_CURRENT_COLUMNS = {
    "item_id",
    "profile",
    "product_name",
    "subniches",
    "last_checked_at",
    "refresh_status",
    "price",
    "reference_price",
    "discount_percent",
    "commission_rate",
    "sales_count",
    "rating",
    "is_free_shipping",
    "shop_type_code",
    "is_scoring_ready",
}


def connect() -> psycopg.Connection:
    load_dotenv()
    database_url = os.getenv("SUPABASE_DB_URL")
    if not database_url:
        raise ValueError("SUPABASE_DB_URL is required")
    return psycopg.connect(database_url, connect_timeout=15)


def database_target_summary() -> tuple[str, str]:
    database_url = os.environ["SUPABASE_DB_URL"]
    parsed = urlparse(database_url)
    username = parsed.username or ""
    project_ref = username.rsplit(".", maxsplit=1)[-1] if "." in username else "unknown"
    masked_ref = (
        f"{project_ref[:4]}...{project_ref[-4:]}"
        if len(project_ref) > 8
        else project_ref
    )
    host_kind = (
        "pooler"
        if (parsed.hostname or "").endswith("pooler.supabase.com")
        else "direct"
    )
    return masked_ref, host_kind


def validate_relations(connection: psycopg.Connection) -> list[tuple[str, str]]:
    rows = connection.execute(
        """
        select table_name, table_type
        from information_schema.tables
        where table_schema = 'offers'
        """
    ).fetchall()
    actual = {(name, relation_type) for name, relation_type in rows}
    missing = EXPECTED_RELATIONS - actual
    if missing:
        raise AssertionError(f"missing offers relations: {sorted(missing)}")
    return sorted(actual)


def validate_control_columns(connection: psycopg.Connection) -> None:
    rows = connection.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema = 'offers'
          and table_name = 'offer_selection_state'
        """
    ).fetchall()
    actual = {row[0] for row in rows}
    missing = EXPECTED_CONTROL_COLUMNS - actual
    if missing:
        raise AssertionError(f"missing selection control columns: {sorted(missing)}")


def validate_score_columns(connection: psycopg.Connection) -> None:
    rows = connection.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema = 'offers'
          and table_name = 'v_offer_ranking_current'
        """
    ).fetchall()
    actual = {row[0] for row in rows}
    missing = EXPECTED_SCORE_COLUMNS - actual
    if missing:
        raise AssertionError(f"missing score view columns: {sorted(missing)}")


def validate_publication_event_columns(connection: psycopg.Connection) -> None:
    rows = connection.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema = 'offers'
          and table_name = 'publication_events'
        """
    ).fetchall()
    actual = {row[0] for row in rows}
    missing = EXPECTED_PUBLICATION_EVENT_COLUMNS - actual
    if missing:
        raise AssertionError(f"missing publication event columns: {sorted(missing)}")


def validate_candidate_refresh_columns(connection: psycopg.Connection) -> None:
    expected_by_relation = {
        "offer_snapshots": EXPECTED_SNAPSHOT_COLUMNS,
        "v_offer_refresh_status": EXPECTED_REFRESH_STATUS_COLUMNS,
        "v_offer_scoring_current": EXPECTED_SCORING_CURRENT_COLUMNS,
    }
    for relation_name, expected in expected_by_relation.items():
        rows = connection.execute(
            """
            select column_name
            from information_schema.columns
            where table_schema = 'offers'
              and table_name = %s
            """,
            (relation_name,),
        ).fetchall()
        actual = {row[0] for row in rows}
        missing = expected - actual
        if missing:
            raise AssertionError(
                f"missing {relation_name} columns: {sorted(missing)}"
            )


def validate_security(connection: psycopg.Connection) -> None:
    rows = connection.execute(
        """
        select relname, relrowsecurity
        from pg_class
        join pg_namespace on pg_namespace.oid = pg_class.relnamespace
        where pg_namespace.nspname = 'offers'
          and relname in (
            'schema_migrations',
            'catalog_imports',
            'catalog_items',
            'candidate_refresh_policies',
            'offer_snapshots',
            'offer_refresh_attempts',
            'offer_selection_state',
            'publication_events'
          )
        """
    ).fetchall()
    without_rls = sorted(name for name, rls_enabled in rows if not rls_enabled)
    if without_rls:
        raise AssertionError(f"offers tables without RLS: {without_rls}")

    public_grants = connection.execute(
        """
        select grantee, table_name, privilege_type
        from information_schema.role_table_grants
        where table_schema = 'offers'
          and grantee in ('anon', 'authenticated')
        order by grantee, table_name, privilege_type
        """
    ).fetchall()
    if public_grants:
        raise AssertionError(f"unexpected public offers grants: {public_grants!r}")


def validate_active_catalogs(
    connection: psycopg.Connection,
) -> list[tuple[str, int, int, int, int, int, str]]:
    rows = connection.execute(
        """
        select
          imp.profile,
          imp.row_count,
          (select count(*) from offers.catalog_items item where item.import_id = imp.id),
          (
            select count(*)
            from offers.v_offer_ranking_current ranking
            where ranking.import_id = imp.id
          ),
          (
            select count(*)
            from offers.v_offer_ranking_current ranking
            where ranking.import_id = imp.id
              and ranking.is_eligible
          ),
          (
            select count(distinct ranking.primary_subniche)
            from offers.v_offer_ranking_current ranking
            where ranking.import_id = imp.id
          ),
          left(imp.source_sha256, 12)
        from offers.catalog_imports imp
        where imp.status = 'active'
        order by imp.profile
        """
    ).fetchall()

    for profile, declared, stored, ranked, eligible, _, _ in rows:
        if declared != stored or stored != ranked:
            raise AssertionError(
                f"catalog count mismatch for {profile}: "
                f"declared={declared} stored={stored} ranked={ranked}"
            )
        rank_stats = connection.execute(
            """
            select count(rank_profile), count(distinct rank_profile), max(rank_profile)
            from offers.v_offer_ranking_current
            where profile = %s
              and is_eligible
            """,
            (profile,),
        ).fetchone()
        ranked_count, distinct_rank_count, max_rank = rank_stats
        if (ranked_count, distinct_rank_count, max_rank) != (
            eligible,
            eligible,
            eligible,
        ):
            raise AssertionError(
                f"profile ranking is not contiguous for {profile}: {rank_stats!r}"
            )
    return rows


def validate_score_fixture(connection: psycopg.Connection) -> None:
    stable_key = "a" * 64
    source_sha256 = "b" * 64
    import_id = connection.execute(
        """
        insert into offers.catalog_imports (
          profile,
          marketplace,
          source_path,
          source_sha256,
          row_count,
          status,
          activated_at,
          validation_summary
        )
        values (
          'schema-validation',
          'shopee',
          'rollback-only.csv',
          %s,
          1,
          'active',
          now(),
          '{"rollback_only": true}'::jsonb
        )
        returning id
        """,
        (source_sha256,),
    ).fetchone()[0]

    connection.execute(
        """
        insert into offers.catalog_items (
          import_id,
          profile,
          marketplace,
          stable_key,
          item_id,
          product_name,
          product_link,
          offer_link,
          price,
          reference_price,
          sales_count,
          rating,
          shop_type_codes,
          seller_commission_rate,
          shopee_commission_rate,
          is_free_shipping,
          subniches,
          source_row_number
        )
        values (
          %s,
          'schema-validation',
          'shopee',
          %s,
          999999999,
          'Oferta de validacao',
          'https://example.com/product/999999999',
          'https://example.com/offer/999999999',
          70,
          100,
          250,
          4.8,
          array[2]::smallint[],
          0.05,
          0.02,
          true,
          array['validacao'],
          2
        )
        """,
        (import_id, stable_key),
    )

    score_row = connection.execute(
        """
        select
          score_version,
          discount_score,
          commission_score,
          sales_score,
          rating_score,
          shipping_score,
          shop_type_score,
          commercial_score,
          is_eligible,
          rank_profile,
          rank_subniche
        from offers.v_offer_ranking_current
        where profile = 'schema-validation'
          and stable_key = %s
        """,
        (stable_key,),
    ).fetchone()

    expected = (
        "commercial_v1",
        Decimal("15.00"),
        Decimal("7.00"),
        Decimal("2.50"),
        Decimal("10.00"),
        Decimal("8.00"),
        Decimal("5.00"),
        Decimal("47.50"),
        True,
        1,
        1,
    )
    if score_row != expected:
        raise AssertionError(f"unexpected score fixture result: {score_row!r}")

    connection.execute(
        """
        insert into offers.offer_selection_state (
          profile,
          marketplace,
          stable_key,
          item_id,
          selected_at,
          cooldown_until,
          selection_count,
          selection_reason
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            "schema-validation",
            "shopee",
            stable_key,
            999999999,
            datetime.now(UTC),
            datetime.now(UTC) + timedelta(hours=24),
            1,
            "rollback-only validation",
        ),
    )

    eligibility_row = connection.execute(
        """
        select is_eligible, ineligibility_reasons, rank_profile, rank_subniche
        from offers.v_offer_ranking_current
        where profile = 'schema-validation'
          and stable_key = %s
        """,
        (stable_key,),
    ).fetchone()
    expected_eligibility = (False, ["cooldown_active"], None, None)
    if eligibility_row != expected_eligibility:
        raise AssertionError(
            f"unexpected cooldown eligibility result: {eligibility_row!r}"
        )


def validate_candidate_refresh_fixture(connection: psycopg.Connection) -> None:
    connection.execute(
        """
        insert into offers.candidate_refresh_policies (profile, marketplace, ttl_hours)
        values ('schema-validation', 'shopee', 24)
        """
    )
    missing_status = connection.execute(
        """
        select refresh_status
        from offers.v_offer_refresh_status
        where profile = 'schema-validation' and item_id = 999999999
        """
    ).fetchone()
    if missing_status != ("MISSING",):
        raise AssertionError(f"unexpected missing refresh status: {missing_status!r}")

    stale_snapshot_id = connection.execute(
        """
        insert into offers.offer_snapshots (
          marketplace,
          item_id,
          checked_at,
          product_name,
          product_link,
          offer_link,
          price,
          price_max,
          commission_rate,
          sales_count,
          rating,
          source,
          source_payload
        )
        values (
          'shopee',
          999999999,
          now() - interval '24 hours',
          'Oferta stale',
          'https://example.com/product/999999999',
          'https://example.com/offer/999999999',
          100,
          120,
          0.10,
          100,
          4.9,
          'schema_validation',
          '{"fixture": "stale"}'::jsonb
        )
        returning id
        """
    ).fetchone()[0]
    stale_status = connection.execute(
        """
        select refresh_status
        from offers.v_offer_refresh_status
        where profile = 'schema-validation' and item_id = 999999999
        """
    ).fetchone()
    if stale_status != ("STALE",):
        raise AssertionError(f"unexpected 24h refresh status: {stale_status!r}")

    fresh_snapshot_id = connection.execute(
        """
        insert into offers.offer_snapshots (
          marketplace,
          item_id,
          checked_at,
          product_name,
          product_link,
          offer_link,
          price,
          price_max,
          commission_rate,
          sales_count,
          rating,
          source,
          source_payload
        )
        values (
          'shopee',
          999999999,
          now(),
          'Oferta fresh',
          'https://example.com/product/999999999',
          'https://example.com/offer/999999999',
          90,
          120,
          0.12,
          110,
          4.9,
          'schema_validation',
          '{"fixture": "fresh"}'::jsonb
        )
        returning id
        """
    ).fetchone()[0]
    history = connection.execute(
        """
        select
          (select count(*) from offers.offer_snapshots where item_id = 999999999),
          latest.id,
          latest.price,
          status.refresh_status,
          scoring.is_scoring_ready
        from offers.v_offer_latest_snapshot latest
        join offers.v_offer_refresh_status status
          on status.marketplace = latest.marketplace and status.item_id = latest.item_id
        join offers.v_offer_scoring_current scoring
          on scoring.marketplace = latest.marketplace and scoring.item_id = latest.item_id
        where latest.marketplace = 'shopee' and latest.item_id = 999999999
        """
    ).fetchone()
    expected = (2, fresh_snapshot_id, Decimal("90.00"), "FRESH", False)
    if history != expected:
        raise AssertionError(
            "unexpected candidate refresh history result: "
            f"stale_snapshot_id={stale_snapshot_id} result={history!r}"
        )


def main() -> int:
    connection = connect()
    try:
        relations = validate_relations(connection)
        validate_control_columns(connection)
        validate_score_columns(connection)
        validate_publication_event_columns(connection)
        validate_candidate_refresh_columns(connection)
        validate_security(connection)
        active_catalogs = validate_active_catalogs(connection)
        validate_score_fixture(connection)
        validate_candidate_refresh_fixture(connection)
        connection.rollback()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    masked_ref, host_kind = database_target_summary()
    print(f"PROJECT_REF_MASKED={masked_ref}")
    print(f"CONNECTION_KIND={host_kind}")
    for relation_name, relation_type in relations:
        print(f"offers.{relation_name} [{relation_type}]")
    for profile, declared, stored, ranked, eligible, subniches, sha_prefix in active_catalogs:
        print(
            "ACTIVE_CATALOG=OK "
            f"profile={profile} "
            f"declared={declared} "
            f"stored={stored} "
            f"ranked={ranked} "
            f"eligible={eligible} "
            f"subniches={subniches} "
            f"sha256={sha_prefix}..."
        )
    print("SCHEMA_VALIDATION=OK")
    print("ROLLBACK_ONLY_FIXTURE=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
