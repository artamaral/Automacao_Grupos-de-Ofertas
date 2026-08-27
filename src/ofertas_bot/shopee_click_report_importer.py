from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

from ofertas_bot.shopee_tracking import dispatch_tracking_id

HEADERS = (
    "click_id", "click_time", "click_region", "referrer", "sub_id_raw",
    "tracking_channel", "tracking_profile", "tracking_dispatch_id", "tracking_item_id",
)


@dataclass(frozen=True)
class ClickEvent:
    click_id: str
    click_time: datetime
    click_region: str | None
    referrer: str | None
    sub_id_raw: str
    tracking_channel: str | None
    tracking_profile: str | None
    tracking_dispatch_id: str | None
    tracking_item_id: int | None
    dispatch_plan_id: UUID | None
    tracking_parse_status: str
    raw_row: dict[str, str]


@dataclass(frozen=True)
class PreparedClickReport:
    filename: str
    sha256: str
    events: tuple[ClickEvent, ...]


def parse_click_report(
    path: Path, lookup_plan: Callable[[UUID], dict[str, object] | None]
) -> PreparedClickReport:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Click Report must be UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text), delimiter=",")
    if tuple(reader.fieldnames or ()) != HEADERS:
        raise ValueError(f"invalid Click Report headers: expected {HEADERS}")
    events = tuple(_parse_row(row, index + 2, lookup_plan) for index, row in enumerate(reader))
    return PreparedClickReport(path.name, hashlib.sha256(raw).hexdigest(), events)


def _parse_row(
    row: dict[str, str], line: int, lookup_plan: Callable[[UUID], dict[str, object] | None]
) -> ClickEvent:
    click_id = row["click_id"].strip()
    sub_raw = row["sub_id_raw"].strip()
    if not click_id or not sub_raw:
        raise ValueError(f"line {line}: click_id and sub_id_raw are required")
    try:
        click_time = datetime.fromisoformat(row["click_time"].strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"line {line}: click_time must be ISO 8601") from exc
    if click_time.tzinfo is None:
        raise ValueError(f"line {line}: click_time requires an explicit offset")
    tracking = [row[name].strip() for name in HEADERS[5:]]
    if sub_raw == "----":
        if any(tracking):
            raise ValueError(f"line {line}: legacy row must have empty tracking columns")
        return ClickEvent(click_id, click_time, _opt(row["click_region"]), _opt(row["referrer"]),
                          sub_raw, None, None, None, None, None, "legacy_empty", dict(row))
    if any(not value for value in tracking):
        raise ValueError(f"line {line}: all four tracking columns are required")
    channel, profile, token, item_text = tracking
    if channel != "wa":
        raise ValueError(f"line {line}: tracking_channel must be wa")
    if not token.startswith("dp") or len(token) != 34:
        raise ValueError(f"line {line}: invalid tracking_dispatch_id")
    try:
        dispatch_id = UUID(hex=token[2:])
        item_id = int(item_text)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"line {line}: invalid dispatch or item id") from exc
    if token != dispatch_tracking_id(dispatch_id):
        raise ValueError(f"line {line}: tracking_dispatch_id is not normalized")
    plan = lookup_plan(dispatch_id)
    if not plan or str(plan["profile"]) != profile or int(plan["item_id"]) != item_id:
        raise ValueError(f"line {line}: tracking does not match daily_dispatch_plan")
    return ClickEvent(click_id, click_time, _opt(row["click_region"]), _opt(row["referrer"]),
                      sub_raw, channel, profile, token, item_id, dispatch_id, "resolved", dict(row))


def event_raw_json(event: ClickEvent) -> str:
    return json.dumps(event.raw_row, ensure_ascii=False, sort_keys=True)


def _opt(value: str) -> str | None:
    return value.strip() or None
