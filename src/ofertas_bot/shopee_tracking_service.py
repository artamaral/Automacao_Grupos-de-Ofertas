from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ofertas_bot.shopee_tracking import build_tracking_sub_ids


class TrackingStore(Protocol):
    def pending_plans(self, profile: str, planned_date: date) -> list: ...
    def save_ready(self, dispatch_plan_id, sub_ids, url: str) -> None: ...
    def save_failed(self, dispatch_plan_id, error: str) -> None: ...


class ShortLinkProvider(Protocol):
    def generate_short_link(self, origin_url: str, sub_ids: list[str]) -> str: ...


@dataclass(frozen=True)
class TrackingResult:
    selected: int
    ready: int
    failed: int


def generate_tracking_links(
    store: TrackingStore, provider: ShortLinkProvider, profile: str, planned_date: date,
    *, apply: bool,
) -> TrackingResult:
    plans = store.pending_plans(profile, planned_date)
    ready = failed = 0
    for plan in plans:
        sub_ids = build_tracking_sub_ids(plan)
        if not apply:
            continue
        try:
            url = provider.generate_short_link(plan.product_link, list(sub_ids))
            if not url.startswith("https://"):
                raise ValueError("shortLink must be HTTPS")
            store.save_ready(plan.dispatch_plan_id, sub_ids, url)
            ready += 1
        except Exception as exc:
            store.save_failed(plan.dispatch_plan_id, str(exc))
            failed += 1
    return TrackingResult(len(plans), ready, failed)
