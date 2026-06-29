from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv

EXPECTED_RELATIONS = {
    ("catalog_imports", "BASE TABLE"),
    ("catalog_items", "BASE TABLE"),
    ("offer_selection_state", "BASE TABLE"),
    ("schema_migrations", "BASE TABLE"),
    ("v_offer_ranking_current", "VIEW"),
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
            'offer_selection_state'
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


def main() -> int:
    connection = connect()
    try:
        relations = validate_relations(connection)
        validate_control_columns(connection)
        validate_score_columns(connection)
        validate_security(connection)
        validate_score_fixture(connection)
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
    print("SCHEMA_VALIDATION=OK")
    print("ROLLBACK_ONLY_FIXTURE=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
