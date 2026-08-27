from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from ofertas_bot.shopee_tracking import ConversionWindow, previous_day_window


class ConversionProvider(Protocol):
    def conversion_page(
        self, start: int, end: int, scroll_id: str | None = None
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class CollectedConversionReport:
    window: ConversionWindow
    nodes: tuple[dict[str, Any], ...]
    last_page: int | None
    page_limit: int | None
    last_scroll_id: str | None


def collect_conversion_report(
    provider: ConversionProvider, now: datetime
) -> CollectedConversionReport:
    window = previous_day_window(now)
    nodes: list[dict[str, Any]] = []
    scroll_id: str | None = None
    last_page = page_limit = None
    while True:
        report = provider.conversion_page(
            window.purchase_time_start, window.purchase_time_end, scroll_id
        )
        nodes.extend(report["nodes"])
        page_info = report["pageInfo"]
        last_page = _optional_int(page_info.get("page"))
        page_limit = _optional_int(page_info.get("limit"))
        next_scroll = page_info.get("scrollId")
        if page_info.get("hasNextPage") is not True:
            return CollectedConversionReport(
                window, tuple(nodes), last_page, page_limit,
                str(next_scroll) if next_scroll is not None else scroll_id,
            )
        if not isinstance(next_scroll, str) or not next_scroll:
            raise ValueError("hasNextPage=true requires pageInfo.scrollId")
        scroll_id = next_scroll


def query_filters(window: ConversionWindow) -> dict[str, Any]:
    return {
        "timezone": "America/Sao_Paulo",
        "purchase_date": window.purchase_date.isoformat(),
        "purchaseTimeStart": window.purchase_time_start,
        "purchaseTimeEnd": window.purchase_time_end,
        "conversionStatus": "ALL", "categoryType": "ALL", "orderStatus": "ALL",
        "buyerType": "ALL", "productType": "ALL", "fraudStatus": "ALL", "device": "ALL",
    }


def _optional_int(value: Any) -> int | None:
    return None if value in (None, "") else int(value)
