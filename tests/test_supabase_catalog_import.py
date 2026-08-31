from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

import scripts.supabase.import_catalog as catalog_import_module
from scripts.supabase.import_catalog import (
    CONFIRMATION,
    CatalogImportError,
    import_catalog,
    parse_observed_at,
    stable_offer_key,
    validate_catalog,
)

FIELDNAMES = [
    "itemId",
    "productName",
    "productLink",
    "offerLink",
    "imageUrl",
    "price",
    "priceMax",
    "sales",
    "ratingStar",
    "shopType",
    "sellerCommissionRate",
    "shopeeCommissionRate",
    "subniches",
]


def write_catalog(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def make_row(*, item_id: str = "123", rating: str = "4.8") -> dict[str, str]:
    return {
        "itemId": item_id,
        "productName": "Produto teste",
        "productLink": f"https://shopee.com.br/product/1/{item_id}",
        "offerLink": f"https://s.shopee.com.br/{item_id}?tracking=abc",
        "imageUrl": "https://example.com/image.jpg",
        "price": "70",
        "priceMax": "100",
        "sales": "250",
        "ratingStar": rating,
        "shopType": "[2]",
        "sellerCommissionRate": "0.05",
        "shopeeCommissionRate": "0.02",
        "subniches": '["teste"]',
    }


def test_validate_catalog_accepts_operational_contract(tmp_path: Path) -> None:
    path = tmp_path / "catalog.csv"
    write_catalog(path, [make_row()])

    validation = validate_catalog(path, profile="feminino", marketplace="shopee")

    assert validation.row_count == 1
    assert str(validation.min_rating) == "4.8"
    assert validation.subniche_count == 1
    assert validation.summary()["contract"] == "clean_catalog_productcatid_rating_4_5_plus_v1"


def test_validate_catalog_rejects_rating_below_operational_cut(tmp_path: Path) -> None:
    path = tmp_path / "catalog.csv"
    write_catalog(path, [make_row(rating="4.49")])

    with pytest.raises(CatalogImportError, match="rating below 4.5"):
        validate_catalog(path, profile="feminino", marketplace="shopee")


def test_validate_catalog_rejects_duplicate_item_id(tmp_path: Path) -> None:
    path = tmp_path / "catalog.csv"
    write_catalog(path, [make_row(), make_row()])

    with pytest.raises(CatalogImportError, match="duplicate itemId"):
        validate_catalog(path, profile="feminino", marketplace="shopee")


def test_stable_offer_key_ignores_query_parameters() -> None:
    first = stable_offer_key("shopee", "https://s.shopee.com.br/abc?one=1")
    second = stable_offer_key("shopee", "https://s.shopee.com.br/abc?two=2")

    assert first == second


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-08-13T10:30:00-03:00", datetime(2026, 8, 13, 13, 30, tzinfo=UTC)),
        ("2026-08-13T13:30:00Z", datetime(2026, 8, 13, 13, 30, tzinfo=UTC)),
    ],
)
def test_parse_observed_at_normalizes_to_utc(raw: str, expected: datetime) -> None:
    assert parse_observed_at(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "2026-08-13T10:30:00", "not-a-date"])
def test_parse_observed_at_requires_valid_timezone(raw: str | None) -> None:
    with pytest.raises(CatalogImportError, match="observed-at"):
        parse_observed_at(raw)


class FakeResult:
    def __init__(self, row: tuple[object, ...] | None = None) -> None:
        self._row = row

    def fetchone(self) -> tuple[object, ...] | None:
        return self._row


class FakeCopy:
    def __init__(self) -> None:
        self.rows: list[tuple[object, ...]] = []

    def __enter__(self) -> FakeCopy:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def write_row(self, row: tuple[object, ...]) -> None:
        self.rows.append(row)


class FakeCursor:
    def __init__(self, copy: FakeCopy) -> None:
        self._copy = copy

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def copy(self, _sql: str) -> FakeCopy:
        return self._copy


