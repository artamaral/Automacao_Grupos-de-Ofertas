from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

BRT = ZoneInfo("America/Sao_Paulo")
DISPATCH_TOKEN_RE = re.compile(r"(?<![0-9a-f])dp([0-9a-f]{32})(?![0-9a-f])", re.IGNORECASE)


@dataclass(frozen=True)
class TrackingPlan:
    dispatch_plan_id: UUID
    profile: str
    item_id: int
    product_link: str


@dataclass(frozen=True)
class ConversionWindow:
    purchase_date: date
    purchase_time_start: int
    purchase_time_end: int


def dispatch_tracking_id(dispatch_plan_id: UUID) -> str:
    return f"dp{dispatch_plan_id.hex}"


def build_tracking_sub_ids(plan: TrackingPlan) -> tuple[str, str, str, str]:
    if not plan.profile.strip() or plan.item_id <= 0 or not plan.product_link.strip():
        raise ValueError("tracking plan requires profile, positive item_id and product_link")
    return ("wa", plan.profile, dispatch_tracking_id(plan.dispatch_plan_id), str(plan.item_id))


def resolve_dispatch_token(value: str | None) -> UUID | None:
    if not value or value.strip() == "----":
        return None
    matches = DISPATCH_TOKEN_RE.findall(value)
    if len(matches) != 1:
        return None
    return UUID(hex=matches[0])


def previous_day_window(now: datetime) -> ConversionWindow:
    local_now = now.astimezone(BRT)
    purchase_date = local_now.date() - timedelta(days=1)
    start = datetime.combine(purchase_date, time.min, BRT)
    end = datetime.combine(purchase_date, time(23, 59, 59), BRT)
    return ConversionWindow(purchase_date, int(start.timestamp()), int(end.timestamp()))


def conversion_node_key(node: dict[str, Any]) -> str:
    conversion_id = str(node.get("conversionId") or "").strip()
    if not conversion_id:
        raise ValueError("conversionId is required")
    order_ids = sorted(
        str(order.get("orderId") or "").strip()
        for order in node.get("orders") or []
        if str(order.get("orderId") or "").strip()
    )
    identity = {
        "conversion_id": conversion_id,
        "orders": order_ids,
    }
    if not order_ids:
        identity.update(
            click_time=node.get("clickTime"),
            purchase_time=node.get("purchaseTime"),
            utm_content=node.get("utmContent"),
        )
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def api_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) or str(value).isdigit():
        return datetime.fromtimestamp(int(value), tz=ZoneInfo("UTC"))
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("API timestamp must contain timezone information")
    return parsed
