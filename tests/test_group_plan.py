from datetime import UTC, datetime, timedelta

from ofertas_bot.group_plan import GroupPlanBuilder, summarize_group_plans
from ofertas_bot.group_profiles import GroupProfile
from ofertas_bot.models import Marketplace, Offer


def make_offer(*, niche: str = "maquiagem", price: float = 49.9) -> Offer:
    return Offer(
        marketplace=Marketplace.MOCK,
        title="Oferta",
        url="https://example.test/oferta",
        image_url=None,
        price=price,
        old_price=None,
        commission_rate=0.05,
        sales_count=10,
        rating=4.5,
        niche=niche,
        is_prime_or_free_shipping=True,
    )


def make_profile(
    *,
    slug: str = "maquiagem-vip",
    max_offers: int = 2,
    minutes: int = 120,
) -> GroupProfile:
    return GroupProfile(
        slug=slug,
        name="Maquiagem VIP",
        allowed_niches=("maquiagem",),
        max_offers_per_run=max_offers,
        min_minutes_between_posts=minutes,
    )


def test_group_plan_selects_eligible_offers_when_cadence_allows() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    offers = [make_offer(), make_offer(niche="pesca"), make_offer()]

    plan = GroupPlanBuilder().build_plan(
        group_profile=make_profile(max_offers=1),
        offers=offers,
        now=now,
        last_run_at=None,
    )

    assert plan.allowed is True
    assert plan.group_slug == "maquiagem-vip"
    assert len(plan.selected_offers) == 1
    assert plan.selected_offers[0].niche == "maquiagem"
    assert plan.reasons == ()


def test_group_plan_blocks_when_cadence_blocks() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    last_run_at = now - timedelta(minutes=60)

    plan = GroupPlanBuilder().build_plan(
        group_profile=make_profile(minutes=120),
        offers=[make_offer()],
        now=now,
        last_run_at=last_run_at,
    )

    assert plan.allowed is False
    assert plan.selected_offers == ()
    assert plan.reasons == ("intervalo mínimo entre rodadas não atingido",)
    assert plan.next_available_at == last_run_at + timedelta(minutes=120)


def test_group_plan_blocks_when_no_offer_is_eligible() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)

    plan = GroupPlanBuilder().build_plan(
        group_profile=make_profile(),
        offers=[make_offer(niche="pesca"), make_offer(price=-1)],
        now=now,
        last_run_at=None,
    )

    assert plan.allowed is False
    assert plan.selected_offers == ()
    assert plan.reasons == ("nenhuma oferta elegível para o grupo",)


def test_group_plan_builder_builds_batch_with_individual_last_runs() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    active_profile = make_profile(slug="maquiagem-vip", minutes=120)
    blocked_profile = make_profile(slug="beleza-vip", minutes=120)

    plans = GroupPlanBuilder().build_plans(
        group_profiles=(active_profile, blocked_profile),
        offers=[make_offer()],
        now=now,
        last_runs_by_group={"beleza-vip": now - timedelta(minutes=30)},
    )

    assert len(plans) == 2
    assert plans[0].group_slug == "maquiagem-vip"
    assert plans[0].allowed is True
    assert plans[1].group_slug == "beleza-vip"
    assert plans[1].allowed is False
    assert plans[1].reasons == ("intervalo mínimo entre rodadas não atingido",)


def test_summarize_group_plans_returns_serializable_counts() -> None:
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    plans = GroupPlanBuilder().build_plans(
        group_profiles=(
            make_profile(slug="maquiagem-vip", minutes=120),
            make_profile(slug="beleza-vip", minutes=120),
        ),
        offers=[make_offer(), make_offer()],
        now=now,
        last_runs_by_group={"beleza-vip": now - timedelta(minutes=30)},
    )

    summary = summarize_group_plans(plans)

    assert summary["total_groups"] == 2
    assert summary["allowed_groups"] == 1
    assert summary["blocked_groups"] == 1
    assert summary["total_selected_offers"] == 2
    assert summary["groups"][0]["group_slug"] == "maquiagem-vip"
    assert summary["groups"][0]["selected_offer_count"] == 2
    assert summary["groups"][1]["allowed"] is False
    assert summary["groups"][1]["next_available_at"] == "2026-06-23T19:30:00+00:00"
