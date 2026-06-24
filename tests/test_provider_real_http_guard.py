import pytest

from ofertas_bot.providers.amazon import AmazonProvider
from ofertas_bot.providers.real_http_guard import RealHttpValidationError
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.settings import Settings


def make_shopee_settings(**overrides) -> Settings:
    values = {
        "enable_real_http": True,
        "shopee_partner_id": "123456",
        "shopee_tracking_id": "tracking",
    }
    values["shopee_" + "secret_key"] = "credential"
    values.update(overrides)
    return Settings(**values)


def make_amazon_settings(**overrides) -> Settings:
    values = {
        "enable_real_http": True,
        "amazon_access_key": "access",
        "amazon_partner_tag": "partner-tag",
    }
    values["amazon_" + "secret_key"] = "credential"
    values.update(overrides)
    return Settings(**values)


def test_shopee_provider_allows_default_graphql_url(monkeypatch) -> None:
    monkeypatch.delenv("SHOPEE_GRAPHQL_URL", raising=False)
    provider = ShopeeProvider(settings=make_shopee_settings())

    provider.validate_real_http_ready()


def test_shopee_provider_blocks_placeholder_graphql_url(monkeypatch) -> None:
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://example.com")
    provider = ShopeeProvider(settings=make_shopee_settings())

    with pytest.raises(RealHttpValidationError, match="non-placeholder base URL"):
        provider.validate_real_http_ready()


def test_shopee_provider_allows_real_http_prerequisites(monkeypatch) -> None:
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://api.shopee.test/graphql")
    provider = ShopeeProvider(settings=make_shopee_settings())

    provider.validate_real_http_ready()


def test_shopee_provider_blocks_non_numeric_partner_id(monkeypatch) -> None:
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://api.shopee.test/graphql")
    provider = ShopeeProvider(settings=make_shopee_settings(shopee_partner_id="partner"))

    with pytest.raises(RealHttpValidationError, match="partner id must be numeric"):
        provider.validate_real_http_ready()


def test_shopee_provider_blocks_out_of_range_partner_id(monkeypatch) -> None:
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://api.shopee.test/graphql")
    provider = ShopeeProvider(settings=make_shopee_settings(shopee_partner_id="4294967296"))

    with pytest.raises(RealHttpValidationError, match="partner id is out of range"):
        provider.validate_real_http_ready()


def test_shopee_provider_blocks_missing_tracking_id(monkeypatch) -> None:
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://api.shopee.test/graphql")
    provider = ShopeeProvider(settings=make_shopee_settings(shopee_tracking_id=""))

    with pytest.raises(RealHttpValidationError, match="tracking id"):
        provider.validate_real_http_ready()


def test_amazon_provider_blocks_real_http_with_placeholder_base_url(monkeypatch) -> None:
    monkeypatch.delenv("AMAZON_BASE_URL", raising=False)
    provider = AmazonProvider(settings=make_amazon_settings())

    with pytest.raises(RealHttpValidationError, match="non-placeholder base URL"):
        provider.validate_real_http_ready()


def test_amazon_provider_allows_real_http_prerequisites(monkeypatch) -> None:
    monkeypatch.setenv("AMAZON_BASE_URL", "https://api.amazon.test")
    provider = AmazonProvider(settings=make_amazon_settings())

    provider.validate_real_http_ready()


def test_amazon_provider_blocks_missing_partner_tag(monkeypatch) -> None:
    monkeypatch.setenv("AMAZON_BASE_URL", "https://api.amazon.test")
    provider = AmazonProvider(settings=make_amazon_settings(amazon_partner_tag=""))

    with pytest.raises(RealHttpValidationError, match="partner tag"):
        provider.validate_real_http_ready()
