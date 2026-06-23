from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ofertas_bot.group_profiles import GroupProfile


@dataclass(frozen=True)
class GroupCadenceResult:
    allowed: bool
    reasons: tuple[str, ...]
    next_available_at: datetime | None = None


class GroupCadencePolicy:
    def can_run_now(
        self,
        group_profile: GroupProfile,
        *,
        now: datetime,
        last_run_at: datetime | None,
    ) -> GroupCadenceResult:
        normalized_now = _as_utc(now)
        normalized_last_run_at = _as_utc(last_run_at) if last_run_at else None
        reasons: list[str] = []

        if not group_profile.active:
            reasons.append("grupo inativo")

        if normalized_last_run_at is None:
            return GroupCadenceResult(allowed=not reasons, reasons=tuple(reasons))

        next_available_at = normalized_last_run_at + timedelta(
            minutes=group_profile.min_minutes_between_posts,
        )
        if normalized_now < next_available_at:
            reasons.append("intervalo mínimo entre rodadas não atingido")
            return GroupCadenceResult(
                allowed=False,
                reasons=tuple(reasons),
                next_available_at=next_available_at,
            )

        return GroupCadenceResult(allowed=not reasons, reasons=tuple(reasons))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
