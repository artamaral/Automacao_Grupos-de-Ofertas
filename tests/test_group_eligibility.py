from ofertas_bot.group_eligibility import GroupEligibilityPolicy
from ofertas_bot.group_profiles import GroupProfile
from ofertas_bot.models import Marketplace, Offer


def make_offer(
    *,
    niche: str = "maquiagem",
    price: float = 49.9,
    url: str = "https://example.test/oferta",
) -> Offer:
    return Offer(
        marketplace=Marketplace.MOCK,
        title="Oferta",
        url=url,
        image_url=None,
        price=price,
        old_price=None,
        commission_rate=0.05,
        sales_count=10,
        rating=4.5,
        niche=niche,
        is_prime_or_free_shipping=True,
    )


def test_group_eligibility_approves_matching_offer() -> None:
    profile = GroupProfile(
        slug="maquiagem-vip",
        name="Maquiagem VIP",
        allowed_niches=("maquiagem",),
    )

    result = GroupEligibilityPolicy().validate_offer(
        offer=make_offer(),
        group_profile=profile,
    )

    assert result.approved is True
    assert result.reasons == ()


def test_group_eligibility_rejects_wrong_niche() -> None:
    profile = GroupProfile(
        slug="maquiagem-vip",
        name="Maquiagem VIP",
        allowed_niches=("maquiagem",),
    )

    result = GroupEligibilityPolicy().validate_offer(
        offer=make_offer(niche="pesca"),
        group_profile=profile,
    )

    assert result.approved is False
    assert result.reasons == ("nicho não permitido para o grupo",)


def test_group_eligibility_rejects_inactive_group() -> None:
    profile = GroupProfile(
        slug="maquiagem-vip",
        name="Maquiagem VIP",
        allowed_niches=("maquiagem",),
        active=False,
    )

    result = GroupEligibilityPolicy().validate_offer(
        offer=make_offer(),
        group_profile=profile,
    )

    assert result.approved is False
    assert "grupo inativo" in result.reasons


def test_group_eligibility_rejects_invalid_offer_data() -> None:
    profile = GroupProfile(
        slug="maquiagem-vip",
        name="Maquiagem VIP",
        allowed_niches=("maquiagem",),
    )

    result = GroupEligibilityPolicy().validate_offer(
        offer=make_offer(price=-1, url=""),
        group_profile=profile,
    )

    assert result.approved is False
    assert "preço inválido" in result.reasons
    assert "oferta sem link" in result.reasons


def test_group_eligibility_allows_unknown_price() -> None:
    profile = GroupProfile(
        slug="maquiagem-vip",
        name="Maquiagem VIP",
        allowed_niches=("maquiagem",),
    )

    result = GroupEligibilityPolicy().validate_offer(
        offer=make_offer(price=0),
        group_profile=profile,
    )

    assert result.approved is True


def test_select_eligible_offers_respects_group_limit() -> None:
    profile = GroupProfile(
        slug="maquiagem-vip",
        name="Maquiagem VIP",
        allowed_niches=("maquiagem",),
        max_offers_per_run=2,
    )
    offers = [
        make_offer(),
        make_offer(niche="pesca"),
        make_offer(),
        make_offer(),
    ]

    selected = GroupEligibilityPolicy().select_eligible_offers(
        offers=offers,
        group_profile=profile,
    )

    assert len(selected) == 2
    assert all(offer.niche == "maquiagem" for offer in selected)
