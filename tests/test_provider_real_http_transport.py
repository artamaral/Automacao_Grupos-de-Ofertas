from ofertas_bot.providers.amazon import AmazonProvider
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.providers.transport import UrllibHttpTransport
from ofertas_bot.settings import Settings


def make_shopee_settings(enabled: bool) -> Settings:
    values = {
        "enable_real_http": enabled,
        "shopee_partner_id": "partner",
        "shopee_tracking_id": "tracking",
    }
    values["shopee_" + "secret_key"] = "credential"
    return Settings(**values)


def make_amazon_settings(enabled: bool) -> Settings:
    values = {
        "enable_real_http": enabled,
        "amazon_access_key": "access",
        "amazon_partner_tag": "partner-tag",
    }
    values["amazon_" + "secret_key"] = "credential"
    return Settings(**values)


def test_shopee_provider_keeps_transport_disabled_by_default() -> None:
    provider = ShopeeProvider(settings=make_shopee_settings(enabled=False))

    assert provider._get_graphql_gateway().transport is None


def test_shopee_provider_connects_real_transport_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://api.shopee.test/graphql")
    provider = ShopeeProvider(settings=make_shopee_settings(enabled=True))

    assert isinstance(provider._get_graphql_gateway().transport, UrllibHttpTransport)


def test_amazon_provider_keeps_transport_disabled_by_default() -> None:
    provider = AmazonProvider(settings=make_amazon_settings(enabled=False))

    assert provider._get_gateway().transport is None


def test_amazon_provider_connects_real_transport_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("AMAZON_BASE_URL", "https://api.amazon.test")
    provider = AmazonProvider(settings=make_amazon_settings(enabled=True))

    assert isinstance(provider._get_gateway().transport, UrllibHttpTransport)
