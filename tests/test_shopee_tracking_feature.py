from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from ofertas_bot.shopee_click_report_importer import HEADERS, parse_click_report
from ofertas_bot.shopee_conversion_sync import collect_conversion_report, query_filters
from ofertas_bot.shopee_tracking import (
    TrackingPlan,
    build_tracking_sub_ids,
    conversion_node_key,
    dispatch_tracking_id,
    previous_day_window,
    resolve_dispatch_token,
)
from ofertas_bot.shopee_tracking_service import generate_tracking_links

PLAN_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def test_exact_tracking_sub_ids_and_origin_url() -> None:
    plan = TrackingPlan(PLAN_ID, "feminino", 18797641257, "https://shopee.com.br/product/x")
    assert dispatch_tracking_id(PLAN_ID) == "dp550e8400e29b41d4a716446655440000"
    assert build_tracking_sub_ids(plan) == (
        "wa", "feminino", "dp550e8400e29b41d4a716446655440000", "18797641257"
    )


def test_tracking_service_persists_by_dispatch_plan_id() -> None:
    plan = TrackingPlan(PLAN_ID, "feminino", 7, "https://shopee.com.br/product/1/7")

    class Store:
        saved = None
        def pending_plans(self, profile, planned_date):
            return [plan]
        def save_ready(self, dispatch_plan_id, sub_ids, url):
            self.saved = (dispatch_plan_id, sub_ids, url)
        def save_failed(self, dispatch_plan_id, error):
            raise AssertionError(error)

    class Provider:
        def generate_short_link(self, origin_url, sub_ids):
            assert origin_url == plan.product_link
            assert sub_ids == ["wa", "feminino", dispatch_tracking_id(PLAN_ID), "7"]
            return "https://s.shopee.com.br/test"

    store = Store()
    result = generate_tracking_links(
        store, Provider(), "feminino", datetime.now().date(), apply=True
    )
    assert result.ready == 1 and result.failed == 0
    assert store.saved[0] == PLAN_ID


def _write_csv(path: Path, row: str, bom: bool = False) -> None:
    content = ",".join(HEADERS) + "\n" + row + "\n"
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + content.encode())


def test_click_report_valid_and_legacy(tmp_path: Path) -> None:
    path = tmp_path / "clicks.csv"
    _write_csv(
        path,
        "c1,2026-08-27T10:00:00-03:00,BR,google,raw,wa,feminino,"
        f"{dispatch_tracking_id(PLAN_ID)},18797641257\n"
        "c2,2026-08-27T10:01:00-03:00,BR,,----,,,,",
        bom=True,
    )
    report = parse_click_report(
        path, lambda value: {"profile": "feminino", "item_id": 18797641257}
        if value == PLAN_ID else None
    )
    assert [event.tracking_parse_status for event in report.events] == ["resolved", "legacy_empty"]


@pytest.mark.parametrize(
    "header,time_value",
    [("bad", "2026-08-27T10:00:00-03:00"), (",".join(HEADERS), "2026-08-27T10:00:00")],
)
def test_click_report_rejects_invalid_contract(
    tmp_path: Path, header: str, time_value: str
) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(
        header + "\n" + f"c1,{time_value},BR,,----,,,,\n", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        parse_click_report(path, lambda value: None)


def test_previous_day_window_uses_sao_paulo() -> None:
    window = previous_day_window(datetime(2026, 8, 27, 11, tzinfo=ZoneInfo("America/Sao_Paulo")))
    assert window.purchase_date.isoformat() == "2026-08-26"
    assert window.purchase_time_start == 1787713200
    assert window.purchase_time_end == 1787799599
    assert query_filters(window)["device"] == "ALL"


def test_conversion_pagination_omits_first_scroll_and_uses_next() -> None:
    class Provider:
        calls = []
        def conversion_page(self, start, end, scroll_id=None):
            self.calls.append(scroll_id)
            if scroll_id is None:
                return {"nodes": [{"conversionId": "1"}],
                        "pageInfo": {"page": 1, "limit": 1, "hasNextPage": True,
                                     "scrollId": "next"}}
            return {"nodes": [{"conversionId": "2"}],
                    "pageInfo": {"page": 2, "limit": 1, "hasNextPage": False,
                                 "scrollId": "done"}}

    provider = Provider()
    report = collect_conversion_report(
        provider, datetime(2026, 8, 27, 11, tzinfo=ZoneInfo("America/Sao_Paulo"))
    )
    assert provider.calls == [None, "next"]
    assert len(report.nodes) == 2


def test_conversion_identity_allows_same_conversion_with_different_orders() -> None:
    first = {"conversionId": "241289038161544", "orders": [{"orderId": "A"}]}
    second = {"conversionId": "241289038161544", "orders": [{"orderId": "B"}]}
    assert conversion_node_key(first) != conversion_node_key(second)
    assert conversion_node_key(first) == conversion_node_key(first)


def test_utm_dispatch_resolution() -> None:
    assert resolve_dispatch_token(f"wa|feminino|{dispatch_tracking_id(PLAN_ID)}|7") == PLAN_ID
    assert resolve_dispatch_token("----") is None
    assert resolve_dispatch_token(
        f"{dispatch_tracking_id(PLAN_ID)} {dispatch_tracking_id(PLAN_ID)}"
    ) is None
