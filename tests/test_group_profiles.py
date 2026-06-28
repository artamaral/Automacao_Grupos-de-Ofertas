import pytest

from ofertas_bot.group_profiles import (
    DEFAULT_GROUP_PROFILES,
    GroupDestination,
    GroupProfile,
    GroupProfileCatalog,
    GroupProfileError,
    load_group_profile_catalog,
)
from ofertas_bot.models import Marketplace


def test_group_profile_normalizes_fields() -> None:
    profile = GroupProfile(
        slug=" Maquiagem-VIP ",
        name=" Maquiagem VIP ",
        allowed_niches=(" Maquiagem ", " Beleza "),
        destination_kind=" Group ",
        destination_ref=" grupo-beleza ",
        channel_adapter=" Telegram ",
        message_tone=" Direto ",
        allowed_content_types=(" Product ", " Coupon "),
    )

    assert profile.slug == "maquiagem-vip"
    assert profile.name == "Maquiagem VIP"
    assert profile.allowed_niches == ("maquiagem", "beleza")
    assert profile.destination_kind == "group"
    assert profile.destination_ref == "grupo-beleza"
    assert profile.channel_adapter == "telegram"
    assert profile.message_tone == "direto"
    assert profile.allowed_content_types == ("product", "coupon")
    assert profile.allows_niche("BELEZA")


def test_group_profile_supports_multiple_destinations() -> None:
    profile = GroupProfile(
        slug="beleza",
        name="Beleza",
        allowed_niches=("beleza",),
        destinations=(
            GroupDestination(
                destination_kind="group",
                destination_ref="grupo-beleza",
                channel_adapter="whatsapp",
                max_messages_per_run=3,
                max_messages_per_hour=10,
                min_interval_seconds=45,
                quiet_periods=("22:00-08:00",),
            ),
            GroupDestination(
                destination_kind="channel",
                destination_ref="canal-beleza",
                channel_adapter="telegram",
                max_messages_per_run=2,
                max_messages_per_hour=6,
                min_interval_seconds=60,
                quiet_periods=("21:00-07:00",),
            ),
        ),
    )

    assert len(profile.destinations) == 2
    assert profile.destination_ref == "grupo-beleza"
    assert profile.channel_adapter == "whatsapp"
    assert profile.destinations[0].max_messages_per_run == 3
    assert profile.destinations[0].max_messages_per_hour == 10
    assert profile.destinations[0].min_interval_seconds == 45
    assert profile.destinations[0].quiet_periods == ("22:00-08:00",)
    assert profile.destinations[1].channel_adapter == "telegram"


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
    assert DEFAULT_GROUP_PROFILES.get("beleza-ofertas") is not None
    assert DEFAULT_GROUP_PROFILES.profiles_for_niche("beleza")
    assert DEFAULT_GROUP_PROFILES.profiles_for_niche("mae e bebe")
    assert DEFAULT_GROUP_PROFILES.profiles_for_niche("auto e moto")


def test_default_group_profiles_expose_destination_metadata() -> None:
    profile = DEFAULT_GROUP_PROFILES.get("auto-e-moto-ofertas")

    assert profile is not None
    assert profile.destination_ref == "grupo-auto-e-moto"
    assert profile.channel_adapter == "whatsapp"
    assert profile.allows_marketplace(Marketplace.SHOPEE)
    assert profile.allows_content_type("coupon")


def test_load_group_profile_catalog_reads_config(tmp_path) -> None:
    path = tmp_path / "group_profiles.toml"
    path.write_text(
        """
[[profiles]]
slug = "teste"
name = "Grupo Teste"
allowed_niches = ["beleza"]
allowed_marketplaces = ["mock", "shopee"]
destination_kind = "group"
destination_ref = "grupo-teste"
channel_adapter = "telegram"
message_tone = "leve"
allowed_content_types = ["product", "context"]
max_offers_per_run = 2
min_minutes_between_posts = 30
active = true
""".strip(),
        encoding="utf-8",
    )

    catalog = load_group_profile_catalog(path)
    profile = catalog.get("teste")

    assert profile is not None
    assert profile.allowed_marketplaces == (Marketplace.MOCK, Marketplace.SHOPEE)
    assert profile.destination_ref == "grupo-teste"
    assert profile.channel_adapter == "telegram"
    assert profile.allowed_content_types == ("product", "context")


def test_load_group_profile_catalog_reads_multiple_destinations(tmp_path) -> None:
    path = tmp_path / "group_profiles.toml"
    path.write_text(
        """
[[profiles]]
slug = "beleza"
name = "Beleza"
allowed_niches = ["beleza"]

[[profiles.destinations]]
destination_kind = "group"
destination_ref = "grupo-beleza"
channel_adapter = "whatsapp"
max_messages_per_run = 3
max_messages_per_hour = 10
min_interval_seconds = 45
quiet_periods = ["22:00-08:00"]

[[profiles.destinations]]
destination_kind = "channel"
destination_ref = "canal-beleza"
channel_adapter = "telegram"
max_messages_per_run = 2
max_messages_per_hour = 6
min_interval_seconds = 60
quiet_periods = ["21:00-07:00"]
""".strip(),
        encoding="utf-8",
    )

    catalog = load_group_profile_catalog(path)
    profile = catalog.get("beleza")

    assert profile is not None
    assert len(profile.destinations) == 2
    assert profile.destinations[0].destination_ref == "grupo-beleza"
    assert profile.destinations[0].max_messages_per_run == 3
    assert profile.destinations[0].max_messages_per_hour == 10
    assert profile.destinations[1].destination_ref == "canal-beleza"
    assert profile.destinations[1].min_interval_seconds == 60
    assert profile.destinations[1].quiet_periods == ("21:00-07:00",)


def test_load_group_profile_catalog_reads_csv_export(tmp_path) -> None:
    path = tmp_path / "group_profiles.csv"
    path.write_text(
        "\n".join(
            [
                "profile_slug,profile_name,allowed_niches_csv,allowed_marketplaces_csv,message_tone,allowed_content_types_csv,max_offers_per_run,min_minutes_between_posts,profile_active,destination_kind,destination_ref,channel_adapter,destination_active,max_messages_per_run,max_messages_per_hour,min_interval_seconds,quiet_periods_csv",
                "beleza-ofertas,Beleza Ofertas,beleza|feminino,mock|shopee,direto,product|coupon|context,3,120,true,group,grupo-beleza,whatsapp,true,3,10,45,22:00-08:00",
                "beleza-ofertas,Beleza Ofertas,beleza|feminino,mock|shopee,direto,product|coupon|context,3,120,true,channel,canal-beleza,telegram,true,2,6,60,21:00-07:00",
            ]
        ),
        encoding="utf-8",
    )

    catalog = load_group_profile_catalog(path)
    profile = catalog.get("beleza-ofertas")

    assert profile is not None
    assert profile.allowed_marketplaces == (Marketplace.MOCK, Marketplace.SHOPEE)
    assert len(profile.destinations) == 2
    assert profile.destinations[0].destination_ref == "grupo-beleza"
    assert profile.destinations[1].destination_ref == "canal-beleza"
