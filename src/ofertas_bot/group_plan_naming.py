from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from ofertas_bot.group_plan_validation import normalize_plan_niche


@dataclass(frozen=True)
class GroupPlanFileNames:
    json_name: str
    text_name: str


def build_group_plan_file_prefix(*, niche: str, generated_at: datetime) -> str:
    normalized_niche = normalize_plan_niche(niche)
    timestamp = _format_timestamp(generated_at)
    return f"{timestamp}-{_slugify(normalized_niche)}"


def build_group_plan_file_names(*, niche: str, generated_at: datetime) -> GroupPlanFileNames:
    prefix = build_group_plan_file_prefix(niche=niche, generated_at=generated_at)
    return GroupPlanFileNames(json_name=f"{prefix}.json", text_name=f"{prefix}.txt")


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "plano"