class FakeConnection:
    def __init__(
        self,
        *,
        existing_count: int,
        new_count: int,
        row_count: int,
        reused: bool = False,
        stable_key_conflict: tuple[object, ...] | None = None,
    ) -> None:
        self.existing_count = existing_count
        self.new_count = new_count
        self.row_count = row_count
        self.reused = reused
        self.stable_key_conflict = stable_key_conflict
        self.import_id = UUID("11111111-1111-1111-1111-111111111111")
        self.sql: list[str] = []
        self.copy = FakeCopy()

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return FakeCursor(self.copy)

    def execute(self, sql: str, _params: object = None) -> FakeResult:
        normalized = " ".join(sql.split()).lower()
        self.sql.append(normalized)
        if "select id, status, row_count, validation_summary" in normalized:
            if self.reused:
                return FakeResult(
                    (
                        self.import_id,
                        "completed",
                        self.row_count,
                        {
                            "new_items": self.new_count,
                            "existing_items": self.existing_count,
                        },
                    )
                )
            return FakeResult(None)
        if "from offers.offer_snapshots where catalog_import_id" in normalized:
            return FakeResult((self.row_count,))
        if "insert into offers.catalog_imports" in normalized:
            return FakeResult((self.import_id,))
        if "select stage.source_row_number" in normalized:
            return FakeResult(self.stable_key_conflict)
        if normalized.startswith("select count(*) from catalog_import_stage"):
            return FakeResult((self.existing_count,))
        if "insert into offers.catalog_items" in normalized:
            return FakeResult((self.new_count,))
        if "insert into offers.offer_snapshots" in normalized:
            return FakeResult((self.row_count,))
        return FakeResult(None)


@pytest.mark.parametrize(
    ("existing_count", "new_count"),
    [(1, 0), (0, 1)],
)
def test_import_catalog_adds_snapshot_without_updating_existing_catalog(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing_count: int,
    new_count: int,
) -> None:
    path = tmp_path / "catalog.csv"
    write_catalog(path, [make_row()])
    validation = validate_catalog(path, profile="feminino", marketplace="shopee")
    connection = FakeConnection(
        existing_count=existing_count,
        new_count=new_count,
        row_count=1,
    )
    monkeypatch.setattr(catalog_import_module, "connect", lambda: connection)

    result = import_catalog(
        validation,
        observed_at=datetime(2026, 8, 13, 13, 30, tzinfo=UTC),
        confirmation=CONFIRMATION,
    )

    assert result.new_items == new_count
    assert result.existing_items == existing_count
    assert result.snapshots == 1
    assert len(connection.copy.rows) == 1
    assert any("insert into offers.offer_snapshots" in sql for sql in connection.sql)
    assert not any("update offers.catalog_items" in sql for sql in connection.sql)


def test_import_catalog_handles_mixed_batch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "catalog.csv"
    write_catalog(path, [make_row(item_id="123"), make_row(item_id="456")])
    validation = validate_catalog(path, profile="feminino", marketplace="shopee")
    connection = FakeConnection(existing_count=1, new_count=1, row_count=2)
    monkeypatch.setattr(catalog_import_module, "connect", lambda: connection)

    result = import_catalog(
        validation,
        observed_at=datetime(2026, 8, 13, 13, 30, tzinfo=UTC),
        confirmation=CONFIRMATION,
    )

    assert (result.new_items, result.existing_items, result.snapshots) == (1, 1, 2)
    assert len(connection.copy.rows) == 2


def test_import_catalog_reuses_exact_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "catalog.csv"
    write_catalog(path, [make_row()])
    validation = validate_catalog(path, profile="feminino", marketplace="shopee")
    connection = FakeConnection(
        existing_count=1,
        new_count=0,
        row_count=1,
        reused=True,
    )
    monkeypatch.setattr(catalog_import_module, "connect", lambda: connection)

    result = import_catalog(
        validation,
        observed_at=datetime(2026, 8, 13, 13, 30, tzinfo=UTC),
        confirmation=CONFIRMATION,
    )

    assert result.operation == "reused"
    assert result.snapshots == 1
    assert connection.copy.rows == []
    assert not any("insert into offers.offer_snapshots" in sql for sql in connection.sql)


def test_import_catalog_rejects_stable_key_for_another_item(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "catalog.csv"
    write_catalog(path, [make_row()])
    validation = validate_catalog(path, profile="feminino", marketplace="shopee")
    connection = FakeConnection(
        existing_count=0,
        new_count=1,
        row_count=1,
        stable_key_conflict=(2, "a" * 64, 123, 999),
    )
    monkeypatch.setattr(catalog_import_module, "connect", lambda: connection)

    with pytest.raises(CatalogImportError, match="stable key conflict"):
        import_catalog(
            validation,
            observed_at=datetime(2026, 8, 13, 13, 30, tzinfo=UTC),
            confirmation=CONFIRMATION,
        )

    assert not any("insert into offers.offer_snapshots" in sql for sql in connection.sql)
