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
    ("catalog_item_import_history", "BASE TABLE"),
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
    "commercial_data_source",
    "refresh_status",
    "latest_snapshot_id",
    "last_checked_at",
    "age_hours",
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
    "catalog_import_id",
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

EXPECTED_IMPORT_COLUMNS = {
    "observed_at",
    "source_sha256",
    "status",
    "validation_summary",
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
    "commercial_data_source",
    "latest_snapshot_id",
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
        "catalog_imports": EXPECTED_IMPORT_COLUMNS,
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
            'catalog_item_import_history',
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


def validate_incremental_catalog_contract(connection: psycopg.Connection) -> None:
    invalid_statuses = connection.execute(
        """
        select array_agg(distinct status order by status)
        from offers.catalog_imports
        where status not in ('completed', 'rejected')
        """
    ).fetchone()[0]
    if invalid_statuses:
        raise AssertionError(f"unexpected catalog import statuses: {invalid_statuses!r}")

    activation_function = connection.execute(
        "select to_regprocedure('offers.activate_catalog_import(uuid)')"
    ).fetchone()[0]
    if activation_function is not None:
        raise AssertionError("legacy activate_catalog_import function still exists")

    duplicate_identity = connection.execute(
        """
        select profile, marketplace, item_id, count(*)
        from offers.catalog_items
        group by profile, marketplace, item_id
        having count(*) > 1
        limit 1
        """
    ).fetchone()
    if duplicate_identity is not None:
        raise AssertionError(f"duplicate persistent catalog identity: {duplicate_identity!r}")

    required_indexes = (
        "offers.catalog_items_profile_marketplace_item_id_idx",
        "offers.catalog_items_profile_marketplace_stable_key_idx",
        "offers.offer_snapshots_catalog_import_item_idx",
    )
    missing_indexes = [
        index_name
        for index_name in required_indexes
        if connection.execute("select to_regclass(%s)", (index_name,)).fetchone()[0]
        is None
    ]
    if missing_indexes:
        raise AssertionError(f"missing incremental catalog indexes: {missing_indexes!r}")

    view_definitions = connection.execute(
        """
        select viewname, lower(definition)
        from pg_views
        where schemaname = 'offers'
          and viewname in ('v_offer_refresh_status', 'v_offer_ranking_current')
        """
    ).fetchall()
    legacy_filters = [
        name for name, definition in view_definitions if "status = 'active'" in definition
    ]
    if legacy_filters:
        raise AssertionError(f"views still filter active imports: {legacy_filters!r}")


def validate_persistent_catalog(
    connection: psycopg.Connection,
) -> list[tuple[str, int, int, int, int]]:
    rows = connection.execute(
        """
        with stored as (
          select
            profile,
            marketplace,
            count(*) as stored_count,
            count(distinct item_id) as distinct_item_count,
            count(distinct stable_key) as distinct_stable_key_count
          from offers.catalog_items
          group by profile, marketplace
        ),
        ranked as (
          select
            profile,
            marketplace,
            count(*) as ranked_count,
            count(*) filter (where is_eligible) as eligible_count,
            count(distinct primary_subniche) as subniche_count,
            count(rank_profile) filter (where is_eligible) as rank_count,
            count(distinct rank_profile) filter (where is_eligible)
              as distinct_rank_count,
            max(rank_profile) filter (where is_eligible) as max_rank
          from offers.v_offer_ranking_current
          group by profile, marketplace
        )
        select
          stored.profile,
          stored.stored_count,
          stored.distinct_item_count,
          stored.distinct_stable_key_count,
          ranked.ranked_count,
          ranked.eligible_count,
          ranked.subniche_count,
          ranked.rank_count,
          ranked.distinct_rank_count,
          ranked.max_rank
        from stored
        join ranked
          on ranked.profile = stored.profile
         and ranked.marketplace = stored.marketplace
        order by stored.profile
        """
    ).fetchall()

    results: list[tuple[str, int, int, int, int]] = []
    for row in rows:
        (
            profile,
            stored_count,
            distinct_item_count,
            distinct_stable_key_count,
            ranked_count,
            eligible,
            subniche_count,
            rank_count,
            distinct_rank_count,
            max_rank,
        ) = row
        if (
            stored_count != distinct_item_count
            or stored_count != distinct_stable_key_count
            or stored_count != ranked_count
        ):
            raise AssertionError(
                f"catalog count mismatch for {profile}: "
                f"stored={stored_count} item_ids={distinct_item_count} "
                f"stable_keys={distinct_stable_key_count} ranked={ranked_count}"
            )
        if (rank_count, distinct_rank_count, max_rank) != (
            eligible,
            eligible,
            eligible,
        ):
            raise AssertionError(
                f"profile ranking is not contiguous for {profile}: "
                f"{(rank_count, distinct_rank_count, max_rank)!r}"
            )
        results.append(
            (
                profile,
                stored_count,
                ranked_count,
                eligible,
                subniche_count,
            )
        )
    return results


def validate_score_fixture(connection: psycopg.Connection) -> None:
    stable_key = "a" * 64
    source_sha256 = "b" * 64
    connection.execute(
        """
        insert into offers.candidate_refresh_policies (profile, marketplace, ttl_hours)
        values ('schema-validation', 'shopee', 24)
        on conflict (profile, marketplace) do nothing
        """
    )
    import_id = connection.execute(
        """
        insert into offers.catalog_imports (
          profile,
          marketplace,
          source_path,
          source_sha256,
          observed_at,
          row_count,
          status,
          validation_summary
        )
        values (
          'schema-validation',
          'shopee',
          'rollback-only.csv',
          %s,
          now(),
          1,
          'completed',
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
          rank_subniche,
          commercial_data_source,
          refresh_status,
          latest_snapshot_id
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
        "catalog",
        "MISSING",
        None,
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
        on conflict (profile, marketplace) do nothing
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
    stale_ranking = connection.execute(
        """
        select price, commercial_data_source, refresh_status, latest_snapshot_id
        from offers.v_offer_ranking_current
        where profile = 'schema-validation' and item_id = 999999999
        """
    ).fetchone()
    expected_stale_ranking = (
        Decimal("100.00"),
        "snapshot",
        "STALE",
        stale_snapshot_id,
    )
    if stale_ranking != expected_stale_ranking:
        raise AssertionError(f"unexpected stale ranking result: {stale_ranking!r}")

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
          scoring.is_scoring_ready,
          ranking.price,
          ranking.commercial_data_source,
          ranking.latest_snapshot_id
        from offers.v_offer_latest_snapshot latest
        join offers.v_offer_refresh_status status
          on status.marketplace = latest.marketplace and status.item_id = latest.item_id
        join offers.v_offer_scoring_current scoring
          on scoring.marketplace = latest.marketplace and scoring.item_id = latest.item_id
        join offers.v_offer_ranking_current ranking
          on ranking.marketplace = latest.marketplace and ranking.item_id = latest.item_id
        where latest.marketplace = 'shopee' and latest.item_id = 999999999
        """
    ).fetchone()
    expected = (
        2,
        fresh_snapshot_id,
        Decimal("90.00"),
        "FRESH",
        False,
        Decimal("90.00"),
        "snapshot",
        fresh_snapshot_id,
    )
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
        validate_incremental_catalog_contract(connection)
        persistent_catalog = validate_persistent_catalog(connection)
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
    for profile, stored, ranked, eligible, subniches in persistent_catalog:
        print(
            "PERSISTENT_CATALOG=OK "
            f"profile={profile} "
            f"stored={stored} "
            f"ranked={ranked} "
            f"eligible={eligible} "
            f"subniches={subniches}"
        )
    print("SCHEMA_VALIDATION=OK")
    print("ROLLBACK_ONLY_FIXTURE=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
