from datetime import UTC, datetime, timedelta

from ofertas_bot.group_cadence import GroupCadencePolicy
from ofertas_bot.group_profiles import GroupProfile


def make_profile(*, active: bool = True, minutes: int = 120) -> GroupProfile:
    return GroupProfile(
        slug="maquiagem-vip",
        name="Maquiagem VIP",
        allowed_niches=("maquiagem",),
        min_minutes_between_posts=minutes,
        active=active,
    )


def test_cadence_allows_first_run() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)

    result = GroupCadencePolicy().can_run_now(
        make_profile(),
        now=now,
        last_run_at=None,
    )

    assert result.allowed is True
    assert result.reasons == ()
    assert result.next_available_at is None


def test_cadence_blocks_before_minimum_interval() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    last_run_at = now - timedelta(minutes=60)

    result = GroupCadencePolicy().can_run_now(
        make_profile(minutes=120),
        now=now,
        last_run_at=last_run_at,
    )

    assert result.allowed is False
    assert result.reasons == ("intervalo mínimo entre rodadas não atingido",)
    assert result.next_available_at == last_run_at + timedelta(minutes=120)


def test_cadence_allows_after_minimum_interval() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    last_run_at = now - timedelta(minutes=120)

    result = GroupCadencePolicy().can_run_now(
        make_profile(minutes=120),
        now=now,
        last_run_at=last_run_at,
    )

    assert result.allowed is True
    assert result.reasons == ()


def test_cadence_blocks_inactive_group() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)

    result = GroupCadencePolicy().can_run_now(
        make_profile(active=False),
        now=now,
        last_run_at=None,
    )

    assert result.allowed is False
    assert result.reasons == ("grupo inativo",)


def test_cadence_normalizes_naive_datetime_to_utc() -> None:
    now = datetime(2026, 6, 23, 18, 0)
    last_run_at = datetime(2026, 6, 23, 17, 0)

    result = GroupCadencePolicy().can_run_now(
        make_profile(minutes=120),
        now=now,
        last_run_at=last_run_at,
    )

    assert result.allowed is False
    assert result.next_available_at == datetime(2026, 6, 23, 19, 0, tzinfo=UTC)
