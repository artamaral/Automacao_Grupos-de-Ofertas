import pytest

from ofertas_bot.group_profiles import (
    DEFAULT_GROUP_PROFILES,
    GroupProfile,
    GroupProfileCatalog,
    GroupProfileError,
)


def test_group_profile_normalizes_fields() -> None:
    profile = GroupProfile(
        slug=" Maquiagem-VIP ",
        name=" Maquiagem VIP ",
        allowed_niches=(" Maquiagem ", " Beleza "),
    )

    assert profile.slug == "maquiagem-vip"
    assert profile.name == "Maquiagem VIP"
    assert profile.allowed_niches == ("maquiagem", "beleza")
    assert profile.allows_niche("BELEZA")


def test_group_profile_requires_niche() -> None:
    with pytest.raises(GroupProfileError, match="at least one niche"):
        GroupProfile(slug="grupo", name="Grupo", allowed_niches=())


def test_group_profile_rejects_invalid_limits() -> None:
    with pytest.raises(GroupProfileError, match="must be positive"):
        GroupProfile(
            slug="grupo",
            name="Grupo",
            allowed_niches=("casa",),
            max_offers_per_run=0,
        )

    with pytest.raises(GroupProfileError, match="cannot be negative"):
        GroupProfile(
            slug="grupo",
            name="Grupo",
            allowed_niches=("casa",),
            min_minutes_between_posts=-1,
        )


def test_catalog_rejects_duplicate_slugs() -> None:
    with pytest.raises(GroupProfileError, match="unique"):
        GroupProfileCatalog.from_iterable(
            (
                GroupProfile(slug="grupo", name="Grupo A", allowed_niches=("casa",)),
                GroupProfile(slug="grupo", name="Grupo B", allowed_niches=("beleza",)),
            )
        )


def test_catalog_filters_active_profiles_by_niche() -> None:
    catalog = GroupProfileCatalog.from_iterable(
        (
            GroupProfile(slug="ativo", name="Ativo", allowed_niches=("casa",)),
            GroupProfile(
                slug="inativo",
                name="Inativo",
                allowed_niches=("casa",),
                active=False,
            ),
        )
    )

    matches = catalog.profiles_for_niche("CASA")

    assert [profile.slug for profile in matches] == ["ativo"]


def test_default_group_profiles_have_expected_niches() -> None:
    assert DEFAULT_GROUP_PROFILES.get("maquiagem-vip") is not None
    assert DEFAULT_GROUP_PROFILES.profiles_for_niche("maquiagem")
    assert DEFAULT_GROUP_PROFILES.profiles_for_niche("casa")
    assert DEFAULT_GROUP_PROFILES.profiles_for_niche("pesca")
